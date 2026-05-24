from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic Financial Operations Intelligence Platform"
    database_url: str = "postgresql+psycopg://finops:finops@localhost:5432/finops"
    enable_database: bool = False
    human_approval_risk_threshold: int = 70

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
