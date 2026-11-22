from datetime import date
from decimal import Decimal

from rastro.conectores import tce_pi, tce_rn, tce_sp
from rastro.jobs.carga_tce import semestres
from tests.conftest import PASTA_FIXTURES, carregar_fixture

# ------------------------------------------------------------------------------------- PI


def test_pi_contratos_e_camara() -> None:
    itens = carregar_fixture("tce_pi", "contratos.json")["items"]
    camaras = [r for r in itens if tce_pi.eh_camara(r["orgao"])]
    assert len(camaras) == 1 and not tce_pi.eh_camara("P. M. DE OEIRAS")
    r = next(r for r in itens if not tce_pi.eh_camara(r["orgao"]))
    ev = tce_pi.evidencia_de_contrato(r, "1" * 14)
    assert ev["fonte"] == "tce_contrato" and ev["id_externo"].startswith("pi:") and ev["codigo_ibge"] == r["codIbgeMun"]
    assert (
        isinstance(ev["valor"], Decimal) and ev["data_publicacao"] and ev["url"].startswith("https://sistemas.tce.pi")
    )


def test_pi_pessoa_fisica_mascarada() -> None:
    r = dict(carregar_fixture("tce_pi", "contratos.json")["items"][0])
    r.update(docContratada="12345678901", nomeContratada="FULANO")
    ev = tce_pi.evidencia_de_contrato(r, "1" * 14)
    assert ev["fornecedor_documento"] == "***.456.789-**" and "FULANO" not in str(ev)


# ------------------------------------------------------------------------------------- SP


def test_sp_ajustes() -> None:
    linhas = list(tce_sp.linhas(PASTA_FIXTURES / "tce_sp" / "ajustes_amostra.zip"))
    assert len(linhas) == 3
    executivo = [r for r in linhas if tce_sp.entidade_do_executivo(r["Entidade"])]
    assert len(executivo) == 2 and all("PREFEITURA" in r["Entidade"] for r in executivo)
    ev = tce_sp.evidencia(executivo[0], "1" * 14, "3500105", "https://arquivo")
    assert ev["id_externo"].startswith("sp:") and ev["tipo_ato"] == "empenho" and ev["valor"] > 0
    assert ev["data_publicacao"] and len(ev["fornecedor_documento"]) == 14
    pf = dict(executivo[0], **{"CNPJ da empresa contratada": "123.456.789-01", "Nome da empresa contratada": "FULANO"})
    ev_pf = tce_sp.evidencia(pf, "1" * 14, "3500105", "u")
    assert ev_pf["fornecedor_documento"] == "***.456.789-**" and "FULANO" not in str(ev_pf)


def test_semestres() -> None:
    assert semestres(date(2024, 1, 1), date(2026, 11, 22)) == [
        (2024, 1),
        (2024, 2),
        (2025, 1),
        (2025, 2),
        (2026, 1),
        (2026, 2),
    ]
    assert semestres(date(2025, 8, 1), date(2025, 9, 1)) == [(2025, 2)]


# ------------------------------------------------------------------------------------- RN


def test_rn_unidades_e_contratos() -> None:
    unidades = carregar_fixture("tce_rn", "unidades.json")
    prefeituras = [u for u in unidades if tce_rn.eh_prefeitura(u)]
    assert [u["identificadorUnidade"] for u in prefeituras] == [337]
    contratos = carregar_fixture("tce_rn", "contratos_acari.json")
    evid = [tce_rn.evidencia_de_contrato(r, "1" * 14, "2400109") for r in contratos]
    assert all(e["id_externo"].startswith("rn:") and e["valor"] and e["data_publicacao"] for e in evid)
    assert all(" " not in (e["url"] or "") for e in evid)
