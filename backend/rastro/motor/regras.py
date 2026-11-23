"""Regras de alerta A1–A8 (indícios para apuração). Funções puras sobre `DadosEmenda`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from rastro.motor.ia import CONFIANCA_MINIMA

PRAZO_PADRAO_DIAS = 180
CONFIANCA_REVISAO = 0.45
FAIXA_A7 = (0.5, 1.5)
MINIMO_CAPITAL = Decimal("0.70")
SITUACOES_RELATORIO_OK = {"DISPONIBILIZADO", "ENVIADO", "ENVIADO_PARA_ANALISE", "CONCLUIDO", "APROVADO", "ANALISADO"}
EXECUCAO_DECLARADA_MINIMA = Decimal("0.70")  # relatório final que declara ≥ 70% do repassado como executado
TIPOS_CONTRATO = {"contrato", "extrato_contrato"}
TIPOS_DIRETOS = {"dispensa", "inexigibilidade"}


@dataclass
class Correspondencia:
    """Evidência avaliada para a emenda (pela IA ou heurística)."""

    id_evidencia: int
    fonte: str
    tipo_ato: str | None
    modalidade: str | None
    valor: Decimal | None
    compativel: bool
    confianca: float
    url: str | None = None
    objeto: str | None = None
    justificativa: str | None = None

    @property
    def conta(self) -> bool:
        """Só conta como evidência quando compatível com confiança ≥ 0,6."""
        return self.compativel and self.confianca >= CONFIANCA_MINIMA

    @property
    def em_revisao(self) -> bool:
        """Possivelmente compatível, mas com confiança insuficiente: não conta como evidência nem como ausência."""
        return self.compativel and CONFIANCA_REVISAO <= self.confianca < CONFIANCA_MINIMA

    @property
    def eh_contrato(self) -> bool:
        return self.fonte in {"pncp_contrato", "tce_contrato"} or (self.tipo_ato or "") in TIPOS_CONTRATO

    @property
    def eh_contratacao_direta(self) -> bool:
        tipo = (self.tipo_ato or "").lower()
        modalidade = (self.modalidade or "").lower()
        return tipo in TIPOS_DIRETOS or "dispensa" in modalidade or "inexigib" in modalidade


@dataclass(frozen=True)
class Relatorio:
    """Relatório de gestão do Transferegov: declaração do próprio ente, não documento independente."""

    tipo: str | None
    situacao: str | None
    valor_executado: Decimal | None = None
    valor_pendente: Decimal | None = None

    @property
    def entregue(self) -> bool:
        return (self.situacao or "").upper() in SITUACOES_RELATORIO_OK

    @property
    def final(self) -> bool:
        return self.entregue and (self.tipo or "").lower() == "final"


@dataclass
class DadosEmenda:
    id_plano_acao: int
    hoje: date
    valor_custeio: Decimal | None = None
    valor_investimento: Decimal | None = None
    valor_repassado: Decimal | None = None
    primeiro_pagamento: date | None = None
    codigo_ibge: str | None = None
    esfera: str | None = None
    populacao: int | None = None
    obrigado_pncp: bool | None = None
    coberto_querido_diario: bool = False
    coberto_tce: str | None = None  # sigla do Tribunal de Contas com dados abertos de contratos (ex.: TCE-RS)
    tem_registro_pncp: bool = False
    pncp_verificado: bool = True  # False enquanto a carga do PNCP não consultou nenhum CNPJ da emenda
    objeto: str | None = None
    plano_generico: bool | None = None
    relatorios: list[Relatorio] = field(default_factory=list)  # aceita também tuplas (tipo, situação, ...)
    correspondencias: list[Correspondencia] = field(default_factory=list)
    prazo_dias: int = PRAZO_PADRAO_DIAS
    limite_populacao: int = 20_000

    def __post_init__(self) -> None:
        self.relatorios = [r if isinstance(r, Relatorio) else Relatorio(*r) for r in self.relatorios]

    @property
    def execucao_declarada(self) -> Decimal | None:
        """Maior valor executado declarado num relatório de gestão final entregue (None se não houver)."""
        valores = [r.valor_executado for r in self.relatorios if r.final and r.valor_executado is not None]
        return max(valores) if valores else None

    @property
    def fracao_declarada(self) -> Decimal | None:
        if self.execucao_declarada is None or not self.valor_repassado:
            return None
        return self.execucao_declarada / self.valor_repassado

    @property
    def execucao_final_declarada(self) -> bool:
        """Relatório final entregue declarando ≥ 70% do repassado como executado."""
        return self.fracao_declarada is not None and self.fracao_declarada >= EXECUCAO_DECLARADA_MINIMA

    @property
    def dias_desde_pagamento(self) -> int | None:
        return (self.hoje - self.primeiro_pagamento).days if self.primeiro_pagamento else None

    @property
    def municipio_pequeno(self) -> bool:
        return self.esfera == "municipal" and self.populacao is not None and self.populacao <= self.limite_populacao

    @property
    def fontes_que_cobrem(self) -> list[str]:
        """Fontes capazes de mostrar a execução neste ente."""
        fontes = []
        if self.obrigado_pncp or self.tem_registro_pncp or not self.municipio_pequeno:
            fontes.append("PNCP")
        if self.coberto_querido_diario:
            fontes.append("Querido Diário")
        if self.coberto_tce:
            fontes.append(self.coberto_tce)
        return fontes

    @property
    def evidencias_validas(self) -> list[Correspondencia]:
        return [c for c in self.correspondencias if c.conta]

    @property
    def em_revisao(self) -> list[Correspondencia]:
        return [c for c in self.correspondencias if c.em_revisao]


def a1_pago_sem_evidencia(d: DadosEmenda) -> bool:
    dias = d.dias_desde_pagamento
    return (
        dias is not None
        and dias > d.prazo_dias
        and d.pncp_verificado
        and bool(d.fontes_que_cobrem)
        and not d.evidencias_validas
        and not d.em_revisao
    )


def a2_plano_generico(d: DadosEmenda) -> bool:
    return bool(d.plano_generico)


def a3_relatorio_ausente(d: DadosEmenda) -> bool:
    dias = d.dias_desde_pagamento
    if dias is None or dias <= d.prazo_dias:
        return False
    return not any(r.entregue for r in d.relatorios)


def a4_capital_abaixo_de_70(d: DadosEmenda) -> bool:
    custeio = d.valor_custeio or Decimal(0)
    investimento = d.valor_investimento or Decimal(0)
    total = custeio + investimento
    return total > 0 and investimento / total < MINIMO_CAPITAL


def a5_objeto_divergente(d: DadosEmenda) -> bool:
    """Contrato do mesmo ente, na janela e na faixa de valor, julgado incompatível — e nenhum compatível."""
    if d.evidencias_validas:
        return False
    return any(c.eh_contrato and not c.compativel and c.confianca >= CONFIANCA_MINIMA for c in d.correspondencias)


def a6_contratacao_direta(d: DadosEmenda) -> bool:
    return any(c.eh_contratacao_direta for c in d.evidencias_validas)


def a7_valor_desproporcional(d: DadosEmenda, faixa: tuple[float, float] = FAIXA_A7) -> bool:
    if not d.valor_repassado:
        return False
    contratos = [c for c in d.evidencias_validas if c.eh_contrato and c.valor]
    if not contratos:
        return False
    razao = float(sum(c.valor for c in contratos) / d.valor_repassado)
    return not (faixa[0] <= razao <= faixa[1])


def a8_execucao_declarada_baixa(d: DadosEmenda) -> bool:
    """Relatório final entregue declara menos de 70% do repassado como executado."""
    return d.fracao_declarada is not None and d.fracao_declarada < EXECUCAO_DECLARADA_MINIMA


REGRAS = {
    "A1": a1_pago_sem_evidencia,
    "A2": a2_plano_generico,
    "A3": a3_relatorio_ausente,
    "A4": a4_capital_abaixo_de_70,
    "A5": a5_objeto_divergente,
    "A6": a6_contratacao_direta,
    "A7": a7_valor_desproporcional,
    "A8": a8_execucao_declarada_baixa,
}

DESCRICAO = {
    "A1": "Pago há mais que o prazo de referência sem contratação ou contrato nas fontes que cobrem o ente",
    "A2": "Plano de trabalho genérico, que dificulta verificar a execução",
    "A3": "Relatório de gestão ausente ou pendente",
    "A4": "Menos de 70% do valor em despesas de capital (art. 166-A da Constituição)",
    "A5": "Contrato do ente no período com objeto diferente do objeto da emenda",
    "A6": "Contratação direta (dispensa ou inexigibilidade) associada ao recurso",
    "A7": "Valor contratado muito acima ou abaixo do valor repassado",
    "A8": "Relatório de gestão final declara menos de 70% do valor repassado como executado",
}


def aplicar_regras(d: DadosEmenda) -> list[str]:
    return [codigo for codigo, regra in REGRAS.items() if regra(d)]
