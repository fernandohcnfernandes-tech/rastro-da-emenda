"""Aplica o schema.sql e as migrações pendentes em ordem (idempotente).

Uso: python -m rastro.db.migrar
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from rastro.db.conexao import transacao
from rastro.log import log

PASTA = Path(__file__).parent


def migracoes() -> list[Path]:
    return sorted((PASTA / "migracoes").glob("[0-9][0-9][0-9]_*.sql"))


def aplicar() -> list[str]:
    aplicadas: list[str] = []
    with transacao() as conn:
        conn.exec_driver_sql((PASTA / "schema.sql").read_text(encoding="utf-8"))
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS schema_migracao (nome text PRIMARY KEY, aplicada_em timestamptz DEFAULT now())"
        )
        feitas = {r[0] for r in conn.execute(text("SELECT nome FROM schema_migracao"))}
        for arq in migracoes():
            if arq.name in feitas:
                continue
            conn.exec_driver_sql(arq.read_text(encoding="utf-8"))
            conn.execute(text("INSERT INTO schema_migracao (nome) VALUES (:n)"), {"n": arq.name})
            aplicadas.append(arq.name)
    log("migracao", etapa="aplicar", quantidade=len(aplicadas), migracoes=aplicadas)
    return aplicadas


if __name__ == "__main__":
    aplicar()
