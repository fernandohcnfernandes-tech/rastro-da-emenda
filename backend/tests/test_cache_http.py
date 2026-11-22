import httpx
import respx

from rastro.conectores.base import ClienteHttp


@respx.mock
def test_cache_em_disco_evita_segunda_requisicao(tmp_path) -> None:
    rota = respx.get("https://x.teste/a").mock(return_value=httpx.Response(200, json={"ok": 1}))
    cli = ClienteHttp("https://x.teste", por_minuto=0, cache_dir=tmp_path)
    assert cli.get("/a", {"p": 1}) == {"ok": 1}
    assert cli.get("/a", {"p": 1}) == {"ok": 1}
    assert rota.call_count == 1
    cli.get("/a", {"p": 2})
    assert rota.call_count == 2
