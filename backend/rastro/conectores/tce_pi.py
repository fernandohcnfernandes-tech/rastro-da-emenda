"""Conector do TCE-PI — Mural de Contratos (muralcon), API pública sem chave.

`GET https://sistemas.tce.pi.gov.br/muralcon/api/contratos?esfera=municipal&expand=true&vigencia=AAAA-MM-DD_AAAA-MM-DD`
com paginação `offset`/`limit`; também `dtAlteracao=AAAA-MM-DD` para atualizações. Confirmado em 22/11/2026.
Os contratos trazem `codIbgeMun`, mas não o CNPJ do órgão: o contrato municipal é ligado ao CNPJ do ente pelo IBGE.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from rastro.conectores.base import ClienteHttp
from rastro.util import data_ou_none, decimal_ou_none, mascarar_cpf, normalizar_cnpj, sem_acentos

BASE = "https://sistemas.tce.pi.gov.br"
SIGLA = "TCE-PI"
TAMANHO = 500


def cliente() -> ClienteHttp:
    return ClienteHttp(BASE, por_minuto=30, timeout=180)


def paginas(cli: ClienteHttp, esfera: str = "municipal", **filtros: str) -> Iterator[list[dict[str, Any]]]:
    offset = 0
    while True:
        params = {"esfera": esfera, "expand": "true", "limit": TAMANHO, "offset": offset, **filtros}
        resposta = cli.get("/muralcon/api/contratos", params=params) or {}
        itens = resposta.get("items") or next((v for v in resposta.values() if isinstance(v, list)), [])
        yield itens
        offset += len(itens)
        if not itens or not resposta.get("next"):
            return


def eh_camara(orgao: str | None) -> bool:
    nome = sem_acentos(orgao or "").upper()
    return bool(re.search(r"\bCAMARA\b|^C\.\s*M\.", nome))


def _https(url: str | None) -> str | None:
    if not url:
        return None
    return url.replace(":-1", "").replace("http://", "https://", 1)


def evidencia_de_contrato(r: dict[str, Any], cnpj_ente: str | None) -> dict[str, Any]:
    documento = r.get("docContratada")
    pf = len(re.sub(r"\D", "", documento or "")) == 11
    bruto = {k: v for k, v in r.items() if v not in (None, "", [])}
    if pf:
        bruto["docContratada"] = mascarar_cpf(documento)
        bruto.pop("nomeContratada", None)
    origem = (r.get("procedOrigem") or [{}])[0].get("descricao") or ""
    return {
        "fonte": "tce_contrato",
        "id_externo": f"pi:{r.get('href', '').rstrip('/').split('/')[-1] or r.get('numProcessoTce')}",
        "cnpj_orgao": cnpj_ente,
        "codigo_ibge": r.get("codIbgeMun") or None,
        "data_publicacao": data_ou_none(r.get("inicioVigenciaAtual") or r.get("dataFinalizacaoCadastro")),
        "data_assinatura": None,
        "objeto": (r.get("objeto") or "").strip()[:4000] or None,
        "valor": decimal_ou_none(r.get("valorContratado")),
        "modalidade": origem.split(" Nº")[0].strip().title() or None,
        "tipo_ato": "contrato",
        "situacao": r.get("status"),
        "numero_controle_compra": None,
        "fornecedor_documento": mascarar_cpf(documento) if pf else (normalizar_cnpj(documento) or documento),
        "fornecedor_nome": "Pessoa física (nome omitido)" if pf else r.get("nomeContratada"),
        "fornecedor_pf": pf,
        "url": _https(r.get("href")),
        "trecho": None,
        "raw": bruto,
    }
