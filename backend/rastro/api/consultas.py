"""Consultas SQL usadas pela API. Toda saída passa por `limpar()` (CPF mascarado, tipos serializáveis)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Connection, text

from rastro.motor.regras import DESCRICAO
from rastro.util import mascarar_cpf

CAMPOS_DOCUMENTO = {"fornecedor_documento", "niFornecedor"}


def limpar(valor: Any, chave: str | None = None) -> Any:
    """Converte para JSON e mascara CPF em qualquer campo de documento de fornecedor."""
    if isinstance(valor, dict):
        return {k: limpar(v, k) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [limpar(v) for v in valor]
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if chave in CAMPOS_DOCUMENTO:
        return mascarar_cpf(valor)
    return valor


def _linhas(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [limpar(dict(r._mapping)) for r in conn.execute(text(sql), params or {})]


BASE_EMENDAS = """
FROM plano_acao p
LEFT JOIN ente en ON en.cnpj = p.cnpj_beneficiario
LEFT JOIN municipio m ON m.codigo_ibge = en.codigo_ibge
LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao
LEFT JOIN LATERAL (SELECT sum(valor) AS repassado, min(data_pagamento) AS primeiro_pagamento
                   FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true
WHERE p.ano_plano_acao >= 2024
  AND (CAST(:uf AS text) IS NULL OR p.uf_beneficiario = :uf)
  AND (CAST(:municipio AS text) IS NULL OR en.codigo_ibge = :municipio
       OR unaccent_simples(m.nome) ILIKE unaccent_simples(:municipio_like))
  AND (CAST(:parlamentar AS text) IS NULL
       OR unaccent_simples(p.parlamentar_nome) ILIKE unaccent_simples(:parlamentar_like))
  AND (CAST(:ano AS integer) IS NULL OR p.emenda_ano = :ano)
  AND (CAST(:status AS text) IS NULL OR a.status::text = :status)
  AND (CAST(:alerta AS text) IS NULL OR CAST(:alerta AS text) = ANY(a.alertas))
  AND (CAST(:esfera AS text) IS NULL OR en.esfera = :esfera)
  AND (CAST(:busca AS text) IS NULL OR unaccent_simples(concat_ws(' ', p.nome_beneficiario, m.nome, p.parlamentar_nome,
       p.objeto_declarado, p.emenda_numero, p.codigo_plano_acao)) ILIKE unaccent_simples(:busca_like))
"""

CAMPOS_RESUMO = """
p.id_plano_acao, p.codigo_plano_acao, p.emenda_numero, p.emenda_ano AS ano, p.parlamentar_nome AS parlamentar,
p.nome_beneficiario AS beneficiario, p.uf_beneficiario AS uf, en.codigo_ibge, m.nome AS municipio, en.populacao,
coalesce(p.valor_custeio, 0) + coalesce(p.valor_investimento, 0) AS valor_previsto, pg.repassado,
pg.primeiro_pagamento, coalesce(a.status::text, 'cinza') AS status, coalesce(a.alertas, '{}') AS alertas,
left(p.objeto_declarado, 240) AS objeto
"""


def filtros(
    uf: str | None = None,
    municipio: str | None = None,
    parlamentar: str | None = None,
    ano: int | None = None,
    status: str | None = None,
    busca: str | None = None,
    alerta: str | None = None,
    esfera: str | None = None,
) -> dict[str, Any]:
    return {
        "alerta": alerta,
        "esfera": esfera,
        "uf": uf.upper() if uf else None,
        "municipio": municipio,
        "municipio_like": f"%{municipio}%" if municipio else None,
        "parlamentar": parlamentar,
        "parlamentar_like": f"%{parlamentar}%" if parlamentar else None,
        "ano": ano,
        "status": status,
        "busca": busca,
        "busca_like": f"%{busca}%" if busca else None,
    }


def listar_emendas(conn: Connection, pagina: int, tamanho: int, ordem: str = "repassado", **f: Any) -> dict[str, Any]:
    params = {**filtros(**f), "lim": tamanho, "off": (pagina - 1) * tamanho}
    total = conn.execute(text("SELECT count(*) " + BASE_EMENDAS), params).scalar_one()
    ordenacao = ORDENACAO_EMENDAS.get(ordem, ORDENACAO_EMENDAS["repassado"])
    itens = _linhas(
        conn,
        f"SELECT {CAMPOS_RESUMO} {BASE_EMENDAS} ORDER BY {ordenacao}, p.id_plano_acao LIMIT :lim OFFSET :off",
        params,
    )
    return {"total": total, "pagina": pagina, "tamanho": tamanho, "itens": itens}


def resumo_status(conn: Connection, **f: Any) -> dict[str, int]:
    params = filtros(**f)
    linhas = conn.execute(
        text(f"SELECT coalesce(a.status::text, 'cinza') AS s, count(*) AS n {BASE_EMENDAS} GROUP BY 1"), params
    ).all()
    return {r.s: r.n for r in linhas}


def ficha_emenda(conn: Connection, id_plano_acao: int) -> dict[str, Any] | None:
    base = _linhas(
        conn,
        f"SELECT {CAMPOS_RESUMO}, p.situacao, p.valor_custeio, p.valor_investimento,"
        " p.objeto_declarado AS objeto_completo,"
        " p.areas_politicas, p.motivo_impedimento, en.esfera, en.obrigado_pncp, en.coberto_querido_diario,"
        " en.coberto_tce,"
        " a.justificativa, a.avaliado_em, a.detalhes, p.cnpj_beneficiario"
        f" {BASE_EMENDAS} AND p.id_plano_acao = :id",
        {**filtros(), "id": id_plano_acao},
    )
    if not base:
        return None
    ficha = base[0]
    p = {"id": id_plano_acao}
    ficha["alertas_detalhados"] = [{"codigo": a, "descricao": DESCRICAO.get(a, a)} for a in ficha["alertas"]]
    ficha["emenda_portal"] = (
        _linhas(
            conn,
            "SELECT codigo_emenda, autor, tipo, funcao, subfuncao, valor_empenhado, valor_liquidado, valor_pago,"
            " localidade, origem FROM emenda WHERE codigo_emenda = (SELECT emenda_numero FROM plano_acao WHERE"
            " id_plano_acao = :id)",
            p,
        )
        or [None]
    )[0]
    ficha["executores"] = _linhas(
        conn,
        "SELECT cnpj_executor, nome_executor, objeto, valor_custeio, valor_investimento FROM executor"
        " WHERE id_plano_acao = :id ORDER BY id",
        p,
    )
    ficha["metas"] = _linhas(
        conn,
        "SELECT nome, descricao, valor_custeio, valor_investimento FROM meta WHERE id_plano_acao = :id ORDER BY id",
        p,
    )
    ficha["plano_trabalho"] = _linhas(
        conn,
        "SELECT situacao, data_inicio_execucao, data_fim_execucao FROM plano_trabalho WHERE id_plano_acao = :id",
        p,
    )
    ficha["pagamentos"] = _linhas(
        conn,
        "SELECT data_pagamento, valor, numero_ordem_bancaria, situacao FROM pagamento WHERE id_plano_acao = :id"
        " ORDER BY data_pagamento",
        p,
    )
    ficha["relatorios_gestao"] = _linhas(
        conn,
        "SELECT tipo, situacao, valor_executado, valor_pendente, data_registro FROM relatorio_gestao"
        " WHERE id_plano_acao = :id ORDER BY data_registro NULLS LAST",
        p,
    )
    ficha["evidencias"] = _linhas(
        conn,
        "SELECT ev.id, ev.fonte::text AS fonte, ev.data_publicacao, ev.data_assinatura, ev.objeto, ev.valor,"
        " ev.modalidade, ev.tipo_ato, ev.situacao, ev.fornecedor_documento, ev.fornecedor_nome, ev.url, ev.trecho,"
        " c.compativel, c.confianca, c.metodo, c.score_pre_filtro,"
        " c.resposta_ia->>'justificativa' AS justificativa_ia, c.resposta_ia->'trechos_citados' AS trechos_citados,"
        " (c.compativel AND c.confianca >= 0.6) AS conta_como_evidencia"
        " FROM correspondencia c JOIN evidencia ev ON ev.id = c.id_evidencia"
        " WHERE c.id_plano_acao = :id ORDER BY (c.compativel AND c.confianca >= 0.6) DESC, c.confianca DESC",
        p,
    )
    ficha["linha_do_tempo"] = linha_do_tempo(ficha)
    ficha["fontes"] = fontes_oficiais(id_plano_acao, ficha.get("emenda_numero"))
    return ficha


TRANSFEREGOV_PUBLICO = "https://especiais.transferegov.sistema.gov.br/transferencia-especial/plano-acao/detalhe"


def fontes_oficiais(id_plano_acao: int, emenda_numero: str | None) -> dict[str, str | None]:
    """Páginas públicas (legíveis por pessoas) onde a informação pode ser conferida — não a API bruta."""
    base = f"{TRANSFEREGOV_PUBLICO}/{id_plano_acao}"
    return {
        "Transferegov — plano de ação (dados básicos)": f"{base}/dados-basicos",
        "Transferegov — plano de trabalho": f"{base}/plano-trabalho",
        "Transferegov — relatório de gestão": f"{base}/relatorio-gestao",
        "Portal da Transparência — emenda": f"https://portaldatransparencia.gov.br/emendas/detalhe?codigoEmenda={emenda_numero}"
        if emenda_numero
        else None,
    }


def linha_do_tempo(f: dict[str, Any]) -> list[dict[str, Any]]:
    """Indicação → plano de trabalho → pagamento → licitação → contrato (só eventos com data)."""
    eventos: list[dict[str, Any]] = []
    if f.get("ano"):
        eventos.append(
            {
                "etapa": "indicacao",
                "data": f"{f['ano']}-01-01",
                "titulo": "Indicação da emenda",
                "descricao": f"Emenda {f.get('emenda_numero') or ''} de {f.get('parlamentar') or 'parlamentar'}",
                "data_aproximada": True,
            }
        )
    for pt in f.get("plano_trabalho", []):
        if pt.get("data_inicio_execucao"):
            eventos.append(
                {
                    "etapa": "plano_trabalho",
                    "data": pt["data_inicio_execucao"],
                    "titulo": "Plano de trabalho",
                    "descricao": f"Situação: {pt.get('situacao') or 'não informada'}; execução prevista até "
                    f"{pt.get('data_fim_execucao') or 'data não informada'}",
                }
            )
    for g in f.get("pagamentos", []):
        eventos.append(
            {
                "etapa": "pagamento",
                "data": g["data_pagamento"],
                "titulo": "Pagamento (ordem bancária)",
                "descricao": f"{g.get('numero_ordem_bancaria') or ''}",
                "valor": g.get("valor"),
            }
        )
    for e in f.get("evidencias", []):
        if not e.get("conta_como_evidencia"):
            continue
        contrato = e["fonte"] == "pncp_contrato" or (e.get("tipo_ato") or "") in {"contrato", "extrato_contrato"}
        eventos.append(
            {
                "etapa": "contrato" if contrato else "licitacao",
                "data": e.get("data_assinatura") or e.get("data_publicacao"),
                "titulo": "Contrato" if contrato else "Licitação / contratação",
                "descricao": (e.get("objeto") or "")[:200],
                "valor": e.get("valor"),
                "url": e.get("url"),
            }
        )
    return sorted([e for e in eventos if e.get("data")], key=lambda e: str(e["data"]))


def municipio(conn: Connection, codigo_ibge: str) -> dict[str, Any] | None:
    dados = _linhas(
        conn,
        "SELECT m.codigo_ibge, m.nome, m.uf, m.populacao, m.ano_populacao, m.coberto_querido_diario,"
        " (m.populacao <= 20000) AS pequeno FROM municipio m WHERE m.codigo_ibge = :c",
        {"c": codigo_ibge},
    )
    if not dados:
        return None
    info = dados[0]
    info["entes"] = _linhas(
        conn, "SELECT cnpj, nome, esfera, obrigado_pncp FROM ente WHERE codigo_ibge = :c", {"c": codigo_ibge}
    )
    info["status"] = resumo_status(conn, municipio=codigo_ibge)
    info["emendas"] = listar_emendas(conn, 1, 200, municipio=codigo_ibge)["itens"]
    info["valor_repassado"] = sum(e["repassado"] or 0 for e in info["emendas"])
    return info


def parlamentar(conn: Connection, nome: str) -> dict[str, Any] | None:
    nomes = _linhas(
        conn,
        "SELECT DISTINCT parlamentar_nome AS nome FROM plano_acao WHERE ano_plano_acao >= 2024"
        " AND unaccent_simples(parlamentar_nome) ILIKE unaccent_simples(:n) ORDER BY 1 LIMIT 20",
        {"n": f"%{nome}%"},
    )
    if not nomes:
        return None
    exato = next((n["nome"] for n in nomes if n["nome"].lower() == nome.lower()), nomes[0]["nome"])
    emendas = listar_emendas(conn, 1, 500, parlamentar=exato)
    perfil = _linhas(
        conn,
        "SELECT pr.id, pr.casa, pr.nome, pr.nome_civil, pr.partido, pr.uf, pr.url_foto, pr.email, pr.telefone,"
        " pr.url_pagina, pr.situacao, pa.metodo AS metodo_ligacao"
        " FROM parlamentar_autor pa JOIN parlamentar pr ON pr.id = pa.id_parlamentar WHERE pa.nome_autor = :n",
        {"n": exato},
    )
    return {
        "nome": exato,
        "perfil": perfil[0] if perfil else None,
        "outros_nomes_encontrados": [n["nome"] for n in nomes if n["nome"] != exato],
        "status": resumo_status(conn, parlamentar=exato),
        "total_emendas": emendas["total"],
        "valor_repassado": sum(e["repassado"] or 0 for e in emendas["itens"]),
        "ufs": sorted({e["uf"] for e in emendas["itens"] if e["uf"]}),
        "emendas": emendas["itens"],
    }


ORDEM_GRAVIDADE = {"vermelho": 5, "laranja": 4, "amarelo": 3, "azul": 2, "verde": 1, "cinza": 0}


def mapa(conn: Connection, uf: str | None = None) -> list[dict[str, Any]]:
    linhas = _linhas(
        conn,
        "SELECT en.codigo_ibge, min(m.nome) AS municipio, min(m.uf) AS uf, min(m.populacao) AS populacao,"
        " count(*) AS emendas, sum(coalesce(pg.v, 0)) AS repassado,"
        " count(*) FILTER (WHERE a.status = 'verde') AS verde,"
        " count(*) FILTER (WHERE a.status = 'amarelo') AS amarelo,"
        " count(*) FILTER (WHERE a.status = 'vermelho') AS vermelho,"
        " count(*) FILTER (WHERE a.status = 'azul') AS azul,"
        " count(*) FILTER (WHERE a.status = 'laranja') AS laranja,"
        " count(*) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza"
        " FROM plano_acao p JOIN ente en ON en.cnpj = p.cnpj_beneficiario"
        " JOIN municipio m ON m.codigo_ibge = en.codigo_ibge"
        " LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao"
        " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true"
        " WHERE p.ano_plano_acao >= 2024 AND en.esfera = 'municipal' AND (CAST(:uf AS text) IS NULL OR m.uf = :uf)"
        " GROUP BY en.codigo_ibge",
        {"uf": uf.upper() if uf else None},
    )
    for linha in linhas:
        linha["status"] = status_predominante(linha)
    return linhas


def mapa_estados(conn: Connection) -> list[dict[str, Any]]:
    """Semáforo das emendas destinadas aos governos estaduais e do DF, por UF."""
    linhas = _linhas(
        conn,
        "SELECT en.uf, min(en.nome) AS nome, min(en.populacao) AS populacao, min(en.coberto_tce) AS coberto_tce,"
        " bool_or(en.coberto_querido_diario) AS coberto_querido_diario,"
        " count(*) AS emendas, sum(coalesce(pg.v, 0)) AS repassado,"
        " count(*) FILTER (WHERE a.status = 'verde') AS verde,"
        " count(*) FILTER (WHERE a.status = 'amarelo') AS amarelo,"
        " count(*) FILTER (WHERE a.status = 'vermelho') AS vermelho,"
        " count(*) FILTER (WHERE a.status = 'azul') AS azul,"
        " count(*) FILTER (WHERE a.status = 'laranja') AS laranja,"
        " count(*) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza"
        " FROM plano_acao p JOIN ente en ON en.cnpj = p.cnpj_beneficiario"
        " LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao"
        " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true"
        " WHERE p.ano_plano_acao >= 2024 AND en.esfera = 'estadual' GROUP BY en.uf ORDER BY en.uf",
    )
    for linha in linhas:
        linha["status"] = status_predominante(linha)
    return linhas


def status_predominante(contagens: dict[str, int]) -> str:
    """Cor do município no mapa: vermelho se houver qualquer vermelho; senão a maioria entre os demais."""
    if contagens.get("vermelho"):
        return "vermelho"
    candidatos = {s: contagens.get(s, 0) for s in ("laranja", "amarelo", "verde", "azul", "cinza")}
    if not any(candidatos.values()):
        return "cinza"
    return max(candidatos, key=lambda s: (candidatos[s], ORDEM_GRAVIDADE[s]))


def cobertura(conn: Connection) -> list[dict[str, Any]]:
    return _linhas(
        conn,
        "SELECT en.uf, count(DISTINCT en.cnpj) AS entes,"
        " count(DISTINCT en.cnpj) FILTER (WHERE en.esfera = 'municipal' AND en.populacao <= 20000)"
        " AS municipios_pequenos,"
        " count(DISTINCT en.cnpj) FILTER (WHERE en.esfera = 'municipal' AND en.populacao <= 20000"
        "   AND en.coberto_querido_diario) AS pequenos_cobertos_querido_diario,"
        " count(DISTINCT en.cnpj) FILTER (WHERE cp.contratos_encontrados > 0) AS entes_com_registro_pncp,"
        " count(DISTINCT en.cnpj) FILTER (WHERE en.coberto_tce IS NOT NULL) AS entes_cobertos_tce,"
        " count(DISTINCT en.cnpj) FILTER (WHERE cp.cnpj IS NOT NULL) AS entes_verificados_pncp,"
        " count(DISTINCT p.id_plano_acao) AS emendas,"
        " count(DISTINCT p.id_plano_acao) FILTER (WHERE a.status = 'verde') AS verde,"
        " count(DISTINCT p.id_plano_acao) FILTER (WHERE a.status = 'amarelo') AS amarelo,"
        " count(DISTINCT p.id_plano_acao) FILTER (WHERE a.status = 'vermelho') AS vermelho,"
        " count(DISTINCT p.id_plano_acao) FILTER (WHERE a.status = 'azul') AS azul,"
        " count(DISTINCT p.id_plano_acao) FILTER (WHERE a.status = 'laranja') AS laranja,"
        " count(DISTINCT p.id_plano_acao) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza"
        " FROM ente en JOIN plano_acao p ON p.cnpj_beneficiario = en.cnpj AND p.ano_plano_acao >= 2024"
        " LEFT JOIN cobertura_pncp cp ON cp.cnpj = en.cnpj"
        " LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao"
        " GROUP BY en.uf ORDER BY en.uf",
    )


def ultima_atualizacao(conn: Connection) -> dict[str, Any]:
    linhas = _linhas(
        conn,
        "SELECT tipo, fim, status FROM execucao_job WHERE status = 'concluido' AND fim IS NOT NULL"
        " ORDER BY fim DESC LIMIT 1",
    )
    avaliacao = conn.execute(text("SELECT max(avaliado_em) FROM avaliacao")).scalar_one()
    return {"ultimo_job": linhas[0] if linhas else None, "ultima_avaliacao": limpar(avaliacao)}


ORDENACAO_EMENDAS = {
    "repassado": "pg.repassado DESC NULLS LAST",
    "recentes": "pg.primeiro_pagamento DESC NULLS LAST",
    "antigas": "pg.primeiro_pagamento ASC NULLS LAST",
    "valor": "(coalesce(p.valor_custeio, 0) + coalesce(p.valor_investimento, 0)) DESC",
}


def resumo(conn: Connection) -> dict[str, Any]:
    """Indicadores da visão geral."""
    totais = _linhas(
        conn,
        "SELECT count(*) AS emendas,"
        " sum(coalesce(p.valor_custeio, 0) + coalesce(p.valor_investimento, 0)) AS valor_previsto,"
        " (SELECT sum(g.valor) FROM pagamento g JOIN plano_acao q USING (id_plano_acao) WHERE q.ano_plano_acao >= 2024)"
        "   AS valor_repassado,"
        " count(DISTINCT p.cnpj_beneficiario) AS entes, count(DISTINCT p.parlamentar_nome) AS parlamentares"
        " FROM plano_acao p WHERE p.ano_plano_acao >= 2024",
    )[0]
    status = {
        r.s: r.n
        for r in conn.execute(
            text(
                "SELECT coalesce(a.status::text, 'cinza') AS s, count(*) AS n FROM plano_acao p"
                " LEFT JOIN avaliacao a USING (id_plano_acao) WHERE p.ano_plano_acao >= 2024 GROUP BY 1"
            )
        )
    }
    ranking = _linhas(
        conn,
        "SELECT en.codigo_ibge, m.nome AS municipio, m.uf, count(*) AS vermelhas,"
        " sum(coalesce(pg.v, 0)) AS repassado_vermelho"
        " FROM avaliacao a JOIN plano_acao p USING (id_plano_acao) JOIN ente en ON en.cnpj = p.cnpj_beneficiario"
        " JOIN municipio m ON m.codigo_ibge = en.codigo_ibge"
        " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true"
        " WHERE a.status = 'vermelho' AND en.esfera = 'municipal'"
        " GROUP BY en.codigo_ibge, m.nome, m.uf ORDER BY repassado_vermelho DESC LIMIT 8",
    )
    por_uf = _linhas(
        conn,
        "SELECT p.uf_beneficiario AS uf, count(*) AS emendas, sum(coalesce(pg.v, 0)) AS repassado,"
        " sum(coalesce(pg.v, 0)) FILTER (WHERE a.status = 'verde') AS verde_valor,"
        " sum(coalesce(pg.v, 0)) FILTER (WHERE a.status = 'amarelo') AS amarelo_valor,"
        " sum(coalesce(pg.v, 0)) FILTER (WHERE a.status = 'vermelho') AS vermelho_valor,"
        " sum(coalesce(pg.v, 0)) FILTER (WHERE a.status = 'azul') AS azul_valor,"
        " sum(coalesce(pg.v, 0)) FILTER (WHERE a.status = 'laranja') AS laranja_valor,"
        " sum(coalesce(pg.v, 0)) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza_valor,"
        " count(*) FILTER (WHERE a.status = 'verde') AS verde,"
        " count(*) FILTER (WHERE a.status = 'amarelo') AS amarelo,"
        " count(*) FILTER (WHERE a.status = 'vermelho') AS vermelho,"
        " count(*) FILTER (WHERE a.status = 'azul') AS azul,"
        " count(*) FILTER (WHERE a.status = 'laranja') AS laranja,"
        " count(*) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza"
        " FROM plano_acao p LEFT JOIN avaliacao a USING (id_plano_acao)"
        " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true"
        " WHERE p.ano_plano_acao >= 2024 AND p.uf_beneficiario IS NOT NULL GROUP BY 1 ORDER BY 1",
    )
    avaliadas_com_fonte = sum(status.get(s, 0) for s in ("verde", "amarelo", "vermelho"))
    return {
        **totais,
        "status": status,
        "percentual_com_evidencia": round(
            100 * (status.get("verde", 0) + status.get("amarelo", 0)) / avaliadas_com_fonte, 1
        )
        if avaliadas_com_fonte
        else None,
        "ranking_indicios": ranking,
        "por_uf": por_uf,
        "atualizacao": ultima_atualizacao(conn),
    }


def alertas(conn: Connection) -> list[dict[str, Any]]:
    contagem = {
        r.codigo: (r.n, r.v)
        for r in conn.execute(
            text(
                "SELECT x.codigo, count(*) AS n, sum(coalesce(pg.v, 0)) AS v"
                " FROM avaliacao a, unnest(a.alertas) AS x(codigo)"
                " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = a.id_plano_acao) pg"
                " ON true GROUP BY x.codigo"
            )
        )
    }
    return [
        {
            "codigo": c,
            "descricao": d,
            "emendas": contagem.get(c, (0, 0))[0],
            "repassado": limpar(contagem.get(c, (0, 0))[1]),
        }
        for c, d in DESCRICAO.items()
    ]


def listar_municipios(conn: Connection, busca: str | None, uf: str | None, pagina: int, tamanho: int) -> dict:
    params = {
        "busca": f"%{busca}%" if busca else None,
        "uf": uf.upper() if uf else None,
        "lim": tamanho,
        "off": (pagina - 1) * tamanho,
    }
    base = (
        " FROM plano_acao p JOIN ente en ON en.cnpj = p.cnpj_beneficiario"
        " JOIN municipio m ON m.codigo_ibge = en.codigo_ibge"
        " LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao"
        " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true"
        " WHERE p.ano_plano_acao >= 2024 AND en.esfera = 'municipal'"
        " AND (CAST(:uf AS text) IS NULL OR m.uf = :uf)"
        " AND (CAST(:busca AS text) IS NULL OR unaccent_simples(m.nome) ILIKE unaccent_simples(:busca))"
    )
    total = conn.execute(text("SELECT count(DISTINCT en.codigo_ibge)" + base), params).scalar_one()
    itens = _linhas(
        conn,
        "SELECT en.codigo_ibge, min(m.nome) AS nome, min(m.uf) AS uf, min(m.populacao) AS populacao,"
        " count(*) AS emendas, sum(coalesce(pg.v, 0)) AS repassado,"
        " count(*) FILTER (WHERE a.status = 'verde') AS verde, count(*) FILTER (WHERE a.status = 'amarelo') AS amarelo,"
        " count(*) FILTER (WHERE a.status = 'vermelho') AS vermelho, count(*) FILTER (WHERE a.status = 'azul') AS azul,"
        " count(*) FILTER (WHERE a.status = 'laranja') AS laranja,"
        " count(*) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza"
        + base
        + " GROUP BY en.codigo_ibge ORDER BY repassado DESC LIMIT :lim OFFSET :off",
        params,
    )
    for i in itens:
        i["status"] = status_predominante(i)
    return {"total": total, "pagina": pagina, "tamanho": tamanho, "itens": itens}


def partidos(conn: Connection) -> list[str]:
    return [
        r[0]
        for r in conn.execute(
            text(
                "SELECT DISTINCT pr.partido FROM parlamentar pr JOIN parlamentar_autor pa ON pa.id_parlamentar = pr.id"
                " WHERE pr.partido IS NOT NULL ORDER BY 1"
            )
        )
    ]


def listar_parlamentares(
    conn: Connection,
    busca: str | None,
    pagina: int,
    tamanho: int,
    uf: str | None = None,
    casa: str | None = None,
    partido: str | None = None,
) -> dict:
    params = {
        "busca": f"%{busca}%" if busca else None,
        "uf": uf.upper() if uf else None,
        "casa": casa,
        "partido": partido.upper() if partido else None,
        "lim": tamanho,
        "off": (pagina - 1) * tamanho,
    }
    base = (
        " FROM plano_acao p LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao"
        " LEFT JOIN parlamentar_autor pa ON pa.nome_autor = p.parlamentar_nome"
        " LEFT JOIN parlamentar pr ON pr.id = pa.id_parlamentar"
        " LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true"
        " WHERE p.ano_plano_acao >= 2024 AND p.parlamentar_nome IS NOT NULL"
        " AND (CAST(:busca AS text) IS NULL"
        "      OR unaccent_simples(p.parlamentar_nome) ILIKE unaccent_simples(:busca))"
        " AND (CAST(:uf AS text) IS NULL OR pr.uf = :uf)"
        " AND (CAST(:casa AS text) IS NULL OR pr.casa = :casa)"
        " AND (CAST(:partido AS text) IS NULL OR upper(pr.partido) = :partido)"
    )
    total = conn.execute(text("SELECT count(DISTINCT p.parlamentar_nome)" + base), params).scalar_one()
    itens = _linhas(
        conn,
        "SELECT p.parlamentar_nome AS nome, count(*) AS emendas, sum(coalesce(pg.v, 0)) AS repassado,"
        " array_agg(DISTINCT p.uf_beneficiario) AS ufs, min(pr.uf) AS uf_parlamentar, min(pr.partido) AS partido,"
        " min(pr.casa) AS casa, min(pr.url_foto) AS url_foto,"
        " count(*) FILTER (WHERE a.status = 'verde') AS verde, count(*) FILTER (WHERE a.status = 'amarelo') AS amarelo,"
        " count(*) FILTER (WHERE a.status = 'vermelho') AS vermelho, count(*) FILTER (WHERE a.status = 'azul') AS azul,"
        " count(*) FILTER (WHERE a.status = 'laranja') AS laranja,"
        " count(*) FILTER (WHERE a.status = 'cinza' OR a.status IS NULL) AS cinza"
        + base
        + " GROUP BY p.parlamentar_nome ORDER BY repassado DESC LIMIT :lim OFFSET :off",
        params,
    )
    for i in itens:
        i["status"] = status_predominante(i)
    return {"total": total, "pagina": pagina, "tamanho": tamanho, "itens": itens}


def _ultima(conn: Connection, padrao: str) -> Any:
    return limpar(
        conn.execute(
            text("SELECT max(coalesce(fim, inicio)) FROM execucao_job WHERE tipo LIKE :p AND status = 'concluido'"),
            {"p": padrao},
        ).scalar()
    )


def coleta(conn: Connection) -> list[dict[str, Any]]:
    """Resumo do que já foi coletado, por fonte: quantidades, período abrangido e última coleta concluída."""

    def um(sql: str, params: dict | None = None) -> dict[str, Any]:
        return limpar(dict(conn.execute(text(sql), params or {}).one()._mapping))

    tg = um(
        "SELECT (SELECT count(*) FROM plano_acao WHERE ano_plano_acao >= 2024) AS planos,"
        " (SELECT min(ano_plano_acao) FROM plano_acao WHERE ano_plano_acao >= 2024) AS ano_inicial,"
        " (SELECT max(ano_plano_acao) FROM plano_acao) AS ano_final,"
        " (SELECT count(*) FROM executor) AS executores, (SELECT count(*) FROM meta) AS metas,"
        " (SELECT count(*) FROM empenho) AS empenhos, (SELECT count(*) FROM pagamento) AS pagamentos,"
        " (SELECT min(data_pagamento) FROM pagamento) AS pagamento_inicial,"
        " (SELECT max(data_pagamento) FROM pagamento) AS pagamento_final,"
        " (SELECT sum(valor) FROM pagamento) AS valor_pago,"
        " (SELECT count(*) FROM relatorio_gestao) AS relatorios"
    )
    portal = um(
        "SELECT count(*) AS emendas, min(ano) AS ano_inicial, max(ano) AS ano_final, sum(valor_pago) AS valor_pago,"
        " max(origem) AS origem, (SELECT count(*) FROM plano_acao WHERE objeto_declarado IS NOT NULL) AS objetos"
        " FROM emenda"
    )
    pncp = um(
        "SELECT count(*) FILTER (WHERE fonte = 'pncp_contrato') AS contratos,"
        " count(*) FILTER (WHERE fonte = 'pncp_contratacao') AS contratacoes,"
        " min(data_publicacao) AS inicio, max(data_publicacao) AS fim,"
        " (SELECT count(*) FROM cobertura_pncp) AS cnpjs_consultados,"
        " (SELECT count(*) FROM cobertura_pncp WHERE contratos_encontrados > 0) AS cnpjs_com_registro"
        " FROM evidencia WHERE fonte IN ('pncp_contrato', 'pncp_contratacao')"
    )
    pncp["cnpjs_monitorados"] = conn.execute(
        text(
            "SELECT count(*) FROM (SELECT cnpj_beneficiario FROM plano_acao WHERE ano_plano_acao >= 2024"
            " UNION SELECT e.cnpj_executor FROM executor e JOIN plano_acao p USING (id_plano_acao)"
            " WHERE p.ano_plano_acao >= 2024) x"
        )
    ).scalar_one()
    qd = um(
        "SELECT count(*) AS trechos, count(DISTINCT codigo_ibge) AS municipios_com_trechos,"
        " min(data_publicacao) AS inicio, max(data_publicacao) AS fim,"
        " (SELECT count(*) FROM municipio WHERE coberto_querido_diario) AS territorios_cobertos,"
        " (SELECT count(*) FROM ente WHERE coberto_querido_diario) AS entes_cobertos"
        " FROM evidencia WHERE fonte = 'querido_diario'"
    )
    tces = _linhas(
        conn,
        "SELECT upper(split_part(id_externo, ':', 1)) AS uf, count(*) AS contratos, min(data_publicacao) AS inicio,"
        " max(data_publicacao) AS fim, count(DISTINCT cnpj_orgao) AS entes FROM evidencia WHERE fonte = 'tce_contrato'"
        " GROUP BY 1 ORDER BY 1",
    )
    congresso = um(
        "SELECT count(*) FILTER (WHERE casa = 'camara') AS deputados,"
        " count(*) FILTER (WHERE casa = 'senado') AS senadores,"
        " (SELECT count(*) FROM parlamentar_autor) AS autores_ligados,"
        " (SELECT count(DISTINCT parlamentar_nome) FROM plano_acao WHERE ano_plano_acao >= 2024) AS autores"
        " FROM parlamentar"
    )
    ibge = um("SELECT count(*) AS municipios, max(ano_populacao) AS ano_populacao FROM municipio")
    return [
        {
            "fonte": "transferegov",
            "nome": "Transferegov — Transferências Especiais",
            "url": "https://api.transferegov.gestao.gov.br/transferenciasespeciais/",
            "periodo": [tg["pagamento_inicial"], tg["pagamento_final"]],
            "ultima_coleta": _ultima(conn, "%transferegov%"),
            "numeros": tg,
        },
        {
            "fonte": "portal",
            "nome": "Portal da Transparência (CGU)",
            "url": "https://portaldatransparencia.gov.br/emendas",
            "periodo": [portal["ano_inicial"], portal["ano_final"]],
            "ultima_coleta": _ultima(conn, "%portal%"),
            "numeros": portal,
        },
        {
            "fonte": "pncp",
            "nome": "PNCP — contratos e contratações",
            "url": "https://pncp.gov.br",
            "periodo": [pncp["inicio"], pncp["fim"]],
            "ultima_coleta": _ultima(conn, "%pncp%"),
            "numeros": pncp,
        },
        {
            "fonte": "tce",
            "nome": "Tribunais de Contas (dados abertos)",
            "url": "https://dados.tce.rs.gov.br",
            "periodo": [
                min((t["inicio"] for t in tces if t["inicio"]), default=None),
                max((t["fim"] for t in tces if t["fim"]), default=None),
            ],
            "ultima_coleta": _ultima(conn, "carga:tce%"),
            "numeros": {"contratos": sum(t["contratos"] for t in tces), "por_uf": tces},
        },
        {
            "fonte": "querido_diario",
            "nome": "Querido Diário (Open Knowledge Brasil)",
            "url": "https://queridodiario.ok.org.br",
            "periodo": [qd["inicio"], qd["fim"]],
            "ultima_coleta": _ultima(conn, "querido_diario%"),
            "numeros": qd,
        },
        {
            "fonte": "congresso",
            "nome": "Câmara dos Deputados e Senado Federal",
            "url": "https://dadosabertos.camara.leg.br",
            "periodo": ["2023-02-01", None],
            "ultima_coleta": _ultima(conn, "carga:congresso"),
            "numeros": congresso,
        },
        {
            "fonte": "ibge",
            "nome": "IBGE",
            "url": "https://servicodados.ibge.gov.br/api/docs",
            "periodo": [ibge["ano_populacao"], ibge["ano_populacao"]],
            "ultima_coleta": _ultima(conn, "%ibge%"),
            "numeros": ibge,
        },
    ]
