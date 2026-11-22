"""Conexão com o PostgreSQL (SQLAlchemy core + psycopg 3)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine

from rastro.config import config


@lru_cache
def engine() -> Engine:
    return create_engine(config().database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)


@contextmanager
def transacao() -> Iterator[Connection]:
    """Abre uma conexão com transação (commit ao sair sem erro, rollback em caso de erro)."""
    with engine().begin() as conn:
        yield conn
