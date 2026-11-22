"""Assistente de análise: responde perguntas sobre uma emenda Pix com base na ficha e em ferramentas de consulta.

Laço manual de uso de ferramentas (SDK anthropic, Messages API). As ferramentas só leem o banco do projeto
(dados públicos já coletados). Respostas cacheadas em `cache_ia` por hash(pergunta + histórico + ficha).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import Connection, text

from rastro.api.consultas import ficha_emenda, limpar
from rastro.config import config
from rastro.log import log
from rastro.motor.ia import _cache_gravar, _cache_ler

VERSAO = "1"
MAX_ITERACOES = 6
MAX_TOKENS = 4000

SISTEMA = """Você é o assistente de análise do Rastro da Emenda, sistema que acompanha a execução das transferências \
especiais ("emendas Pix") de 2024 até hoje. Você ajuda jornalistas, conselheiros, controladores e cidadãos a entender \
uma emenda específica e a redigir o dossiê.

Regras obrigatórias:
- Use somente a ficha fornecida e o que as ferramentas devolverem. Não invente dados, valores, datas nem documentos.
- Linguagem: fale em "indício para apuração" e "sem evidência encontrada nas fontes consultadas". Nunca afirme \
irregularidade, desvio, fraude, crime ou má-fé, nem atribua culpa a pessoas.
- Cite a fonte de cada fato relevante com o link oficial quando houver (PNCP, Tribunal de Contas, Querido Diário, \
Transferegov, Portal da Transparência).
- Explique limitações: ausência de evidência pode significar publicação fora das fontes consultadas; classificações \
"heurísticas" são automáticas e merecem conferência.
- Não exponha dados pessoais (CPF aparece mascarado; não tente reconstruí-lo).
- Responda em português do Brasil, de forma objetiva, com parágrafos curtos e listas quando ajudar. Ao redigir texto \
para o dossiê, use tom técnico e neutro.
- Se a pergunta não tiver relação com emendas, contratos ou o dossiê, diga educadamente que só pode ajudar \
nesse tema."""

FERRAMENTAS = [
    {
        "name": "buscar_documentos_do_ente",
        "description": (
            "Busca contratos, contratações e trechos de diários oficiais já coletados para os CNPJs desta emenda "
            "(beneficiário e executores). Use para procurar documentos além dos candidatos já avaliados na ficha, "
            "por palavras do objeto (ex.: 'pavimentação', 'ambulância')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "termos": {"type": "string", "description": "palavras a procurar no objeto do documento"},
                "data_inicial": {"type": "string", "description": "AAAA-MM-DD; padrão: 30 dias antes do 1º pagamento"},
            },
            "required": ["termos"],
            "additionalProperties": False,
        },
    },
    {
        "name": "outras_emendas_do_beneficiario",
        "description": "Lista outras emendas Pix (desde 2024) recebidas pelo mesmo beneficiário, com status e valor.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "detalhar_documento",
        "description": "Mostra todos os campos de um documento (evidência) pelo id que aparece na ficha ou na busca.",
        "input_schema": {
            "type": "object",
            "properties": {"id_evidencia": {"type": "integer"}},
            "required": ["id_evidencia"],
            "additionalProperties": False,
        },
    },
]


def _ficha_compacta(f: dict[str, Any]) -> dict[str, Any]:
    """Recorta a ficha para caber no contexto sem perder o essencial."""
    campos = [
        "id_plano_acao", "codigo_plano_acao", "emenda_numero", "ano", "parlamentar", "beneficiario", "uf",
        "municipio", "populacao", "esfera", "situacao", "valor_previsto", "valor_custeio", "valor_investimento",
        "repassado", "primeiro_pagamento", "status", "alertas_detalhados", "justificativa", "fontes",
    ]  # fmt: skip
    compacta = {k: f.get(k) for k in campos}
    compacta["objeto_declarado"] = (f.get("objeto_completo") or "")[:3000]
    compacta["executores"] = [
        {k: e.get(k) for k in ("cnpj_executor", "nome_executor", "objeto")} for e in f.get("executores", [])
    ]
    compacta["metas"] = [(m.get("descricao") or m.get("nome") or "")[:300] for m in f.get("metas", [])][:15]
    compacta["pagamentos"] = f.get("pagamentos", [])[:20]
    compacta["relatorios_gestao"] = f.get("relatorios_gestao", [])[:10]
    compacta["evidencias_avaliadas"] = [
        {
            k: e.get(k)
            for k in (
                "id",
                "fonte",
                "data_publicacao",
                "objeto",
                "valor",
                "modalidade",
                "fornecedor_nome",
                "fornecedor_documento",
                "url",
                "confianca",
                "compativel",
                "conta_como_evidencia",
                "metodo",
                "justificativa_ia",
            )
        }  # fmt: skip
        for e in f.get("evidencias", [])
    ]
    return limpar(compacta)


def _cnpjs(conn: Connection, id_plano: int) -> list[str]:
    linhas = conn.execute(
        text(
            "SELECT cnpj_beneficiario FROM plano_acao WHERE id_plano_acao = :i"
            " UNION SELECT cnpj_executor FROM executor WHERE id_plano_acao = :i AND cnpj_executor IS NOT NULL"
        ),
        {"i": id_plano},
    )
    return [r[0] for r in linhas if r[0]]


def executar_ferramenta(conn: Connection, id_plano: int, ficha: dict[str, Any], nome: str, entrada: dict) -> Any:
    if nome == "buscar_documentos_do_ente":
        termos = [t for t in str(entrada.get("termos", "")).split() if len(t) >= 3][:6]
        desde = entrada.get("data_inicial") or ficha.get("primeiro_pagamento") or "2024-01-01"
        filtro = " AND ".join(
            f"unaccent_simples(coalesce(objeto, trecho, '')) ILIKE unaccent_simples(:t{i})" for i in range(len(termos))
        )
        params = {
            "c": _cnpjs(conn, id_plano),
            "d": str(desde)[:10],
            **{f"t{i}": f"%{t}%" for i, t in enumerate(termos)},
        }
        sql = (
            "SELECT id, fonte::text AS fonte, data_publicacao, left(coalesce(objeto, trecho), 400) AS objeto, valor,"
            " modalidade, url FROM evidencia WHERE cnpj_orgao = ANY(:c) AND data_publicacao >= CAST(:d AS date) - 30"
            + (f" AND {filtro}" if filtro else "")
            + " ORDER BY data_publicacao DESC LIMIT 12"
        )
        return limpar([dict(r._mapping) for r in conn.execute(text(sql), params)])
    if nome == "outras_emendas_do_beneficiario":
        sql = (
            "SELECT p.id_plano_acao, p.emenda_numero, p.parlamentar_nome, coalesce(a.status::text, 'cinza') AS status,"
            " (SELECT sum(valor) FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) AS repassado,"
            " left(p.objeto_declarado, 160) AS objeto FROM plano_acao p LEFT JOIN avaliacao a USING (id_plano_acao)"
            " WHERE p.cnpj_beneficiario = (SELECT cnpj_beneficiario FROM plano_acao WHERE id_plano_acao = :i)"
            " AND p.id_plano_acao <> :i AND p.ano_plano_acao >= 2024 ORDER BY repassado DESC NULLS LAST LIMIT 15"
        )
        return limpar([dict(r._mapping) for r in conn.execute(text(sql), {"i": id_plano})])
    if nome == "detalhar_documento":
        sql = (
            "SELECT id, fonte::text AS fonte, id_externo, cnpj_orgao, data_publicacao, data_assinatura, objeto, valor,"
            " modalidade, tipo_ato, situacao, fornecedor_documento, fornecedor_nome, url, trecho FROM evidencia"
            " WHERE id = :e AND cnpj_orgao = ANY(:c)"
        )
        linha = conn.execute(text(sql), {"e": int(entrada.get("id_evidencia", 0)), "c": _cnpjs(conn, id_plano)}).first()
        return limpar(dict(linha._mapping)) if linha else {"erro": "documento não encontrado entre os desta emenda"}
    return {"erro": f"ferramenta desconhecida: {nome}"}


def _cliente():
    import anthropic

    cfg = config()
    cabecalhos = {"anthropic-workspace-id": cfg.anthropic_workspace_id} if cfg.anthropic_workspace_id else None
    return anthropic.Anthropic(api_key=cfg.anthropic_api_key, max_retries=3, default_headers=cabecalhos)


def _criar(cli, **kw):
    """Chamada com fallback no servidor em caso de recusa (beta); sem suporte, faz a chamada simples."""
    try:
        return cli.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"], extra_body={"fallbacks": "default"}, **kw
        )
    except Exception as exc:  # fallback indisponível na conta/SDK: segue sem ele
        if "fallback" not in str(exc).lower():
            raise
        return cli.messages.create(**kw)


def conversar(cli, modelo: str, sistema: str, ferramentas: list, mensagens: list, executar, msg_recusa: str):
    """Laço manual de ferramentas. Devolve (texto, ferramentas usadas, última resposta)."""
    usadas: list[str] = []
    resposta = None
    for _ in range(MAX_ITERACOES):
        resposta = _criar(
            cli,
            model=modelo,
            max_tokens=MAX_TOKENS,
            system=sistema,
            tools=ferramentas,
            messages=mensagens,
            output_config={"effort": "medium"},
        )
        if resposta.stop_reason == "refusal":
            break
        if resposta.stop_reason == "pause_turn":
            mensagens.append({"role": "assistant", "content": resposta.content})
            continue
        chamadas = [b for b in resposta.content if getattr(b, "type", None) == "tool_use"]
        if resposta.stop_reason != "tool_use" or not chamadas:
            break
        mensagens.append({"role": "assistant", "content": resposta.content})
        resultados = []
        for chamada in chamadas:
            usadas.append(chamada.name)
            try:
                saida = executar(chamada.name, dict(chamada.input or {}))
                resultados.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": chamada.id,
                        "content": json.dumps(saida, ensure_ascii=False, default=str)[:15000],
                    }
                )
            except Exception as exc:
                log("agente", "ferramenta:erro", ferramenta=chamada.name, erro=repr(exc)[:200])
                resultados.append(
                    {"type": "tool_result", "tool_use_id": chamada.id, "content": "erro ao consultar", "is_error": True}
                )
        mensagens.append({"role": "user", "content": resultados})

    if resposta is None or resposta.stop_reason == "refusal":
        texto = msg_recusa
    else:
        texto = "\n".join(b.text for b in resposta.content if getattr(b, "type", None) == "text").strip()
        texto = texto or "Não encontrei informação suficiente nos dados disponíveis para responder."
    return texto, usadas, resposta


def responder(
    conn: Connection, id_plano: int, pergunta: str, historico: list[dict[str, str]] | None = None, cliente=None
) -> dict[str, Any]:
    """Devolve {resposta, ferramentas, modelo, cache}. Levanta LookupError se a emenda não existir."""
    if not (cliente or config().anthropic_api_key):
        raise RuntimeError("ANTHROPIC_API_KEY não configurada")
    ficha = ficha_emenda(conn, id_plano)
    if not ficha:
        raise LookupError("emenda não encontrada")
    compacta = _ficha_compacta(ficha)
    historico = (historico or [])[-8:]
    modelo = config().modelo_analise
    chave = hashlib.sha256(
        json.dumps(
            [VERSAO, modelo, compacta, historico, pergunta], sort_keys=True, default=str, ensure_ascii=False
        ).encode()
    ).hexdigest()
    em_cache = _cache_ler(conn, chave)
    if em_cache:
        return {**em_cache, "cache": True}

    mensagens: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": "Ficha da emenda (JSON):\n" + json.dumps(compacta, ensure_ascii=False, default=str),
        },
        {"role": "assistant", "content": "Li a ficha. Pode perguntar."},
    ]
    for m in historico:
        if m.get("papel") in ("usuario", "assistente") and m.get("texto"):
            mensagens.append({"role": "user" if m["papel"] == "usuario" else "assistant", "content": m["texto"][:4000]})
    mensagens.append({"role": "user", "content": pergunta[:2000]})

    texto, usadas, resposta = conversar(
        cliente or _cliente(),
        modelo,
        SISTEMA,
        FERRAMENTAS,
        mensagens,
        lambda nome, entrada: executar_ferramenta(conn, id_plano, ficha, nome, entrada),
        "Não consegui responder a esta pergunta. Reformule com foco na emenda, nos contratos ou no dossiê.",
    )
    resultado = {"resposta": texto, "ferramentas": usadas, "modelo": getattr(resposta, "model", modelo)}
    if resposta is not None and resposta.stop_reason != "refusal":
        _cache_gravar(conn, chave, modelo, resultado)
    log("agente", "resposta", plano=id_plano, ferramentas=len(usadas), caracteres=len(texto))
    return {**resultado, "cache": False}


PERGUNTA_DOSSIE = (
    "Redija a seção 'Análise assistida' do dossiê desta emenda, em até 4 parágrafos: (1) o que foi prometido e "
    "quanto foi repassado; (2) o que as fontes mostram sobre a execução, citando os documentos com link; "
    "(3) os alertas e o que precisa ser conferido; (4) limitações da verificação. Tom técnico e neutro."
)
