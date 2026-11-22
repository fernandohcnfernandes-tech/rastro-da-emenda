"""Conector do Portal da Transparência (CGU).

Dois caminhos, ambos oficiais:
- API de dados (`/emendas`, `/emendas/documentos/{codigo}`), chave gratuita no cabeçalho `chave-api-dados`;
- arquivo de dados abertos da CGU (EmendasParlamentares.zip), usado quando não há chave configurada.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.config import config
from rastro.util import data_ou_none, decimal_ou_none, normalizar_cnpj

URL_ARQUIVO_CGU = (
    "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/emendas-parlamentares/"
    "EmendasParlamentares.zip"
)
TIPO_PIX = "Transferências Especiais"
REQ_POR_MINUTO = 80  # o Portal limita a 90/min das 6h às 24h


def eh_pix(tipo: str | None) -> bool:
    return TIPO_PIX.lower() in (tipo or "").lower()


# ----------------------------------------------------------------------------- API


def cliente() -> ClienteHttp:
    return ClienteHttp(
        config().portal_base_url,
        por_minuto=REQ_POR_MINUTO,
        cabecalhos={"chave-api-dados": config().portal_transparencia_api_key},
    )


def emenda_da_api(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "codigo_emenda": str(r.get("codigoEmenda")),
        "ano": r.get("ano"),
        "numero": r.get("numeroEmenda"),
        "autor": r.get("nomeAutor") or r.get("autor"),
        "tipo": r.get("tipoEmenda"),
        "funcao": r.get("funcao"),
        "subfuncao": r.get("subfuncao"),
        "valor_empenhado": decimal_ou_none(r.get("valorEmpenhado")),
        "valor_liquidado": decimal_ou_none(r.get("valorLiquidado")),
        "valor_pago": decimal_ou_none(r.get("valorPago")),
        "localidade": r.get("localidadeDoGasto"),
        "uf": None,
        "origem": "api",
        "raw": r,
    }


def documento_da_api(codigo_emenda: str, r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(r.get("codigoDocumento")),
        "codigo_emenda": codigo_emenda,
        "data": data_ou_none(r.get("data")),
        "fase": r.get("fase"),
        "especie": r.get("especieTipo"),
        "valor": decimal_ou_none(r.get("valor")),
        "raw": r,
    }


def emendas_api(cli: ClienteHttp, ano: int, pagina_inicial: int = 1) -> Iterator[tuple[int, list[dict]]]:
    pagina = pagina_inicial
    while True:
        linhas = cli.get("/emendas", params={"ano": ano, "pagina": pagina}) or []
        yield pagina, linhas
        if not linhas:
            return
        pagina += 1


def documentos_api(cli: ClienteHttp, codigo: str) -> Iterator[dict[str, Any]]:
    pagina = 1
    while True:
        linhas = cli.get(f"/emendas/documentos/{codigo}", params={"pagina": pagina}) or []
        yield from linhas
        if not linhas:
            return
        pagina += 1


# ------------------------------------------------------------------ arquivo de dados abertos


def _linhas_csv(zip_path: Path, nome: str) -> Iterator[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as z, z.open(nome) as bruto:
        texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
        for linha in csv.DictReader(texto, delimiter=";"):
            yield {k.strip(): (v or "").strip() for k, v in linha.items() if k}


def emenda_do_csv(r: dict[str, str]) -> dict[str, Any]:
    return {
        "codigo_emenda": r["Código da Emenda"],
        "ano": int(r["Ano da Emenda"]),
        "numero": r.get("Número da emenda"),
        "autor": r.get("Nome do Autor da Emenda"),
        "tipo": r.get("Tipo de Emenda"),
        "funcao": r.get("Nome Função"),
        "subfuncao": r.get("Nome Subfunção"),
        "valor_empenhado": decimal_ou_none(r.get("Valor Empenhado")),
        "valor_liquidado": decimal_ou_none(r.get("Valor Liquidado")),
        "valor_pago": decimal_ou_none(r.get("Valor Pago")),
        "localidade": r.get("Localidade de aplicação do recurso"),
        "uf": r.get("UF"),
        "origem": "arquivo_cgu",
        "raw": r,
    }


def emendas_pix_do_arquivo(zip_path: Path, ano_minimo: int) -> list[dict[str, Any]]:
    resultado = []
    for r in _linhas_csv(zip_path, "EmendasParlamentares.csv"):
        if eh_pix(r.get("Tipo de Emenda")) and r.get("Ano da Emenda", "0").isdigit():
            if int(r["Ano da Emenda"]) >= ano_minimo and r["Código da Emenda"].isdigit():
                resultado.append(emenda_do_csv(r))
    return resultado


def codigo_plano(plano_portal: str) -> str:
    """'09032024-064698/2024' → '09032024-064698' (mesmo formato de codigo_plano_acao no Transferegov)."""
    return (plano_portal or "").split("/")[0].strip()


def objetos_declarados_do_arquivo(zip_path: Path) -> Iterator[dict[str, Any]]:
    for r in _linhas_csv(zip_path, "EmendasParlamentares_PlanodeTrabalhoTransferenciasEspeciais.csv"):
        yield {
            "codigo_plano_acao": codigo_plano(r.get("Plano de Ação", "")),
            "codigo_emenda": r.get("Emenda Parlamentar"),
            "cnpj": normalizar_cnpj(r.get("CNPJ do Beneficiário")),
            "objeto": r.get("Detalhamento do Objeto") or None,
            "valor": decimal_ou_none(r.get("Valor")),
        }
