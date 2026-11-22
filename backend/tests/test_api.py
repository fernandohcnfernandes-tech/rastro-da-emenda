"""Testes de API contra um banco PostgreSQL de teste (rastro_teste), criado e populado pelo próprio teste.

Pulados automaticamente se o PostgreSQL de desenvolvimento não estiver acessível.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from rastro import config as modulo_config
from rastro.db import conexao

HOJE = date.today()


def _url_teste() -> tuple[str, str]:
    url = make_url(modulo_config.config().database_url)
    return url.set(database="postgres").render_as_string(hide_password=False), url.set(
        database="rastro_teste"
    ).render_as_string(hide_password=False)


@pytest.fixture(scope="module")
def cliente(monkeypatch_modulo):
    admin, teste = _url_teste()
    try:
        eng = create_engine(admin, isolation_level="AUTOCOMMIT")
        with eng.connect() as c:
            c.execute(text("DROP DATABASE IF EXISTS rastro_teste WITH (FORCE)"))
            c.execute(text("CREATE DATABASE rastro_teste"))
        eng.dispose()
    except Exception as exc:  # pragma: no cover - ambiente sem banco
        pytest.skip(f"PostgreSQL indisponível: {exc}")
    monkeypatch_modulo.setenv("DATABASE_URL", teste)
    modulo_config.config.cache_clear()
    conexao.engine.cache_clear()
    from rastro.db.migrar import aplicar

    aplicar()
    _popular()
    from rastro.api.main import app

    yield TestClient(app)
    conexao.engine().dispose()
    conexao.engine.cache_clear()
    modulo_config.config.cache_clear()


@pytest.fixture(scope="module")
def monkeypatch_modulo():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _popular() -> None:
    with conexao.transacao() as c:
        c.execute(
            text("INSERT INTO municipio VALUES ('2401859','Exemplo do Norte','RN','EXEMPLODONORTE',8000,2026,true)")
        )
        c.execute(
            text(
                "INSERT INTO ente (cnpj, nome, uf, esfera, codigo_ibge, populacao, obrigado_pncp,"
                " coberto_querido_diario)"
                " VALUES ('11111111000111','MUNICIPIO DE EXEMPLO DO NORTE','RN','municipal','2401859',8000,false,true)"
            )
        )
        for id_, num, status, alertas in [(1, "202400010001", "verde", []), (2, "202400010002", "vermelho", ["A1"])]:
            c.execute(
                text(
                    "INSERT INTO plano_acao (id_plano_acao, codigo_plano_acao, ano_plano_acao, emenda_ano,"
                    " emenda_numero,"
                    " parlamentar_nome, cnpj_beneficiario, nome_beneficiario, uf_beneficiario, valor_custeio,"
                    " valor_investimento, objeto_declarado) VALUES (:i, :c, 2024, 2024, :n, 'Fulana de Tal',"
                    " '11111111000111', 'MUNICIPIO DE EXEMPLO DO NORTE', 'RN', 0, 400000, 'Pavimentação da Rua A')"
                ),
                {"i": id_, "c": f"09032024-00000{id_}", "n": num},
            )
            c.execute(
                text("INSERT INTO pagamento (id, id_plano_acao, data_pagamento, valor) VALUES (:p, :i, :d, 400000)"),
                {"p": f"op{id_}", "i": id_, "d": HOJE - timedelta(days=300)},
            )
            c.execute(
                text(
                    "INSERT INTO avaliacao (id_plano_acao, status, alertas, justificativa)"
                    " VALUES (:i, CAST(:s AS status_semaforo), :a, 'teste')"
                ),
                {"i": id_, "s": status, "a": alertas},
            )
        ev = c.execute(
            text(
                "INSERT INTO evidencia (fonte, id_externo, cnpj_orgao, data_publicacao, objeto, valor, tipo_ato,"
                " fornecedor_documento, fornecedor_nome, url, raw) VALUES ('pncp_contrato', 'x-2-1/2025',"
                " '11111111000111', :d, 'Pavimentação da Rua A', 390000, 'contrato', '12345678901',"
                " 'Pessoa física (nome omitido)', 'https://pncp.gov.br/app/contratos/x/2025/1', '{}') RETURNING id"
            ),
            {"d": HOJE - timedelta(days=200)},
        ).scalar_one()
        c.execute(
            text(
                "INSERT INTO correspondencia (id_plano_acao, id_evidencia, score_pre_filtro, compativel, confianca,"
                " resposta_ia, metodo) VALUES (1, :e, 0.8, true, 0.9, CAST(:r AS jsonb), 'heuristica')"
            ),
            {"e": ev, "r": json.dumps({"justificativa": "mesmo objeto", "trechos_citados": ["Rua A"]})},
        )


def test_saude(cliente) -> None:
    assert cliente.get("/saude").json()["status"] == "ok"


def test_listar_emendas_com_filtros(cliente) -> None:
    r = cliente.get("/emendas", params={"uf": "RN"}).json()
    assert r["total"] == 2 and r["resumo_status"] == {"verde": 1, "vermelho": 1}
    assert cliente.get("/emendas", params={"status": "vermelho"}).json()["total"] == 1
    assert cliente.get("/emendas", params={"parlamentar": "fulana"}).json()["total"] == 2
    assert cliente.get("/emendas", params={"municipio": "2401859"}).json()["total"] == 2
    assert cliente.get("/emendas", params={"municipio": "exemplo"}).json()["total"] == 2
    assert cliente.get("/emendas", params={"ano": 2025}).json()["total"] == 0
    assert cliente.get("/emendas", params={"busca": "pavimentacao"}).json()["total"] == 2
    p = cliente.get("/emendas", params={"tamanho": 1, "pagina": 2}).json()
    assert p["pagina"] == 2 and len(p["itens"]) == 1
    assert cliente.get("/emendas", params={"status": "roxo"}).status_code == 422


def test_ficha_com_linha_do_tempo_evidencia_e_cpf_mascarado(cliente) -> None:
    f = cliente.get("/emendas/1").json()
    assert f["status"] == "verde" and f["evidencias"][0]["conta_como_evidencia"] is True
    assert f["evidencias"][0]["fornecedor_documento"] == "***.456.789-**"
    etapas = [e["etapa"] for e in f["linha_do_tempo"]]
    assert etapas[0] == "indicacao" and "pagamento" in etapas and etapas[-1] == "contrato"
    assert f["evidencias"][0]["url"].startswith("https://pncp.gov.br")
    assert "12345678901" not in json.dumps(f)
    assert cliente.get("/emendas/999").status_code == 404


def test_alertas_detalhados(cliente) -> None:
    f = cliente.get("/emendas/2").json()
    assert f["alertas_detalhados"][0]["codigo"] == "A1"


def test_dossie_pdf(cliente) -> None:
    r = cliente.get("/emendas/1/dossie.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_municipio_parlamentar_mapa_cobertura(cliente) -> None:
    m = cliente.get("/municipios/2401859").json()
    assert m["nome"] == "Exemplo do Norte" and m["pequeno"] and m["status"]["verde"] == 1
    assert cliente.get("/municipios/123").status_code == 422
    assert cliente.get("/municipios/0000000").status_code == 404
    p = cliente.get("/parlamentares/Fulana").json()
    assert p["total_emendas"] == 2 and p["ufs"] == ["RN"]
    assert cliente.get("/parlamentares/zzzzz").status_code == 404
    mapa = cliente.get("/mapa").json()
    assert mapa[0]["codigo_ibge"] == "2401859" and mapa[0]["status"] == "vermelho"
    cob = cliente.get("/cobertura").json()
    assert cob[0]["uf"] == "RN" and cob[0]["pequenos_cobertos_querido_diario"] == 1


def test_assinaturas(cliente) -> None:
    ok = cliente.post("/assinaturas", json={"email": "A@Exemplo.org", "tipo": "municipio", "chave": "2401859"})
    assert ok.status_code == 201
    repetida = cliente.post("/assinaturas", json={"email": "a@exemplo.org", "tipo": "municipio", "chave": "2401859"})
    assert repetida.status_code == 201
    assert cliente.post("/assinaturas", json={"email": "x", "tipo": "municipio", "chave": "2401859"}).status_code == 422
    assert cliente.post("/assinaturas", json={"email": "a@b.co", "tipo": "municipio", "chave": "12"}).status_code == 422


def test_atualizacao(cliente) -> None:
    assert "ultima_avaliacao" in cliente.get("/atualizacao").json()


def test_status_predominante() -> None:
    from rastro.api.consultas import status_predominante

    assert status_predominante({"vermelho": 1, "verde": 9}) == "vermelho"
    assert status_predominante({"verde": 3, "azul": 1}) == "verde"
    assert status_predominante({"amarelo": 1, "verde": 1}) == "amarelo"
    assert status_predominante({}) == "cinza"
