"""Runtime configuration, loaded from environment / .env."""

from __future__ import annotations

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
