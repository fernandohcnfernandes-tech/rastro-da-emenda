"""Execução contábil das emendas Pix por ente (MSC do SICONFI, fonte 706) comparada ao recebido no Transferegov.

O dado é do ente inteiro (todas as emendas Pix dele juntas) e é declarado pelo próprio ente ao Tesouro. Serve para
separar "o ente empenhou o dinheiro, mas não achamos o contrato" de "o dinheiro está parado sem empenho".
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

ANO_INICIAL = 2024
USO_DA_FONTE_MINIMO = Decimal("0.50")  # receita na fonte 706 ≥ 50% do recebido: o ente classifica as emendas Pix nela

SQL_CONTABIL = """
SELECT codigo_ibge, ano, mes, sem_dados,
       empenhado_1706 + CASE WHEN ano > :ano0 THEN empenhado_2706 ELSE 0 END AS empenhado,
       pago_1706 + CASE WHEN ano > :ano0 THEN pago_2706 + rp_pago ELSE 0 END AS pago,
       receita_1706 + receita_2706 AS receita
FROM execucao_contabil WHERE codigo_ibge = ANY(:codigos) ORDER BY codigo_ibge, ano
"""

SQL_RECEBIDO = """
SELECT en.codigo_ibge, g.data_pagamento, g.valor
FROM pagamento g JOIN plano_acao p USING (id_plano_acao) JOIN ente en ON en.cnpj = p.cnpj_beneficiario
WHERE en.codigo_ibge = ANY(:codigos) AND g.valor IS NOT NULL
"""


@dataclass(frozen=True)
class ExecucaoContabil:
    data_referencia: date  # fim do mês da matriz mais recente
    receita: Decimal  # receita realizada na fonte 706 (2024 até a referência)
    empenhado: Decimal  # empenhado com recursos da fonte 706 (exercício e anteriores)
    pago: Decimal  # pago, inclusive restos a pagar
    recebido_ate_ref: Decimal  # emendas Pix pagas ao ente até a referência (Transferegov)
    recebido_ate_corte: Decimal  # pagas até 180 dias antes da referência
    corte: date

    @property
    def usa_fonte(self) -> bool:
        return self.recebido_ate_ref > 0 and self.receita >= self.recebido_ate_ref * USO_DA_FONTE_MINIMO

    @property
    def fracao_empenhada(self) -> Decimal | None:
        """Empenhado acumulado ÷ recebido há mais de 180 dias (None se não houver recebimento antigo)."""
        if not self.recebido_ate_corte:
            return None
        return self.empenhado / self.recebido_ate_corte

    def resumo(self) -> dict[str, Any]:
        return {
            "data_referencia": self.data_referencia.isoformat(),
            "recebido": float(self.recebido_ate_ref),
            "recebido_ate_corte": float(self.recebido_ate_corte),
            "receita_fonte_706": float(self.receita),
            "empenhado": float(self.empenhado),
            "pago": float(self.pago),
            "usa_fonte": self.usa_fonte,
            "fracao_empenhada": None if self.fracao_empenhada is None else float(self.fracao_empenhada),
        }


def montar(
    anos: list[tuple[int, int, bool, Decimal, Decimal, Decimal]],
    pagamentos: list[tuple[date, Decimal]],
    prazo_dias: int,
) -> ExecucaoContabil | None:
    """`anos`: (ano, mês, sem_dados, empenhado, pago, receita). Exige matrizes de todos os anos até a referência:
    um ano faltando subestimaria o empenhado e geraria falso "dinheiro parado"."""
    entregues = [a for a in anos if not a[2]]
    if not entregues:
        return None
    ano_ref, mes_ref = max((a[0], a[1]) for a in entregues)
    if {a[0] for a in entregues} != set(range(ANO_INICIAL, ano_ref + 1)):
        return None
    ref = date(ano_ref, mes_ref, calendar.monthrange(ano_ref, mes_ref)[1])
    corte = ref - timedelta(days=prazo_dias)
    considerados = [a for a in entregues if a[0] <= ano_ref]
    return ExecucaoContabil(
        data_referencia=ref,
        empenhado=sum((Decimal(a[3]) for a in considerados), Decimal(0)),
        pago=sum((Decimal(a[4]) for a in considerados), Decimal(0)),
        receita=sum((Decimal(a[5]) for a in considerados), Decimal(0)),
        recebido_ate_ref=sum((Decimal(v) for d, v in pagamentos if d <= ref), Decimal(0)),
        recebido_ate_corte=sum((Decimal(v) for d, v in pagamentos if d <= corte), Decimal(0)),
        corte=corte,
    )


def carregar(conn: Any, codigos: list[str], prazo_dias: int) -> dict[str, ExecucaoContabil]:
    if not codigos:
        return {}
    anos: dict[str, list] = {}
    for r in conn.execute(text(SQL_CONTABIL), {"codigos": codigos, "ano0": ANO_INICIAL}):
        anos.setdefault(r.codigo_ibge, []).append((r.ano, r.mes, r.sem_dados, r.empenhado, r.pago, r.receita))
    pagamentos: dict[str, list] = {}
    for r in conn.execute(text(SQL_RECEBIDO), {"codigos": codigos}):
        pagamentos.setdefault(r.codigo_ibge, []).append((r.data_pagamento, r.valor))
    resultado = {}
    for codigo, linhas in anos.items():
        montado = montar(linhas, pagamentos.get(codigo, []), prazo_dias)
        if montado:
            resultado[codigo] = montado
    return resultado
