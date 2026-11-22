"""Conector da API de consultas do PNCP (sem autenticação).

Limites confirmados em 22/11/2026: período máximo de 365 dias por consulta; `/v1/contratos` aceita
`tamanhoPagina` de 10 a 500 e `/v1/contratacoes/publicacao` até 50.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.config import config
from rastro.util import data_ou_none, decimal_ou_none, mascarar_cpf, normalizar_cnpj

TAMANHO_CONTRATOS = 500
TAMANHO_CONTRATACOES = 50
REQ_POR_MINUTO = 30  # medido em 22/11/2026: 1 req a cada 1 s gera 429; 1 a cada 1,5 s não
MAX_DIAS_JANELA = 365

# Modalidades usadas na varredura de contratações (códigos do PNCP).
MODALIDADES = {
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
}
MODALIDADES_DIRETAS = {8, 9}

_CONTROLE = re.compile(r"^(?P<cnpj>\d{14})-(?P<tipo>\d)-(?P<seq>\d+)/(?P<ano>\d{4})$")


def cliente(por_minuto: int = REQ_POR_MINUTO) -> ClienteHttp:
    return ClienteHttp(config().pncp_base_url, por_minuto=por_minuto, timeout=120)


def janelas(inicio: date, fim: date, dias: int = MAX_DIAS_JANELA) -> list[tuple[date, date]]:
    """Divide [inicio, fim] em janelas de no máximo `dias` dias (o PNCP recusa períodos maiores que 365)."""
    resultado = []
    atual = inicio
    while atual <= fim:
        final = min(atual + timedelta(days=dias - 1), fim)
        resultado.append((atual, final))
        atual = final + timedelta(days=1)
    return resultado


def janelas_mensais(inicio: date, fim: date) -> list[tuple[date, date]]:
    resultado = []
    atual = inicio.replace(day=1)
    while atual <= fim:
        proximo = (atual.replace(day=28) + timedelta(days=4)).replace(day=1)
        resultado.append((max(atual, inicio), min(proximo - timedelta(days=1), fim)))
        atual = proximo
    return resultado


def url_publica(numero_controle: str | None) -> str | None:
    """'05943030000155-2-000001/2025' → https://pncp.gov.br/app/contratos/05943030000155/2025/1"""
    m = _CONTROLE.match(numero_controle or "")
    if not m:
        return None
    caminho = "contratos" if m["tipo"] == "2" else "editais" if m["tipo"] == "1" else "atas"
    return f"https://pncp.gov.br/app/{caminho}/{m['cnpj']}/{m['ano']}/{int(m['seq'])}"


def _paginar(cli: ClienteHttp, caminho: str, params: dict[str, Any]) -> Iterator[list[dict[str, Any]]]:
    pagina = 1
    while True:
        resposta = cli.get(caminho, params={**params, "pagina": pagina}) or {}
        dados = resposta.get("data") or []
        yield dados
        if not dados or not resposta.get("paginasRestantes"):
            return
        pagina += 1


def contratos(cli: ClienteHttp, cnpj: str, inicio: date, fim: date) -> Iterator[list[dict[str, Any]]]:
    for ini, fin in janelas(inicio, fim):
        params = {
            "dataInicial": ini.strftime("%Y%m%d"),
            "dataFinal": fin.strftime("%Y%m%d"),
            "cnpjOrgao": cnpj,
            "tamanhoPagina": TAMANHO_CONTRATOS,
        }
        yield from _paginar(cli, "/v1/contratos", params)


def contratacoes(
    cli: ClienteHttp, inicio: date, fim: date, modalidade: int, uf: str | None = None, cnpj: str | None = None
) -> Iterator[list[dict[str, Any]]]:
    for ini, fin in janelas(inicio, fim):
        params: dict[str, Any] = {
            "dataInicial": ini.strftime("%Y%m%d"),
            "dataFinal": fin.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": modalidade,
            "tamanhoPagina": TAMANHO_CONTRATACOES,
        }
        if uf:
            params["uf"] = uf
        if cnpj:
            params["cnpj"] = cnpj
        yield from _paginar(cli, "/v1/contratacoes/publicacao", params)


# ---------------------------------------------------------------- transformações (funções puras)


def _fornecedor(r: dict[str, Any]) -> tuple[str | None, str | None, bool]:
    """Documento e nome do fornecedor. Pessoa física: CPF mascarado e nome omitido (dado pessoal)."""
    documento = r.get("niFornecedor")
    pf = (r.get("tipoPessoa") or "").upper() == "PF" or len(re.sub(r"\D", "", documento or "")) == 11
    if pf:
        return mascarar_cpf(documento), "Pessoa física (nome omitido)", True
    return normalizar_cnpj(documento) or documento, r.get("nomeRazaoSocialFornecedor"), False


def _raw_seguro(r: dict[str, Any], pf: bool) -> dict[str, Any]:
    """JSON bruto sem campos nulos e sem dados pessoais de fornecedor pessoa física."""
    bruto = {k: v for k, v in r.items() if v is not None}
    if pf:
        bruto["niFornecedor"] = mascarar_cpf(bruto.get("niFornecedor"))
        bruto.pop("nomeRazaoSocialFornecedor", None)
    for chave in ("niFornecedorSubContratado", "nomeFornecedorSubContratado"):
        if r.get("tipoPessoaSubContratada") == "PF":
            bruto.pop(chave, None)
    return bruto


def evidencia_de_contrato(r: dict[str, Any]) -> dict[str, Any]:
    documento, nome, pf = _fornecedor(r)
    controle = r.get("numeroControlePNCP")
    objeto = (r.get("objetoContrato") or "").strip()
    complemento = (r.get("informacaoComplementar") or "").strip()
    if complemento and complemento.lower() not in objeto.lower():
        objeto = f"{objeto} — {complemento}" if objeto else complemento
    return {
        "fonte": "pncp_contrato",
        "id_externo": controle,
        "cnpj_orgao": normalizar_cnpj((r.get("orgaoEntidade") or {}).get("cnpj")),
        "codigo_ibge": ((r.get("unidadeOrgao") or {}).get("codigoIbge") or None),
        "data_publicacao": data_ou_none(r.get("dataPublicacaoPncp")),
        "data_assinatura": data_ou_none(r.get("dataAssinatura")),
        "objeto": objeto[:4000] or None,
        "valor": decimal_ou_none(r.get("valorGlobal") if r.get("valorGlobal") is not None else r.get("valorInicial")),
        "modalidade": None,
        "tipo_ato": "contrato",
        "situacao": (r.get("tipoContrato") or {}).get("nome"),
        "numero_controle_compra": r.get("numeroControlePncpCompra"),
        "fornecedor_documento": documento,
        "fornecedor_nome": nome,
        "fornecedor_pf": pf,
        "url": url_publica(controle),
        "trecho": None,
        "raw": _raw_seguro(r, pf),
    }


def tipo_ato_da_modalidade(modalidade_id: int | None) -> str:
    if modalidade_id == 8:
        return "dispensa"
    if modalidade_id == 9:
        return "inexigibilidade"
    return "licitacao"


def evidencia_de_contratacao(r: dict[str, Any]) -> dict[str, Any]:
    controle = r.get("numeroControlePNCP")
    valor = r.get("valorTotalHomologado") or r.get("valorTotalEstimado")
    return {
        "fonte": "pncp_contratacao",
        "id_externo": controle,
        "cnpj_orgao": normalizar_cnpj((r.get("orgaoEntidade") or {}).get("cnpj")),
        "codigo_ibge": ((r.get("unidadeOrgao") or {}).get("codigoIbge") or None),
        "data_publicacao": data_ou_none(r.get("dataPublicacaoPncp")),
        "data_assinatura": None,
        "objeto": ((r.get("objetoCompra") or "").strip())[:4000] or None,
        "valor": decimal_ou_none(valor),
        "modalidade": r.get("modalidadeNome"),
        "tipo_ato": tipo_ato_da_modalidade(r.get("modalidadeId")),
        "situacao": r.get("situacaoCompraNome"),
        "numero_controle_compra": controle,
        "fornecedor_documento": None,
        "fornecedor_nome": None,
        "fornecedor_pf": False,
        "url": url_publica(controle),
        "trecho": None,
        "raw": _raw_seguro(r, False),
    }
