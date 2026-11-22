from decimal import Decimal

from rastro.conectores import portal
from tests.conftest import PASTA_FIXTURES, carregar_fixture

ZIP = PASTA_FIXTURES / "portal" / "EmendasParlamentares_amostra.zip"


def test_emendas_pix_do_arquivo_filtra_tipo_e_ano() -> None:
    emendas = portal.emendas_pix_do_arquivo(ZIP, 2024)
    codigos = {e["codigo_emenda"] for e in emendas}
    assert codigos == {"202437940002", "202538970001"}
    e = next(x for x in emendas if x["codigo_emenda"] == "202538970001")
    assert e["valor_pago"] == Decimal("15721200.00") and e["origem"] == "arquivo_cgu" and e["ano"] == 2025
    assert portal.emendas_pix_do_arquivo(ZIP, 2026) == []


def test_objeto_declarado_e_codigo_do_plano() -> None:
    objetos = list(portal.objetos_declarados_do_arquivo(ZIP))
    alvo = next(o for o in objetos if o["codigo_plano_acao"] == "09032024-064698")
    assert alvo["codigo_emenda"] == "202437940002" and "PONTES" in alvo["objeto"]
    assert portal.codigo_plano("0903-003307/2020") == "0903-003307"


def test_emenda_da_api_conforme_swagger() -> None:
    linhas = carregar_fixture("portal", "emendas_api_exemplo_swagger.json")
    pix = [portal.emenda_da_api(r) for r in linhas if portal.eh_pix(r["tipoEmenda"])]
    assert len(pix) == 1 and pix[0]["valor_pago"] == Decimal("9000000.00") and pix[0]["origem"] == "api"
