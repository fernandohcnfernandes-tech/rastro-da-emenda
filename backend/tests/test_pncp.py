from datetime import date
from decimal import Decimal

import httpx
import respx

from rastro.conectores import pncp
from rastro.conectores.base import ClienteHttp
from rastro.jobs.carga_pncp import valor_relevante
from tests.conftest import carregar_fixture

CONTRATOS = carregar_fixture("pncp", "contratos_boa_vista_2025_p1.json")
CONTRATACOES = carregar_fixture("pncp", "contratacoes_dispensa_boa_vista_2024_p1.json")


def test_janelas_respeitam_365_dias() -> None:
    js = pncp.janelas(date(2024, 1, 1), date(2026, 11, 22))
    assert js[0] == (date(2024, 1, 1), date(2024, 12, 30))
    assert js[-1][1] == date(2026, 11, 22)
    assert all((fim - ini).days <= 364 for ini, fim in js)
    assert all(js[i + 1][0] == date.fromordinal(js[i][1].toordinal() + 1) for i in range(len(js) - 1))


def test_janelas_mensais() -> None:
    js = pncp.janelas_mensais(date(2024, 1, 15), date(2024, 3, 10))
    assert js == [
        (date(2024, 1, 15), date(2024, 1, 31)),
        (date(2024, 2, 1), date(2024, 2, 29)),
        (date(2024, 3, 1), date(2024, 3, 10)),
    ]


def test_url_publica() -> None:
    assert pncp.url_publica("05943030000155-2-000001/2025") == "https://pncp.gov.br/app/contratos/05943030000155/2025/1"
    assert pncp.url_publica("05943030000155-1-000034/2024") == "https://pncp.gov.br/app/editais/05943030000155/2024/34"
    assert pncp.url_publica("lixo") is None


def test_evidencia_de_contrato() -> None:
    ev = pncp.evidencia_de_contrato(CONTRATOS["data"][0])
    assert ev["fonte"] == "pncp_contrato" and ev["cnpj_orgao"] == "05943030000155"
    assert ev["codigo_ibge"] == "1400100" and ev["url"].startswith("https://pncp.gov.br/app/contratos/")
    assert isinstance(ev["valor"], Decimal) and ev["data_publicacao"] and ev["numero_controle_compra"]


def test_contrato_com_pessoa_fisica_mascara_cpf_e_omite_nome() -> None:
    pf = next(r for r in CONTRATOS["data"] if r["tipoPessoa"] == "PF")
    ev = pncp.evidencia_de_contrato(pf)
    assert ev["fornecedor_documento"] == "***.456.789-**" and ev["fornecedor_pf"]
    assert "FULANO" not in str(ev["raw"]) and "12345678901" not in str(ev["raw"])
    assert ev["fornecedor_nome"] == "Pessoa física (nome omitido)"


def test_evidencia_de_contratacao_dispensa() -> None:
    ev = pncp.evidencia_de_contratacao(CONTRATACOES["data"][0])
    assert ev["fonte"] == "pncp_contratacao" and ev["tipo_ato"] == "dispensa"
    assert ev["modalidade"] == "Dispensa" or "Dispensa" in ev["modalidade"]
    assert ev["url"].startswith("https://pncp.gov.br/app/editais/")
    assert pncp.tipo_ato_da_modalidade(6) == "licitacao" and pncp.tipo_ato_da_modalidade(9) == "inexigibilidade"


def test_valor_relevante() -> None:
    assert valor_relevante(Decimal("9999"), Decimal("100000")) is False
    assert valor_relevante(Decimal("10000"), Decimal("100000")) is True
    assert valor_relevante(None, Decimal("100000")) is True
    assert valor_relevante(Decimal("1"), None) is True


@respx.mock
def test_contratos_pagina_ate_acabar() -> None:
    base = "https://pncp.teste"
    p1 = {**CONTRATOS, "paginasRestantes": 1}
    p2 = {**CONTRATOS, "data": CONTRATOS["data"][:3], "paginasRestantes": 0}
    rota = respx.get(f"{base}/v1/contratos").mock(
        side_effect=[httpx.Response(200, json=p1), httpx.Response(200, json=p2)]
    )
    cli = ClienteHttp(base, por_minuto=0)
    paginas = list(pncp.contratos(cli, "05943030000155", date(2025, 1, 1), date(2025, 6, 30)))
    assert [len(p) for p in paginas] == [10, 3]
    assert rota.calls[0].request.url.params["tamanhoPagina"] == "500"
    assert rota.calls[1].request.url.params["pagina"] == "2"


@respx.mock
def test_resposta_204_encerra() -> None:
    base = "https://pncp.teste"
    respx.get(f"{base}/v1/contratos").mock(return_value=httpx.Response(204))
    cli = ClienteHttp(base, por_minuto=0)
    assert list(pncp.contratos(cli, "1", date(2025, 1, 1), date(2025, 1, 31))) == [[]]


def test_inicio_da_busca() -> None:
    from rastro.jobs.carga_pncp import inicio_da_busca

    assert inicio_da_busca(date(2024, 1, 1), None) is None
    assert inicio_da_busca(date(2024, 1, 1), date(2025, 3, 31)) == date(2025, 3, 1)
    assert inicio_da_busca(date(2024, 1, 1), date(2024, 1, 10)) == date(2024, 1, 1)
