from datetime import date
from decimal import Decimal

from rastro.util import (
    data_ou_none,
    decimal_ou_none,
    mascarar_cpf,
    normalizar_cnpj,
    sem_acentos,
    sem_campos_bancarios,
)


def test_normalizar_cnpj() -> None:
    assert normalizar_cnpj("08.787.012/0001-10") == "08787012000110"
    assert normalizar_cnpj(8787012000110) == "08787012000110"
    assert normalizar_cnpj("") is None
    assert normalizar_cnpj("123456789012345") is None


def test_decimal_e_data() -> None:
    assert decimal_ou_none(30000.00000000) == Decimal("30000.00")
    assert decimal_ou_none("1.234,56") == Decimal("1234.56")
    assert decimal_ou_none(None) is None
    assert data_ou_none("2024-07-03T00:00:00") == date(2024, 7, 3)
    assert data_ou_none("20240703") == date(2024, 7, 3)
    assert data_ou_none("03/07/2024") == date(2024, 7, 3)
    assert data_ou_none("x") is None


def test_mascarar_cpf() -> None:
    assert mascarar_cpf("123.456.789-01") == "***.456.789-**"
    assert mascarar_cpf("12345678901") == "***.456.789-**"
    assert mascarar_cpf("08787012000110") == "08787012000110"
    assert mascarar_cpf(None) is None


def test_sem_campos_bancarios_e_acentos() -> None:
    reg = {"nome_banco_plano_acao": "BB", "numero_conta_plano_acao": 1, "id": 3}
    assert sem_campos_bancarios(reg) == {"id": 3}
    assert sem_acentos("São João do Piauí") == "Sao Joao do Piaui"
