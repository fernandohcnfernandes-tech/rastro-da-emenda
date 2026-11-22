from rastro.conectores import ibge
from tests.conftest import carregar_fixture


def test_chave_nome_remove_prefixos_acentos_e_pontuacao() -> None:
    assert ibge.chave_nome("MUNICIPIO DE PAU D:ARCO DO PIAUI") == "PAUDARCODOPIAUI"
    assert ibge.chave_nome("Pau D'Arco do Piauí") == "PAUDARCODOPIAUI"
    assert ibge.chave_nome("PREFEITURA MUNICIPAL DE SÃO JOÃO") == "SAOJOAO"
    assert ibge.chave_nome("FUNDO MUNICIPAL DE SAUDE DE BOA VISTA") == "BOAVISTA"
    assert ibge.chave_nome("FUNDO MUNICIPAL DE SAUDE DO MUNICIPIO DE BOA VISTA") == "BOAVISTA"
    assert ibge.chave_nome("MUNICIPIO DA ESTANCIA TURISTICA DE OLIMPIA") == "OLIMPIA"
    assert ibge.chave_nome("MUNICIPIO DE MULUNGU PREFEITURA MUNICIPAL") == "MULUNGU"
    assert ibge.chave_nome("Teresina - PI") == "TERESINA"


def test_resolver_municipio_exato_aproximado_e_sinonimo() -> None:
    municipios = [ibge.municipio(r) for r in carregar_fixture("ibge", "municipios.json")]
    indice = {(m["uf"], m["nome_chave"]): m["codigo_ibge"] for m in municipios}
    assert ibge.resolver_municipio("MUNICIPIO DE BOA VISTA", "RR", indice) == ("1400100", "exato")
    sao_miguel = ibge.resolver_municipio("MUNICIPIO DE SAO MIGUEL D'OESTE", "SC", indice)
    assert sao_miguel == ("4217204", "aproximado")
    assert ibge.resolver_municipio("MUNICIPIO DE SAO LUIZ", "RR", indice) == ("1400605", "sinonimo")
    assert ibge.resolver_municipio("MUNICIPIO DE BOA VISTA", "PI", indice) == (None, None)
    assert ibge.resolver_municipio("X", None, indice) == (None, None)


def test_populacoes_do_sidra() -> None:
    pops = ibge.populacoes(carregar_fixture("ibge", "populacao_2025.json"))
    assert pops["1400100"][1] == 2025 and pops["1400100"][0] > 400_000
    vazio = [{"resultados": [{"series": [{"localidade": {"id": "1"}, "serie": {"2026": "-"}}]}]}]
    assert ibge.populacoes(vazio) == {}
