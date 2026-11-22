"""Dossiê PDF de uma emenda com a identidade visual QKV works (fpdf2, fontes core Helvetica ~ Arial)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fpdf import FPDF

TITULO = (11, 15, 26)  # #0B0F1A
DESTAQUE = (37, 99, 235)  # #2563EB
APOIO = (100, 116, 139)  # #64748B
CORES_STATUS = {
    "verde": (22, 163, 74),
    "amarelo": (234, 179, 8),
    "vermelho": (220, 38, 38),
    "azul": (37, 99, 235),
    "cinza": (148, 163, 184),
}
ROTULO_STATUS = {
    "verde": "Execução com evidência",
    "amarelo": "Evidência parcial",
    "vermelho": "Indício para apuração",
    "azul": "Sem fonte para verificar",
    "cinza": "Dados insuficientes / dentro do prazo",
}
ASSINATURA = "A próxima resposta pode transformar seu negócio."


def _t(texto: Any) -> str:
    """Fontes core do PDF usam latin-1: troca caracteres fora dele."""
    s = "" if texto is None else str(texto)
    s = s.replace("—", "-").replace("–", "-").replace("“", '"').replace("”", '"').replace("’", "'").replace("•", "-")
    return s.encode("latin-1", "replace").decode("latin-1")


def brl(valor: Any) -> str:
    if valor is None:
        return "não informado"
    return "R$ " + f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Dossie(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*TITULO)
        self.cell(0, 6, _t("QKV works  |  Rastro da Emenda"), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*DESTAQUE)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*APOIO)
        self.cell(0, 5, _t(f"{ASSINATURA}   -   página {self.page_no()}"), align="C")

    def secao(self, titulo: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DESTAQUE)
        self.cell(0, 7, _t(titulo), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*TITULO)

    def par(self, texto: str, tamanho: int = 10, cor=TITULO) -> None:
        self.set_font("Helvetica", "", tamanho)
        self.set_text_color(*cor)
        self.multi_cell(0, 5, _t(texto), new_x="LMARGIN", new_y="NEXT")

    def campo(self, rotulo: str, valor: Any) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*APOIO)
        self.cell(48, 5, _t(rotulo))
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*TITULO)
        self.multi_cell(0, 5, _t(valor if valor not in (None, "") else "-"), new_x="LMARGIN", new_y="NEXT")

    def link_texto(self, texto: str, url: str | None) -> None:
        if not url:
            return
        self.set_font("Helvetica", "U", 8)
        self.set_text_color(*DESTAQUE)
        self.multi_cell(0, 4, _t(texto), link=url, new_x="LMARGIN", new_y="NEXT")


def gerar(ficha: dict[str, Any], analise_ia: str | None = None) -> bytes:
    pdf = Dossie(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*TITULO)
    pdf.multi_cell(0, 8, _t(f"Dossiê da emenda Pix {ficha.get('emenda_numero') or ''}"), new_x="LMARGIN", new_y="NEXT")
    pdf.par(f"Plano de ação {ficha.get('codigo_plano_acao')}  -  gerado em {date.today():%d/%m/%Y}", 9, APOIO)

    status = ficha.get("status") or "cinza"
    pdf.ln(2)
    pdf.set_fill_color(*CORES_STATUS[status])
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 9, _t(f"  {status.upper()}  -  {ROTULO_STATUS[status]}"), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.par(ficha.get("justificativa") or "Ainda não avaliada.", 10)

    pdf.secao("Dados da emenda")
    pdf.campo("Parlamentar", ficha.get("parlamentar"))
    pdf.campo("Beneficiário", f"{ficha.get('beneficiario')} ({ficha.get('uf')})")
    pdf.campo("Município / IBGE", f"{ficha.get('municipio') or '-'} / {ficha.get('codigo_ibge') or '-'}")
    pdf.campo("População (IBGE)", ficha.get("populacao"))
    pdf.campo("Valor previsto", brl(ficha.get("valor_previsto")))
    pdf.campo("Custeio / investimento", f"{brl(ficha.get('valor_custeio'))} / {brl(ficha.get('valor_investimento'))}")
    pdf.campo("Valor repassado", brl(ficha.get("repassado")))
    pdf.campo("Primeiro pagamento", ficha.get("primeiro_pagamento"))
    pdf.campo("Objeto declarado", ficha.get("objeto_completo"))

    if analise_ia:
        pdf.secao("Análise assistida por IA")
        pdf.par(analise_ia.replace("**", "").replace("#", ""), 9)
        pdf.par(
            "Texto gerado automaticamente pelo assistente do Rastro da Emenda a partir dos dados desta ficha; "
            "confira os documentos oficiais.",
            8,
            APOIO,
        )

    if ficha.get("alertas_detalhados"):
        pdf.secao("Alertas (indícios para apuração)")
        for a in ficha["alertas_detalhados"]:
            pdf.par(f"{a['codigo']} - {a['descricao']}", 9)

    pdf.secao("Linha do tempo")
    for ev in ficha.get("linha_do_tempo", []):
        valor = f" - {brl(ev['valor'])}" if ev.get("valor") is not None else ""
        pdf.par(f"{ev['data']}  {ev['titulo']}{valor}: {ev.get('descricao') or ''}", 9)
        pdf.link_texto(ev.get("url") or "", ev.get("url"))

    pdf.secao("Evidências avaliadas")
    if not ficha.get("evidencias"):
        pdf.par("Sem evidência encontrada nas fontes consultadas.", 9)
    for ev in ficha.get("evidencias", []):
        conta = "conta como evidência" if ev.get("conta_como_evidencia") else "não conta como evidência"
        pdf.par(
            f"[{ev.get('fonte')}] {ev.get('data_publicacao') or ''} - {brl(ev.get('valor'))} - "
            f"confiança {float(ev.get('confianca') or 0):.0%} ({conta}; método: {ev.get('metodo')})",
            9,
            APOIO,
        )
        pdf.par((ev.get("objeto") or ev.get("trecho") or "")[:600], 9)
        if ev.get("fornecedor_nome"):
            pdf.par(f"Fornecedor: {ev.get('fornecedor_nome')} ({ev.get('fornecedor_documento') or '-'})", 8, APOIO)
        if ev.get("justificativa_ia"):
            pdf.par(f"Análise: {ev['justificativa_ia']}", 8, APOIO)
        pdf.link_texto(ev.get("url") or "", ev.get("url"))
        pdf.ln(1)

    pdf.secao("Fontes oficiais")
    for nome, url in (ficha.get("fontes") or {}).items():
        if url:
            pdf.link_texto(f"{nome}: {url}", url)
    pdf.ln(3)
    pdf.par(
        "Aviso: este dossiê aponta indícios para apuração, nunca acusações. A ausência de evidência significa "
        "apenas que nada foi encontrado nas fontes consultadas (PNCP e, para municípios de até 20 mil habitantes, "
        "Querido Diário). Confira sempre os documentos oficiais nos links acima.",
        8,
        APOIO,
    )
    return bytes(pdf.output())
