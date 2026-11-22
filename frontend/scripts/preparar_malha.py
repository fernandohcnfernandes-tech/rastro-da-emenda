"""Baixa as malhas oficiais do IBGE (municípios e UFs) e grava versões compactas em public/malha/.

Uso: python3 scripts/preparar_malha.py
Fonte: https://servicodados.ibge.gov.br/api/v3/malhas (qualidade mínima, municípios).
"""

import json
import urllib.request
from pathlib import Path

BASE = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=minima"
PASTA = Path(__file__).resolve().parents[1] / "public" / "malha"
MALHAS = {"municipios.json": f"{BASE}&intrarregiao=municipio", "ufs.json": f"{BASE}&intrarregiao=UF"}


def arredondar(coords, casas=3):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], casas), round(coords[1], casas)]
    return [arredondar(c, casas) for c in coords]


def area_assinada(anel: list) -> float:
    """Área pela fórmula do laço (positiva = anti-horário em lon/lat)."""
    return sum(anel[i][0] * anel[i + 1][1] - anel[i + 1][0] * anel[i][1] for i in range(len(anel) - 1)) / 2


def orientar(poligono: list) -> list:
    """d3-geo exige anel externo no sentido horário e furos no anti-horário. A orientação é imposta anel a
    anel (e não invertida às cegas): a malha de UFs do IBGE mistura orientações."""
    saida = []
    for i, anel in enumerate(poligono):
        horario = area_assinada(anel) < 0
        quer_horario = i == 0
        saida.append(anel if horario == quer_horario else list(reversed(anel)))
    return saida


def inverter_aneis(geometria: dict) -> None:
    if geometria["type"] == "Polygon":
        geometria["coordinates"] = orientar(geometria["coordinates"])
    elif geometria["type"] == "MultiPolygon":
        geometria["coordinates"] = [orientar(p) for p in geometria["coordinates"]]


def main() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    for nome, url in MALHAS.items():
        req = urllib.request.Request(url, headers={"User-Agent": "RastroDaEmenda/0.1 (Hack Brasil 2026; equipe QKV)"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            dados = json.load(resp)
        for f in dados["features"]:
            f["properties"] = {"c": f["properties"]["codarea"]}
            f["geometry"]["coordinates"] = arredondar(f["geometry"]["coordinates"])
            inverter_aneis(f["geometry"])
        destino = PASTA / nome
        destino.write_text(json.dumps(dados, separators=(",", ":")), encoding="utf-8")
        print(f"{len(dados['features'])} feições → {destino} ({destino.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
