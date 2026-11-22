"""Conector IBGE: municípios (localidades) e população estimada (SIDRA, agregado 6579, variável 9324)."""

from __future__ import annotations

import difflib
import re
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.config import config
from rastro.util import sem_acentos

AGREGADO_POPULACAO = 6579
VARIAVEL_POPULACAO = 9324

CODIGO_UF = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25",
    "PE": "26", "AL": "27", "SE": "28", "BA": "29",
    "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43",
    "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}  # fmt: skip

# Prefixos que aparecem no nome do beneficiário/executor e não fazem parte do nome do município.
_PREFIXOS = re.compile(
    r"^(?:PREFEITURA MUNICIPAL|PREFEITURA|MUNICIPIO|MUNICIPALIDADE|FUNDO MUNICIPAL DE SAUDE|"
    r"FUNDO MUNICIPAL DE ASSISTENCIA SOCIAL|FUNDO MUNICIPAL DE EDUCACAO|FUNDO MUNICIPAL|"
    r"SECRETARIA MUNICIPAL DE SAUDE|CAMARA MUNICIPAL|ESTADO|GOVERNO DO ESTADO|ESTANCIA TURISTICA|"
    r"ESTANCIA HIDROMINERAL|ESTANCIA BALNEARIA|ESTANCIA CLIMATICA)\b\s*(?:DE|DO|DA|DOS|DAS)?\s+"
)
_SUFIXOS = re.compile(r"\s+(?:PREFEITURA MUNICIPAL|PREFEITURA|PM)$")

# Grafias antigas ou alternativas usadas nos cadastros federais → nome atual no IBGE (chaves normalizadas).
SINONIMOS: dict[tuple[str, str], str] = {
    ("TO", "SAOVALERIODANATIVIDADE"): "SAOVALERIO",
    ("TO", "FORTALEZADOTABOCAO"): "TABOCAO",
    ("RN", "BOASAUDE"): "JANUARIOCICCO",
    ("RN", "PRESIDENTEJUSCELINO"): "SERRACAIADA",
    ("RN", "ARES"): "AREZ",
    ("RR", "SAOLUIZ"): "SAOLUIZDOANAUA",
    ("PE", "IGUARACI"): "IGUARACY",
    ("GO", "BOMJESUS"): "BOMJESUSDEGOIAS",
    ("SP", "JAHU"): "JAU",
    ("MT", "POXOREO"): "POXOREU",
}


def chave_nome(nome: str) -> str:
    """Normaliza nome de município para comparação: sem acentos, sem prefixos, só letras e dígitos."""
    texto = sem_acentos(nome or "").upper().strip()
    texto = re.sub(r"\s*[-/(]\s*[A-Z]{2}\)?\s*$", "", texto)  # sufixo " - PI", "/PI", "(PI)"
    texto = re.sub(r"\s+", " ", texto)
    texto = _SUFIXOS.sub("", texto)
    anterior = None
    while anterior != texto:  # remove prefixos encadeados ("FUNDO MUNICIPAL DE SAUDE DO MUNICIPIO DE X")
        anterior = texto
        texto = _PREFIXOS.sub("", texto).strip()
    return re.sub(r"[^A-Z0-9]", "", texto)


def resolver_municipio(nome: str, uf: str | None, indice: dict[tuple[str, str], str]) -> tuple[str | None, str | None]:
    """Devolve (codigo_ibge, metodo) para um nome de ente + UF usando o índice {(uf, chave): codigo}."""
    if not uf:
        return None, None
    chave = chave_nome(nome)
    if not chave:
        return None, None
    codigo = indice.get((uf, chave))
    if codigo:
        return codigo, "exato"
    if (uf, chave) in SINONIMOS and (uf, SINONIMOS[(uf, chave)]) in indice:
        return indice[(uf, SINONIMOS[(uf, chave)])], "sinonimo"
    candidatos = [c for (u, c) in indice if u == uf]
    proximos = difflib.get_close_matches(chave, candidatos, n=2, cutoff=0.88)
    if len(proximos) == 1 or (len(proximos) == 2 and proximos[0] != proximos[1]):
        return indice[(uf, proximos[0])], "aproximado"
    return None, None


def municipio(r: dict[str, Any]) -> dict[str, Any]:
    """Linha do endpoint /v1/localidades/municipios?view=nivelado."""
    return {
        "codigo_ibge": str(r["municipio-id"]),
        "nome": r["municipio-nome"],
        "uf": r["UF-sigla"],
        "nome_chave": chave_nome(r["municipio-nome"]),
    }


def populacoes(resposta: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    """Converte a resposta do SIDRA em {codigo_localidade: (populacao, ano)}; ignora valores ausentes."""
    resultado: dict[str, tuple[int, int]] = {}
    for variavel in resposta or []:
        for res in variavel.get("resultados", []):
            for serie in res.get("series", []):
                codigo = str(serie["localidade"]["id"])
                for ano, valor in serie.get("serie", {}).items():
                    if valor and str(valor).isdigit():
                        resultado[codigo] = (int(valor), int(ano))
    return resultado


def cliente() -> ClienteHttp:
    return ClienteHttp(config().ibge_base_url, por_minuto=60, timeout=180)


def baixar_municipios(cli: ClienteHttp) -> list[dict[str, Any]]:
    return [municipio(r) for r in cli.get("/v1/localidades/municipios", params={"view": "nivelado"})]


def periodo_mais_recente_com_dados(cli: ClienteHttp, nivel: str = "N6") -> tuple[str, dict[str, tuple[int, int]]]:
    """Procura, do período mais novo para o mais antigo, a primeira estimativa publicada."""
    periodos = [p["id"] for p in cli.get(f"/v3/agregados/{AGREGADO_POPULACAO}/periodos")]
    for periodo in sorted(periodos, reverse=True):
        resposta = cli.get(
            f"/v3/agregados/{AGREGADO_POPULACAO}/periodos/{periodo}/variaveis/{VARIAVEL_POPULACAO}",
            params={"localidades": f"{nivel}[all]"},
        )
        dados = populacoes(resposta)
        if dados:
            return periodo, dados
    return "", {}
