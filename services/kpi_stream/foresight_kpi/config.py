"""KPI stream configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kafka_bootstrap_servers: str = "localhost:9092"
    subscribe_pattern: str = "stripe\\.events\\..*"
    database_url: str = "postgresql://foresight:foresight@localhost:5432/foresight"
    flush_every: int = 100


settings = Settings()
