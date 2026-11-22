"""Carga do PNCP: contratos por CNPJ monitorado e contratações por UF + modalidade. Retomável."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from rastro.conectores import pncp
from rastro.db.conexao import transacao
from rastro.db.repositorio import upsert
from rastro.jobs.execucao import Execucao
from rastro.log import log

FRACAO_MINIMA_VALOR = Decimal("0.10")  # contrato abaixo de 10% do menor repasse nunca passa no pré-filtro
TRABALHADORES = 5  # páginas de 500 levam ~13 s: o limite real é a latência, não as 30 req/min

SQL_MONITORADOS = """
WITH pagos AS (
    SELECT id_plano_acao, min(data_pagamento) AS primeiro_pagamento FROM pagamento
    WHERE id_plano_acao IS NOT NULL GROUP BY id_plano_acao
), planos AS (
    SELECT p.id_plano_acao, p.cnpj_beneficiario, p.uf_beneficiario, pg.primeiro_pagamento,
           coalesce(p.valor_custeio, 0) + coalesce(p.valor_investimento, 0) AS valor
    FROM plano_acao p LEFT JOIN pagos pg USING (id_plano_acao)
    WHERE p.ano_plano_acao >= :ano AND (:todas OR p.uf_beneficiario = ANY(:ufs))
), alvos AS (
    SELECT cnpj_beneficiario AS cnpj, uf_beneficiario AS uf, valor, primeiro_pagamento FROM planos
    UNION ALL
    SELECT e.cnpj_executor, p.uf_beneficiario,
           coalesce(nullif(coalesce(e.valor_custeio, 0) + coalesce(e.valor_investimento, 0), 0), p.valor),
           p.primeiro_pagamento
    FROM executor e JOIN planos p USING (id_plano_acao)
)
SELECT cnpj, min(uf) AS uf, min(nullif(valor, 0)) AS menor_valor, min(primeiro_pagamento) AS primeiro_pagamento
FROM alvos WHERE cnpj IS NOT NULL GROUP BY cnpj ORDER BY min(uf), cnpj
"""

TOLERANCIA_DIAS = 30


def inicio_da_busca(desde: date, primeiro_pagamento: date | None) -> date | None:
    """Evidência só conta a partir do 1º pagamento − 30 dias; sem pagamento, não há o que buscar."""
    if primeiro_pagamento is None:
        return None
    return max(desde, primeiro_pagamento - timedelta(days=TOLERANCIA_DIAS))


def cnpjs_monitorados(desde: date, ufs: list[str] | None = None) -> list[Any]:
    params = {"ano": desde.year, "todas": not ufs, "ufs": [u.upper() for u in (ufs or [])]}
    with transacao() as conn:
        return conn.execute(text(SQL_MONITORADOS), params).all()


def valor_relevante(valor: Decimal | None, menor_repasse: Decimal | None) -> bool:
    if valor is None or not menor_repasse:
        return True
    return valor >= menor_repasse * FRACAO_MINIMA_VALOR


def _gravar(evidencias: list[dict[str, Any]]) -> int:
    unicas = {(e["fonte"], e["id_externo"]): e for e in evidencias if e["id_externo"]}
    if not unicas:
        return 0
    with transacao() as conn:
        return upsert(conn, "evidencia", unicas.values(), ("fonte", "id_externo"))


def carregar_contratos(desde: date, ate: date | None = None, ufs: list[str] | None = None) -> dict[str, Any]:
    ate = ate or date.today()
    tipo = "carga_inicial:pncp_contratos" + (f":{','.join(sorted(ufs))}" if ufs else "")
    execucao = Execucao(tipo)
    feitos: set[str] = set(execucao.progresso.get("feitos", []))
    alvos = [
        a
        for a in cnpjs_monitorados(desde, ufs)
        if a.cnpj not in feitos and inicio_da_busca(desde, a.primeiro_pagamento) is not None
    ]
    cli = pncp.cliente()
    trava = threading.Lock()
    totais = {"gravados": execucao.progresso.get("gravados", 0), "descartados_valor": 0, "erros": 0}
    log("pncp", "contratos:inicio", cnpjs=len(alvos), ja_feitos=len(feitos))

    def processar(alvo: Any) -> tuple[str, int, int]:
        gravados = descartados = 0
        for pagina in pncp.contratos(cli, alvo.cnpj, inicio_da_busca(desde, alvo.primeiro_pagamento), ate):
            evid = [pncp.evidencia_de_contrato(r) for r in pagina]
            relevantes = [e for e in evid if valor_relevante(e["valor"], alvo.menor_valor)]
            descartados += len(evid) - len(relevantes)
            gravados += _gravar(relevantes)
        return alvo.cnpj, gravados, descartados

    try:
        with ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
            futuros = {pool.submit(processar, a): a for a in alvos}
            for i, futuro in enumerate(as_completed(futuros), 1):
                try:
                    cnpj, gravados, descartados = futuro.result()
                except Exception as exc:  # um CNPJ com erro não derruba a carga; fica para a próxima execução
                    totais["erros"] += 1
                    log("pncp", "contratos:erro", cnpj=futuros[futuro].cnpj, erro=repr(exc)[:300])
                    continue
                with transacao() as conn:
                    conn.execute(
                        text(
                            "INSERT INTO cobertura_pncp (cnpj, contratos_encontrados, contratos_gravados)"
                            " VALUES (:c, :e, :g) ON CONFLICT (cnpj) DO UPDATE SET"
                            " contratos_encontrados = EXCLUDED.contratos_encontrados,"
                            " contratos_gravados = EXCLUDED.contratos_gravados, verificado_em = now()"
                        ),
                        {"c": cnpj, "e": gravados + descartados, "g": gravados},
                    )
                with trava:
                    feitos.add(cnpj)
                    totais["gravados"] += gravados
                    totais["descartados_valor"] += descartados
                    if i % 5 == 0 or i == len(alvos):
                        execucao.salvar(feitos=sorted(feitos), gravados=totais["gravados"])
                        log(
                            "pncp",
                            "contratos:progresso",
                            feitos=len(feitos),
                            total=len(alvos) + len(feitos) - i,
                            **totais,
                        )
        execucao.salvar(feitos=sorted(feitos), gravados=totais["gravados"])
        resumo = {"cnpjs": len(feitos), **totais}
        execucao.concluir(resumo, status="concluido" if not totais["erros"] else "erro")
        log("pncp", "contratos:concluido", **resumo)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()


def carregar_contratacoes(
    desde: date, ate: date | None = None, ufs: list[str] | None = None, modalidades: list[int] | None = None
) -> dict[str, Any]:
    """Varre /contratacoes/publicacao por UF + modalidade (janelas mensais); guarda só CNPJs monitorados."""
    ate = ate or date.today()
    tipo = "carga_inicial:pncp_contratacoes" + (f":{','.join(sorted(ufs))}" if ufs else "")
    execucao = Execucao(tipo)
    feitos: set[str] = set(execucao.progresso.get("feitos", []))
    monitorados = {a.cnpj: a.menor_valor for a in cnpjs_monitorados(desde, None)}
    lista_ufs = ufs or sorted({a.uf for a in cnpjs_monitorados(desde, None) if a.uf})
    tarefas = [
        (uf, m, ini, fim)
        for uf in lista_ufs
        for m in (modalidades or sorted(pncp.MODALIDADES))
        for ini, fim in pncp.janelas_mensais(desde, ate)
        if f"{uf}:{m}:{ini:%Y%m}" not in feitos
    ]
    cli = pncp.cliente()
    totais = {"gravados": execucao.progresso.get("gravados", 0), "lidos": 0, "erros": 0}
    trava = threading.Lock()
    log("pncp", "contratacoes:inicio", tarefas=len(tarefas), ja_feitas=len(feitos))

    def processar(tarefa: tuple) -> tuple[str, int, int]:
        uf, m, ini, fim = tarefa
        lidos = gravados = 0
        for pagina in pncp.contratacoes(cli, ini, fim, m, uf=uf):
            lidos += len(pagina)
            evid = [pncp.evidencia_de_contratacao(r) for r in pagina]
            evid = [e for e in evid if e["cnpj_orgao"] in monitorados]
            evid = [e for e in evid if valor_relevante(e["valor"], monitorados[e["cnpj_orgao"]])]
            gravados += _gravar(evid)
        return f"{uf}:{m}:{ini:%Y%m}", lidos, gravados

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = {pool.submit(processar, t): t for t in tarefas}
            for i, futuro in enumerate(as_completed(futuros), 1):
                try:
                    chave, lidos, gravados = futuro.result()
                except Exception as exc:
                    totais["erros"] += 1
                    log("pncp", "contratacoes:erro", tarefa=str(futuros[futuro][:3]), erro=repr(exc)[:300])
                    continue
                with trava:
                    feitos.add(chave)
                    totais["lidos"] += lidos
                    totais["gravados"] += gravados
                    if i % 20 == 0 or i == len(tarefas):
                        execucao.salvar(feitos=sorted(feitos), gravados=totais["gravados"])
                        log(
                            "pncp",
                            "contratacoes:progresso",
                            feitas=len(feitos),
                            restantes=len(tarefas) - i,
                            **totais,
                        )
        execucao.salvar(feitos=sorted(feitos), gravados=totais["gravados"])
        resumo = {"tarefas": len(feitos), **totais}
        execucao.concluir(resumo, status="concluido" if not totais["erros"] else "erro")
        log("pncp", "contratacoes:concluido", **resumo)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()


def atualizar_recentes(dias: int = 14, ate: date | None = None) -> dict[str, Any]:
    """Atualização semanal: varre o PNCP nacional dos últimos `dias` (sem filtro de CNPJ na API, que é bem mais
    barato que consultar CNPJ por CNPJ) e guarda só contratos e contratações dos CNPJs monitorados."""
    ate = ate or date.today()
    inicio = ate - timedelta(days=dias)
    monitorados = {a.cnpj: a.menor_valor for a in cnpjs_monitorados(date(2024, 1, 1), None)}
    cli = pncp.cliente()
    totais = {"contratos_lidos": 0, "contratos_gravados": 0, "contratacoes_lidas": 0, "contratacoes_gravadas": 0}
    cnpjs_com_novidade: set[str] = set()

    def filtrar(evid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            e
            for e in evid
            if e["cnpj_orgao"] in monitorados and valor_relevante(e["valor"], monitorados[e["cnpj_orgao"]])
        ]

    try:
        params = {"dataInicial": inicio.strftime("%Y%m%d"), "dataFinal": ate.strftime("%Y%m%d")}
        for pagina in pncp._paginar(cli, "/v1/contratos", {**params, "tamanhoPagina": pncp.TAMANHO_CONTRATOS}):
            totais["contratos_lidos"] += len(pagina)
            evid = filtrar([pncp.evidencia_de_contrato(r) for r in pagina])
            totais["contratos_gravados"] += _gravar(evid)
            cnpjs_com_novidade |= {e["cnpj_orgao"] for e in evid}
        for modalidade in sorted(pncp.MODALIDADES):
            for pagina in pncp.contratacoes(cli, inicio, ate, modalidade):
                totais["contratacoes_lidas"] += len(pagina)
                evid = filtrar([pncp.evidencia_de_contratacao(r) for r in pagina])
                totais["contratacoes_gravadas"] += _gravar(evid)
                cnpjs_com_novidade |= {e["cnpj_orgao"] for e in evid}
        if cnpjs_com_novidade:
            with transacao() as conn:
                # Só atualiza CNPJs que já tiveram a consulta completa: 14 dias não bastam para dizer
                # que o ente foi verificado no PNCP (isso marcaria vermelho/azul indevidos).
                conn.execute(
                    text(
                        "UPDATE cobertura_pncp SET contratos_encontrados = greatest(contratos_encontrados, 1),"
                        " verificado_em = now() WHERE cnpj = ANY(:c)"
                    ),
                    {"c": sorted(cnpjs_com_novidade)},
                )
        log("pncp", "recentes:concluido", dias=dias, cnpjs_com_novidade=len(cnpjs_com_novidade), **totais)
        return {**totais, "cnpjs_com_novidade": len(cnpjs_com_novidade)}
    finally:
        cli.fechar()
