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
        c.execute(
            text(
                "INSERT INTO parlamentar (id, casa, nome, chave_nome, partido, uf, url_foto, email, url_pagina)"
                " VALUES ('camara:9', 'camara', 'Fulana de Tal', 'FULANADETAL', 'XYZ', 'PB',"
                " 'https://foto', 'f@camara.leg.br', 'https://www.camara.leg.br/deputados/9')"
            )
        )
        c.execute(text("INSERT INTO parlamentar_autor VALUES ('Fulana de Tal', 'camara:9', 'exato')"))
        c.execute(
            text(
                "INSERT INTO ente (cnpj, nome, uf, esfera, codigo_ibge, populacao, obrigado_pncp)"
                " VALUES ('22222222000122', 'ESTADO DO RIO GRANDE DO NORTE', 'RN', 'estadual', '2400000',"
                " 3400000, true)"
            )
        )
        c.execute(
            text(
                "INSERT INTO plano_acao (id_plano_acao, codigo_plano_acao, ano_plano_acao, emenda_ano, emenda_numero,"
                " parlamentar_nome, cnpj_beneficiario, nome_beneficiario, uf_beneficiario, valor_investimento,"
                " objeto_declarado) VALUES (3, '09032024-000003', 2024, 2024, '202400010003', 'Beltrano',"
                " '22222222000122', 'ESTADO DO RIO GRANDE DO NORTE', 'RN', 900000, 'Ponte estadual')"
            )
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
    r = cliente.get("/emendas", params={"uf": "RN", "esfera": "municipal"}).json()
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


def test_acessos(cliente) -> None:
    from rastro.api import main

    main._acessos.clear()
    inicio = cliente.get("/acessos").json()
    depois = cliente.post("/acessos").json()
    assert depois["total"] == inicio["total"] + 1 and depois["hoje"] == inicio["hoje"] + 1 and depois["desde"]
    assert cliente.get("/acessos").json() == depois
    for _ in range(main.LIMITE_ACESSOS_POR_IP + 5):  # excesso do mesmo IP não conta
        ultimo = cliente.post("/acessos").json()
    assert ultimo["total"] == inicio["total"] + main.LIMITE_ACESSOS_POR_IP
    outro_ip = cliente.post("/acessos", headers={"x-forwarded-for": "203.0.113.9"}).json()
    assert outro_ip["total"] == ultimo["total"] + 1


def test_atualizacao(cliente) -> None:
    assert "ultima_avaliacao" in cliente.get("/atualizacao").json()


def test_status_predominante() -> None:
    from rastro.api.consultas import status_predominante

    assert status_predominante({"vermelho": 2, "verde": 8}) == "vermelho"  # 20%
    assert status_predominante({"vermelho": 1, "verde": 2, "amarelo": 1, "azul": 19}) == "azul"  # RN: 1 de 23
    assert status_predominante({"vermelho": 1}) == "vermelho"
    assert status_predominante({"verde": 3, "azul": 1}) == "verde"
    assert status_predominante({"amarelo": 1, "verde": 1}) == "amarelo"
    assert status_predominante({"laranja": 2, "verde": 1}) == "laranja"
    assert status_predominante({}) == "cinza"


def test_resumo_alertas_e_listas(cliente) -> None:
    r = cliente.get("/resumo").json()
    assert r["emendas"] == 3 and r["status"] == {"verde": 1, "vermelho": 1, "cinza": 1}
    assert r["percentual_com_evidencia"] == 50.0 and r["ranking_indicios"][0]["codigo_ibge"] == "2401859"
    assert r["por_uf"][0]["uf"] == "RN"
    al = {a["codigo"]: a for a in cliente.get("/alertas").json()}
    assert al["A1"]["emendas"] == 1 and al["A2"]["emendas"] == 0 and len(al) == 9
    assert cliente.get("/emendas", params={"alerta": "A1"}).json()["total"] == 1
    assert cliente.get("/emendas", params={"alerta": "A10"}).status_code == 422
    assert cliente.get("/emendas", params={"ordem": "recentes"}).status_code == 200
    m = cliente.get("/municipios", params={"busca": "exemplo"}).json()
    assert m["total"] == 1 and m["itens"][0]["status"] == "vermelho"
    p = cliente.get("/parlamentares", params={"busca": "fulana"}).json()
    assert p["total"] == 1 and p["itens"][0]["emendas"] == 2


def test_parlamentares_por_uf_casa_partido_e_perfil(cliente) -> None:
    assert cliente.get("/parlamentares", params={"uf": "PB"}).json()["total"] == 1
    assert (
        cliente.get("/parlamentares", params={"uf": "RN"}).json()["total"] == 0
    )  # UF do parlamentar, não do município
    r = cliente.get("/parlamentares", params={"casa": "camara", "partido": "xyz"}).json()
    assert r["total"] == 1 and r["itens"][0]["uf_parlamentar"] == "PB" and r["partidos"] == ["XYZ"]
    perfil = cliente.get("/parlamentares/Fulana de Tal").json()["perfil"]
    assert perfil["casa"] == "camara" and perfil["url_pagina"].startswith("https://www.camara.leg.br")


def test_esfera_e_mapa_dos_estados(cliente) -> None:
    assert cliente.get("/emendas", params={"esfera": "estadual"}).json()["total"] == 1
    assert cliente.get("/emendas", params={"esfera": "municipal"}).json()["total"] == 2
    assert cliente.get("/emendas", params={"esfera": "federal"}).status_code == 422
    estados = cliente.get("/mapa/estados").json()
    assert len(estados) == 1 and estados[0]["uf"] == "RN" and estados[0]["emendas"] == 1
    assert estados[0]["status"] == "cinza"


def test_coleta_e_valores_por_uf(cliente) -> None:
    fontes = {f["fonte"]: f for f in cliente.get("/coleta").json()}
    assert set(fontes) >= {"transferegov", "portal", "pncp", "tce", "querido_diario", "congresso", "ibge"}
    assert fontes["transferegov"]["numeros"]["planos"] == 3 and fontes["transferegov"]["numeros"]["pagamentos"] == 2
    assert fontes["pncp"]["numeros"]["contratos"] == 1 and fontes["pncp"]["numeros"]["cnpjs_monitorados"] >= 2
    uf = cliente.get("/resumo").json()["por_uf"][0]
    assert uf["repassado"] == 800000 and uf["verde_valor"] == 400000 and uf["vermelho_valor"] == 400000


def test_assistente_sem_chave_e_com_resposta(cliente, monkeypatch) -> None:
    from rastro.api import main

    monkeypatch.setattr(main, "config", lambda: type("C", (), {"anthropic_api_key": "", "modelo_analise": "m"})())
    assert cliente.get("/assistente").json()["disponivel"] is False
    assert cliente.post("/emendas/1/assistente", json={"pergunta": "Resuma"}).status_code == 503
    monkeypatch.setattr(main, "config", lambda: type("C", (), {"anthropic_api_key": "k", "modelo_analise": "m"})())
    monkeypatch.setattr(main.assistente, "responder", lambda conn, i, p, h: {"resposta": f"ok {i} {p}", "cache": False})
    r = cliente.post(
        "/emendas/1/assistente", json={"pergunta": "Resuma", "historico": [{"papel": "usuario", "texto": "oi"}]}
    )
    assert r.status_code == 200 and r.json()["resposta"] == "ok 1 Resuma"
    assert cliente.post("/emendas/1/assistente", json={"pergunta": "x"}).status_code == 422
    pdf = cliente.get("/emendas/1/dossie.pdf", params={"analise": "true"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_dossie_com_analise_desativado(cliente, monkeypatch) -> None:
    from rastro.api import main

    chamadas: list[int] = []

    def responder(conn, i, p, h=None):
        chamadas.append(i)
        return {"resposta": "análise", "cache": False}

    monkeypatch.setattr(main.assistente, "responder", responder)
    for ligado, esperado in ((False, 0), (True, 1)):
        monkeypatch.setattr(
            main,
            "config",
            lambda ligado=ligado: type(
                "C", (), {"anthropic_api_key": "k", "modelo_analise": "m", "dossie_com_analise": ligado}
            )(),
        )
        main._uso.clear()
        pdf = cliente.get("/emendas/1/dossie.pdf", params={"analise": "true"})
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
        assert len(chamadas) == esperado


def test_ferramentas_do_consultor_no_banco(cliente) -> None:
    from rastro.agente import consultor

    with conexao.engine().connect() as conn:
        r = consultor.executar_ferramenta(conn, "ranking", {"agrupar_por": "uf", "metrica": "repassado"})
        assert r[0]["grupo"] == "RN" and r[0]["repassado"] == 800000 and r[0]["vermelho"] == 1
        assert consultor.executar_ferramenta(conn, "ranking", {"agrupar_por": "parlamentar", "metrica": "vermelho"})
        b = consultor.executar_ferramenta(conn, "buscar_emendas", {"uf": "RN", "limite": 5})
        assert b["total"] == 3 and set(b["itens"][0]) >= {"id_plano_acao", "status", "repassado"}
        m = consultor.executar_ferramenta(conn, "dados_do_municipio", {"municipio": "exemplo"})
        assert m["codigo_ibge"] == "2401859" and len(m["emendas"]) == 2
        assert consultor.executar_ferramenta(conn, "ficha_da_emenda", {"id_plano_acao": 999}) == {
            "erro": "emenda não encontrada"
        }
        with pytest.raises(KeyError):
            consultor.executar_ferramenta(conn, "ranking", {"agrupar_por": "x; DROP", "metrica": "emendas"})
        with pytest.raises(ValueError):
            consultor.executar_ferramenta(conn, "ranking", {"agrupar_por": "uf", "metrica": "1; DROP"})


def test_consultor_endpoint(cliente, monkeypatch) -> None:
    from rastro.api import main

    monkeypatch.setattr(main.consultor, "responder", lambda conn, p, h: {"resposta": "ok", "ferramentas": []})
    monkeypatch.setattr(main, "config", lambda: type("C", (), {"anthropic_api_key": "x", "modelo_analise": "m"})())
    assert cliente.post("/assistente/perguntar", json={"pergunta": "Quais UFs?"}).json()["resposta"] == "ok"
    assert cliente.post("/assistente/perguntar", json={"pergunta": "x"}).status_code == 422


def test_fontes_oficiais_apontam_para_paginas_publicas():
    from rastro.api.consultas import fontes_oficiais

    f = fontes_oficiais(64847, "202442770003")
    urls = [u for u in f.values() if u]
    assert all("api.transferegov" not in u for u in urls)
    assert f["Transferegov — plano de ação (dados básicos)"] == (
        "https://especiais.transferegov.sistema.gov.br/transferencia-especial/plano-acao/detalhe/64847/dados-basicos"
    )
    assert f["Portal da Transparência — emenda"].endswith("codigoEmenda=202442770003")
    assert fontes_oficiais(1, None)["Portal da Transparência — emenda"] is None


def test_atualizacao_consulta_no_pncp_so_cnpjs_novos(cliente, monkeypatch) -> None:
    """A atualização semanal consulta por completo só os CNPJs que nunca foram verificados no PNCP."""
    from rastro.conectores import pncp
    from rastro.db.conexao import transacao
    from rastro.jobs import carga_pncp

    # só CNPJs com pagamento têm o que buscar no PNCP
    cnpjs = sorted(a.cnpj for a in carga_pncp.cnpjs_monitorados(date(2024, 1, 1)) if a.primeiro_pagamento)
    assert cnpjs
    with transacao() as conn:
        conn.execute(text("DELETE FROM cobertura_pncp"))
    consultados: list[str] = []

    def contratos_falsos(_cli, cnpj, _ini, _fim):
        consultados.append(cnpj)
        return iter([])

    monkeypatch.setattr(pncp, "contratos", contratos_falsos)
    carga_pncp.carregar_contratos(date(2024, 1, 1), somente_novos=True)  # nunca verificados: consulta todos
    assert sorted(consultados) == cnpjs
    with transacao() as conn:  # mesmo verificado há 60 dias, não é "novo": não consulta de novo
        conn.execute(text("UPDATE cobertura_pncp SET verificado_em = now() - interval '60 days'"))
    consultados.clear()
    carga_pncp.carregar_contratos(date(2024, 1, 1), somente_novos=True)
    assert consultados == []
