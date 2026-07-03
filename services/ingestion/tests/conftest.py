"""Test fixtures — a fake Kafka producer and a signed-webhook helper."""

from __future__ import annotations

import time
from typing import Any

import pytest
import stripe
from fastapi.testclient import TestClient

TEST_WEBHOOK_SECRET = "whsec_test_secret_0123456789"


class FakeProducer:
    """Records sent messages instead of talking to a broker."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.started = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    async def send(self, topic: str, key: str | None, value: dict[str, Any]) -> None:
        self.sent.append({"topic": topic, "key": key, "value": value})


@pytest.fixture
def fake_producer(monkeypatch: pytest.MonkeyPatch) -> FakeProducer:
    fake = FakeProducer()
    # Patch the singleton referenced by both main.py and the webhook handler.
    monkeypatch.setattr("app.kafka_producer.producer", fake)
    monkeypatch.setattr("app.webhooks.stripe.producer", fake)
    monkeypatch.setattr("app.main.producer", fake)
    return fake


@pytest.fixture
def client(fake_producer: FakeProducer, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    monkeypatch.setattr("app.config.settings.stripe_webhook_secret", TEST_WEBHOOK_SECRET)
    # Import after patching so lifespan uses the fake producer.
    from app.main import app

    with TestClient(app) as c:
        yield c


def sign_payload(payload: bytes, secret: str = TEST_WEBHOOK_SECRET) -> str:
    """Produce a valid Stripe-Signature header for a raw payload."""
    timestamp = int(time.time())
    signed = stripe.WebhookSignature._compute_signature(  # type: ignore[attr-defined]
        f"{timestamp}.{payload.decode('utf-8')}", secret
    )
    return f"t={timestamp},v1={signed}"
