"""Conector do TCE-RS (dados abertos oficiais, sem chave): contratos do LicitaCon e cadastro de órgãos.

- Órgãos: https://dados.tce.rs.gov.br/dados/auxiliar/orgaos_auditados_rs.csv (CD_ORGAO → CNPJ e código IBGE)
- Contratos por ano: https://dados.tce.rs.gov.br/dados/licitacon/contrato/ano/{ano}.csv.zip (arquivo contrato.csv)
Confirmado em 22/11/2026: 2025 tem ~119 mil contratos de 1.135 órgãos (prefeituras, câmaras, autarquias, Estado).
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from rastro.conectores.base import USER_AGENT
from rastro.util import data_ou_none, decimal_ou_none, mascarar_cpf, normalizar_cnpj

BASE = "https://dados.tce.rs.gov.br/dados"
URL_ORGAOS = f"{BASE}/auxiliar/orgaos_auditados_rs.csv"
SIGLA = "TCE-RS"

# Códigos de modalidade do LicitaCon usados nas regras (demais ficam com o código bruto). Ver docs/decisoes.md.
MODALIDADES = {
    "PRD": "Dispensa de licitação",
    "PDE": "Dispensa eletrônica",
    "PRI": "Inexigibilidade",
    "PCE": "Pregão eletrônico",
    "PRE": "Pregão presencial",
    "CCE": "Concorrência eletrônica",
}


def url_contratos(ano: int) -> str:
    return f"{BASE}/licitacon/contrato/ano/{ano}.csv.zip"


def baixar(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, timeout=900, follow_redirects=True) as resp:
        resp.raise_for_status()
        with destino.open("wb") as arq:
            for bloco in resp.iter_bytes():
                arq.write(bloco)
    return destino


def ler_orgaos(texto_csv: str) -> dict[str, dict[str, Any]]:
    """{CD_ORGAO: {cnpj, codigo_ibge, esfera, nome}} a partir do cadastro de órgãos auditados."""
    orgaos = {}
    for r in csv.DictReader(io.StringIO(texto_csv.lstrip("﻿"))):
        orgaos[r["CD_ORGAO"].strip()] = {
            "cnpj": normalizar_cnpj(r.get("CNPJ")),
            "codigo_ibge": (r.get("CD_MUNICIPIO_IBGE") or "").strip() or None,
            "esfera": (r.get("ESFERA") or "").strip().lower(),
            "nome": (r.get("NOME_ORGAO") or "").strip(),
        }
    return orgaos


def linhas_contratos(zip_path: Path) -> Iterator[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as z, z.open("contrato.csv") as bruto:
        yield from csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline=""))


def evidencia_de_contrato(r: dict[str, str], orgao: dict[str, Any]) -> dict[str, Any]:
    pf = (r.get("TP_DOCUMENTO") or "").upper() == "F"
    documento = r.get("NR_DOCUMENTO") or None
    codigo_mod = (r.get("CD_TIPO_MODALIDADE") or "").strip()
    id_externo = ":".join(
        [
            "rs",
            r.get("CD_ORGAO", ""),
            f"{r.get('NR_CONTRATO', '')}/{r.get('ANO_CONTRATO', '')}",
            r.get("TP_INSTRUMENTO", ""),
            f"{r.get('NR_LICITACAO', '')}/{r.get('ANO_LICITACAO', '')}",
        ]
    )
    bruto = {k: v for k, v in r.items() if v not in ("", None)}
    if pf:
        bruto["NR_DOCUMENTO"] = mascarar_cpf(documento)
    modalidade = MODALIDADES.get(codigo_mod, codigo_mod or None)  # A6 usa a modalidade (dispensa/inexigibilidade)
    return {
        "fonte": "tce_contrato",
        "id_externo": id_externo,
        "cnpj_orgao": orgao.get("cnpj"),
        "codigo_ibge": orgao.get("codigo_ibge"),
        "data_publicacao": data_ou_none(r.get("DT_ASSINATURA") or r.get("DT_INICIO_VIGENCIA")),
        "data_assinatura": data_ou_none(r.get("DT_ASSINATURA")),
        "objeto": (r.get("DS_OBJETO") or "").strip()[:4000] or None,
        "valor": decimal_ou_none(r.get("VL_CONTRATO")),
        "modalidade": modalidade,
        "tipo_ato": "contrato",
        "situacao": None,
        "numero_controle_compra": None,
        "fornecedor_documento": mascarar_cpf(documento) if pf else (normalizar_cnpj(documento) or documento),
        "fornecedor_nome": None,
        "fornecedor_pf": pf,
        "url": r.get("LINK_LICITACON_CIDADAO") or None,
        "trecho": None,
        "raw": bruto,
    }
