"""Funções puras de normalização usadas por todos os conectores."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

CAMPOS_BANCARIOS = ("banco", "agencia", "conta", "dado_bancario")


def so_digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def normalizar_cnpj(valor: Any) -> str | None:
    """CNPJ só com dígitos e 14 posições; None se vazio ou inválido no tamanho."""
    digitos = so_digitos(valor)
    if not digitos:
        return None
    if len(digitos) > 14:
        return None
    return digitos.zfill(14)


def decimal_ou_none(valor: Any) -> Decimal | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if "," in valor:  # formato brasileiro: 1.234,56
            valor = valor.replace(".", "").replace(",", ".")
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def data_ou_none(valor: Any) -> date | None:
    """Aceita AAAA-MM-DD, AAAA-MM-DDTHH:MM:SS, AAAAMMDD e DD/MM/AAAA."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato, tamanho in (("%Y-%m-%d", 10), ("%Y%m%d", 8), ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(texto[:tamanho], formato).date()
        except ValueError:
            continue
    return None


def sem_campos_bancarios(registro: dict[str, Any]) -> dict[str, Any]:
    """Remove banco/agência/conta do JSON bruto (não exibir dados bancários além do necessário)."""
    return {k: v for k, v in registro.items() if not any(c in k for c in CAMPOS_BANCARIOS)}


def sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def mascarar_cpf(documento: Any) -> str | None:
    """Mascara CPF (11 dígitos) como ***.456.789-**; CNPJ e outros valores voltam inalterados."""
    if documento is None:
        return None
    digitos = so_digitos(documento)
    if len(digitos) == 11:
        return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
    return str(documento)
