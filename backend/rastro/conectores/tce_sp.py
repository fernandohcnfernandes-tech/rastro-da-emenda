"""Conector do TCE-SP — arquivos semestrais de "ajustes" (contratos e notas de empenho) da Audesp.

`https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/licitacoes-contratos/ajustes-{ano}-{1|2}o-semestre.zip`
(CSV UTF-8, `;`, 644 municípios; a capital é fiscalizada pelo TCM-SP). Confirmado em 22/11/2026.
A entidade vem só pelo nome; o município (nome) é ligado ao IBGE e daí ao CNPJ do ente.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from rastro.util import data_ou_none, decimal_ou_none, mascarar_cpf, normalizar_cnpj, sem_acentos

SIGLA = "TCE-SP"
BASE = "https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/licitacoes-contratos"


def url_semestre(ano: int, semestre: int) -> str:
    return f"{BASE}/ajustes-{ano}-{semestre}o-semestre.zip"


def linhas(zip_path: Path) -> Iterator[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as bruto:
            leitor = csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline=""), delimiter=";")
            for r in leitor:
                yield {(k or "").strip(): (v or "").strip() for k, v in r.items()}


def entidade_do_executivo(nome: str | None) -> bool:
    """Prefeitura e fundos municipais executam a emenda; câmaras, autarquias e universidades não."""
    n = sem_acentos(nome or "").upper()
    if re.search(r"\bCAMARA\b", n):
        return False
    return bool(re.search(r"\bPREFEITURA\b|\bFUNDO\b|\bMUNICIPIO\b", n))


def evidencia(r: dict[str, str], cnpj_ente: str | None, codigo_ibge: str | None, url_arquivo: str) -> dict[str, Any]:
    documento = r.get("CNPJ da empresa contratada") or None
    pf = len(re.sub(r"\D", "", documento or "")) == 11
    instrumento = r.get("Instrumento") or ""
    valor = r.get("Valor total do contrato") or r.get("Valor da Nota de Empenho/Documento Similar")
    data = (
        r.get("Vigência do contrato - Data Assinatura")
        or r.get("Data da Nota de Empenho/Documento Similar")
        or r.get("Vigência do contrato - Data início")
    )
    objeto = r.get("Descrição do objeto contratado") or r.get("Descrição do objeto da licitação") or ""
    bruto = {k: v for k, v in r.items() if v}
    if pf:
        bruto["CNPJ da empresa contratada"] = mascarar_cpf(documento)
        bruto.pop("Nome da empresa contratada", None)
    return {
        "fonte": "tce_contrato",
        "id_externo": f"sp:{r.get('Código do Ajuste') or r.get('Código da Licitação')}",
        "cnpj_orgao": cnpj_ente,
        "codigo_ibge": codigo_ibge,
        "data_publicacao": data_ou_none(data),
        "data_assinatura": data_ou_none(r.get("Vigência do contrato - Data Assinatura")),
        "objeto": objeto[:4000] or None,
        "valor": decimal_ou_none(valor),
        "modalidade": r.get("Modalidade de licitação") or None,
        "tipo_ato": "contrato" if "contrato" in instrumento.lower() else "empenho",
        "situacao": instrumento or None,
        "numero_controle_compra": None,
        "fornecedor_documento": mascarar_cpf(documento) if pf else (normalizar_cnpj(documento) or documento),
        "fornecedor_nome": "Pessoa física (nome omitido)" if pf else (r.get("Nome da empresa contratada") or None),
        "fornecedor_pf": pf,
        "url": url_arquivo,
        "trecho": None,
        "raw": bruto,
    }
