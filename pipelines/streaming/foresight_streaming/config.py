"""Streaming job configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamingConfig:
    # Kafka / Event Hubs. Locally: localhost:9092 (PLAINTEXT). On Databricks:
    # the Event Hubs Kafka endpoint (<namespace>.servicebus.windows.net:9093)
    # with SASL_SSL — pass the extra options via KAFKA_OPTIONS_JSON.
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    subscribe_pattern: str = os.getenv("KAFKA_SUBSCRIBE_PATTERN", "stripe.events.*")
    starting_offsets: str = os.getenv("KAFKA_STARTING_OFFSETS", "latest")

    # Iceberg target.
    catalog: str = os.getenv("ICEBERG_CATALOG", "lakehouse")
    bronze_table: str = os.getenv("BRONZE_TABLE", "lakehouse.bronze_stripe_events")

    # Streaming runtime.
    checkpoint_location: str = os.getenv(
        "CHECKPOINT_LOCATION", "abfss://checkpoints@foresightlake.dfs.core.windows.net/bronze"
    )
    trigger_interval: str = os.getenv("TRIGGER_INTERVAL", "5 seconds")
    max_offsets_per_trigger: str = os.getenv("MAX_OFFSETS_PER_TRIGGER", "50000")


config = StreamingConfig()
