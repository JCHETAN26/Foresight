"""KPI stream configuration."""

from __future__ import annotations

import ssl
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kafka_bootstrap_servers: str = "localhost:9092"
    subscribe_pattern: str = "stripe\\.events\\..*"
    database_url: str = "postgresql://foresight:foresight@localhost:5432/foresight"
    flush_every: int = 100

    # Optional SASL_SSL for the Azure Event Hubs Kafka endpoint (see ingestion).
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_sasl_mechanism: str = ""
    kafka_sasl_username: str = ""
    kafka_sasl_password: str = ""

    def kafka_conn_kwargs(self) -> dict[str, Any]:
        """aiokafka connection kwargs; adds SASL_SSL only when configured."""
        kwargs: dict[str, Any] = {"bootstrap_servers": self.kafka_bootstrap_servers}
        if self.kafka_security_protocol != "PLAINTEXT":
            kwargs["security_protocol"] = self.kafka_security_protocol
            kwargs["sasl_mechanism"] = self.kafka_sasl_mechanism
            kwargs["sasl_plain_username"] = self.kafka_sasl_username
            kwargs["sasl_plain_password"] = self.kafka_sasl_password
            if self.kafka_security_protocol == "SASL_SSL":
                kwargs["ssl_context"] = ssl.create_default_context()
        return kwargs


settings = Settings()
