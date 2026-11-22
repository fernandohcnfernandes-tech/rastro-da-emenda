"""Logs estruturados em JSON (uma linha por evento) no stderr."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any


def log(fonte: str, etapa: str, **campos: Any) -> None:
    evento = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), "fonte": fonte, "etapa": etapa, **campos}
    print(json.dumps(evento, ensure_ascii=False, default=str), file=sys.stderr, flush=True)


@contextmanager
def cronometro(fonte: str, etapa: str, **campos: Any) -> Iterator[dict[str, Any]]:
    """Registra `duracao_ms` ao final; o chamador pode preencher `quantidade` no dict devolvido."""
    info: dict[str, Any] = dict(campos)
    inicio = time.monotonic()
    try:
        yield info
    finally:
        log(fonte, etapa, duracao_ms=int((time.monotonic() - inicio) * 1000), **info)
