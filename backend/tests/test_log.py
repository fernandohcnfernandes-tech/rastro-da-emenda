import json

from rastro.log import cronometro, log


def test_log_emite_json_com_campos(capsys) -> None:
    log("teste", "etapa_x", quantidade=3)
    evento = json.loads(capsys.readouterr().err)
    assert evento["fonte"] == "teste" and evento["etapa"] == "etapa_x" and evento["quantidade"] == 3


def test_cronometro_registra_duracao(capsys) -> None:
    with cronometro("teste", "etapa_y") as info:
        info["quantidade"] = 7
    evento = json.loads(capsys.readouterr().err)
    assert evento["quantidade"] == 7 and "duracao_ms" in evento
