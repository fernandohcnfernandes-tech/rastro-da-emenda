"""Configuração lida do ambiente (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://rastro:rastro@localhost:5432/rastro"

    anthropic_api_key: str = ""
    modelo_rapido: str = "claude-haiku-5-5"
    modelo_analise: str = "claude-sonnet-5-5"

    portal_transparencia_api_key: str = ""

    transferegov_base_url: str = "https://api.transferegov.gestao.gov.br/transferenciasespeciais"
    portal_base_url: str = "https://api.portaldatransparencia.gov.br/api-de-dados"
    pncp_base_url: str = "https://pncp.gov.br/api/consulta"
    querido_diario_base_url: str = "https://api.queridodiario.org.br"
    ibge_base_url: str = "https://servicodados.ibge.gov.br/api"

    data_inicio: str = "2024-01-01"
    prazo_sem_evidencia_dias: int = 180
    limite_populacao_pequeno: int = 20_000
    querido_diario_req_por_minuto: int = 60

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_remetente: str = ""
    url_site: str = "http://localhost:3000"


@lru_cache
def config() -> Config:
    return Config()
