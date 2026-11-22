from types import SimpleNamespace

import pytest

from rastro.agente import assistente


class ClienteFalso:
    """Primeira chamada pede uma ferramenta; a segunda devolve o texto final."""

    def __init__(self):
        self.chamadas = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._criar))

    def _criar(self, **kw):
        self.chamadas.append(kw)
        if len(self.chamadas) == 1:
            uso = SimpleNamespace(type="tool_use", id="t1", name="outras_emendas_do_beneficiario", input={})
            return SimpleNamespace(stop_reason="tool_use", content=[uso], model="m")
        texto = SimpleNamespace(type="text", text="Há indício para apuração; veja o contrato no PNCP.")
        return SimpleNamespace(stop_reason="end_turn", content=[texto], model="m")


def test_laco_de_ferramentas(monkeypatch) -> None:
    monkeypatch.setattr(
        assistente, "ficha_emenda", lambda conn, i: {"id_plano_acao": i, "evidencias": [], "objeto_completo": "x"}
    )
    monkeypatch.setattr(assistente, "_cache_ler", lambda conn, chave: None)
    monkeypatch.setattr(assistente, "_cache_gravar", lambda *a: None)
    monkeypatch.setattr(assistente, "executar_ferramenta", lambda conn, i, f, nome, entrada: [{"id_plano_acao": 2}])
    cli = ClienteFalso()
    r = assistente.responder(None, 1, "Resuma a execução", cliente=cli)
    assert r["resposta"].startswith("Há indício") and r["ferramentas"] == ["outras_emendas_do_beneficiario"]
    segunda = cli.chamadas[1]["messages"]
    assert segunda[-1]["content"][0]["type"] == "tool_result" and segunda[-1]["content"][0]["tool_use_id"] == "t1"
    assert "Nunca afirme" in cli.chamadas[0]["system"] and cli.chamadas[0]["tools"] == assistente.FERRAMENTAS


def test_recusa_vira_mensagem_neutra(monkeypatch) -> None:
    monkeypatch.setattr(assistente, "ficha_emenda", lambda conn, i: {"id_plano_acao": i})
    monkeypatch.setattr(assistente, "_cache_ler", lambda conn, chave: None)
    gravado = []
    monkeypatch.setattr(assistente, "_cache_gravar", lambda *a: gravado.append(a))
    cli = SimpleNamespace(
        beta=SimpleNamespace(
            messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(stop_reason="refusal", content=[], model="m"))
        )
    )
    r = assistente.responder(None, 1, "pergunta", cliente=cli)
    assert "Não consegui responder" in r["resposta"] and not gravado


def test_emenda_inexistente(monkeypatch) -> None:
    monkeypatch.setattr(assistente, "ficha_emenda", lambda conn, i: None)
    with pytest.raises(LookupError):
        assistente.responder(None, 1, "x", cliente=object())


def test_ficha_compacta_limita_tamanho() -> None:
    f = {
        "objeto_completo": "a" * 10_000,
        "metas": [{"descricao": "m" * 1000}] * 30,
        "evidencias": [{"id": 1, "raw": "x"}],
    }
    c = assistente._ficha_compacta(f)
    assert len(c["objeto_declarado"]) == 3000 and len(c["metas"]) == 15 and "raw" not in c["evidencias_avaliadas"][0]


def test_consultor_usa_laco_e_regras(monkeypatch) -> None:
    from rastro.agente import consultor

    monkeypatch.setattr(consultor.consultas, "ultima_atualizacao", lambda conn: {"em": "hoje"})
    monkeypatch.setattr(consultor, "_cache_ler", lambda conn, chave: None)
    monkeypatch.setattr(consultor, "_cache_gravar", lambda *a: None)
    monkeypatch.setattr(consultor, "executar_ferramenta", lambda conn, nome, entrada: [{"grupo": "BA"}])
    cli = ClienteFalso()
    r = consultor.responder(None, "Qual UF recebeu mais?", cliente=cli)
    assert r["resposta"].startswith("Há indício") and r["ferramentas"] == ["outras_emendas_do_beneficiario"]
    sistema = cli.chamadas[0]["system"]
    assert "Nunca afirme" in sistema and "/emendas/<id_plano_acao>" in sistema and "{site}" not in sistema
    assert cli.chamadas[0]["tools"] == consultor.FERRAMENTAS
