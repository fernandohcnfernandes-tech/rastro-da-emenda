"""Pré-filtro antes da IA: CNPJ, janela de data, faixa de valor e similaridade TF-IDF (funções puras)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rastro.util import sem_acentos

TOLERANCIA_DIAS = 30
FAIXA_VALOR = (Decimal("0.10"), Decimal("2.00"))
LIMIAR_SIMILARIDADE = 0.08
MAX_CANDIDATOS = 5

_STOP = set(
    """de da do das dos e em no na nos nas para por com sem um uma a o os as ao aos que se ou pelo pela
    municipio municipal prefeitura contratacao empresa especializada servico servicos aquisicao objeto
    destinado destinada atender execucao referente fornecimento conforme termo referencia""".split()
)


_PREAMBULO = re.compile(
    r"termo de contrato que entre si celebram .{0,200}? (?:para|objetivando|visando|tendo por objeto) "
)


def normalizar_texto(texto: str | None) -> str:
    t = sem_acentos(texto or "").lower()
    t = _PREAMBULO.sub(" ", re.sub(r"\s+", " ", t))  # "TERMO DE CONTRATO QUE ENTRE SI CELEBRAM O MUNICÍPIO X ... PARA"
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(p for p in t.split() if len(p) > 2 and p not in _STOP)


@dataclass
class Evidencia:
    id: int
    fonte: str
    cnpj_orgao: str | None
    data_publicacao: date | None
    objeto: str | None
    valor: Decimal | None
    tipo_ato: str | None = None
    modalidade: str | None = None
    url: str | None = None


@dataclass
class Candidato:
    evidencia: Evidencia
    similaridade: float
    motivos: list[str] = field(default_factory=list)


class Similaridade:
    """Média do cosseno TF-IDF de palavras (uni e bigramas) e de trechos de caracteres (3 a 5).

    Os trechos de caracteres aproximam variações da mesma raiz ("pavimentação"/"pavimentar",
    "iluminação"/"luminárias"), comuns entre o plano de trabalho e o objeto do contrato.
    """

    def __init__(self, corpus: Iterable[str]) -> None:
        textos = [normalizar_texto(t) for t in corpus]
        textos = [t for t in textos if t] or ["vazio"]
        self.palavras = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True).fit(textos)
        self.caracteres = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit(textos)

    def pontuar(self, referencia: str, textos: Sequence[str]) -> list[float]:
        if not textos:
            return []
        docs = [normalizar_texto(referencia)] + [normalizar_texto(t) for t in textos]
        notas = []
        for vetorizador in (self.palavras, self.caracteres):
            matriz = vetorizador.transform(docs)
            notas.append(cosine_similarity(matriz[0], matriz[1:])[0])
        return [float((a + b) / 2) for a, b in zip(*notas, strict=True)]


def na_janela(ev: Evidencia, primeiro_pagamento: date | None) -> bool:
    if primeiro_pagamento is None or ev.data_publicacao is None:
        return False
    return ev.data_publicacao >= primeiro_pagamento - timedelta(days=TOLERANCIA_DIAS)


def valor_na_faixa(valor: Decimal | None, repassado: Decimal | None) -> bool:
    if valor is None or not repassado:
        return True
    return repassado * FAIXA_VALOR[0] <= valor <= repassado * FAIXA_VALOR[1]


def selecionar_candidatos(
    texto_emenda: str,
    evidencias: Sequence[Evidencia],
    cnpjs: set[str],
    primeiro_pagamento: date | None,
    valor_repassado: Decimal | None,
    similaridade: Similaridade,
    limiar: float = LIMIAR_SIMILARIDADE,
    maximo: int = MAX_CANDIDATOS,
) -> list[Candidato]:
    """Aplica CNPJ, data, faixa de valor e similaridade; devolve no máximo `maximo` candidatos ordenados."""
    filtradas = [
        e
        for e in evidencias
        if (e.cnpj_orgao in cnpjs) and na_janela(e, primeiro_pagamento) and valor_na_faixa(e.valor, valor_repassado)
    ]
    if not filtradas:
        return []
    notas = similaridade.pontuar(texto_emenda, [e.objeto or "" for e in filtradas])
    candidatos = [
        Candidato(e, n, ["cnpj", "data", "valor", f"similaridade={n:.2f}"])
        for e, n in zip(filtradas, notas, strict=True)
        if n >= limiar
    ]
    candidatos.sort(key=lambda c: (-c.similaridade, -(c.evidencia.valor or 0)))
    return candidatos[:maximo]
