"""Conector da API Transferências Especiais (Transferegov/MGI) — PostgREST, sem autenticação.

Cadeia de ligação confirmada em 22/11/2026:
plano_acao ← executor ← meta;  plano_acao ← empenho ← documento_habil ← ordem_pagamento_ordem_bancaria.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.config import config
from rastro.util import data_ou_none, decimal_ou_none, normalizar_cnpj, sem_acentos, sem_campos_bancarios

TAMANHO_PAGINA = 1000
REQ_POR_MINUTO = 60


def cliente() -> ClienteHttp:
    return ClienteHttp(config().transferegov_base_url, por_minuto=REQ_POR_MINUTO)


def paginas(
    cli: ClienteHttp,
    tabela: str,
    filtros: dict[str, str] | None = None,
    ordem: str = "",
    offset: int = 0,
    tamanho: int = TAMANHO_PAGINA,
) -> Iterator[tuple[int, list[dict[str, Any]]]]:
    """Percorre a tabela com limit/offset ordenado pela chave. Devolve (próximo offset, linhas)."""
    while True:
        params = {**(filtros or {}), "limit": tamanho, "offset": offset}
        if ordem:
            params["order"] = ordem
        linhas = cli.get(f"/{tabela}", params=params) or []
        offset += len(linhas)
        yield offset, linhas
        if len(linhas) < tamanho:
            return


# ---------------------------------------------------------------- transformações (funções puras)


def esfera_do_ente(nome: str | None) -> str:
    n = sem_acentos(nome or "").upper().strip()
    if n.startswith(("ESTADO", "GOVERNO DO ESTADO", "DISTRITO FEDERAL")):
        return "estadual"
    if n.startswith(("MUNICIPIO", "PREFEITURA")):
        return "municipal"
    return "outro"


def ente_de_plano(r: dict[str, Any]) -> dict[str, Any] | None:
    cnpj = normalizar_cnpj(r.get("cnpj_beneficiario_plano_acao"))
    if not cnpj:
        return None
    nome = (r.get("nome_beneficiario_plano_acao") or "").strip()
    return {
        "cnpj": cnpj,
        "nome": nome,
        "uf": r.get("uf_beneficiario_plano_acao"),
        "esfera": esfera_do_ente(nome),
    }


def plano_acao(r: dict[str, Any]) -> dict[str, Any]:
    ano_emenda = r.get("ano_emenda_parlamentar_plano_acao")
    return {
        "id_plano_acao": r["id_plano_acao"],
        "codigo_plano_acao": r.get("codigo_plano_acao"),
        "ano_plano_acao": r.get("ano_plano_acao"),
        "situacao": r.get("situacao_plano_acao"),
        "emenda_ano": int(ano_emenda) if ano_emenda else None,
        "emenda_numero": r.get("numero_emenda_parlamentar_plano_acao"),
        "parlamentar_nome": (r.get("nome_parlamentar_emenda_plano_acao") or "").strip() or None,
        "codigo_parlamentar": r.get("codigo_parlamentar_emenda_plano_acao"),
        "cnpj_beneficiario": normalizar_cnpj(r.get("cnpj_beneficiario_plano_acao")),
        "nome_beneficiario": r.get("nome_beneficiario_plano_acao"),
        "uf_beneficiario": r.get("uf_beneficiario_plano_acao"),
        "valor_custeio": decimal_ou_none(r.get("valor_custeio_plano_acao")),
        "valor_investimento": decimal_ou_none(r.get("valor_investimento_plano_acao")),
        "descricao_programacao": r.get("descricao_programacao_orcamentaria_plano_acao"),
        "motivo_impedimento": r.get("motivo_impedimento_plano_acao"),
        "areas_politicas": r.get("codigo_descricao_areas_politicas_publicas_plano_acao"),
        "id_programa": r.get("id_programa"),
        "raw": sem_campos_bancarios(r),
    }


def plano_trabalho(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id_plano_trabalho"],
        "id_plano_acao": r["id_plano_acao"],
        "descricao": r.get("classificacao_orcamentaria_pt"),
        "situacao": r.get("situacao_plano_trabalho"),
        "data_inicio_execucao": data_ou_none(r.get("data_inicio_execucao_plano_trabalho")),
        "data_fim_execucao": data_ou_none(r.get("data_fim_execucao_plano_trabalho")),
        "raw": r,
    }


def executor(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id_executor"],
        "id_plano_acao": r["id_plano_acao"],
        "cnpj_executor": normalizar_cnpj(r.get("cnpj_executor")),
        "nome_executor": r.get("nome_executor"),
        "objeto": (r.get("objeto_executor") or "").strip() or None,
        "valor_custeio": decimal_ou_none(r.get("vl_custeio_executor")),
        "valor_investimento": decimal_ou_none(r.get("vl_investimento_executor")),
        "raw": sem_campos_bancarios(r),
    }


def meta(r: dict[str, Any], plano_do_executor: dict[int, int]) -> dict[str, Any] | None:
    id_plano = plano_do_executor.get(r.get("id_executor"))
    if id_plano is None:
        return None
    return {
        "id": r["id_meta"],
        "id_plano_acao": id_plano,
        "id_executor": r.get("id_executor"),
        "nome": r.get("nome_meta"),
        "descricao": (r.get("desc_meta") or "").strip() or None,
        "valor_custeio": decimal_ou_none(r.get("vl_custeio_emenda_especial_meta")),
        "valor_investimento": decimal_ou_none(r.get("vl_investimento_emenda_especial_meta")),
        "raw": r,
    }


def empenho(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id_empenho": r["id_empenho"],
        "id_plano_acao": r["id_plano_acao"],
        "numero": r.get("numero_empenho"),
        "situacao": r.get("descricao_situacao_empenho"),
        "data_emissao": data_ou_none(r.get("data_emissao_empenho")),
        "valor": decimal_ou_none(r.get("valor_empenho")),
        "raw": r,
    }


def documento_habil(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id_dh": r["id_dh"],
        "id_empenho": r.get("id_empenho"),
        "numero": r.get("numero_documento_habil"),
        "situacao": r.get("descricao_situacao_dh"),
        "data_emissao": data_ou_none(r.get("data_emissao_dh")),
        "valor": decimal_ou_none(r.get("valor_dh")),
        "raw": r,
    }


def pagamento(r: dict[str, Any]) -> dict[str, Any]:
    """Ordem de pagamento/bancária. Plano e valor são resolvidos depois via documento hábil → empenho."""
    return {
        "id": str(r["id_op_ob"]),
        "id_dh": r.get("id_dh"),
        "data_pagamento": data_ou_none(r.get("data_emissao_ob") or r.get("data_emissao_op")),
        "numero_ordem_bancaria": r.get("numero_ordem_bancaria"),
        "situacao": r.get("descricao_situacao_op"),
        "raw": r,
    }


def relatorio_gestao(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"rg:{r['id_relatorio_gestao']}",
        "id_plano_acao": r["id_plano_acao"],
        "situacao": r.get("situacao_relatorio_gestao"),
        "tipo": None,
        "parecer": r.get("parecer_relatorio_gestao"),
        "valor_executado": None,
        "valor_pendente": None,
        "data_registro": None,
        "raw": r,
    }


def relatorio_gestao_novo(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"rgn:{r['id_relatorio_gestao_novo']}",
        "id_plano_acao": r["id_plano_acao"],
        "situacao": r.get("situacao_relatorio_gestao_novo"),
        "tipo": r.get("tipo_relatorio_gestao_novo"),
        "parecer": None,
        "valor_executado": decimal_ou_none(r.get("valor_executado_relatorio_gestao_novo")),
        "valor_pendente": decimal_ou_none(r.get("valor_pendente_relatorio_gestao_novo")),
        "data_registro": r.get("data_e_hora_relatorio_gestao_novo"),
        "raw": r,
    }


@dataclass(frozen=True)
class Tabela:
    """Tabela filha: de onde vem, qual coluna a liga ao pai já carregado e como transformar."""

    nome_api: str
    chave_api: str
    coluna_pai: str
    destino: str
    chave_destino: tuple[str, ...]
    transformar: Callable[..., dict[str, Any] | None]


TABELAS_FILHAS: list[Tabela] = [
    Tabela("executor_especial", "id_executor", "id_plano_acao", "executor", ("id",), executor),
    Tabela("meta_especial", "id_meta", "id_executor", "meta", ("id",), meta),
    Tabela(
        "plano_trabalho_especial",
        "id_plano_trabalho",
        "id_plano_acao",
        "plano_trabalho",
        ("id",),
        plano_trabalho,
    ),
    Tabela("empenho_especial", "id_empenho", "id_plano_acao", "empenho", ("id_empenho",), empenho),
    Tabela("documento_habil_especial", "id_dh", "id_empenho", "documento_habil", ("id_dh",), documento_habil),
    Tabela("ordem_pagamento_ordem_bancaria_especial", "id_op_ob", "id_dh", "pagamento", ("id",), pagamento),
    Tabela(
        "relatorio_gestao_especial",
        "id_relatorio_gestao",
        "id_plano_acao",
        "relatorio_gestao",
        ("id",),
        relatorio_gestao,
    ),
    Tabela(
        "relatorio_gestao_novo_especial",
        "id_relatorio_gestao_novo",
        "id_plano_acao",
        "relatorio_gestao",
        ("id",),
        relatorio_gestao_novo,
    ),
]
