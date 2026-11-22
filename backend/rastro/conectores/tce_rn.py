"""Conector do TCE-RN — API de dados abertos (sem chave).

- Unidades: `GET /api/InformacoesBasicasApi/JurisdicionadosTCE/json` (923 unidades; prefeituras com CNPJ)
- Contratos: `GET /api/ContratosApi/Contratos/Json/{identificadorUnidade}/true` (`true` inclui os subórgãos, como os
  fundos municipais). Confirmado em 22/11/2026.
"""

from __future__ import annotations

import re
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.util import data_ou_none, decimal_ou_none, mascarar_cpf, normalizar_cnpj, sem_acentos

BASE = "https://apidadosabertos.tce.rn.gov.br"
SIGLA = "TCE-RN"


def cliente() -> ClienteHttp:
    return ClienteHttp(BASE, por_minuto=30, timeout=180)


def unidades(cli: ClienteHttp) -> list[dict[str, Any]]:
    return cli.get("/api/InformacoesBasicasApi/JurisdicionadosTCE/json") or []


def eh_prefeitura(u: dict[str, Any]) -> bool:
    return bool(re.search(r"\bPREFEITURA\b", sem_acentos(u.get("nomeOrgao") or "").upper()))


def contratos(cli: ClienteHttp, identificador: int) -> list[dict[str, Any]]:
    return cli.get(f"/api/ContratosApi/Contratos/Json/{identificador}/true") or []


def evidencia_de_contrato(r: dict[str, Any], cnpj_ente: str, codigo_ibge: str | None) -> dict[str, Any]:
    documento = r.get("cpfcnpjContratado")
    pf = r.get("idTipoDocumentoContratado") == 1 or len(re.sub(r"\D", "", documento or "")) == 11
    bruto = {k: v for k, v in r.items() if v not in (None, "")}
    if pf:
        bruto["cpfcnpjContratado"] = mascarar_cpf(documento)
        bruto.pop("nomeContratado", None)
    url = r.get("caminhonomeArquivoContrato")
    return {
        "fonte": "tce_contrato",
        "id_externo": f"rn:{r.get('idContrato')}",
        "cnpj_orgao": cnpj_ente,
        "codigo_ibge": codigo_ibge,
        "data_publicacao": data_ou_none(r.get("dataDataPublicacao") or r.get("dataDataAssinatura")),
        "data_assinatura": data_ou_none(r.get("dataDataAssinatura")),
        "objeto": (r.get("objetoContrato") or "").strip()[:4000] or None,
        "valor": decimal_ou_none(r.get("valorContrato")),
        "modalidade": None,
        "tipo_ato": "contrato",
        "situacao": "ativo" if r.get("ativo") else "inativo",
        "numero_controle_compra": None,
        "fornecedor_documento": mascarar_cpf(documento) if pf else (normalizar_cnpj(documento) or documento),
        "fornecedor_nome": "Pessoa física (nome omitido)" if pf else r.get("nomeContratado"),
        "fornecedor_pf": pf,
        "url": url.replace(" ", "%20") if url else None,
        "trecho": None,
        "raw": bruto,
    }
