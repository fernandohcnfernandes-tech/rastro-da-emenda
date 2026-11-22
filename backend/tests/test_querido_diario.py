from datetime import date

from rastro.conectores import querido_diario as qd
from tests.conftest import carregar_fixture


def test_palavras_chave_ignoram_termos_genericos() -> None:
    texto = "Aquisição de ambulância e pavimentação de ruas; pavimentação em paralelepípedo no município"
    palavras = qd.palavras_chave(texto, n=3)
    assert palavras[0] == "pavimentação"
    assert "aquisição" not in palavras and "município" not in palavras
    assert qd.palavras_chave(None) == []


def test_montar_consulta_combina_objeto_e_atos() -> None:
    consulta = qd.montar_consulta(["pavimentação", "ambulância"])
    assert consulta.startswith("(pavimentação | ambulância) + (")
    assert '"extrato de contrato"' in consulta and "dispensa" in consulta
    assert qd.montar_consulta([]).startswith('("extrato')


def test_classificar_ato() -> None:
    assert qd.classificar_ato("EXTRATO DE CONTRATO nº 1") == "extrato_contrato"
    assert qd.classificar_ato("Aviso de Licitação - Pregão") == "aviso_licitacao"
    assert qd.classificar_ato("Termo de homologação") == "homologacao"
    assert qd.classificar_ato("Dispensa de licitação 2/2025") == "dispensa"
    assert qd.classificar_ato("Inexigibilidade nº 3") == "inexigibilidade"
    assert qd.classificar_ato("Portaria de nomeação") == "outro"


def test_evidencias_de_diarios() -> None:
    evid = qd.evidencias_de_diarios(carregar_fixture("querido_diario", "gazettes_exemplo_documentado.json"), "1" * 14)
    assert len(evid) == 3
    assert evid[0]["tipo_ato"] == "extrato_contrato" and evid[0]["data_publicacao"] == date(2025, 3, 14)
    assert evid[0]["url"].endswith(".pdf") and evid[0]["codigo_ibge"] == "2401859"
    assert evid[2]["id_externo"] == "2401859:2025-01-20::0" and evid[2]["tipo_ato"] == "homologacao"
    assert len({e["id_externo"] for e in evid}) == 3


def test_territorios_cobertos() -> None:
    cobertos = qd.territorios_cobertos(carregar_fixture("querido_diario", "cities_exemplo_documentado.json"))
    assert cobertos == {"2401859", "1400100"}
