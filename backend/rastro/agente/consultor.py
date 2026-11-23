"""Consultor do portal: responde perguntas gerais sobre os dados públicos do Rastro da Emenda.

Mesmo laço de ferramentas do assistente da ficha (`assistente.conversar`), com ferramentas somente leitura que
reaproveitam as consultas da API: panorama, busca de emendas, rankings, município, parlamentar, ficha e cobertura.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import Connection, text

from rastro.agente.assistente import _cliente, _ficha_compacta, conversar
from rastro.api import consultas
from rastro.api.consultas import limpar
from rastro.config import config
from rastro.log import log
from rastro.motor.ia import _cache_gravar, _cache_ler

VERSAO = "4"  # 4: laranja (em revisão). 2: fontes oficiais públicas. 3: relatório de gestão como execução declarada
LIMITE_LISTA = 20

SISTEMA = """Você é o consultor de dados do Rastro da Emenda ({site}), portal público que acompanha a execução das \
transferências especiais ("emendas Pix") destinadas a municípios, estados e DF, de 2024 até hoje. Você responde \
perguntas de cidadãos, jornalistas e órgãos de controle sobre os dados do portal.

Como os dados funcionam:
- Cada plano de ação (emenda) recebe um status: verde (execução com evidência: contrato compatível cobrindo ≥ 70% do \
repasse), amarelo (evidência parcial, ou execução declarada pelo ente no relatório de gestão final \
sem documento independente), laranja (em revisão: documento possivelmente compatível, \
mas com confiança abaixo de 60%; não é evidência nem ausência), vermelho (indício para apuração: pago há mais \
de 180 dias sem evidência nas \
fontes que cobrem o ente), azul (ente sem fonte pública para verificar — neutro) e cinza (dados insuficientes, \
pagamento recente ou verificação em andamento).
- Fontes: Transferegov e Portal da Transparência (emendas e pagamentos), PNCP (contratos e licitações), Tribunais de \
Contas com dados abertos (RS, SP, PI, RN), Querido Diário (diários oficiais), Câmara e Senado (perfil dos autores).
- A verificação no PNCP ainda está em andamento para parte dos entes; muitos cinzas são "verificação em andamento". \
Diga isso quando ajudar a interpretar números.

Regras obrigatórias:
- Use somente o que as ferramentas devolverem. Não invente números, nomes, valores nem documentos. Se a ferramenta \
não trouxer o dado, diga que ele não está disponível.
- Linguagem: "indício para apuração" e "sem evidência encontrada nas fontes consultadas". Nunca afirme \
irregularidade, desvio, fraude, crime ou má-fé, nem atribua culpa a pessoas — nem a parlamentares, nem a gestores.
- Ao citar emendas, inclua o link da ficha: {site}/emendas/<id_plano_acao>. Para municípios: \
{site}/municipios/<codigo_ibge>. Para parlamentares: {site}/parlamentares/<nome com espaços como %20>.
- Valores em reais no formato brasileiro (R$ 1,2 milhão; R$ 350 mil). Datas em DD/MM/AAAA.
- Não exponha dados pessoais (CPF aparece mascarado; não tente reconstruí-lo).
- Responda em português do Brasil, de forma objetiva, com listas ou tabelas curtas em markdown quando ajudar.
- Se a pergunta não tiver relação com emendas, contratos ou os dados do portal, diga educadamente que só pode ajudar \
nesse tema."""

_FILTROS = {
    "uf": {"type": "string", "description": "sigla da UF do beneficiário, ex.: 'BA'"},
    "municipio": {"type": "string", "description": "código IBGE ou parte do nome do município"},
    "parlamentar": {"type": "string", "description": "parte do nome do parlamentar autor"},
    "ano": {"type": "integer", "description": "ano da emenda"},
    "status": {"type": "string", "enum": ["verde", "amarelo", "laranja", "vermelho", "azul", "cinza"]},
    "alerta": {"type": "string", "enum": ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]},
    "esfera": {"type": "string", "enum": ["municipal", "estadual"], "description": "estadual inclui o DF"},
    "busca": {"type": "string", "description": "texto livre: beneficiário, objeto (ex.: 'ambulância'), número"},
}

FERRAMENTAS = [
    {
        "name": "panorama_geral",
        "description": (
            "Totais do portal: número de emendas, valores previstos e repassados, entes, parlamentares, contagem por "
            "status, percentual com evidência, municípios com mais valor em vermelho e quadro por UF."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "buscar_emendas",
        "description": (
            "Lista emendas com filtros (UF, município, parlamentar, ano, status, alerta, esfera, texto) e devolve o "
            "total, a contagem por status do recorte e até 20 itens ordenados."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_FILTROS,
                "ordem": {"type": "string", "enum": ["repassado", "recentes", "antigas", "valor"]},
                "limite": {"type": "integer", "minimum": 1, "maximum": LIMITE_LISTA},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ranking",
        "description": (
            "Agrega emendas por UF, município, parlamentar, partido ou beneficiário e ordena por uma métrica "
            "(quantidade, valor repassado, quantidade ou valor por status). Aceita filtros de UF, esfera, ano, "
            "parlamentar e status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agrupar_por": {
                    "type": "string",
                    "enum": ["uf", "municipio", "parlamentar", "partido", "beneficiario"],
                },
                "metrica": {
                    "type": "string",
                    "enum": [
                        "emendas",
                        "repassado",
                        "verde",
                        "amarelo",
                        "laranja",
                        "vermelho",
                        "azul",
                        "cinza",
                        "valor_verde",
                        "valor_amarelo",
                        "valor_laranja",
                        "valor_vermelho",
                        "valor_azul",
                        "valor_cinza",
                    ],  # fmt: skip
                },
                "uf": _FILTROS["uf"],
                "esfera": _FILTROS["esfera"],
                "ano": _FILTROS["ano"],
                "parlamentar": _FILTROS["parlamentar"],
                "status": _FILTROS["status"],
                "limite": {"type": "integer", "minimum": 1, "maximum": LIMITE_LISTA},
            },
            "required": ["agrupar_por", "metrica"],
            "additionalProperties": False,
        },
    },
    {
        "name": "dados_do_municipio",
        "description": "Dados de um município (nome ou código IBGE): população, cobertura, status e maiores emendas.",
        "input_schema": {
            "type": "object",
            "properties": {"municipio": {"type": "string"}, "uf": _FILTROS["uf"]},
            "required": ["municipio"],
            "additionalProperties": False,
        },
    },
    {
        "name": "dados_do_parlamentar",
        "description": "Perfil (partido, UF, casa), totais, status e maiores emendas de um parlamentar autor.",
        "input_schema": {
            "type": "object",
            "properties": {"nome": {"type": "string"}},
            "required": ["nome"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ficha_da_emenda",
        "description": "Ficha completa de uma emenda pelo id_plano_acao: objeto, pagamentos, documentos avaliados.",
        "input_schema": {
            "type": "object",
            "properties": {"id_plano_acao": {"type": "integer"}},
            "required": ["id_plano_acao"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cobertura_das_fontes",
        "description": "O que já foi coletado por fonte (quantidade, período, última coleta) e a contagem de alertas.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

DIMENSOES = {
    "uf": "p.uf_beneficiario",
    "municipio": "CASE WHEN en.esfera = 'municipal' THEN concat_ws('/', m.nome, m.uf) END",
    "parlamentar": "p.parlamentar_nome",
    "partido": "pr.partido",
    "beneficiario": "p.nome_beneficiario",
}
_STATUS = ("verde", "amarelo", "laranja", "vermelho", "azul", "cinza")
_ST = "coalesce(a.status::text, 'cinza')"


def ranking(conn: Connection, entrada: dict[str, Any]) -> list[dict[str, Any]]:
    dim = DIMENSOES[entrada["agrupar_por"]]
    metrica = entrada["metrica"]
    if metrica not in ("emendas", "repassado", *_STATUS, *(f"valor_{s}" for s in _STATUS)):
        raise ValueError("métrica inválida")
    contagens = ", ".join(f"count(*) FILTER (WHERE {_ST} = '{s}') AS {s}" for s in _STATUS)
    valores = ", ".join(f"sum(coalesce(pg.v, 0)) FILTER (WHERE {_ST} = '{s}') AS valor_{s}" for s in _STATUS)
    f = consultas.filtros(
        uf=entrada.get("uf"),
        parlamentar=entrada.get("parlamentar"),
        ano=entrada.get("ano"),
        status=entrada.get("status"),
        esfera=entrada.get("esfera"),
    )
    sql = f"""
SELECT {dim} AS grupo, count(*) AS emendas, sum(coalesce(pg.v, 0)) AS repassado, {contagens}, {valores}
FROM plano_acao p
LEFT JOIN ente en ON en.cnpj = p.cnpj_beneficiario
LEFT JOIN municipio m ON m.codigo_ibge = en.codigo_ibge
LEFT JOIN avaliacao a ON a.id_plano_acao = p.id_plano_acao
LEFT JOIN parlamentar_autor pa ON pa.nome_autor = p.parlamentar_nome
LEFT JOIN parlamentar pr ON pr.id = pa.id_parlamentar
LEFT JOIN LATERAL (SELECT sum(valor) v FROM pagamento g WHERE g.id_plano_acao = p.id_plano_acao) pg ON true
WHERE p.ano_plano_acao >= 2024
  AND (CAST(:uf AS text) IS NULL OR p.uf_beneficiario = :uf)
  AND (CAST(:parlamentar AS text) IS NULL
       OR unaccent_simples(p.parlamentar_nome) ILIKE unaccent_simples(:parlamentar_like))
  AND (CAST(:ano AS integer) IS NULL OR p.emenda_ano = :ano)
  AND (CAST(:status AS text) IS NULL OR {_ST} = :status)
  AND (CAST(:esfera AS text) IS NULL OR en.esfera = :esfera)
GROUP BY 1 HAVING {dim} IS NOT NULL
ORDER BY {metrica} DESC NULLS LAST, 1 LIMIT :lim"""
    limite = min(int(entrada.get("limite") or 10), LIMITE_LISTA)
    return [limpar(dict(r._mapping)) for r in conn.execute(text(sql), {**f, "lim": limite})]


def _enxugar(emendas: list[dict[str, Any]], n: int = 15) -> list[dict[str, Any]]:
    campos = ("id_plano_acao", "emenda_numero", "ano", "parlamentar", "beneficiario", "uf", "municipio", "repassado",
              "primeiro_pagamento", "status", "alertas", "objeto")  # fmt: skip
    return [{k: e.get(k) for k in campos} for e in emendas[:n]]


def executar_ferramenta(conn: Connection, nome: str, entrada: dict[str, Any]) -> Any:
    if nome == "panorama_geral":
        r = consultas.resumo(conn)
        r["por_uf"] = [{k: v for k, v in u.items() if not k.endswith("_valor") or k == "vermelho_valor"}
                       for u in r.get("por_uf", [])]  # fmt: skip
        return r
    if nome == "buscar_emendas":
        f = {k: entrada.get(k) for k in _FILTROS}
        limite = min(int(entrada.get("limite") or 10), LIMITE_LISTA)
        lista = consultas.listar_emendas(conn, 1, limite, entrada.get("ordem") or "repassado", **f)
        return {
            "total": lista["total"],
            "por_status": consultas.resumo_status(conn, **f),
            "itens": _enxugar(lista["itens"], limite),
        }
    if nome == "ranking":
        return ranking(conn, entrada)
    if nome == "dados_do_municipio":
        alvo = str(entrada.get("municipio", "")).strip()
        if not alvo.isdigit():
            achados = consultas.listar_municipios(conn, alvo, entrada.get("uf"), 1, 5)["itens"]
            if not achados:
                return {"erro": "município não encontrado entre os que receberam emendas Pix"}
            alvo = achados[0]["codigo_ibge"]
            outros = [f"{a['nome']}/{a['uf']}" for a in achados[1:]]
        else:
            outros = []
        info = consultas.municipio(conn, alvo)
        if not info:
            return {"erro": "município não encontrado"}
        info["emendas"] = _enxugar(info["emendas"])
        info["outros_municipios_com_nome_parecido"] = outros
        return info
    if nome == "dados_do_parlamentar":
        info = consultas.parlamentar(conn, str(entrada.get("nome", "")))
        if not info:
            return {"erro": "parlamentar não encontrado entre os autores de emendas Pix"}
        info["emendas"] = _enxugar(info["emendas"])
        if info.get("perfil"):
            info["perfil"].pop("url_foto", None)
        return info
    if nome == "ficha_da_emenda":
        ficha = consultas.ficha_emenda(conn, int(entrada.get("id_plano_acao", 0)))
        return _ficha_compacta(ficha) if ficha else {"erro": "emenda não encontrada"}
    if nome == "cobertura_das_fontes":
        return {"coleta": consultas.coleta(conn), "alertas": consultas.alertas(conn)}
    return {"erro": f"ferramenta desconhecida: {nome}"}


def responder(conn: Connection, pergunta: str, historico: list[dict[str, str]] | None = None, cliente=None) -> dict:
    """Devolve {resposta, ferramentas, modelo, cache}."""
    if not (cliente or config().anthropic_api_key):
        raise RuntimeError("ANTHROPIC_API_KEY não configurada")
    historico = (historico or [])[-8:]
    modelo = config().modelo_analise
    versao_dados = consultas.ultima_atualizacao(conn)
    chave = hashlib.sha256(
        json.dumps(
            ["consultor", VERSAO, modelo, versao_dados, historico, pergunta], sort_keys=True, default=str
        ).encode()
    ).hexdigest()
    em_cache = _cache_ler(conn, chave)
    if em_cache:
        return {**em_cache, "cache": True}

    mensagens: list[dict[str, Any]] = []
    for m in historico:
        if m.get("papel") in ("usuario", "assistente") and m.get("texto"):
            mensagens.append({"role": "user" if m["papel"] == "usuario" else "assistant", "content": m["texto"][:4000]})
    mensagens.append({"role": "user", "content": pergunta[:2000]})

    site = (config().url_site or "https://rastrodaemenda.com.br").rstrip("/")
    texto, usadas, resposta = conversar(
        cliente or _cliente(),
        modelo,
        SISTEMA.format(site=site),
        FERRAMENTAS,
        mensagens,
        lambda nome, entrada: executar_ferramenta(conn, nome, entrada),
        "Não consegui responder a esta pergunta. Reformule com foco nas emendas Pix e nos dados do portal.",
    )
    resultado = {"resposta": texto, "ferramentas": usadas, "modelo": getattr(resposta, "model", modelo)}
    if resposta is not None and resposta.stop_reason != "refusal":
        _cache_gravar(conn, chave, modelo, resultado)
    log("agente", "consultor:resposta", ferramentas=len(usadas), caracteres=len(texto))
    return {**resultado, "cache": False}
