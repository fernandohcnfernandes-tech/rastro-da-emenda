"""Carga do Transferegov: plano de ação (ano ≥ desde) → entes → tabelas filhas. Idempotente e retomável."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text

from rastro.conectores import transferegov as tg
from rastro.conectores.base import ClienteHttp
from rastro.db.conexao import transacao
from rastro.db.repositorio import upsert
from rastro.jobs.execucao import Execucao
from rastro.log import cronometro, log

# Até este número de pais, busca as filhas por filtro `in.(...)` em lotes; acima, varre a tabela inteira.
LIMITE_BUSCA_POR_LOTE = 3000
TAMANHO_LOTE_IN = 150

_FILTRO_PLANO = " WHERE p.ano_plano_acao >= :ano AND (:todas OR p.uf_beneficiario = ANY(:ufs))"
PAIS: dict[str, str] = {
    "id_plano_acao": "SELECT p.id_plano_acao FROM plano_acao p" + _FILTRO_PLANO,
    "id_executor": "SELECT e.id FROM executor e JOIN plano_acao p USING (id_plano_acao)" + _FILTRO_PLANO,
    "id_empenho": "SELECT e.id_empenho FROM empenho e JOIN plano_acao p USING (id_plano_acao)"
    + _FILTRO_PLANO,
    "id_dh": "SELECT d.id_dh FROM documento_habil d JOIN empenho e USING (id_empenho)"
    " JOIN plano_acao p USING (id_plano_acao)" + _FILTRO_PLANO,
}


def _filtro_planos(desde: date, ufs: list[str] | None) -> dict[str, str]:
    filtros = {"ano_plano_acao": f"gte.{desde.year}"}
    if ufs:
        filtros["uf_beneficiario_plano_acao"] = f"in.({','.join(u.upper() for u in ufs)})"
    return filtros


def _gravar_planos(linhas: list[dict[str, Any]]) -> int:
    entes = {e["cnpj"]: e for e in (tg.ente_de_plano(r) for r in linhas) if e}
    with transacao() as conn:
        # Não sobrescreve campos preenchidos por outras fontes (IBGE, Querido Diário).
        upsert(conn, "ente", entes.values(), ("cnpj",), atualizar=("nome", "uf", "esfera"), jsonb=())
        return upsert(conn, "plano_acao", [tg.plano_acao(r) for r in linhas], ("id_plano_acao",))


def _gravar_filhas(tab: tg.Tabela, linhas: list[dict[str, Any]], pais: set[int], contexto: dict) -> int:
    linhas = [r for r in linhas if r.get(tab.coluna_pai) in pais]
    if not linhas:
        return 0
    if tab.destino == "meta":
        registros = [tab.transformar(r, contexto["plano_do_executor"]) for r in linhas]
    else:
        registros = [tab.transformar(r) for r in linhas]
    registros = [r for r in registros if r]
    with transacao() as conn:
        return upsert(conn, tab.destino, registros, tab.chave_destino)


def _ids_pais(coluna: str, desde: date, ufs: list[str] | None) -> set[int]:
    params = {"ano": desde.year, "todas": not ufs, "ufs": [u.upper() for u in (ufs or [])]}
    with transacao() as conn:
        return {r[0] for r in conn.execute(text(PAIS[coluna]), params)}


def _carregar_filha(cli: ClienteHttp, tab: tg.Tabela, desde: date, ufs, execucao: Execucao) -> int:
    estado = execucao.progresso.get(tab.nome_api, {})
    if estado.get("concluida"):
        return estado.get("gravados", 0)
    pais = _ids_pais(tab.coluna_pai, desde, ufs)
    contexto: dict[str, Any] = {}
    if tab.destino == "meta":
        with transacao() as conn:
            contexto["plano_do_executor"] = dict(
                conn.execute(text("SELECT id, id_plano_acao FROM executor")).all()
            )
    gravados = estado.get("gravados", 0)
    with cronometro("transferegov", f"carga:{tab.nome_api}", pais=len(pais)) as info:
        if len(pais) <= LIMITE_BUSCA_POR_LOTE:
            ordenados = sorted(pais)
            inicio = estado.get("lote", 0)
            for i in range(inicio, len(ordenados), TAMANHO_LOTE_IN):
                lote = ordenados[i : i + TAMANHO_LOTE_IN]
                filtros = {tab.coluna_pai: f"in.({','.join(map(str, lote))})"}
                for _, linhas in tg.paginas(cli, tab.nome_api, filtros, ordem=tab.chave_api):
                    gravados += _gravar_filhas(tab, linhas, pais, contexto)
                execucao.salvar(**{tab.nome_api: {"lote": i + TAMANHO_LOTE_IN, "gravados": gravados}})
        else:
            offset = estado.get("offset", 0)
            for proximo, linhas in tg.paginas(cli, tab.nome_api, ordem=tab.chave_api, offset=offset):
                gravados += _gravar_filhas(tab, linhas, pais, contexto)
                execucao.salvar(**{tab.nome_api: {"offset": proximo, "gravados": gravados}})
        info["quantidade"] = gravados
    execucao.salvar(**{tab.nome_api: {"concluida": True, "gravados": gravados}})
    return gravados


def ligar_pagamentos() -> int:
    """Resolve plano de ação e valor de cada ordem bancária via documento hábil → empenho."""
    with transacao() as conn:
        return conn.execute(
            text(
                "UPDATE pagamento p SET id_plano_acao = e.id_plano_acao, valor = d.valor"
                " FROM documento_habil d JOIN empenho e USING (id_empenho)"
                " WHERE p.id_dh = d.id_dh"
                " AND (p.id_plano_acao IS DISTINCT FROM e.id_plano_acao OR p.valor IS DISTINCT FROM d.valor)"
            )
        ).rowcount


def contagens() -> dict[str, int]:
    tabelas = ["ente", "plano_acao", "plano_trabalho", "meta", "executor", "empenho", "documento_habil"]
    tabelas += ["pagamento", "relatorio_gestao"]
    with transacao() as conn:
        resultado = {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in tabelas}
        resultado["pagamento_ligado"] = conn.execute(
            text("SELECT count(*) FROM pagamento WHERE id_plano_acao IS NOT NULL")
        ).scalar_one()
    return resultado


def carregar(desde: date, ufs: list[str] | None = None, retomar: bool = True) -> dict[str, Any]:
    tipo = "carga_inicial:transferegov" + (f":{','.join(sorted(u.upper() for u in ufs))}" if ufs else "")
    execucao = Execucao(tipo, retomar=retomar)
    cli = tg.cliente()
    try:
        estado = execucao.progresso.get("plano_acao_especial", {})
        if not estado.get("concluida"):
            with cronometro("transferegov", "carga:plano_acao_especial") as info:
                gravados = estado.get("gravados", 0)
                for proximo, linhas in tg.paginas(
                    cli,
                    "plano_acao_especial",
                    _filtro_planos(desde, ufs),
                    ordem="id_plano_acao",
                    offset=estado.get("offset", 0),
                ):
                    gravados += _gravar_planos(linhas)
                    execucao.salvar(plano_acao_especial={"offset": proximo, "gravados": gravados})
                info["quantidade"] = gravados
            execucao.salvar(plano_acao_especial={"concluida": True, "gravados": gravados})
        for tab in tg.TABELAS_FILHAS:
            _carregar_filha(cli, tab, desde, ufs, execucao)
        ligados = ligar_pagamentos()
        resumo = {"pagamentos_ligados_agora": ligados, **contagens()}
        execucao.concluir(resumo)
        log("transferegov", "carga:concluida", **resumo)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()
