"""Tests for the Stripe webhook receiver → Kafka path."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.conftest import FakeProducer, sign_payload


def _event(account: str | None = None, event_type: str = "payment_intent.succeeded") -> bytes:
    body: dict = {
        "id": "evt_test_123",
        "object": "event",
        "type": event_type,
        "livemode": False,
        "created": 1719900000,
        "api_version": "2024-06-20",
        "data": {"object": {"id": "pi_test_1", "amount": 4200, "currency": "usd"}},
    }
    if account is not None:
        body["account"] = account
    return json.dumps(body).encode("utf-8")


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_valid_webhook_is_enqueued_with_tenant_routing(
    client: TestClient, fake_producer: FakeProducer
) -> None:
    payload = _event(account="acct_tenant_A")
    headers = {"Stripe-Signature": sign_payload(payload)}

    resp = client.post("/webhooks/stripe", content=payload, headers=headers)

    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted", "event_id": "evt_test_123"}

    assert len(fake_producer.sent) == 1
    msg = fake_producer.sent[0]
    assert msg["topic"] == "stripe.events.acct_tenant_A"
    assert msg["key"] == "acct_tenant_A"
    assert msg["value"]["tenant_id"] == "acct_tenant_A"
    assert msg["value"]["event_type"] == "payment_intent.succeeded"
    assert msg["value"]["source"] == "stripe"


def test_platform_event_without_account_uses_default_topic(
    client: TestClient, fake_producer: FakeProducer
) -> None:
    payload = _event(account=None)
    headers = {"Stripe-Signature": sign_payload(payload)}

    resp = client.post("/webhooks/stripe", content=payload, headers=headers)

    assert resp.status_code == 202
    assert fake_producer.sent[0]["topic"] == "stripe.events.unknown"
    assert fake_producer.sent[0]["key"] is None


def test_bad_signature_is_rejected_and_not_enqueued(
    client: TestClient, fake_producer: FakeProducer
) -> None:
    payload = _event(account="acct_tenant_A")
    headers = {"Stripe-Signature": "t=1719900000,v1=deadbeef"}

    resp = client.post("/webhooks/stripe", content=payload, headers=headers)

    assert resp.status_code == 401
    assert fake_producer.sent == []


def test_malformed_payload_is_rejected(
    client: TestClient, fake_producer: FakeProducer
) -> None:
    payload = b"not-json"
    headers = {"Stripe-Signature": sign_payload(payload)}

    resp = client.post("/webhooks/stripe", content=payload, headers=headers)

    assert resp.status_code == 400
    assert fake_producer.sent == []
