"""Processamento em lote: pré-filtro → IA → regras → semáforo, gravando `correspondencia` e `avaliacao`.

Uso: python -m rastro.motor.processar [--ufs RN,PB] [--forcar]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from rastro.config import config
from rastro.db.conexao import transacao
from rastro.jobs.execucao import Execucao
from rastro.log import cronometro
from rastro.motor import contabil, ia, semaforo
from rastro.motor.pre_filtro import Evidencia, Similaridade, selecionar_candidatos
from rastro.motor.regras import Correspondencia, DadosEmenda, Relatorio

PARALELISMO_IA = 8  # chamadas simultâneas à IA (cada uma com sua conexão ao banco para o cache)
VERSAO_MOTOR = "10"  # 2: similaridade palavras + caracteres; fonte TCE. 3: faixa "em revisão"
# 6: relatório de gestão final como execução declarada (amarelo) e alerta A8. 7: "em revisão" passa a ser laranja
# 8: vermelho só com sinal contrário (SICONFI sem empenho, A9; ou relatório final < 70%); sem documento → azul;
#    execução contábil (SICONFI) e relatórios parciais entram como execução declarada (amarelo)
# 9: SICONFI soma o empenho inscrito em restos a pagar (matriz de dezembro) e só julga ente que orça na fonte 706
# 10: pré-empenho (6.2.2.1.2.02) conta como execução em andamento (cinza); bloqueio de crédito não conta

SQL_PLANOS = """
SELECT p.id_plano_acao, p.uf_beneficiario AS uf, p.emenda_numero, p.cnpj_beneficiario,
       p.valor_custeio, p.valor_investimento,
       p.objeto_declarado, en.codigo_ibge, en.esfera, en.populacao, en.obrigado_pncp, en.coberto_querido_diario,
       en.coberto_tce,
       (SELECT min(data_pagamento) FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) AS primeiro_pagamento,
       (SELECT sum(valor) FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) AS repassado,
       (SELECT array_agg(DISTINCT e.cnpj_executor) FROM executor e
         WHERE e.id_plano_acao = p.id_plano_acao AND e.cnpj_executor IS NOT NULL) AS executores,
       (SELECT string_agg(e.objeto, ' ') FROM executor e WHERE e.id_plano_acao = p.id_plano_acao) AS objeto_executor,
       (SELECT string_agg(m.descricao, ' ') FROM meta m WHERE m.id_plano_acao = p.id_plano_acao) AS metas,
       (SELECT json_agg(json_build_array(r.tipo, r.situacao, r.valor_executado, r.valor_pendente))
         FROM relatorio_gestao r
         WHERE r.id_plano_acao = p.id_plano_acao) AS relatorios,
       a.hash_entrada AS hash_anterior
FROM plano_acao p
LEFT JOIN ente en ON en.cnpj = p.cnpj_beneficiario
LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao
WHERE p.ano_plano_acao >= :ano AND p.uf_beneficiario = :uf
  AND (:todos OR p.id_plano_acao = ANY(:ids))
"""

SQL_EVIDENCIAS = """
SELECT ev.id, ev.fonte::text AS fonte, ev.cnpj_orgao, ev.data_publicacao, ev.objeto, ev.valor, ev.tipo_ato,
       coalesce(ev.modalidade, c.modalidade) AS modalidade, ev.url, ev.trecho, ev.coletado_em
FROM evidencia ev
LEFT JOIN evidencia c ON c.fonte = 'pncp_contratacao' AND c.id_externo = ev.numero_controle_compra
WHERE ev.cnpj_orgao = ANY(:cnpjs)
"""


def _relatorio(r: list) -> Relatorio:
    """[tipo, situação, valor_executado, valor_pendente] vindo do json_agg → Relatorio com Decimal."""
    tipo, situacao, *valores = list(r) + [None, None]
    executado, pendente = (None if v is None else Decimal(str(v)) for v in valores[:2])
    return Relatorio(tipo, situacao, executado, pendente)


def texto_da_emenda(p: Any) -> str:
    partes = [p.objeto_declarado, p.objeto_executor, p.metas]
    return " ".join(x.strip() for x in partes if x and x.strip())


def _hash(p: Any, candidatos: list, tem_pncp: Any, contabil: Any = None) -> str:
    base = {
        "v": VERSAO_MOTOR,
        "ia": ia.ia_disponivel(),
        "pag": [str(p.primeiro_pagamento), str(p.repassado)],
        "obj": texto_da_emenda(p),
        "cand": [(c.evidencia.id, str(c.evidencia.valor), c.evidencia.tipo_ato) for c in candidatos],
        "rel": p.relatorios,
        "contabil": contabil.resumo() if contabil else None,
        "cob": [p.codigo_ibge, p.populacao, p.obrigado_pncp, p.coberto_querido_diario, p.coberto_tce, tem_pncp],
        "hoje_semana": date.today().isocalendar()[:2],  # reavalia o prazo de 180 dias ao menos 1x por semana
    }
    return hashlib.sha256(json.dumps(base, default=str, sort_keys=True).encode()).hexdigest()


def processar_uf(uf: str, somente: set[int] | None = None, forcar: bool = False) -> dict[str, int]:
    cfg = config()
    ano = date.fromisoformat(cfg.data_inicio).year
    params = {"ano": ano, "uf": uf, "todos": somente is None, "ids": list(somente or [])}
    with transacao() as conn:
        planos = conn.execute(text(SQL_PLANOS), params).all()
        cnpjs = sorted({c for p in planos for c in [p.cnpj_beneficiario, *(p.executores or [])] if c})
        evidencias = conn.execute(text(SQL_EVIDENCIAS), {"cnpjs": cnpjs}).all()
        contabeis = contabil.carregar(
            conn, sorted({p.codigo_ibge for p in planos if p.codigo_ibge}), cfg.prazo_sem_evidencia_dias
        )
        verificados = {
            r[0] for r in conn.execute(text("SELECT cnpj FROM cobertura_pncp WHERE cnpj = ANY(:c)"), {"c": cnpjs})
        }
        com_pncp = {
            r[0] for r in conn.execute(
                text("SELECT cnpj FROM cobertura_pncp WHERE cnpj = ANY(:c) AND contratos_encontrados > 0"
                     " UNION SELECT DISTINCT cnpj_orgao FROM evidencia WHERE cnpj_orgao = ANY(:c)"
                     " AND fonte IN ('pncp_contrato', 'pncp_contratacao')"),
                {"c": cnpjs},
            )
        }  # fmt: skip
    por_cnpj: dict[str, list[Evidencia]] = defaultdict(list)
    extras: dict[int, Any] = {}
    for r in evidencias:
        por_cnpj[r.cnpj_orgao].append(
            Evidencia(
                r.id,
                r.fonte,
                r.cnpj_orgao,
                r.data_publicacao,
                r.objeto,
                r.valor,
                r.tipo_ato,
                r.modalidade,
                r.url,
            )
        )
        extras[r.id] = r
    similaridade = Similaridade([texto_da_emenda(p) for p in planos] + [r.objeto or "" for r in evidencias[:200_000]])
    contagem: dict[str, int] = defaultdict(int)
    hoje = date.today()
    pendentes = []
    for p in planos:
        cnpjs_plano = {c for c in [p.cnpj_beneficiario, *(p.executores or [])] if c}
        texto = texto_da_emenda(p)
        candidatas = [e for c in cnpjs_plano for e in por_cnpj.get(c, [])]
        repassado = Decimal(p.repassado) if p.repassado is not None else None
        cands = selecionar_candidatos(
            texto, candidatas, cnpjs_plano, p.primeiro_pagamento, repassado, similaridade, numero_emenda=p.emenda_numero
        )
        tem_pncp = bool(cnpjs_plano & com_pncp)
        pncp_verificado = bool(cnpjs_plano & verificados)
        chave = _hash(p, cands, (tem_pncp, pncp_verificado), contabeis.get(p.codigo_ibge))
        if not forcar and chave == p.hash_anterior:
            contagem["sem_mudanca"] += 1
            continue
        pendentes.append((p, texto, repassado, cands, tem_pncp, pncp_verificado, chave))

    # Avaliação dos candidatos (IA ou heurística) em paralelo; cada tarefa usa sua própria conexão.
    def avaliar(tarefa):
        texto, ev, sim, repassado = tarefa
        with transacao() as conn_ia:
            return ia.avaliar_correspondencia(texto, dict(ev._mapping), sim, repassado, conn_ia)

    tarefas = [
        ((p.id_plano_acao, c.evidencia.id), (texto, extras[c.evidencia.id], c.similaridade, repassado))
        for p, texto, repassado, cands, *_ in pendentes
        for c in cands
    ]
    with ThreadPoolExecutor(max_workers=PARALELISMO_IA if ia.ia_disponivel() else 1) as pool:
        avaliacoes = dict(zip([t[0] for t in tarefas], pool.map(avaliar, [t[1] for t in tarefas]), strict=True))

    for p, texto, repassado, cands, tem_pncp, pncp_verificado, chave in pendentes:
        with transacao() as conn:
            correspondencias = []
            conn.execute(text("DELETE FROM correspondencia WHERE id_plano_acao = :id"), {"id": p.id_plano_acao})
            for c in cands:
                resposta, metodo = avaliacoes[(p.id_plano_acao, c.evidencia.id)]
                contagem[f"metodo_{metodo}"] += 1
                conn.execute(
                    text(
                        "INSERT INTO correspondencia (id_plano_acao, id_evidencia, score_pre_filtro, compativel,"
                        " confianca, resposta_ia, metodo) VALUES (:p, :e, :s, :c, :conf, CAST(:r AS jsonb), :m)"
                    ),
                    {
                        "p": p.id_plano_acao,
                        "e": c.evidencia.id,
                        "s": c.similaridade,
                        "c": resposta.compativel,
                        "conf": resposta.confianca,
                        "r": resposta.model_dump_json(),
                        "m": metodo,
                    },
                )
                correspondencias.append(
                    Correspondencia(
                        id_evidencia=c.evidencia.id,
                        fonte=c.evidencia.fonte,
                        tipo_ato=(resposta.tipo_ato or c.evidencia.tipo_ato)
                        if c.evidencia.fonte == "querido_diario"
                        else c.evidencia.tipo_ato,
                        modalidade=c.evidencia.modalidade,
                        valor=c.evidencia.valor
                        if c.evidencia.valor is not None
                        else (Decimal(str(resposta.valor_extraido)) if resposta.valor_extraido else None),
                        compativel=resposta.compativel,
                        confianca=resposta.confianca,
                        url=c.evidencia.url,
                        objeto=c.evidencia.objeto,
                        justificativa=resposta.justificativa,
                    )
                )
            generico, _ = ia.avaliar_genericidade(p.objeto_declarado, conn)
            dados = DadosEmenda(
                id_plano_acao=p.id_plano_acao,
                hoje=hoje,
                valor_custeio=p.valor_custeio,
                valor_investimento=p.valor_investimento,
                valor_repassado=repassado,
                primeiro_pagamento=p.primeiro_pagamento,
                codigo_ibge=p.codigo_ibge,
                esfera=p.esfera,
                populacao=p.populacao,
                obrigado_pncp=p.obrigado_pncp,
                coberto_querido_diario=bool(p.coberto_querido_diario),
                coberto_tce=p.coberto_tce,
                tem_registro_pncp=tem_pncp,
                pncp_verificado=pncp_verificado,
                objeto=texto,
                plano_generico=generico.generico and generico.confianca >= ia.CONFIANCA_MINIMA,
                relatorios=[_relatorio(r) for r in (p.relatorios or [])],
                correspondencias=correspondencias,
                contabil=contabeis.get(p.codigo_ibge),
                prazo_dias=cfg.prazo_sem_evidencia_dias,
                limite_populacao=cfg.limite_populacao_pequeno,
            )
            status, alertas, justificativa = semaforo.avaliar(dados)
            detalhes = {
                "fontes_que_cobrem": dados.fontes_que_cobrem,
                "dias_desde_pagamento": dados.dias_desde_pagamento,
                "candidatos": len(cands),
                "evidencias_validas": len(dados.evidencias_validas),
                "plano_generico": dados.plano_generico,
                "contabil": dados.contabil.resumo() if dados.contabil else None,
            }
            conn.execute(
                text(
                    "INSERT INTO avaliacao (id_plano_acao, status, alertas, justificativa, hash_entrada, detalhes,"
                    " avaliado_em) VALUES (:p, :s, :a, :j, :h, CAST(:d AS jsonb), now())"
                    " ON CONFLICT (id_plano_acao) DO UPDATE SET status = EXCLUDED.status, alertas = EXCLUDED.alertas,"
                    " justificativa = EXCLUDED.justificativa, hash_entrada = EXCLUDED.hash_entrada,"
                    " detalhes = EXCLUDED.detalhes, avaliado_em = now()"
                ),
                {
                    "p": p.id_plano_acao,
                    "s": status,
                    "a": alertas,
                    "j": justificativa,
                    "h": chave,
                    "d": json.dumps(detalhes, default=str),
                },
            )
        contagem[status] += 1
    return dict(contagem)


def ufs_com_planos() -> list[str]:
    with transacao() as conn:
        return [r[0] for r in conn.execute(text("SELECT DISTINCT uf_beneficiario FROM plano_acao ORDER BY 1")) if r[0]]


def processar(ufs: list[str] | None = None, somente: set[int] | None = None, forcar: bool = False) -> dict[str, Any]:
    execucao = Execucao("motor:processar", retomar=False)
    resumo: dict[str, Any] = {}
    try:
        for uf in ufs or ufs_com_planos():
            with cronometro("motor", "processar_uf", uf=uf) as info:
                resultado = processar_uf(uf, somente, forcar)
                info["quantidade"] = sum(v for k, v in resultado.items() if k in semaforo.STATUS)
                info.update(resultado)
            resumo[uf] = resultado
            execucao.salvar(**{uf: resultado})
        execucao.concluir(resumo)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise


def distribuicao_por_uf() -> list[Any]:
    with transacao() as conn:
        return conn.execute(
            text(
                "SELECT p.uf_beneficiario AS uf, a.status::text AS status, count(*) AS n FROM avaliacao a"
                " JOIN plano_acao p USING (id_plano_acao) GROUP BY 1, 2 ORDER BY 1, 2"
            )
        ).all()


def main() -> None:
    parser = argparse.ArgumentParser(description="Processa o motor de correspondência e o semáforo")
    parser.add_argument("--ufs", default="")
    parser.add_argument("--forcar", action="store_true")
    args = parser.parse_args()
    ufs = [u.strip().upper() for u in args.ufs.split(",") if u.strip()] or None
    processar(ufs, forcar=args.forcar)


if __name__ == "__main__":
    main()
