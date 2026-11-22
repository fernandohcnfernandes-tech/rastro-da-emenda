"""Cliente HTTP comum: limite de taxa, retry exponencial e timeout.

Todos os conectores devem usar esta classe para respeitar os limites e os termos de uso das fontes.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
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
        cache_dir: Path | None = None,
        cache_ttl_s: int = 7 * 24 * 3600,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_ttl_s = cache_ttl_s
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
        self.limite = LimiteTaxa(por_minuto)
        self.http = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(cabecalhos or {})},
            timeout=timeout,
        )

    def _arquivo_cache(self, caminho: str, params: dict[str, Any] | None) -> Path | None:
        if not self.cache_dir:
            return None
        chave = json.dumps([caminho, sorted((params or {}).items())], default=str, ensure_ascii=False)
        return self.cache_dir / f"{hashlib.sha256(chave.encode()).hexdigest()}.json"

    def get(self, caminho: str, params: dict[str, Any] | None = None) -> Any:
        """GET com cache opcional em disco (respostas válidas por `cache_ttl_s`)."""
        arquivo = self._arquivo_cache(caminho, params)
        if arquivo and arquivo.exists() and time.time() - arquivo.stat().st_mtime < self.cache_ttl_s:
            return json.loads(arquivo.read_text(encoding="utf-8"))
        dados = self._get_rede(caminho, params)
        if arquivo is not None:
            arquivo.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        return dados

    @retry(
        retry=retry_if_exception_type(ErroTemporario),
        wait=wait_exponential(multiplier=2, min=2, max=120),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def _get_rede(self, caminho: str, params: dict[str, Any] | None = None) -> Any:
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
        try:
            return resp.json()
        except ValueError as exc:  # 200 com corpo truncado/inválido: instabilidade da fonte, vale repetir
            raise ErroTemporario(f"JSON inválido em {resp.url}") from exc

    def fechar(self) -> None:
        self.http.close()
