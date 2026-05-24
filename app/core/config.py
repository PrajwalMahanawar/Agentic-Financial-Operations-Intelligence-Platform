from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Financial Operations Intelligence Platform"
    database_url: str = "postgresql+psycopg://finops:finops@localhost:5432/finops"
    enable_database: bool = False
    human_approval_risk_threshold: int = 70
    auth_secret_key: str = "change-me-before-production"
    auth_token_ttl_seconds: int = 3600
    auth_users: str = (
        "admin@example.com:admin123:admin,"
        "analyst@example.com:analyst123:analyst,"
        "approver@example.com:approver123:approver"
    )
    llm_provider: str = "local"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    rag_backend: str = "local"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
