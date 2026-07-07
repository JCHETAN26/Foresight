"""Runtime configuration, loaded from environment / .env."""

from __future__ import annotations

import ssl
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ingestion service settings.

    Values come from environment variables (12-factor). A local `.env` is read
    for convenience during development but never in production containers.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_template: str = "stripe.events.{tenant_id}"
    kafka_default_topic: str = "stripe.events.unknown"

    # Optional SASL_SSL — e.g. the Azure Event Hubs Kafka endpoint. Local Kafka
    # stays PLAINTEXT (defaults below are no-ops). For Event Hubs, set:
    #   KAFKA_SECURITY_PROTOCOL=SASL_SSL  KAFKA_SASL_MECHANISM=PLAIN
    #   KAFKA_SASL_USERNAME=$ConnectionString
    #   KAFKA_SASL_PASSWORD=<namespace primary connection string>
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

    # Stripe webhook verification
    stripe_webhook_secret: str = "whsec_replace_me"
    stripe_webhook_tolerance: int = 300

    # Service
    log_level: str = "INFO"
    env: str = "local"

    def topic_for(self, tenant_id: str | None) -> str:
        """Resolve the destination topic for a given tenant id."""
        if not tenant_id:
            return self.kafka_default_topic
        return self.kafka_topic_template.format(tenant_id=tenant_id)


settings = Settings()
