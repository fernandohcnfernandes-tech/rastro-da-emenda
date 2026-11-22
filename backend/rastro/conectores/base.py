"""Cliente HTTP comum: limite de taxa, retry exponencial e timeout.

Todos os conectores devem usar esta classe para respeitar os limites e os termos de uso das fontes.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

USER_AGENT = "RastroDaEmenda/0.1 (Hack Brasil 2026; equipe QKV)"


class LimiteTaxa:
    """Garante no máximo `por_minuto` requisições por minuto (espaçamento uniforme)."""

    def __init__(self, por_minuto: int) -> None:
        self.intervalo = 60.0 / por_minuto if por_minuto > 0 else 0.0
        self._ultimo = 0.0
        self._trava = threading.Lock()

    def aguardar(self) -> None:
        with self._trava:
            espera = self._ultimo + self.intervalo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()


class ErroTemporario(Exception):
    """Erro que vale repetir (429, 5xx, timeout)."""


class ErroFonte(Exception):
    """Resposta inesperada da fonte (ex.: página HTML de bloqueio no lugar de JSON). Não repetir."""


class ClienteHttp:
    def __init__(
        self,
        base_url: str,
        por_minuto: int = 120,
        cabecalhos: dict[str, str] | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.limite = LimiteTaxa(por_minuto)
        self.http = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(cabecalhos or {})},
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(ErroTemporario),
        wait=wait_exponential(multiplier=2, min=2, max=120),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def get(self, caminho: str, params: dict[str, Any] | None = None) -> Any:
        self.limite.aguardar()
        try:
            resp = self.http.get(caminho, params=params)
        except httpx.TransportError as exc:
            raise ErroTemporario(str(exc)) from exc
        if resp.status_code == 429 or resp.status_code >= 500:
            raise ErroTemporario(f"{resp.status_code} em {resp.url}")
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        if "json" not in resp.headers.get("content-type", "json"):
            raise ErroFonte(f"resposta não JSON ({resp.headers.get('content-type')}) em {resp.url}")
        return resp.json()

    def fechar(self) -> None:
        self.http.close()
