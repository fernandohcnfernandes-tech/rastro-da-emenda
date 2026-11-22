from rastro import alertas
from rastro.alertas import Assinatura, Mudanca

M1 = Mudanca(1, "202400010001", "MUNICIPIO X", "2401859", "Fulana de Tal", "cinza", "vermelho")
M2 = Mudanca(2, "202400010002", "MUNICIPIO Y", "2400000", "Beltrano", None, "verde")


def test_montar_mensagens_por_municipio_e_parlamentar() -> None:
    assinaturas = [
        Assinatura("a@x.org", "municipio", "2401859"),
        Assinatura("a@x.org", "parlamentar", "FULANA DE TAL"),  # mesma mudança não se repete
        Assinatura("b@x.org", "parlamentar", "beltrano"),
        Assinatura("c@x.org", "municipio", "9999999"),
    ]
    msgs = alertas.montar_mensagens([M1, M2], assinaturas, "https://site")
    assert set(msgs) == {"a@x.org", "b@x.org"}
    assert msgs["a@x.org"].count("202400010001") == 1 and "cinza → vermelho" in msgs["a@x.org"]
    assert "https://site/emendas/2" in msgs["b@x.org"] and "sem avaliação → verde" in msgs["b@x.org"]
    assert "indícios" in msgs["a@x.org"] and "fraude" not in msgs["a@x.org"]


def test_enviar_sem_smtp_so_registra(monkeypatch) -> None:
    monkeypatch.setattr(alertas, "config", lambda: type("C", (), {"smtp_host": "", "email_remetente": ""})())
    assert alertas.enviar({"a@x.org": "oi"}) == {"enviados": 0, "registrados": 1}
    assert alertas.enviar({}) == {"enviados": 0, "registrados": 0}


def test_enviar_com_smtp(monkeypatch) -> None:
    enviados = []

    class SMTPFalso:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            pass

        def login(self, u, s):
            pass

        def send_message(self, msg):
            enviados.append(msg["To"])

    cfg = type(
        "C", (), {"smtp_host": "h", "smtp_port": 587, "smtp_user": "u", "smtp_password": "s", "email_remetente": "r@x"}
    )
    monkeypatch.setattr(alertas, "config", lambda: cfg())
    monkeypatch.setattr(alertas.smtplib, "SMTP", SMTPFalso)
    assert alertas.enviar({"a@x.org": "oi", "b@x.org": "oi"})["enviados"] == 2 and enviados == ["a@x.org", "b@x.org"]
