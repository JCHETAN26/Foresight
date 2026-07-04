"""Tests for Prometheus instrumentation."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.conftest import FakeProducer, sign_payload


def _event(account: str = "acct_metrics") -> bytes:
    return json.dumps(
        {
            "id": "evt_metrics_1",
            "object": "event",
            "type": "payment_intent.succeeded",
            "livemode": False,
            "created": 1719900000,
            "account": account,
            "data": {"object": {"id": "pi_1", "amount": 100, "currency": "usd"}},
        }
    ).encode("utf-8")


def test_metrics_endpoint_exposes_series(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "foresight_ingestion_events_received_total" in resp.text


def test_accepted_event_increments_received_counter(
    client: TestClient, fake_producer: FakeProducer
) -> None:
    payload = _event()
    headers = {"Stripe-Signature": sign_payload(payload)}

    before = _counter_value(client, outcome="accepted")
    resp = client.post("/webhooks/stripe", content=payload, headers=headers)
    assert resp.status_code == 202
    after = _counter_value(client, outcome="accepted")

    assert after == before + 1


def test_bad_signature_increments_rejected_counter(client: TestClient) -> None:
    payload = _event()
    headers = {"Stripe-Signature": "t=1719900000,v1=deadbeef"}

    before = _counter_value(client, outcome="rejected_signature")
    resp = client.post("/webhooks/stripe", content=payload, headers=headers)
    assert resp.status_code == 401
    after = _counter_value(client, outcome="rejected_signature")

    assert after == before + 1


def _counter_value(client: TestClient, outcome: str) -> float:
    """Scrape the received-counter value for a given outcome label."""
    text = client.get("/metrics").text
    needle = (
        'foresight_ingestion_events_received_total{'
        f'outcome="{outcome}",source="stripe"}} '
    )
    for line in text.splitlines():
        if line.startswith(needle):
            return float(line[len(needle):])
    return 0.0
