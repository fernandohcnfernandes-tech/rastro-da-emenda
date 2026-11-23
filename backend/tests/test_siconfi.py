from decimal import Decimal

from rastro.conectores import siconfi


def linha(conta: str, fonte: str, valor: float, funcao: str | None = "10") -> dict:
    return {"conta_contabil": conta, "fonte_recursos": fonte, "valor": valor, "funcao": funcao}


def test_id_ente_municipio_e_estado() -> None:
    assert siconfi.id_ente("2612109", "municipal") == "2612109"
    assert siconfi.id_ente("2400000", "estadual") == "24"
    assert siconfi.id_ente("5300000", "estadual") == "53"


def test_agregar_soma_so_a_fonte_706_por_conta() -> None:
    t = siconfi.agregar(
        [
            linha("621200000", "1706", 1000, None),
            linha("621200000", "1500", 999, None),  # outra fonte: ignorada
            linha("622130100", "1706", 100),  # empenhado a liquidar
            linha("622130300", "2706", 50),  # liquidado a pagar (recurso de exercício anterior)
            linha("622130400", "1706", 300, "15"),  # pago
            linha("631400000", "2706", 20),  # restos a pagar não processados pagos
            linha("632200000", "1706", 5),  # restos a pagar processados pagos
            linha("622110000", "1706", 7777),  # crédito disponível: não é execução
        ]
    )
    assert t["receita_1706"] == Decimal(1000)
    assert t["empenhado_1706"] == Decimal(400) and t["empenhado_2706"] == Decimal(50)
    assert t["liquidado_1706"] == Decimal(300) and t["liquidado_2706"] == Decimal(50)
    assert t["pago_1706"] == Decimal(300)
    assert t["rp_pago"] == Decimal(25)
    assert t["pago_por_funcao"] == {"15": 300.0}
