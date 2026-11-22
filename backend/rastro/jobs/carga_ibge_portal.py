"""Cargas do IBGE (municípios, população, CNPJ → código IBGE) e do Portal da Transparência (emendas Pix)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text

from rastro.conectores import ibge, portal
from rastro.conectores.base import USER_AGENT
from rastro.config import config
from rastro.db.conexao import transacao
from rastro.db.repositorio import upsert
from rastro.jobs.execucao import Execucao
from rastro.log import cronometro, log

RAIZ = Path(__file__).resolve().parents[3]
PASTA_DADOS = RAIZ / "dados"
RELATORIO_NAO_RESOLVIDOS = RAIZ / "docs" / "relatorios" / "cnpjs-nao-resolvidos.md"


# ------------------------------------------------------------------------------------ IBGE


def carregar_ibge() -> dict[str, Any]:
    execucao = Execucao("carga_inicial:ibge", retomar=False)
    cli = ibge.cliente()
    try:
        with cronometro("ibge", "municipios") as info:
            municipios = ibge.baixar_municipios(cli)
            with transacao() as conn:
                upsert(
                    conn,
                    "municipio",
                    municipios,
                    ("codigo_ibge",),
                    atualizar=("nome", "uf", "nome_chave"),
                    jsonb=(),
                )
            info["quantidade"] = len(municipios)
        with cronometro("ibge", "populacao") as info:
            periodo, pops = ibge.periodo_mais_recente_com_dados(cli, "N6")
            _, pops_uf = ibge.periodo_mais_recente_com_dados(cli, "N3")
            with transacao() as conn:
                conn.execute(
                    text("UPDATE municipio SET populacao = :p, ano_populacao = :a WHERE codigo_ibge = :c"),
                    [{"c": c, "p": p, "a": a} for c, (p, a) in pops.items()],
                )
            info.update(quantidade=len(pops), periodo=periodo)
        resumo = resolver_entes(pops_uf)
        resumo["periodo_populacao"] = periodo
        execucao.concluir(resumo)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise
    finally:
        cli.fechar()


def resolver_entes(pops_uf: dict[str, tuple[int, int]] | None = None) -> dict[str, Any]:
    """Preenche ente.codigo_ibge, populacao e obrigado_pncp; gera o relatório dos não resolvidos."""
    limite = config().limite_populacao_pequeno
    pops_uf = pops_uf or {}
    with transacao() as conn:
        indice = {(r.uf, r.nome_chave): r.codigo_ibge for r in conn.execute(text("SELECT * FROM municipio"))}
        pop_mun = dict(conn.execute(text("SELECT codigo_ibge, populacao FROM municipio")).all())
        entes = conn.execute(text("SELECT cnpj, nome, uf, esfera FROM ente")).all()
        atualizacoes, nao_resolvidos = [], []
        for e in entes:
            if e.esfera == "estadual" and e.uf in ibge.CODIGO_UF:
                cod_uf = ibge.CODIGO_UF[e.uf]
                pop = pops_uf.get(cod_uf, (None, None))[0]
                atualizacoes.append((e.cnpj, cod_uf + "00000", pop, True, "estado"))
                continue
            codigo, metodo = ibge.resolver_municipio(e.nome, e.uf, indice)
            if not codigo:
                nao_resolvidos.append(e)
                continue
            pop = pop_mun.get(codigo)
            atualizacoes.append((e.cnpj, codigo, pop, (pop or 0) > limite if pop else None, metodo))
        conn.execute(
            text(
                "UPDATE ente SET codigo_ibge = :c, populacao = :p, obrigado_pncp = :o,"
                " metodo_resolucao_ibge = :m, atualizado_em = now(),"
                " esfera = CASE WHEN :m = 'estado' THEN esfera ELSE 'municipal' END WHERE cnpj = :cnpj"
            ),
            [{"cnpj": a[0], "c": a[1], "p": a[2], "o": a[3], "m": a[4]} for a in atualizacoes],
        )
    _escrever_relatorio(nao_resolvidos, total=len(entes))
    resumo = {
        "entes": len(entes),
        "resolvidos": len(atualizacoes),
        "nao_resolvidos": len(nao_resolvidos),
        "percentual_resolvido": round(100 * len(atualizacoes) / len(entes), 2) if entes else 0.0,
        "por_metodo": {m: sum(1 for a in atualizacoes if a[4] == m) for m in {a[4] for a in atualizacoes}},
    }
    log("ibge", "resolver_entes", **resumo)
    return resumo


def _escrever_relatorio(nao_resolvidos: list, total: int) -> None:
    RELATORIO_NAO_RESOLVIDOS.parent.mkdir(parents=True, exist_ok=True)
    linhas = [
        "# CNPJs de entes não resolvidos para código IBGE",
        "",
        f"Gerado em {date.today().isoformat()} por `rastro.jobs.carga_ibge_portal.resolver_entes`.",
        f"{len(nao_resolvidos)} de {total} entes sem código IBGE (ficam com status cinza até a correção).",
        "",
        "| CNPJ | Nome | UF | Esfera |",
        "|---|---|---|---|",
    ]
    linhas += [f"| {e.cnpj} | {e.nome} | {e.uf or ''} | {e.esfera or ''} |" for e in nao_resolvidos]
    RELATORIO_NAO_RESOLVIDOS.write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------- Portal


def baixar_arquivo_cgu(destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", portal.URL_ARQUIVO_CGU, headers={"User-Agent": USER_AGENT}, timeout=600) as resp:
        resp.raise_for_status()
        with destino.open("wb") as arq:
            for bloco in resp.iter_bytes():
                arq.write(bloco)
    return destino


def carregar_portal(desde: date, arquivo: Path | None = None) -> dict[str, Any]:
    execucao = Execucao("carga_inicial:portal", retomar=False)
    try:
        if config().portal_transparencia_api_key:
            resumo = _carregar_portal_api(desde, execucao)
        else:
            log("portal", "sem_chave", mensagem="PORTAL_TRANSPARENCIA_API_KEY ausente: usando arquivo da CGU")
            resumo = _carregar_portal_arquivo(desde, arquivo)
        resumo.update(estatisticas_ligacao(desde))
        execucao.concluir(resumo)
        log("portal", "carga:concluida", **resumo)
        return resumo
    except Exception as exc:
        execucao.falhar(repr(exc))
        raise


def _carregar_portal_arquivo(desde: date, arquivo: Path | None) -> dict[str, Any]:
    zip_path = arquivo or PASTA_DADOS / "portal" / "EmendasParlamentares.zip"
    if not arquivo:
        with cronometro("portal", "download_arquivo_cgu"):
            baixar_arquivo_cgu(zip_path)
    with cronometro("portal", "emendas_arquivo") as info:
        emendas = portal.emendas_pix_do_arquivo(zip_path, desde.year)
        with transacao() as conn:
            upsert(conn, "emenda", emendas, ("codigo_emenda",))
        info["quantidade"] = len(emendas)
    with cronometro("portal", "objeto_declarado") as info:
        objetos = [
            {"c": o["codigo_plano_acao"], "o": o["objeto"]}
            for o in portal.objetos_declarados_do_arquivo(zip_path)
            if o["objeto"]
            and o["codigo_plano_acao"][4:8].isdigit()
            and int(o["codigo_plano_acao"][4:8]) >= desde.year
        ]
        with transacao() as conn:
            conn.execute(text("CREATE TEMP TABLE tmp_objeto (c text, o text) ON COMMIT DROP"))
            conn.execute(text("INSERT INTO tmp_objeto VALUES (:c, :o)"), objetos)
            info["quantidade"] = conn.execute(
                text(
                    "UPDATE plano_acao p SET objeto_declarado = t.o FROM tmp_objeto t"
                    " WHERE p.codigo_plano_acao = t.c AND p.objeto_declarado IS DISTINCT FROM t.o"
                )
            ).rowcount
    return {"emendas": len(emendas), "origem": "arquivo_cgu"}


def _carregar_portal_api(desde: date, execucao: Execucao) -> dict[str, Any]:
    cli = portal.cliente()
    total = 0
    try:
        for ano in range(desde.year, date.today().year + 1):
            inicio = execucao.progresso.get(f"pagina_{ano}", 1)
            for pagina, linhas in portal.emendas_api(cli, ano, inicio):
                pix = [portal.emenda_da_api(r) for r in linhas if portal.eh_pix(r.get("tipoEmenda"))]
                with transacao() as conn:
                    upsert(conn, "emenda", pix, ("codigo_emenda",))
                total += len(pix)
                execucao.salvar(**{f"pagina_{ano}": pagina + 1})
        with transacao() as conn:
            codigos = [
                r[0]
                for r in conn.execute(
                    text("SELECT codigo_emenda FROM emenda WHERE ano >= :a"), {"a": desde.year}
                )
            ]
        for codigo in codigos:
            docs = [portal.documento_da_api(codigo, d) for d in portal.documentos_api(cli, codigo)]
            with transacao() as conn:
                upsert(conn, "emenda_documento", docs, ("id",))
        return {"emendas": total, "origem": "api"}
    finally:
        cli.fechar()


def estatisticas_ligacao(desde: date) -> dict[str, Any]:
    with transacao() as conn:
        r = conn.execute(
            text(
                "SELECT count(*) AS planos,"
                " count(*) FILTER (WHERE e.codigo_emenda IS NOT NULL) AS ligados,"
                " count(*) FILTER (WHERE p.objeto_declarado IS NOT NULL) AS com_objeto"
                " FROM plano_acao p LEFT JOIN emenda e ON e.codigo_emenda = p.emenda_numero"
                " WHERE p.ano_plano_acao >= :a"
            ),
            {"a": desde.year},
        ).one()
        emendas = conn.execute(
            text(
                "SELECT count(*) AS total, count(*) FILTER (WHERE EXISTS"
                " (SELECT 1 FROM plano_acao p WHERE p.emenda_numero = e.codigo_emenda)) AS ligadas"
                " FROM emenda e WHERE e.ano >= :a"
            ),
            {"a": desde.year},
        ).one()

    def pct(a, b):
        return round(100 * a / b, 2) if b else 0.0

    return {
        "planos": r.planos,
        "planos_ligados_a_emenda": r.ligados,
        "percentual_planos_ligados": pct(r.ligados, r.planos),
        "planos_com_objeto_declarado": r.com_objeto,
        "emendas_portal": emendas.total,
        "percentual_emendas_ligadas": pct(emendas.ligadas, emendas.total),
    }
