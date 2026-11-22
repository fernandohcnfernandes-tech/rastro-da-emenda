"""Carga dos contratos municipais informados aos Tribunais de Contas (dados abertos): RS, PI, SP e RN."""

from __future__ import annotations

import time
from datetime import date, timedelta
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
from rastro.util import normalizar_cnpj

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


# ----------------------------------------------------------------------------------- comum


def entes_municipais(uf: str) -> dict[str, str]:
    """{codigo_ibge: cnpj do ente municipal beneficiário} — prefere o CNPJ cujo nome começa por MUNICIPIO."""
    with transacao() as conn:
        linhas = conn.execute(
            text(
                "SELECT codigo_ibge, cnpj, nome FROM ente WHERE uf = :uf AND esfera = 'municipal'"
                " AND codigo_ibge IS NOT NULL ORDER BY (nome ILIKE 'MUNICIPIO%') DESC, cnpj"
            ),
            {"uf": uf},
        ).all()
    mapa: dict[str, str] = {}
    for r in linhas:
        mapa.setdefault(r.codigo_ibge, r.cnpj)
    return mapa


def _marcar_cobertura(sigla: str, uf: str, cnpjs: list[str]) -> int:
    with transacao() as conn:
        return conn.execute(
            text("UPDATE ente SET coberto_tce = :s WHERE uf = :uf AND cnpj = ANY(:c)"),
            {"s": sigla, "uf": uf, "c": cnpjs},
        ).rowcount


def _relevante(ev: dict[str, Any], desde: date, monitorados: dict[str, Any]) -> bool:
    if not ev["cnpj_orgao"] or ev["cnpj_orgao"] not in monitorados:
        return False
    if ev["data_publicacao"] and ev["data_publicacao"] < desde - timedelta(days=30):
        return False
    return valor_relevante(ev["valor"], monitorados[ev["cnpj_orgao"]])


# -------------------------------------------------------------------------------------- PI


def carregar_tce_pi(desde: date, alterados_desde: date | None = None) -> dict[str, Any]:
    """Contratos municipais do TCE-PI por vigência (carga inicial) ou por data de alteração (semanal)."""
    from rastro.conectores import tce_pi

    execucao = Execucao("carga:tce_pi", retomar=False)
    cli = tce_pi.cliente()
    try:
        monitorados = {a.cnpj: a.menor_valor for a in cnpjs_monitorados(desde, ["PI"])}
        por_ibge = entes_municipais("PI")
        cobertos = _marcar_cobertura(tce_pi.SIGLA, "PI", list(por_ibge.values()))
        totais = {"entes_cobertos": cobertos, "lidos": 0, "gravados": 0}
        if alterados_desde:
            consultas = [{"dtAlteracao": alterados_desde.isoformat()}]
        else:
            # Janelas mensais: paginar um ano inteiro devolveu 502 (offset > 18 mil) em 22/11/2026.
            from rastro.conectores.pncp import janelas_mensais

            consultas = [{"vigencia": f"{i}_{f}"} for i, f in janelas_mensais(desde, date.today())]
        totais["erros"] = 0
        lote: dict[tuple[str, str], dict[str, Any]] = {}
        for filtros in consultas:
            with cronometro("tce_pi", "contratos", **filtros) as info:
                try:
                    for itens in tce_pi.paginas(cli, **filtros):
                        for r in itens:
                            totais["lidos"] += 1
                            if tce_pi.eh_camara(r.get("orgao")):
                                continue
                            ev = tce_pi.evidencia_de_contrato(r, por_ibge.get(r.get("codIbgeMun") or ""))
                            if _relevante(ev, desde, monitorados):
                                lote[(ev["fonte"], ev["id_externo"])] = ev
                        if len(lote) >= LOTE:
                            totais["gravados"] += _gravar(lote)
                except Exception as exc:  # uma janela com erro não interrompe as demais
                    totais["erros"] += 1
                    log("tce_pi", "contratos:erro", erro=repr(exc)[:300], **filtros)
                totais["gravados"] += _gravar(lote)
                info["quantidade"] = totais["gravados"]
            execucao.salvar(**{str(filtros): dict(totais)})
        execucao.concluir(totais, status="concluido" if not totais["erros"] else "erro")
        log("tce_pi", "carga:concluida", **totais)
        return totais
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()


# -------------------------------------------------------------------------------------- SP


def semestres(desde: date, ate: date) -> list[tuple[int, int]]:
    return [
        (ano, s)
        for ano in range(desde.year, ate.year + 1)
        for s in (1, 2)
        if (ano, s) >= (desde.year, 1 if desde.month <= 6 else 2) and (ano, s) <= (ate.year, 1 if ate.month <= 6 else 2)
    ]


def carregar_tce_sp(desde: date, so_recentes: bool = False) -> dict[str, Any]:
    from rastro.conectores import ibge, tce_sp

    execucao = Execucao("carga:tce_sp", retomar=False)
    try:
        monitorados = {a.cnpj: a.menor_valor for a in cnpjs_monitorados(desde, ["SP"])}
        por_ibge = entes_municipais("SP")
        with transacao() as conn:
            indice = {
                r.nome_chave: r.codigo_ibge
                for r in conn.execute(text("SELECT nome_chave, codigo_ibge FROM municipio WHERE uf = 'SP'"))
            }
        capital = "3550308"  # São Paulo é fiscalizada pelo TCM-SP
        cobertos = _marcar_cobertura(tce_sp.SIGLA, "SP", [c for i, c in por_ibge.items() if i != capital])
        totais = {"entes_cobertos": cobertos, "lidos": 0, "gravados": 0, "arquivos": 0}
        lista = semestres(desde, date.today())
        for ano, semestre in lista[-2:] if so_recentes else lista:
            destino = PASTA_DADOS / "tce_sp" / f"ajustes_{ano}_{semestre}.zip"
            url = tce_sp.url_semestre(ano, semestre)
            atual = (ano, semestre) == lista[-1]
            if not destino.exists() or atual:
                try:
                    with cronometro("tce_sp", "download", ano=ano, semestre=semestre):
                        tce_rs.baixar(url, destino)
                except httpx.HTTPStatusError as exc:
                    log("tce_sp", "arquivo_indisponivel", ano=ano, semestre=semestre, status=exc.response.status_code)
                    destino.unlink(missing_ok=True)
                    continue
            totais["arquivos"] += 1
            lote: dict[tuple[str, str], dict[str, Any]] = {}
            with cronometro("tce_sp", "ajustes", ano=ano, semestre=semestre) as info:
                for r in tce_sp.linhas(destino):
                    totais["lidos"] += 1
                    if not tce_sp.entidade_do_executivo(r.get("Entidade")):
                        continue
                    codigo = indice.get(ibge.chave_nome(r.get("Município") or ""))
                    ev = tce_sp.evidencia(r, por_ibge.get(codigo or ""), codigo, url)
                    if _relevante(ev, desde, monitorados):
                        lote[(ev["fonte"], ev["id_externo"])] = ev
                        if len(lote) >= LOTE:
                            totais["gravados"] += _gravar(lote)
                totais["gravados"] += _gravar(lote)
                info["quantidade"] = totais["gravados"]
            execucao.salvar(**{f"{ano}-{semestre}": dict(totais)})
        execucao.concluir(totais)
        log("tce_sp", "carga:concluida", **totais)
        return totais
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise


# -------------------------------------------------------------------------------------- RN


def carregar_tce_rn(desde: date) -> dict[str, Any]:
    from rastro.conectores import ibge, tce_rn

    execucao = Execucao("carga:tce_rn", retomar=False)
    cli = tce_rn.cliente()
    try:
        monitorados = {a.cnpj: a.menor_valor for a in cnpjs_monitorados(desde, ["RN"])}
        por_ibge = entes_municipais("RN")
        cnpj_para_ibge = {c: i for i, c in por_ibge.items()}
        with transacao() as conn:
            indice = {
                r.nome_chave: r.codigo_ibge
                for r in conn.execute(text("SELECT nome_chave, codigo_ibge FROM municipio WHERE uf = 'RN'"))
            }
        alvos = []
        for u in tce_rn.unidades(cli):
            if not tce_rn.eh_prefeitura(u):
                continue
            cnpj = normalizar_cnpj(u.get("cnpj"))
            codigo = cnpj_para_ibge.get(cnpj or "") or indice.get(ibge.chave_nome(u.get("nomeOrgao") or ""))
            cnpj_ente = por_ibge.get(codigo or "")
            if cnpj_ente and cnpj_ente in monitorados:
                alvos.append((u["identificadorUnidade"], cnpj_ente, codigo))
        cobertos = _marcar_cobertura(tce_rn.SIGLA, "RN", [a[1] for a in alvos])
        totais = {"prefeituras": len(alvos), "entes_cobertos": cobertos, "lidos": 0, "gravados": 0, "erros": 0}
        lote: dict[tuple[str, str], dict[str, Any]] = {}
        with cronometro("tce_rn", "contratos") as info:
            for identificador, cnpj_ente, codigo in alvos:
                try:
                    itens = tce_rn.contratos(cli, identificador)
                except Exception as exc:
                    totais["erros"] += 1
                    log("tce_rn", "contratos:erro", unidade=identificador, erro=repr(exc)[:200])
                    continue
                for r in itens:
                    totais["lidos"] += 1
                    ev = tce_rn.evidencia_de_contrato(r, cnpj_ente, codigo)
                    if _relevante(ev, desde, monitorados):
                        lote[(ev["fonte"], ev["id_externo"])] = ev
                if len(lote) >= LOTE:
                    totais["gravados"] += _gravar(lote)
            totais["gravados"] += _gravar(lote)
            info["quantidade"] = totais["gravados"]
        execucao.concluir(totais, status="concluido" if not totais["erros"] else "erro")
        log("tce_rn", "carga:concluida", **totais)
        return totais
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()


CARGAS = {"RS": carregar_tce_rs, "PI": carregar_tce_pi, "SP": carregar_tce_sp, "RN": carregar_tce_rn}
