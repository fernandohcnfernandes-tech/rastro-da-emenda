"""Semáforo de execução (docs/regras-e-semaforo.md). Função pura: dados → (status, justificativa)."""

from __future__ import annotations

from decimal import Decimal

from rastro.motor.regras import DESCRICAO, EXECUCAO_DECLARADA_MINIMA, DadosEmenda, aplicar_regras

STATUS = ("verde", "amarelo", "laranja", "vermelho", "azul", "cinza")
COBERTURA_VERDE = Decimal("0.70")  # contratos compatíveis cobrindo ≥ 70% do repassado → verde


def _brl(valor: Decimal | None) -> str:
    if valor is None:
        return "valor não informado"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def classificar(d: DadosEmenda) -> tuple[str, str]:
    """Ordem: cinza (dados) → verde → amarelo (documento parcial, execução declarada ou contábil) → laranja
    → cinza (verificação em andamento ou prazo) → vermelho (só com sinal contrário: A9 ou A8) → azul (sem evidência)."""
    if d.primeiro_pagamento is None:
        return "cinza", "Dados insuficientes: ainda não há pagamento registrado no Transferegov."
    if not d.codigo_ibge:
        return "cinza", "Dados insuficientes: o CNPJ do beneficiário não foi ligado a um código IBGE."
    if not (d.objeto or "").strip():
        return "cinza", "Dados insuficientes: plano de ação sem objeto declarado."

    validas = d.evidencias_validas
    contratos = [c for c in validas if c.eh_contrato]
    nota = _nota_declarada(d) + _nota_contabil(d)
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
            return "verde", texto + nota
        return "amarelo", (
            f"Evidência parcial: contrato(s) compatível(is) somam {_brl(sum(com_valor))}, "
            f"{cobertura:.0%} do valor repassado ({_brl(d.valor_repassado)})." + nota
        )
    if validas:
        melhor = max(validas, key=lambda c: c.confianca)
        return "amarelo", (
            f"Evidência parcial: {_ato(melhor.tipo_ato)} compatível encontrado(a) em {_fonte(melhor.fonte)}, "
            "ainda sem contrato localizado." + nota
        )

    # Declarações do próprio ente (relatório de gestão, contabilidade): nunca levam a verde, que exige documento.
    if d.execucao_declarada_suficiente:
        return "amarelo", (
            f"Execução declarada pelo ente: relatório de gestão entregue no Transferegov declara "
            f"{_brl(d.execucao_declarada)} executados ({d.fracao_declarada:.0%} do repassado). Nenhum documento "
            "independente (contrato ou contratação) foi localizado nas fontes consultadas; a declaração não "
            "substitui o documento." + _nota_contabil(d)
        )
    if d.execucao_contabil:
        c = d.contabil
        return "amarelo", (
            f"Execução contábil declarada pelo ente: até {c.data_referencia:%m/%Y}, a contabilidade enviada ao "
            f"Tesouro (SICONFI) registra {_brl(c.empenhado)} empenhados com recursos de emendas Pix "
            f"({c.fracao_empenhada:.0%} do recebido até {c.corte:%d/%m/%Y}). O dado soma todas as emendas Pix do "
            "ente; nenhum contrato desta emenda foi localizado nas fontes consultadas." + _nota_declarada(d)
        )

    if d.em_revisao:
        melhor = max(d.em_revisao, key=lambda c: c.confianca)
        return "laranja", (
            f"Em revisão: {len(d.em_revisao)} documento(s) possivelmente compatível(is) em {_fonte(melhor.fonte)}, "
            f"com confiança abaixo de 60% (maior: {melhor.confianca:.0%}). Não conta como evidência nem como ausência."
        )

    fontes = d.fontes_que_cobrem
    dias = d.dias_desde_pagamento or 0
    if not d.pncp_verificado:
        return "cinza", (
            "Verificação em andamento: os contratos deste ente ainda não foram consultados no PNCP. "
            "Sem conclusão até a consulta terminar."
        )
    if not fontes and not d.contabil_aplicavel:
        return "azul", (
            "Sem evidência localizada: município com até 20 mil habitantes, sem registros no PNCP, fora da "
            "cobertura do Querido Diário e sem dados abertos de contratos do Tribunal de Contas. "
            "Isto não é indício de problema." + nota
        )
    if dias <= d.prazo_dias:
        return "cinza", (
            f"Dentro do prazo de referência: pago há {dias} dias (prazo de {d.prazo_dias}); "
            "ainda sem evidência encontrada nas fontes consultadas." + nota
        )

    # Vermelho exige sinal contrário à execução, não apenas a ausência de documento.
    if d.recursos_sem_empenho:
        c = d.contabil
        return "vermelho", (
            f"Indício para apuração: pago há {dias} dias, sem documento nas fontes consultadas e, até "
            f"{c.data_referencia:%m/%Y}, a contabilidade enviada pelo ente ao Tesouro (SICONFI) registra só "
            f"{_brl(c.empenhado)} empenhados com recursos de emendas Pix — {c.fracao_empenhada:.0%} do recebido "
            f"até {c.corte:%d/%m/%Y} ({_brl(c.recebido_ate_corte)})."
        )
    if d.fracao_final_declarada is not None and d.fracao_final_declarada < EXECUCAO_DECLARADA_MINIMA:
        return "vermelho", (
            f"Indício para apuração: pago há {dias} dias, sem documento nas fontes consultadas, e o relatório de "
            f"gestão final declara só {d.fracao_final_declarada:.0%} do repassado como executado."
        )
    onde = ", ".join(fontes) if fontes else "nenhuma fonte de contratos cobre o ente"
    return "azul", (
        f"Sem evidência localizada: pago há {dias} dias e nenhum contrato ou contratação compatível encontrado "
        f"nas fontes consultadas ({onde}). Não há sinal contrário à execução (contabilidade do ente ou relatório "
        "final); a ausência do documento, sozinha, não é indício de problema." + nota
    )


def _nota_declarada(d: DadosEmenda) -> str:
    if d.fracao_declarada is None:
        return ""
    return f" O ente declarou no relatório de gestão {d.fracao_declarada:.0%} do repassado como executado."


def _nota_contabil(d: DadosEmenda) -> str:
    if not d.contabil_aplicavel:
        return ""
    c = d.contabil
    return (
        f" Contabilidade do ente (SICONFI, até {c.data_referencia:%m/%Y}): {c.fracao_empenhada:.0%} das emendas Pix "
        f"recebidas até {c.corte:%d/%m/%Y} empenhadas."
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
