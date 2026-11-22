"""Configuração comum dos testes: fixtures gravadas e acesso opcional ao banco."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

PASTA_FIXTURES = Path(__file__).parent / "fixtures"


def carregar_fixture(fonte: str, nome: str) -> Any:
    return json.loads((PASTA_FIXTURES / fonte / nome).read_text(encoding="utf-8"))


@pytest.fixture
def fixture_json():
    return carregar_fixture
