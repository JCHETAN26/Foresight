"""Prometheus metrics for the ingestion service.

Deliberately low-cardinality: we label by `source` and coarse `outcome`/`event_type`
buckets, never by `tenant_id`. At 500+ tenants, per-tenant labels would blow up
Prometheus series cardinality — tenant-level analytics belong in the data
platform (gold KPIs), not in platform observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

EVENTS_RECEIVED = Counter(
    "foresight_ingestion_events_received_total",
    "Webhook events received, by source and outcome.",
    ["source", "outcome"],  # outcome: accepted | rejected_signature | rejected_payload
)

EVENTS_PUBLISHED = Counter(
    "foresight_ingestion_events_published_total",
    "Events successfully published to Kafka, by source.",
    ["source"],
)

PUBLISH_ERRORS = Counter(
    "foresight_ingestion_publish_errors_total",
    "Kafka publish failures, by source.",
    ["source"],
)

PUBLISH_DURATION = Histogram(
    "foresight_ingestion_publish_duration_seconds",
    "Time to publish an event to Kafka (send_and_wait).",
    ["source"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
