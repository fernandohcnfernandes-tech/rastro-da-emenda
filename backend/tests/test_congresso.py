from rastro.conectores import congresso
from rastro.jobs.carga_congresso import ligar_autores
from tests.conftest import carregar_fixture


def test_chave_remove_prefixos_e_acentos() -> None:
    assert congresso.chave("Dep. Roseana Sarney") == congresso.chave("Roseana Sarney") == "ROSEANASARNEY"
    assert congresso.chave("Sen. Omar Aziz") == "OMARAZIZ"
    assert congresso.chave("Abílio Santana") == "ABILIOSANTANA"


def test_deputado_sem_dados_pessoais() -> None:
    lista = carregar_fixture("congresso", "deputados_p1.json")["dados"]
    detalhe = carregar_fixture("congresso", "deputado_detalhe.json")["dados"]
    p = congresso.deputado(lista[0], detalhe)
    assert p["id"] == f"camara:{lista[0]['id']}" and p["casa"] == "camara" and len(p["uf"]) == 2
    assert p["url_pagina"].startswith("https://www.camara.leg.br/deputados/") and p["url_foto"].startswith("https://")
    assert "cpf" not in p["raw"] and "dataNascimento" not in p["raw"]


def test_senadores_atuais_e_legislatura() -> None:
    atuais = carregar_fixture("congresso", "senadores_atuais.json")["ListaParlamentarEmExercicio"]["Parlamentares"][
        "Parlamentar"
    ]
    s = congresso.senador(atuais[0])
    assert (
        s["casa"] == "senado"
        and s["partido"]
        and s["email"].endswith("senado.leg.br")
        and s["situacao"] == "Em exercício"
    )
    legislatura = carregar_fixture("congresso", "senadores_legislatura.json")["ListaParlamentarLegislatura"][
        "Parlamentares"
    ]["Parlamentar"]
    s2 = congresso.senador(legislatura[0])
    assert s2["uf"] and s2["url_foto"].startswith("https://www.senado.leg.br/senadores/img/fotos-oficiais/senador")


def test_ligar_autores() -> None:
    parl = [
        {"id": "camara:1", "casa": "camara", "chave_nome": "ROSEANASARNEY", "situacao": None},
        {"id": "senado:2", "casa": "senado", "chave_nome": "OMARAZIZ", "situacao": "Em exercício"},
        {"id": "camara:3", "casa": "camara", "chave_nome": "OMARAZIZ", "situacao": None},
    ]
    lig = ligar_autores(["Dep. Roseana Sarney", "Omar Aziz", "Omar Azizz", "Ninguém"], parl)
    assert lig["Dep. Roseana Sarney"] == ("camara:1", "exato")
    assert lig["Omar Aziz"] == ("senado:2", "exato")
    assert lig["Omar Azizz"] == ("senado:2", "aproximado")
    assert "Ninguém" not in lig
