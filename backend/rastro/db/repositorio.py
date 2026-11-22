"""Upserts genéricos (INSERT ... ON CONFLICT) usados pelos conectores."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Connection, text


def _valor_sql(valor: Any) -> Any:
    if isinstance(valor, dict | list) and not isinstance(valor, str):
        return json.dumps(valor, ensure_ascii=False, default=str)
    return valor


def upsert(
    conn: Connection,
    tabela: str,
    linhas: Iterable[dict[str, Any]],
    chave: Sequence[str],
    atualizar: Sequence[str] | None = None,
    jsonb: Sequence[str] = ("raw",),
) -> int:
    """Insere ou atualiza `linhas` em `tabela`. Colunas em `jsonb` são serializadas e convertidas."""
    linhas = [dict(linha) for linha in linhas]
    if not linhas:
        return 0
    colunas = list(linhas[0].keys())
    if atualizar is None:
        atualizar = [c for c in colunas if c not in chave]
    valores = ", ".join(f"CAST(:{c} AS jsonb)" if c in jsonb else f":{c}" for c in colunas)
    conflito = ", ".join(chave)
    if atualizar:
        acao = "DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in atualizar)
        if "atualizado_em" not in colunas and tabela in {"ente", "plano_acao", "emenda"}:
            acao += ", atualizado_em = now()"
    else:
        acao = "DO NOTHING"
    sql = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({valores}) ON CONFLICT ({conflito}) {acao}"
    params = [{c: _valor_sql(linha.get(c)) for c in colunas} for linha in linhas]
    conn.execute(text(sql), params)
    return len(params)
