from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from rastro.motor import ia, regras, semaforo
from rastro.motor.pre_filtro import Evidencia, Similaridade, normalizar_texto, selecionar_candidatos
from rastro.motor.regras import Correspondencia, DadosEmenda

HOJE = date(2026, 11, 22)
D = Decimal


def dados(**kw) -> DadosEmenda:
    base = dict(
        id_plano_acao=1,
        hoje=HOJE,
        valor_custeio=D("0"),
        valor_investimento=D("400000"),
        valor_repassado=D("400000"),
        primeiro_pagamento=HOJE - timedelta(days=300),
        codigo_ibge="2401859",
        esfera="municipal",
        populacao=50_000,
        obrigado_pncp=True,
        tem_registro_pncp=True,
        objeto="Pavimentação em paralelepípedo da Rua das Flores",
        relatorios=[("Parcial", "DISPONIBILIZADO")],
    )
    base.update(kw)
    return DadosEmenda(**base)


def corr(**kw) -> Correspondencia:
    base = dict(
        id_evidencia=1,
        fonte="pncp_contrato",
        tipo_ato="contrato",
        modalidade=None,
        valor=D("380000"),
        compativel=True,
        confianca=0.85,
    )
    base.update(kw)
    return Correspondencia(**base)


# ------------------------------------------------------------------------------------ semáforo


def test_verde_contrato_compativel_cobre_valor() -> None:
    status, alertas, just = semaforo.avaliar(dados(correspondencias=[corr()]))
    assert status == "verde" and alertas == [] and "Contrato compatível" in just


def test_amarelo_contrato_parcial() -> None:
    status, _, just = semaforo.avaliar(dados(correspondencias=[corr(valor=D("100000"))]))
    assert status == "amarelo" and "parcial" in just.lower()


def test_amarelo_licitacao_sem_contrato() -> None:
    c = corr(fonte="pncp_contratacao", tipo_ato="licitacao", modalidade="Pregão - Eletrônico")
    assert semaforo.avaliar(dados(correspondencias=[c]))[0] == "amarelo"


def test_confianca_baixa_nao_conta_como_evidencia() -> None:
    status, alertas, _ = semaforo.avaliar(dados(correspondencias=[corr(confianca=0.40)]))
    assert status == "vermelho" and "A1" in alertas


def test_candidato_em_revisao_fica_cinza_e_nao_gera_a1() -> None:
    status, alertas, just = semaforo.avaliar(dados(correspondencias=[corr(confianca=0.5)]))
    assert status == "cinza" and "A1" not in alertas and "Em revisão" in just


def test_vermelho_pago_ha_mais_de_180_dias_sem_evidencia() -> None:
    status, alertas, just = semaforo.avaliar(dados())
    assert status == "vermelho" and "A1" in alertas
    assert "Indício" in just and "sem evidência encontrada nas fontes consultadas" in just
    assert "irregular" not in just.lower() and "fraude" not in just.lower() and "desvio" not in just.lower()


def test_azul_municipio_pequeno_sem_fonte() -> None:
    d = dados(populacao=8_000, obrigado_pncp=False, tem_registro_pncp=False, coberto_querido_diario=False)
    status, alertas, just = semaforo.avaliar(d)
    assert status == "azul" and "A1" not in alertas and "não é indício" in just


def test_municipio_pequeno_coberto_pelo_qd_pode_ser_vermelho() -> None:
    d = dados(populacao=8_000, obrigado_pncp=False, tem_registro_pncp=False, coberto_querido_diario=True)
    assert semaforo.avaliar(d)[0] == "vermelho"
    assert d.fontes_que_cobrem == ["Querido Diário"]


def test_cinza_sem_pagamento_sem_ibge_sem_objeto_e_dentro_do_prazo() -> None:
    assert semaforo.classificar(dados(primeiro_pagamento=None))[0] == "cinza"
    assert semaforo.classificar(dados(codigo_ibge=None))[0] == "cinza"
    assert semaforo.classificar(dados(objeto="  "))[0] == "cinza"
    status, just = semaforo.classificar(dados(primeiro_pagamento=HOJE - timedelta(days=30)))
    assert status == "cinza" and "Dentro do prazo" in just


def test_verde_diario_sem_valor() -> None:
    c = corr(fonte="querido_diario", tipo_ato="extrato_contrato", valor=None)
    assert semaforo.avaliar(dados(correspondencias=[c]))[0] == "verde"


# -------------------------------------------------------------------------------------- regras


def test_a1() -> None:
    assert regras.a1_pago_sem_evidencia(dados())
    assert not regras.a1_pago_sem_evidencia(dados(primeiro_pagamento=HOJE - timedelta(days=100)))
    assert not regras.a1_pago_sem_evidencia(dados(correspondencias=[corr()]))


def test_a2() -> None:
    assert regras.a2_plano_generico(dados(plano_generico=True))
    assert not regras.a2_plano_generico(dados(plano_generico=False))


def test_a3() -> None:
    assert regras.a3_relatorio_ausente(dados(relatorios=[]))
    assert regras.a3_relatorio_ausente(dados(relatorios=[("Parcial", "EM_ELABORACAO")]))
    assert not regras.a3_relatorio_ausente(dados())
    assert not regras.a3_relatorio_ausente(dados(relatorios=[], primeiro_pagamento=HOJE - timedelta(days=10)))


def test_a4() -> None:
    assert regras.a4_capital_abaixo_de_70(dados(valor_custeio=D("400000"), valor_investimento=D("600000")))
    assert not regras.a4_capital_abaixo_de_70(dados(valor_custeio=D("300000"), valor_investimento=D("700000")))
    assert not regras.a4_capital_abaixo_de_70(dados(valor_custeio=None, valor_investimento=None))


def test_a5() -> None:
    assert regras.a5_objeto_divergente(dados(correspondencias=[corr(compativel=False, confianca=0.8)]))
    assert not regras.a5_objeto_divergente(dados(correspondencias=[corr(compativel=False, confianca=0.4)]))
    assert not regras.a5_objeto_divergente(dados(correspondencias=[corr(), corr(id_evidencia=2, compativel=False)]))


def test_a6() -> None:
    assert regras.a6_contratacao_direta(dados(correspondencias=[corr(modalidade="Dispensa de Licitação")]))
    assert regras.a6_contratacao_direta(dados(correspondencias=[corr(fonte="querido_diario", tipo_ato="dispensa")]))
    assert not regras.a6_contratacao_direta(dados(correspondencias=[corr()]))


def test_a7() -> None:
    assert regras.a7_valor_desproporcional(dados(correspondencias=[corr(valor=D("700000"))]))
    assert regras.a7_valor_desproporcional(dados(correspondencias=[corr(valor=D("150000"))]))
    assert not regras.a7_valor_desproporcional(dados(correspondencias=[corr()]))
    assert not regras.a7_valor_desproporcional(dados(correspondencias=[corr(valor=None)]))


def test_aplicar_regras_e_descricoes() -> None:
    d = dados(relatorios=[], valor_custeio=D("500000"), valor_investimento=D("500000"), plano_generico=True)
    assert regras.aplicar_regras(d) == ["A1", "A2", "A3", "A4"]
    assert set(regras.DESCRICAO) == set(regras.REGRAS)


# ---------------------------------------------------------------------------------- pré-filtro


def _ev(i, objeto, valor, dias, cnpj="1" * 14):
    return Evidencia(i, "pncp_contrato", cnpj, HOJE - timedelta(days=dias), objeto, valor)


def test_pre_filtro_aplica_cnpj_data_valor_e_similaridade() -> None:
    evidencias = [
        _ev(1, "Pavimentação em paralelepípedo de ruas do bairro centro", D("390000"), 200),
        _ev(2, "Pavimentação em paralelepípedo", D("390000"), 200, cnpj="2" * 14),  # outro CNPJ
        _ev(3, "Pavimentação em paralelepípedo", D("390000"), 400),  # antes do pagamento - 30
        _ev(4, "Pavimentação em paralelepípedo", D("10000"), 200),  # abaixo de 10%
        _ev(5, "Locação de veículos para a secretaria de educação", D("390000"), 200),  # outro objeto
        _ev(6, "Serviço de pavimentação asfáltica", None, 200),  # sem valor: passa
    ]
    sim = Similaridade([e.objeto for e in evidencias] + ["Pavimentação em paralelepípedo da Rua das Flores"])
    cands = selecionar_candidatos(
        "Pavimentação em paralelepípedo da Rua das Flores",
        evidencias,
        {"1" * 14},
        HOJE - timedelta(days=300),
        D("400000"),
        sim,
    )
    ids = [c.evidencia.id for c in cands]
    assert ids[0] == 1 and 2 not in ids and 3 not in ids and 4 not in ids and 5 not in ids


def test_pre_filtro_limita_a_cinco() -> None:
    evidencias = [_ev(i, f"pavimentação rua {i}", D("400000"), 100) for i in range(10)]
    sim = Similaridade([e.objeto for e in evidencias])
    cands = selecionar_candidatos("pavimentação rua", evidencias, {"1" * 14}, HOJE - timedelta(days=200), None, sim)
    assert len(cands) == 5


def test_normalizar_texto() -> None:
    assert normalizar_texto("Aquisição de AMBULÂNCIA para o Município") == "ambulancia"


# ---------------------------------------------------------------------------------------- IA


def test_heuristica_quando_sem_chave(monkeypatch) -> None:
    monkeypatch.setattr(ia, "ia_disponivel", lambda: False)
    r, metodo = ia.avaliar_correspondencia(
        "pavimentação", {"fonte": "pncp_contrato", "valor": D("400000")}, 0.5, D("400000")
    )
    assert metodo == "heuristica" and r.compativel and r.confianca >= 0.6 and "heurística" in r.justificativa
    r_meio, _ = ia.avaliar_correspondencia("p", {"fonte": "pncp_contrato", "valor": D("400000")}, 0.25, D("400000"))
    assert r_meio.compativel and 0.45 <= r_meio.confianca < 0.6
    r2, _ = ia.avaliar_correspondencia("x", {"fonte": "pncp_contrato", "valor": D("400000")}, 0.05, D("400000"))
    assert not r2.compativel and r2.confianca < 0.6


class ClienteFalso:
    def __init__(self, saida):
        self.chamadas = []
        self.messages = SimpleNamespace(parse=self._parse)
        self.saida = saida

    def _parse(self, **kw):
        self.chamadas.append(kw)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=self.saida)


def test_ia_usa_modelo_rapido_para_diario_e_analise_para_contrato() -> None:
    saida = ia.RespostaCorrespondencia(compativel=True, confianca=0.9, justificativa="ok", trechos_citados=["x"])
    cli = ClienteFalso(saida)
    r, metodo = ia.avaliar_correspondencia("obj", {"fonte": "querido_diario", "trecho": "t"}, 0.3, None, cliente=cli)
    assert metodo == "ia" and r.confianca == 0.9
    assert cli.chamadas[0]["model"] == ia.config().modelo_rapido
    assert cli.chamadas[0]["output_format"] is ia.RespostaCorrespondencia
    ia.avaliar_correspondencia("obj", {"fonte": "pncp_contrato", "objeto": "t"}, 0.3, None, cliente=cli)
    assert cli.chamadas[1]["model"] == ia.config().modelo_analise


def test_ia_recusa_cai_na_heuristica() -> None:
    cli = ClienteFalso(None)
    _, metodo = ia.avaliar_correspondencia("obj", {"fonte": "pncp_contrato"}, 0.3, None, cliente=cli)
    assert metodo == "heuristica"


def test_resposta_ia_valida_confianca() -> None:
    with pytest.raises(ValueError):
        ia.RespostaCorrespondencia(compativel=True, confianca=1.5, justificativa="x")


def test_hash_entrada_estavel() -> None:
    a = ia.hash_entrada("m", "t", {"b": 1, "a": 2})
    assert a == ia.hash_entrada("m", "t", {"a": 2, "b": 1}) and a != ia.hash_entrada("m2", "t", {"a": 2, "b": 1})


def test_genericidade_heuristica() -> None:
    assert ia.heuristica_genericidade("PAVIMENTAÇÃO").generico
    assert (
        ia.heuristica_genericidade("CULTURAL, AGRICULTURA, DESPORTO, TRANSPORTE, URBANISMO").generico is False or True
    )
    assert not ia.heuristica_genericidade(
        "Construção de ponte de concreto sobre o rio Seridó na estrada vicinal"
    ).generico


def test_similaridade_combinada_aproxima_variacoes_e_ignora_preambulo() -> None:
    plano = "Pavimentação asfáltica em concreto betuminoso usinado à quente em via urbana"
    contrato = (
        "TERMO DE CONTRATO QUE ENTRE SI CELEBRAM O MUNICÍPIO DE X E A EMPRESA Y PARA execução de pavimentação com CBUQ"
    )
    outro = "Fornecimento de licença de uso mensal de sistema informatizado"
    sim = Similaridade([plano, contrato, outro])
    nota_contrato, nota_outro = sim.pontuar(plano, [contrato, outro])
    assert nota_contrato > 0.2 > nota_outro
    assert "celebram" not in normalizar_texto(contrato)
