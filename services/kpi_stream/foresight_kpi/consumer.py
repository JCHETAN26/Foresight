"""Kafka consumer: Stripe events → recomputed KPIs → Postgres kpi_daily.

Buffers events per tenant and, on each poll batch, recomputes that tenant's daily
KPI series and upserts it. Recompute-from-events keeps the live KPIs identical to
the batch (dbt) semantics; a production build would checkpoint incremental state.
"""

from __future__ import annotations

import json
from collections import defaultdict

import psycopg
from aiokafka import AIOKafkaConsumer

from foresight_kpi.config import settings
from foresight_kpi.kpi import compute_daily_kpis

_UPSERT = """
INSERT INTO kpi_daily (tenant_id, metric_date, mrr, conversion_rate, refund_rate, checkout_volume)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (tenant_id, metric_date) DO UPDATE SET
    mrr = EXCLUDED.mrr, conversion_rate = EXCLUDED.conversion_rate,
    refund_rate = EXCLUDED.refund_rate, checkout_volume = EXCLUDED.checkout_volume
"""


def _flush(tenant_events: dict[str, list[dict]], dsn: str) -> int:
    written = 0
    with psycopg.connect(dsn) as conn:
        for events in tenant_events.values():
            for kpi in compute_daily_kpis(events):
                conn.execute(
                    "INSERT INTO tenants (tenant_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (kpi.tenant_id,),
                )
                conn.execute(
                    _UPSERT,
                    (
                        kpi.tenant_id, kpi.metric_date, kpi.mrr,
                        kpi.conversion_rate, kpi.refund_rate, kpi.checkout_volume,
                    ),
                )
                written += 1
        conn.commit()
    return written


async def run() -> None:
    consumer = AIOKafkaConsumer(
        **settings.kafka_conn_kwargs(),
        group_id="kpi-stream",
        auto_offset_reset="earliest",
    )
    consumer.subscribe(pattern=settings.subscribe_pattern)
    await consumer.start()
    tenant_events: dict[str, list[dict]] = defaultdict(list)
    try:
        async for msg in consumer:
            event = json.loads(msg.value)
            tenant = event.get("tenant_id")
            if tenant:
                tenant_events[tenant].append(event)
            # Flush opportunistically; in prod this would be time/size-triggered.
            if sum(len(v) for v in tenant_events.values()) >= settings.flush_every:
                _flush(dict(tenant_events), settings.database_url)
                tenant_events.clear()
    finally:
        if tenant_events:
            _flush(dict(tenant_events), settings.database_url)
        await consumer.stop()
