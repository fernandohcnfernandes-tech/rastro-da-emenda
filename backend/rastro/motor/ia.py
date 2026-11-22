"""Avaliação por IA (SDK anthropic, saída estruturada validada por Pydantic) com cache em `cache_ia`.

Sem ANTHROPIC_API_KEY, usa uma heurística transparente (similaridade + valor), marcada como tal no resultado.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text

from rastro.config import config
from rastro.log import log

VERSAO_PROMPT = "v1"
CONFIANCA_MINIMA = 0.6

TipoAto = Literal[
    "contrato",
    "extrato_contrato",
    "aviso_licitacao",
    "homologacao",
    "dispensa",
    "inexigibilidade",
    "licitacao",
    "outro",
]


class RespostaCorrespondencia(BaseModel):
    """Contrato da resposta da IA (docs/regras-e-semaforo.md)."""

    compativel: bool
    confianca: float = Field(ge=0, le=1)
    tipo_ato: TipoAto | None = None
    objeto_extraido: str | None = None
    valor_extraido: float | None = None
    fornecedor_cnpj: str | None = None
    justificativa: str
    trechos_citados: list[str] = Field(default_factory=list)


class RespostaGenericidade(BaseModel):
    generico: bool
    confianca: float = Field(ge=0, le=1)
    justificativa: str


SISTEMA = (
    "Você é analista de controle externo e ajuda a fiscalizar a execução de transferências especiais "
    "(emendas Pix). Compare o objeto declarado da emenda com o documento público fornecido. "
    "Responda só com base no texto recebido; cite trechos literais. Nunca afirme irregularidade, desvio ou "
    "fraude: fale em 'indício' e 'sem evidência encontrada nas fontes consultadas'. "
    "Confiança abaixo de 0,6 significa que o documento não deve contar como evidência."
)


def hash_entrada(modelo: str, tarefa: str, entrada: dict[str, Any]) -> str:
    bruto = json.dumps([VERSAO_PROMPT, modelo, tarefa, entrada], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(bruto.encode()).hexdigest()


def _cache_ler(conn, chave: str) -> dict | None:
    if conn is None:
        return None
    linha = conn.execute(text("SELECT resposta FROM cache_ia WHERE hash_entrada = :h"), {"h": chave}).first()
    return linha[0] if linha else None


def _cache_gravar(conn, chave: str, modelo: str, resposta: dict) -> None:
    if conn is None:
        return
    conn.execute(
        text(
            "INSERT INTO cache_ia (hash_entrada, modelo, resposta) VALUES (:h, :m, CAST(:r AS jsonb))"
            " ON CONFLICT (hash_entrada) DO NOTHING"
        ),
        {"h": chave, "m": modelo, "r": json.dumps(resposta, ensure_ascii=False)},
    )


def ia_disponivel() -> bool:
    return bool(config().anthropic_api_key)


def _cliente():
    import anthropic

    return anthropic.Anthropic(api_key=config().anthropic_api_key, max_retries=4)


def _chamar(modelo: str, prompt: str, formato: type[BaseModel], cliente=None) -> BaseModel:
    cli = cliente or _cliente()
    resposta = cli.messages.parse(
        model=modelo,
        max_tokens=2000,
        system=SISTEMA,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
        output_format=formato,
    )
    if resposta.stop_reason == "refusal" or resposta.parsed_output is None:
        raise RuntimeError(f"resposta sem saída estruturada (stop_reason={resposta.stop_reason})")
    return resposta.parsed_output


# ----------------------------------------------------------------------- heurística (sem chave)


def heuristica_correspondencia(
    similaridade: float, valor: Decimal | None, repassado: Decimal | None, tipo_ato: str | None
) -> RespostaCorrespondencia:
    """Regra transparente usada sem IA: similaridade de texto + coerência de valor."""
    razao = float(valor / repassado) if valor and repassado else None
    valor_coerente = razao is None or 0.5 <= razao <= 1.5
    confianca = min(0.95, 0.35 + similaridade * 1.2 + (0.1 if valor_coerente and razao is not None else 0.0))
    compativel = similaridade >= 0.20 and valor_coerente
    if not compativel:
        confianca = min(confianca, 0.55)
    partes = [f"similaridade textual {similaridade:.2f}"]
    if razao is not None:
        partes.append(f"valor equivale a {razao:.0%} do repassado")
    return RespostaCorrespondencia(
        compativel=compativel,
        confianca=round(confianca, 2),
        tipo_ato=tipo_ato if tipo_ato in TipoAto.__args__ else "outro",  # type: ignore[attr-defined]
        justificativa="Classificação heurística (IA não configurada): " + "; ".join(partes) + ".",
        trechos_citados=[],
    )


# ----------------------------------------------------------------------------- funções públicas


def avaliar_correspondencia(
    objeto_emenda: str,
    evidencia: dict[str, Any],
    similaridade: float,
    repassado: Decimal | None,
    conn=None,
    cliente=None,
) -> tuple[RespostaCorrespondencia, str]:
    """Devolve (resposta, método). Método: 'ia', 'cache' ou 'heuristica'."""
    rapido = evidencia.get("fonte") == "querido_diario"
    modelo = config().modelo_rapido if rapido else config().modelo_analise
    entrada = {
        "objeto_emenda": (objeto_emenda or "")[:3000],
        "valor_repassado": str(repassado) if repassado is not None else None,
        "fonte": evidencia.get("fonte"),
        "documento": (evidencia.get("trecho") or evidencia.get("objeto") or "")[:3000],
        "valor_documento": str(evidencia.get("valor")) if evidencia.get("valor") is not None else None,
        "modalidade": evidencia.get("modalidade"),
        "tipo_ato": evidencia.get("tipo_ato"),
    }
    if not (ia_disponivel() or cliente):
        return heuristica_correspondencia(similaridade, evidencia.get("valor"), repassado, evidencia.get("tipo_ato")), (
            "heuristica"
        )
    chave = hash_entrada(modelo, "correspondencia", entrada)
    em_cache = _cache_ler(conn, chave)
    if em_cache:
        return RespostaCorrespondencia.model_validate(em_cache), "cache"
    prompt = (
        "Objeto declarado da emenda Pix e valor repassado:\n"
        f"{json.dumps({k: entrada[k] for k in ('objeto_emenda', 'valor_repassado')}, ensure_ascii=False)}\n\n"
        "Documento público encontrado (contrato, contratação ou trecho de diário oficial):\n"
        f"{json.dumps({k: entrada[k] for k in ('fonte', 'documento', 'valor_documento', 'modalidade', 'tipo_ato')}, ensure_ascii=False)}\n\n"  # noqa: E501
        "O documento corresponde ao uso do recurso da emenda (mesmo objeto ou meta, valor coerente)? "
        "Preencha tipo_ato, objeto_extraido, valor_extraido e fornecedor_cnpj quando estiverem no documento."
    )
    try:
        resposta = _chamar(modelo, prompt, RespostaCorrespondencia, cliente)
    except Exception as exc:
        log("ia", "correspondencia:erro", erro=repr(exc)[:300])
        return heuristica_correspondencia(similaridade, evidencia.get("valor"), repassado, evidencia.get("tipo_ato")), (
            "heuristica"
        )
    _cache_gravar(conn, chave, modelo, resposta.model_dump())
    return resposta, "ia"


PALAVRAS_GENERICAS = set(
    """pavimentacao infraestrutura saude educacao manutencao custeio investimento obras diversos
    diversas geral aquisicao materiais servicos urbanismo cultura cultural agricultura desporto
    esporte lazer transporte assistencia social turismo seguranca saneamento habitacao ambiental
    gestao administracao consumo equipamentos permanente fortalecimento implementacao valorizacao
    melhorias melhoria acoes areas construcao reforma ampliacao atencao basica especializada media
    alta complexidade publica publicas publico rede municipio municipal secretaria fundo apoio""".split()
)


def heuristica_genericidade(objeto: str | None) -> RespostaGenericidade:
    from rastro.motor.pre_filtro import normalizar_texto

    palavras = normalizar_texto(objeto).split()
    especificas = [p for p in palavras if p not in PALAVRAS_GENERICAS]
    generico = len(palavras) == 0 or len(especificas) <= 2
    return RespostaGenericidade(
        generico=generico,
        confianca=0.7 if generico else 0.6,
        justificativa=(
            f"Classificação heurística: o objeto tem {len(especificas)} termo(s) específico(s) "
            f"além de categorias amplas."
        ),
    )


def avaliar_genericidade(objeto: str | None, conn=None, cliente=None) -> tuple[RespostaGenericidade, str]:
    """A2: o plano de trabalho é genérico demais para permitir verificar a execução?"""
    if not objeto or not (ia_disponivel() or cliente):
        return heuristica_genericidade(objeto), "heuristica"
    modelo = config().modelo_rapido
    entrada = {"objeto": objeto[:3000]}
    chave = hash_entrada(modelo, "genericidade", entrada)
    em_cache = _cache_ler(conn, chave)
    if em_cache:
        return RespostaGenericidade.model_validate(em_cache), "cache"
    prompt = (
        "Objeto declarado no plano de trabalho de uma emenda Pix:\n"
        f"{json.dumps(entrada, ensure_ascii=False)}\n\n"
        "Ele é genérico (ex.: só 'pavimentação', 'saúde', 'aquisição de materiais', lista de áreas sem obra, "
        "local ou bem identificável), a ponto de impedir verificar a execução? "
        "Responda generico=true nesse caso."
    )
    try:
        resposta = _chamar(modelo, prompt, RespostaGenericidade, cliente)
    except Exception as exc:
        log("ia", "genericidade:erro", erro=repr(exc)[:300])
        return heuristica_genericidade(objeto), "heuristica"
    _cache_gravar(conn, chave, modelo, resposta.model_dump())
    return resposta, "ia"
