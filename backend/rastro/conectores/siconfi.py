"""Conector do SICONFI (Tesouro Nacional) — Matriz de Saldos Contábeis (MSC), API aberta, sem chave.

`GET /msc_orcamentaria?id_ente=&an_referencia=&me_referencia=&co_tipo_matriz=MSCC&classe_conta=6&id_tv=ending_balance`
devolve a execução orçamentária do ente acumulada até o mês, com a fonte de recursos de cada linha. Desde 2023 a
padronização de fontes do Tesouro dá às transferências especiais da União (emendas Pix) a fonte 706: `1706` para
recursos do exercício e `2706` para recursos de exercícios anteriores. Paginação de 5.000 linhas (`hasMore`).
Confirmado em 23/11/2026 (Salgadinho/PE, Uarini/AM e Mirante da Serra/RO batem com o Transferegov).

Contas usadas (PCASP, classe 6):
- 6.2.1.2 receita realizada;
- 6.2.2.1 dotação atualizada (crédito disponível + indisponível + utilizado), para saber se o ente orça na fonte;
- 6.2.2.1.3.01 a .04 crédito empenhado (a liquidar, em liquidação, liquidado a pagar, pago) e .05 a .07 empenho
  inscrito em restos a pagar — na matriz de dezembro o empenho não liquidado migra de .01/.02/.03 para .05/.06/.07;
- 6.3.1.4 e 6.3.2.2 restos a pagar (não processados e processados) pagos.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from rastro.conectores.base import ClienteHttp

BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
FONTE = "706"
POR_MINUTO = 90
EMPENHADO = tuple(f"622130{i}" for i in range(1, 8))  # .01 a .04 no exercício; .05 a .07 inscritos em RP


def cliente() -> ClienteHttp:
    return ClienteHttp(BASE, por_minuto=POR_MINUTO, timeout=120)


def id_ente(codigo_ibge: str, esfera: str | None) -> str:
    """Município: código IBGE de 7 dígitos. Estado e DF: código da UF (2 dígitos)."""
    return codigo_ibge[:2] if esfera == "estadual" else codigo_ibge


def msc(cli: ClienteHttp, ente: str, ano: int, mes: int) -> list[dict[str, Any]]:
    linhas: list[dict[str, Any]] = []
    deslocamento = 0
    while True:
        dados = (
            cli.get(
                "/msc_orcamentaria",
                {
                    "id_ente": ente,
                    "an_referencia": ano,
                    "me_referencia": mes,
                    "co_tipo_matriz": "MSCC",
                    "classe_conta": 6,
                    "id_tv": "ending_balance",
                    "offset": deslocamento,
                },
            )
            or {}
        )
        itens = dados.get("items") or []
        linhas.extend(itens)
        if not dados.get("hasMore") or not itens:
            return linhas
        deslocamento += len(itens)


def _d(valor: Any) -> Decimal:
    return Decimal(str(valor or 0))


def agregar(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """Totais da fonte 706 (exercício `1706` e anteriores `2706`) por conta, e o pago por função de governo."""
    t: dict[str, Decimal] = defaultdict(Decimal)
    por_funcao: dict[str, Decimal] = defaultdict(Decimal)
    for r in linhas:
        fonte = str(r.get("fonte_recursos") or "")
        if not fonte.endswith(FONTE) or fonte[:1] not in ("1", "2"):
            continue
        sufixo = "1706" if fonte.startswith("1") else "2706"
        conta = str(r.get("conta_contabil") or "")
        valor = _d(r.get("valor"))
        if conta.startswith("6212"):
            t[f"receita_{sufixo}"] += valor
        elif conta[:4] in ("6314", "6322"):
            t["rp_pago"] += valor
        elif conta.startswith("6221"):
            t[f"dotacao_{sufixo}"] += valor
        if conta[:7] in EMPENHADO:
            t[f"empenhado_{sufixo}"] += valor
            if conta[:7] in ("6221303", "6221304", "6221307"):
                t[f"liquidado_{sufixo}"] += valor
            if conta[:7] == "6221304":
                t[f"pago_{sufixo}"] += valor
                por_funcao[str(r.get("funcao") or "sem função")] += valor
    return {**{k: v for k, v in t.items()}, "pago_por_funcao": {k: float(v) for k, v in por_funcao.items()}}
