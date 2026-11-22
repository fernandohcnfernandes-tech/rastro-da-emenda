"""Conector do Querido Diário (Open Knowledge Brasil) — só para municípios de até 20 mil habitantes.

Limite de referência: 60 requisições por minuto; respostas cacheadas em disco.
Endpoints: GET /cities (cobertura) e GET /gazettes (busca textual nos diários oficiais).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.config import config
from rastro.util import data_ou_none, sem_acentos

TERMOS_ATO = ['"extrato de contrato"', '"aviso de licitação"', "homologação", "dispensa"]

_STOP = set(
    """a o os as de da do das dos e em no na nos nas para por com sem um uma uns umas ao aos à às que
    se ou pelo pela pelos pelas sua seu suas seus este esta estes estas esse essa isso the of and
    municipio municipal municipios prefeitura cidade aquisicao aquisicoes contratacao contratacoes
    servico servicos execucao recursos recurso emenda emendas parlamentar destinado destinada
    destinados destinadas atender atendimento diversos diversas geral outros outras demais material
    materiais apoio acoes acao realizacao melhoria melhorias implementacao fortalecimento manutencao
    custeio investimento investimentos meta metas objeto valor secretaria fundo publico publica
    publicos publicas conforme plano trabalho rede unidade unidades""".split()
)


def cliente(cache_dir: Path | None = None) -> ClienteHttp:
    return ClienteHttp(
        config().querido_diario_base_url,
        por_minuto=config().querido_diario_req_por_minuto,
        timeout=90,
        cache_dir=cache_dir,
    )


def palavras_chave(texto: str | None, n: int = 4) -> list[str]:
    """Palavras mais informativas do objeto (sem stopwords e termos genéricos), na forma original."""
    if not texto:
        return []
    formas: dict[str, str] = {}
    contagem: Counter[str] = Counter()
    for palavra in re.findall(r"[A-Za-zÀ-ÿ]{4,}", texto):
        chave = sem_acentos(palavra).lower()
        if chave in _STOP:
            continue
        formas.setdefault(chave, palavra.lower())
        contagem[chave] += 1
    ordem = sorted(contagem, key=lambda k: (-contagem[k], list(formas).index(k)))
    return [formas[k] for k in ordem[:n]]


def montar_consulta(palavras: list[str]) -> str:
    """Consulta no formato simple_query_string: (objeto) + (termos de ato)."""
    objeto = " | ".join(palavras)
    atos = " | ".join(TERMOS_ATO)
    return f"({objeto}) + ({atos})" if objeto else f"({atos})"


def classificar_ato(trecho: str) -> str:
    t = sem_acentos(trecho or "").lower()
    if "extrato" in t and "contrato" in t:
        return "extrato_contrato"
    if "inexigib" in t:
        return "inexigibilidade"
    if "dispensa" in t:
        return "dispensa"
    if "homolog" in t:
        return "homologacao"
    if "aviso" in t and "licita" in t:
        return "aviso_licitacao"
    if "contrato" in t:
        return "contrato"
    return "outro"


NIVEL_MINIMO_PESQUISAVEL = (
    2  # confirmado em 22/11/2026: nível 0 = sem diários; 1 = só arquivos (busca vazia); 3 = texto
)


def territorios_cobertos(resposta: dict[str, Any] | list) -> set[str]:
    """Municípios cuja cobertura permite busca textual nos diários (campo `level` de /cities)."""
    cidades = resposta.get("cities", []) if isinstance(resposta, dict) else resposta
    cobertos = set()
    for c in cidades:
        nivel = str(c.get("level") or "0")
        if c.get("territory_id") and nivel.isdigit() and int(nivel) >= NIVEL_MINIMO_PESQUISAVEL:
            cobertos.add(str(c["territory_id"]))
    return cobertos


def buscar(
    cli: ClienteHttp, codigo_ibge: str, consulta: str, desde: date, ate: date | None = None, tamanho: int = 10
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "territory_ids": codigo_ibge,
        "querystring": consulta,
        "published_since": desde.isoformat(),
        "excerpt_size": 600,
        "number_of_excerpts": 3,
        "size": tamanho,
        "sort_by": "descending_date",
    }
    if ate:
        params["published_until"] = ate.isoformat()
    return cli.get("/gazettes", params=params) or {}


def evidencias_de_diarios(resposta: dict[str, Any], cnpj_orgao: str | None) -> list[dict[str, Any]]:
    resultado = []
    for g in resposta.get("gazettes", []) or []:
        data = data_ou_none(g.get("date"))
        for i, trecho in enumerate(g.get("excerpts") or []):
            trecho = re.sub(r"\s+", " ", trecho or "").strip()
            if not trecho:
                continue
            id_externo = f"{g.get('territory_id')}:{g.get('date')}:{g.get('edition') or ''}:{i}"
            resultado.append(
                {
                    "fonte": "querido_diario",
                    "id_externo": id_externo,
                    "cnpj_orgao": cnpj_orgao,
                    "codigo_ibge": str(g.get("territory_id") or "") or None,
                    "data_publicacao": data,
                    "data_assinatura": None,
                    "objeto": trecho[:600],
                    "valor": None,
                    "modalidade": None,
                    "tipo_ato": classificar_ato(trecho),
                    "situacao": None,
                    "numero_controle_compra": None,
                    "fornecedor_documento": None,
                    "fornecedor_nome": None,
                    "fornecedor_pf": False,
                    "url": g.get("url") or g.get("txt_url"),
                    "trecho": trecho,
                    "raw": {
                        k: g.get(k) for k in ("territory_id", "territory_name", "date", "edition", "url", "txt_url")
                    },
                }
            )
    return resultado
