from decimal import Decimal

import httpx
import respx

from rastro.conectores import transferegov as tg
from rastro.conectores.base import ClienteHttp
from tests.conftest import carregar_fixture


def fx(nome: str):
    return carregar_fixture("transferegov", f"{nome}.json")


def test_esfera_do_ente() -> None:
    assert tg.esfera_do_ente("MUNICIPIO DE IRACEMA") == "municipal"
    assert tg.esfera_do_ente("ESTADO DE RORAIMA") == "estadual"
    assert tg.esfera_do_ente("Distrito Federal") == "estadual"
    assert tg.esfera_do_ente("CONSORCIO X") == "outro"


def test_plano_acao_normaliza_e_remove_dados_bancarios() -> None:
    bruto = fx("plano_acao_especial")[0]
    bruto = {**bruto, "numero_conta_plano_acao": 123, "nome_banco_plano_acao": "BB"}
    plano = tg.plano_acao(bruto)
    assert plano["id_plano_acao"] == bruto["id_plano_acao"]
    assert len(plano["cnpj_beneficiario"]) == 14
    assert isinstance(plano["valor_custeio"], Decimal)
    assert plano["emenda_ano"] >= 2024
    assert not any("conta" in k or "banco" in k for k in plano["raw"])
    ente = tg.ente_de_plano(bruto)
    assert ente["cnpj"] == plano["cnpj_beneficiario"] and ente["esfera"] in {"municipal", "estadual", "outro"}


def test_cadeia_de_pagamento_das_fixtures() -> None:
    plano = fx("plano_acao_especial")[0]["id_plano_acao"]
    empenhos = [tg.empenho(r) for r in fx("empenho_especial")]
    assert all(e["id_plano_acao"] == plano for e in empenhos)
    ids_empenho = {e["id_empenho"] for e in empenhos}
    dhs = [tg.documento_habil(r) for r in fx("documento_habil_especial")]
    assert all(d["id_empenho"] in ids_empenho for d in dhs)
    ids_dh = {d["id_dh"] for d in dhs}
    pagamentos = [tg.pagamento(r) for r in fx("ordem_pagamento_ordem_bancaria_especial")]
    assert pagamentos and all(p["id_dh"] in ids_dh and p["data_pagamento"] for p in pagamentos)


def test_meta_usa_executor_para_achar_plano() -> None:
    executores = [tg.executor(r) for r in fx("executor_especial")]
    mapa = {e["id"]: e["id_plano_acao"] for e in executores}
    metas = [tg.meta(r, mapa) for r in fx("meta_especial")]
    assert metas and all(m and m["id_plano_acao"] == executores[0]["id_plano_acao"] for m in metas)
    assert tg.meta({"id_meta": 1, "id_executor": -5}, mapa) is None


def test_relatorios_tem_prefixo_por_origem() -> None:
    rg = tg.relatorio_gestao(fx("relatorio_gestao_especial")[0])
    rgn = tg.relatorio_gestao_novo(fx("relatorio_gestao_novo_especial")[0])
    assert rg["id"].startswith("rg:") and rgn["id"].startswith("rgn:")
    assert rgn["tipo"] in {"Parcial", "Final"}


@respx.mock
def test_paginas_usa_limit_offset_ate_pagina_incompleta() -> None:
    base = "https://tg.teste"
    linhas = fx("meta_especial")
    rota = respx.get(f"{base}/meta_especial").mock(
        side_effect=[
            httpx.Response(200, json=linhas[:4], headers={"content-type": "application/json"}),
            httpx.Response(200, json=linhas[4:6], headers={"content-type": "application/json"}),
        ]
    )
    cli = ClienteHttp(base, por_minuto=0)
    paginas = list(tg.paginas(cli, "meta_especial", ordem="id_meta", tamanho=4))
    assert [p[0] for p in paginas] == [4, 6]
    assert rota.calls[1].request.url.params["offset"] == "4"
    assert rota.calls[0].request.url.params["order"] == "id_meta"
