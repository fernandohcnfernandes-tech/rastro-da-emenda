import time

from rastro.conectores.base import LimiteTaxa


def test_limite_taxa_espaca_requisicoes() -> None:
    limite = LimiteTaxa(por_minuto=600)  # 0,1 s entre chamadas
    inicio = time.monotonic()
    for _ in range(3):
        limite.aguardar()
    assert time.monotonic() - inicio >= 0.19
