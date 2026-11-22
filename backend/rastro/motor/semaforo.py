"""Semáforo de execução (docs/regras-e-semaforo.md). Função pura: dados → (status, justificativa)."""

from __future__ import annotations

from decimal import Decimal

from rastro.motor.regras import DESCRICAO, DadosEmenda, aplicar_regras

STATUS = ("verde", "amarelo", "vermelho", "azul", "cinza")
COBERTURA_VERDE = Decimal("0.70")  # contratos compatíveis cobrindo ≥ 70% do repassado → verde


def _brl(valor: Decimal | None) -> str:
    if valor is None:
        return "valor não informado"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def classificar(d: DadosEmenda) -> tuple[str, str]:
    """Ordem: cinza → verde → amarelo → (vermelho | azul) → cinza."""
    if d.primeiro_pagamento is None:
        return "cinza", "Dados insuficientes: ainda não há pagamento registrado no Transferegov."
    if not d.codigo_ibge:
        return "cinza", "Dados insuficientes: o CNPJ do beneficiário não foi ligado a um código IBGE."
    if not (d.objeto or "").strip():
        return "cinza", "Dados insuficientes: plano de ação sem objeto declarado."

    validas = d.evidencias_validas
    contratos = [c for c in validas if c.eh_contrato]
    if contratos:
        com_valor = [c.valor for c in contratos if c.valor]
        cobertura = (sum(com_valor) / d.valor_repassado) if (com_valor and d.valor_repassado) else None
        melhor = max(contratos, key=lambda c: c.confianca)
        if cobertura is None or cobertura >= COBERTURA_VERDE:
            texto = (
                f"Contrato compatível com o objeto encontrado em {_fonte(melhor.fonte)} "
                f"(confiança {melhor.confianca:.0%}"
            )
            texto += f"; contratos somam {cobertura:.0%} do repassado)." if cobertura is not None else ")."
            return "verde", texto
        return "amarelo", (
            f"Evidência parcial: contrato(s) compatível(is) somam {_brl(sum(com_valor))}, "
            f"{cobertura:.0%} do valor repassado ({_brl(d.valor_repassado)})."
        )
    if validas:
        melhor = max(validas, key=lambda c: c.confianca)
        return "amarelo", (
            f"Evidência parcial: {_ato(melhor.tipo_ato)} compatível encontrado(a) em {_fonte(melhor.fonte)}, "
            "ainda sem contrato localizado."
        )

    if d.em_revisao:
        melhor = max(d.em_revisao, key=lambda c: c.confianca)
        return "cinza", (
            f"Em revisão: {len(d.em_revisao)} documento(s) possivelmente compatível(is) em {_fonte(melhor.fonte)}, "
            f"com confiança abaixo de 60% (maior: {melhor.confianca:.0%}). Não conta como evidência nem como ausência."
        )

    fontes = d.fontes_que_cobrem
    dias = d.dias_desde_pagamento or 0
    if not fontes:
        return "azul", (
            "Sem fonte para verificar: município com até 20 mil habitantes, sem registros no PNCP, fora da "
            "cobertura do Querido Diário e sem dados abertos de contratos do Tribunal de Contas. "
            "Isto não é indício de problema."
        )
    if dias > d.prazo_dias:
        return "vermelho", (
            f"Indício para apuração: pago há {dias} dias e sem evidência encontrada nas fontes consultadas "
            f"({', '.join(fontes)})."
        )
    return "cinza", (
        f"Dentro do prazo de referência: pago há {dias} dias (prazo de {d.prazo_dias}); "
        "ainda sem evidência encontrada nas fontes consultadas."
    )


def _fonte(fonte: str) -> str:
    return {
        "pncp_contrato": "contrato do PNCP",
        "pncp_contratacao": "contratação do PNCP",
        "tce_contrato": "contrato informado ao Tribunal de Contas",
    }.get(fonte, "diário oficial (Querido Diário)")


def _ato(tipo: str | None) -> str:
    return {
        "aviso_licitacao": "aviso de licitação",
        "homologacao": "homologação",
        "dispensa": "dispensa",
        "inexigibilidade": "inexigibilidade",
        "licitacao": "licitação",
    }.get(tipo or "", "ato de contratação")


def avaliar(d: DadosEmenda) -> tuple[str, list[str], str]:
    """Status, alertas e justificativa completa (com a descrição dos alertas)."""
    status, justificativa = classificar(d)
    alertas = aplicar_regras(d)
    if alertas:
        justificativa += " Alertas: " + "; ".join(f"{a} — {DESCRICAO[a]}" for a in alertas) + "."
    return status, alertas, justificativa
