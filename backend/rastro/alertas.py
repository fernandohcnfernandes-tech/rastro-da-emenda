"""Alertas por e-mail para assinantes cujo município ou parlamentar teve mudança de status.

Sem SMTP configurado, as mensagens são apenas registradas no log (nada é enviado).
"""

from __future__ import annotations

import smtplib
from collections import defaultdict
from dataclasses import dataclass
from email.message import EmailMessage

from rastro.config import config
from rastro.log import log
from rastro.util import sem_acentos

URL_SITE_PADRAO = "http://localhost:3000"


@dataclass(frozen=True)
class Mudanca:
    id_plano_acao: int
    emenda_numero: str | None
    beneficiario: str | None
    codigo_ibge: str | None
    parlamentar: str | None
    antes: str | None
    depois: str


@dataclass(frozen=True)
class Assinatura:
    email: str
    tipo: str  # municipio | parlamentar
    chave: str


def _norm(texto: str | None) -> str:
    return sem_acentos(texto or "").strip().lower()


def montar_mensagens(mudancas: list[Mudanca], assinaturas: list[Assinatura], url_site: str) -> dict[str, str]:
    """Agrupa as mudanças por e-mail de assinante e devolve {email: corpo da mensagem}."""
    por_email: dict[str, list[Mudanca]] = defaultdict(list)
    for a in assinaturas:
        for m in mudancas:
            if (a.tipo == "municipio" and a.chave == m.codigo_ibge) or (
                a.tipo == "parlamentar" and _norm(a.chave) == _norm(m.parlamentar)
            ):
                if m not in por_email[a.email]:
                    por_email[a.email].append(m)
    mensagens = {}
    for email, lista in por_email.items():
        linhas = [
            "Olá! Houve mudança no semáforo de emendas Pix que você acompanha no Rastro da Emenda:",
            "",
        ]
        for m in lista:
            linhas.append(
                f"- Emenda {m.emenda_numero or m.id_plano_acao} ({m.beneficiario}; {m.parlamentar}): "
                f"{m.antes or 'sem avaliação'} → {m.depois}. {url_site}/emendas/{m.id_plano_acao}"
            )
        linhas += [
            "",
            "Lembrete: o sistema aponta indícios para apuração, nunca acusações.",
            "Confira os documentos oficiais na ficha da emenda.",
            "",
            "QKV works — A próxima resposta pode transformar seu negócio.",
        ]
        mensagens[email] = "\n".join(linhas)
    return mensagens


def enviar(mensagens: dict[str, str]) -> dict[str, int]:
    cfg = config()
    if not mensagens:
        return {"enviados": 0, "registrados": 0}
    if not (cfg.smtp_host and cfg.email_remetente):
        for email, corpo in mensagens.items():
            log("alertas", "sem_smtp", destinatario=email, linhas=corpo.count("\n") + 1)
        return {"enviados": 0, "registrados": len(mensagens)}
    enviados = 0
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if cfg.smtp_user:
            smtp.login(cfg.smtp_user, cfg.smtp_password)
        for email, corpo in mensagens.items():
            msg = EmailMessage()
            msg["Subject"] = "Rastro da Emenda: mudança de status em emendas que você acompanha"
            msg["From"] = cfg.email_remetente
            msg["To"] = email
            msg.set_content(corpo)
            smtp.send_message(msg)
            enviados += 1
    log("alertas", "enviados", quantidade=enviados)
    return {"enviados": enviados, "registrados": 0}
