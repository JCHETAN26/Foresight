"""Stripe webhook receiver.

Verifies the Stripe signature, normalizes the event into a Foresight envelope,
and hands it to the Kafka producer keyed by tenant. Signature verification is
mandatory — an unverified webhook is a spoofable ingestion vector.

Tenant resolution: in Stripe Connect, events originating from a connected
account carry the account id in the top-level ``account`` field. That id is the
Foresight ``tenant_id``. Platform-level events without an account fall back to
the default topic.
"""

from __future__ import annotations

import json
from typing import Any

import stripe
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import settings
from app.kafka_producer import producer
from app.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _build_envelope(event: dict[str, Any], tenant_id: str | None) -> dict[str, Any]:
    """Wrap the raw Stripe event in a Foresight ingestion envelope.

    The bronze layer stores the raw event immutably; the envelope adds the
    routing/lineage metadata the downstream pipeline needs without mutating the
    original payload.
    """
    return {
        "id": event["id"],
        "source": "stripe",
        "tenant_id": tenant_id,
        "event_type": event["type"],
        "livemode": event.get("livemode", False),
        "created": event.get("created"),
        "api_version": event.get("api_version"),
        "data": event["data"],
    }


@router.post("/stripe", status_code=status.HTTP_202_ACCEPTED)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> dict[str, str]:
    """Receive, verify, and enqueue a Stripe webhook event."""
    payload = await request.body()

    try:
        # Verifies the signature and rejects stale timestamps (replay guard).
        stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
            tolerance=settings.stripe_webhook_tolerance,
        )
    except ValueError:
        # Malformed payload — not JSON or not a Stripe event shape.
        log.warning("stripe_webhook_invalid_payload")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid payload") from None
    except stripe.SignatureVerificationError:
        # Bad or missing signature — reject; do not enqueue.
        log.warning("stripe_webhook_bad_signature")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "signature verification failed") from None

    # The payload is now verified authentic; parse the raw bytes directly to a
    # plain dict (avoids StripeObject serialization quirks across SDK versions).
    event_dict: dict[str, Any] = json.loads(payload)
    tenant_id = event_dict.get("account")  # present on Connect events

    envelope = _build_envelope(event_dict, tenant_id)
    topic = settings.topic_for(tenant_id)

    await producer.send(topic=topic, key=tenant_id, value=envelope)

    return {"status": "accepted", "event_id": event_dict["id"]}
