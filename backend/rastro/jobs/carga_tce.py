"""Carga dos contratos municipais informados aos Tribunais de Contas (dados abertos). Hoje: TCE-RS."""

from __future__ import annotations

import time
from datetime import date
from typing import Any

import httpx
from sqlalchemy import text

from rastro.conectores import tce_rs
from rastro.conectores.base import USER_AGENT
from rastro.db.conexao import transacao
from rastro.db.repositorio import upsert
from rastro.jobs.carga_ibge_portal import PASTA_DADOS
from rastro.jobs.carga_pncp import cnpjs_monitorados, valor_relevante
from rastro.jobs.execucao import Execucao
from rastro.log import cronometro, log

LOTE = 2000
IDADE_MAXIMA_ARQUIVO_S = 6 * 24 * 3600  # o TCE-RS atualiza os arquivos diariamente; a carga semanal rebaixa


def _arquivo_ano(ano: int, forcar: bool) -> Any:
    destino = PASTA_DADOS / "tce_rs" / f"contratos_{ano}.csv.zip"
    atual = ano == date.today().year
    if forcar or not destino.exists() or (atual and time.time() - destino.stat().st_mtime > IDADE_MAXIMA_ARQUIVO_S):
        with cronometro("tce_rs", "download", ano=ano):
            tce_rs.baixar(tce_rs.url_contratos(ano), destino)
    return destino


def carregar_tce_rs(desde: date, anos: list[int] | None = None, forcar_download: bool = False) -> dict[str, Any]:
    execucao = Execucao("carga:tce_rs", retomar=False)
    try:
        resp = httpx.get(tce_rs.URL_ORGAOS, headers={"User-Agent": USER_AGENT}, timeout=120)
        resp.raise_for_status()
        orgaos = tce_rs.ler_orgaos(resp.content.decode("utf-8-sig"))
        monitorados = {a.cnpj: a.menor_valor for a in cnpjs_monitorados(desde, ["RS"])}
        alvo = {cd: o for cd, o in orgaos.items() if o["cnpj"] in monitorados}
        cnpjs_auditados = sorted({o["cnpj"] for o in orgaos.values() if o["cnpj"]})
        with transacao() as conn:
            cobertos = conn.execute(
                text("UPDATE ente SET coberto_tce = :s WHERE uf = 'RS' AND cnpj = ANY(:c)"),
                {"s": tce_rs.SIGLA, "c": cnpjs_auditados},
            ).rowcount
        totais = {"orgaos_monitorados": len(alvo), "entes_cobertos": cobertos, "lidos": 0, "gravados": 0}
        for ano in anos or list(range(desde.year, date.today().year + 1)):
            caminho = _arquivo_ano(ano, forcar_download)
            lote: dict[tuple[str, str], dict[str, Any]] = {}
            with cronometro("tce_rs", "contratos", ano=ano) as info:
                for r in tce_rs.linhas_contratos(caminho):
                    totais["lidos"] += 1
                    orgao = alvo.get((r.get("CD_ORGAO") or "").strip())
                    if not orgao:
                        continue
                    ev = tce_rs.evidencia_de_contrato(r, orgao)
                    if ev["data_publicacao"] and ev["data_publicacao"] < desde:
                        continue
                    if not valor_relevante(ev["valor"], monitorados.get(ev["cnpj_orgao"])):
                        continue
                    lote[(ev["fonte"], ev["id_externo"])] = ev
                    if len(lote) >= LOTE:
                        totais["gravados"] += _gravar(lote)
                totais["gravados"] += _gravar(lote)
                info["quantidade"] = totais["gravados"]
            execucao.salvar(**{str(ano): dict(totais)})
        execucao.concluir(totais)
        log("tce_rs", "carga:concluida", **totais)
        return totais
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise


def _gravar(lote: dict) -> int:
    if not lote:
        return 0
    with transacao() as conn:
        n = upsert(conn, "evidencia", list(lote.values()), ("fonte", "id_externo"))
    lote.clear()
    return n
