from decimal import Decimal

from rastro.conectores import tce_rs
from tests.conftest import PASTA_FIXTURES

PASTA = PASTA_FIXTURES / "tce_rs"


def _orgaos():
    return tce_rs.ler_orgaos((PASTA / "orgaos_amostra.csv").read_text(encoding="utf-8-sig"))


def test_ler_orgaos_traz_cnpj_e_ibge() -> None:
    orgaos = _orgaos()
    assert orgaos
    for o in orgaos.values():
        assert len(o["cnpj"]) == 14 and o["codigo_ibge"].startswith("43")


def test_evidencias_dos_contratos() -> None:
    orgaos = _orgaos()
    evid = [
        tce_rs.evidencia_de_contrato(r, orgaos[r["CD_ORGAO"]])
        for r in tce_rs.linhas_contratos(PASTA / "contratos_amostra.csv.zip")
    ]
    assert len(evid) == 4 and all(e["fonte"] == "tce_contrato" and e["tipo_ato"] == "contrato" for e in evid)
    assert all(e["url"].startswith("https://portal.tce.rs.gov.br") and isinstance(e["valor"], Decimal) for e in evid)
    assert all(e["cnpj_orgao"] and e["codigo_ibge"] and e["data_publicacao"] for e in evid)
    assert len({e["id_externo"] for e in evid}) == 4
    assert any(e["modalidade"] == "Dispensa de licitação" for e in evid)
    pf = [e for e in evid if e["fornecedor_pf"]]
    assert pf and pf[0]["fornecedor_documento"] == "***.456.789-**" and "12345678901" not in str(pf[0]["raw"])


def test_contrato_tce_conta_como_contrato_e_dispensa_gera_a6() -> None:
    from datetime import date

    from rastro.motor.regras import Correspondencia, DadosEmenda, a6_contratacao_direta

    c = Correspondencia(1, "tce_contrato", "contrato", "Dispensa de licitação", Decimal("100"), True, 0.9)
    assert c.eh_contrato and c.eh_contratacao_direta
    d = DadosEmenda(1, date(2026, 1, 1), correspondencias=[c], esfera="municipal", populacao=5000, coberto_tce="TCE-RS")
    assert a6_contratacao_direta(d) and d.fontes_que_cobrem == ["TCE-RS"]
