"""Async Kafka producer wrapper.

A single long-lived producer is shared across requests. Messages are keyed by
tenant_id so all events for a tenant land on the same partition, preserving
per-tenant ordering — a requirement for the downstream time-series detection.
"""

from __future__ import annotations

import json
from typing import Any

from aiokafka import AIOKafkaProducer

from app.config import settings
from app.logging import get_logger
from app.metrics import EVENTS_PUBLISHED, PUBLISH_DURATION, PUBLISH_ERRORS

log = get_logger(__name__)


class KafkaEventProducer:
    """Thin async wrapper around AIOKafkaProducer with JSON serialization."""

    def __init__(self, conn_kwargs: dict[str, Any]) -> None:
        self._conn_kwargs = conn_kwargs
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            **self._conn_kwargs,
            enable_idempotence=True,  # exactly-once producing within a session
            acks="all",
            linger_ms=5,
        )
        await self._producer.start()
        log.info(
            "kafka_producer_started",
            bootstrap_servers=self._conn_kwargs.get("bootstrap_servers"),
        )

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None
        log.info("kafka_producer_stopped")

    async def send(self, topic: str, key: str | None, value: dict[str, Any]) -> None:
        """Publish a JSON event, keyed for per-tenant partition affinity."""
        if self._producer is None:
            raise RuntimeError("producer not started")
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None
        source = value.get("source", "unknown")
        try:
            with PUBLISH_DURATION.labels(source).time():
                await self._producer.send_and_wait(topic, value=payload, key=key_bytes)
        except Exception:
            PUBLISH_ERRORS.labels(source).inc()
            log.error("event_publish_failed", topic=topic, key=key)
            raise
        EVENTS_PUBLISHED.labels(source).inc()
        log.info("event_published", topic=topic, key=key, event_id=value.get("id"))


producer = KafkaEventProducer(settings.kafka_conn_kwargs())
