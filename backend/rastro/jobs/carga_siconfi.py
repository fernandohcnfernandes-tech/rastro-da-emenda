"""Carga da execução contábil das transferências especiais (MSC do SICONFI, fonte 706) por ente e ano.

Anos encerrados usam a matriz de dezembro; o ano corrente usa o mês mais recente publicado. Só entes que receberam
emenda Pix. Idempotente: um par (ente, ano) já gravado com o mesmo mês não é consultado de novo.

    python -m rastro.jobs.carga_inicial --fonte siconfi
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any

from sqlalchemy import text

from rastro.conectores import siconfi
from rastro.db.conexao import transacao
from rastro.jobs.execucao import Execucao
from rastro.log import log

ANO_INICIAL = 2024  # primeiro ano com pagamento de emenda Pix no banco
TRABALHADORES = 3
ENTE_SONDA = "35"  # estado de SP: entrega a matriz cedo; serve para descobrir o mês mais recente publicado

SQL_ENTES = """
SELECT DISTINCT en.codigo_ibge, en.esfera
FROM ente en JOIN plano_acao p ON p.cnpj_beneficiario = en.cnpj
WHERE en.codigo_ibge IS NOT NULL AND EXISTS (SELECT 1 FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao)
ORDER BY 1
"""

COLUNAS = (
    "receita_1706 receita_2706 dotacao_1706 dotacao_2706 empenhado_1706 empenhado_2706"
    " liquidado_1706 liquidado_2706 pago_1706 pago_2706 rp_pago"
).split()


def mes_mais_recente(cli: Any, ano: int, hoje: date) -> int:
    if ano < hoje.year:
        return 12
    for mes in range(hoje.month - 1, 0, -1):
        if siconfi.msc(cli, ENTE_SONDA, ano, mes):
            return mes
    return 0


def _gravar(codigo: str, ano: int, mes: int, totais: dict[str, Any] | None) -> None:
    valores = {c: (totais or {}).get(c, 0) for c in COLUNAS}
    with transacao() as conn:
        conn.execute(
            text(
                f"INSERT INTO execucao_contabil (codigo_ibge, ano, mes, sem_dados, {', '.join(COLUNAS)},"
                " pago_por_funcao, coletado_em) VALUES (:codigo, :ano, :mes, :sem, "
                + ", ".join(":" + c for c in COLUNAS)
                + ","
                " CAST(:funcao AS jsonb), now()) ON CONFLICT (codigo_ibge, ano) DO UPDATE SET mes = EXCLUDED.mes,"
                " sem_dados = EXCLUDED.sem_dados, "
                + ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUNAS)
                + ", pago_por_funcao = EXCLUDED.pago_por_funcao, coletado_em = now()"
            ),
            {
                "codigo": codigo,
                "ano": ano,
                "mes": mes,
                "sem": totais is None,
                "funcao": json.dumps((totais or {}).get("pago_por_funcao") or {}),
                **valores,
            },
        )


def carregar(anos: list[int] | None = None, hoje: date | None = None) -> dict[str, Any]:
    hoje = hoje or date.today()
    anos = anos or list(range(ANO_INICIAL, hoje.year + 1))
    cli = siconfi.cliente()
    execucao = Execucao("siconfi:msc", retomar=False)
    try:
        meses = {ano: mes_mais_recente(cli, ano, hoje) for ano in anos}
        with transacao() as conn:
            entes = conn.execute(text(SQL_ENTES)).all()
            feitos = {
                (r.codigo_ibge, r.ano): (r.mes, r.sem_dados)
                for r in conn.execute(text("SELECT codigo_ibge, ano, mes, sem_dados FROM execucao_contabil"))
            }
        tarefas = []
        for e in entes:
            for ano in anos:
                if not meses[ano]:
                    continue
                anterior = feitos.get((e.codigo_ibge, ano))
                # refaz se o mês publicado avançou ou se a matriz ainda não tinha sido entregue
                if anterior and anterior[0] >= meses[ano] and not anterior[1]:
                    continue
                tarefas.append((e.codigo_ibge, e.esfera, ano))
        log("siconfi", "msc:inicio", tarefas=len(tarefas), meses=meses)
        totais = {"gravados": 0, "sem_dados": 0, "erros": 0}
        trava = threading.Lock()

        def processar(tarefa: tuple) -> bool:
            codigo, esfera, ano = tarefa
            ente = siconfi.id_ente(codigo, esfera)
            # ano corrente: entes atrasados entregam a matriz com 1 ou 2 meses de defasagem
            for mes in [meses[ano]] if ano < hoje.year else range(meses[ano], max(meses[ano] - 3, 0), -1):
                linhas = siconfi.msc(cli, ente, ano, mes)
                if linhas:
                    _gravar(codigo, ano, mes, siconfi.agregar(linhas))
                    return True
            _gravar(codigo, ano, meses[ano], None)
            return False

        with ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
            futuros = {pool.submit(processar, t): t for t in tarefas}
            for i, futuro in enumerate(as_completed(futuros), 1):
                with trava:
                    try:
                        totais["gravados" if futuro.result() else "sem_dados"] += 1
                    except Exception as exc:  # um ente com erro fica para a próxima execução
                        totais["erros"] += 1
                        log("siconfi", "msc:erro", tarefa=str(futuros[futuro]), erro=repr(exc)[:300])
                    if i % 200 == 0 or i == len(tarefas):
                        log("siconfi", "msc:progresso", feitas=i, total=len(tarefas), **totais)
        resumo = {"tarefas": len(tarefas), "meses": meses, **totais}
        execucao.concluir(resumo, status="concluido" if not totais["erros"] else "erro")
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()
