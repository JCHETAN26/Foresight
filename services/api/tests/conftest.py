"""Shared test fixtures: a seeded client backed by real Postgres (+ Redis if set)."""

from __future__ import annotations

import json

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.cache import cache
from app.db import db
from app.main import app

TENANT = "test_tenant"


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await db.connect()
    await cache.connect()
    if cache.client is not None:
        await cache.client.flushdb()  # clean rate-limit + cache state per test

    async with db.pool.connection() as conn:  # type: ignore[union-attr]
        await conn.execute(
            "INSERT INTO tenants (tenant_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (TENANT, "Test Tenant"),
        )
        await conn.execute(
            """
            INSERT INTO anomaly_log
                (tenant_id, metric_date, anomaly_type, anomaly_score, type_confidence,
                 top_contributors, metrics, explanation, faithfulness, sources, status)
            VALUES (%s, '2026-06-14', 'payment_failure', 0.97, 0.71,
                    %s, %s, 'Refund rate spiked.', 1.0, %s, 'ready')
            ON CONFLICT DO NOTHING
            """,
            (
                TENANT,
                json.dumps([["refund_rate", 9.8]]),
                json.dumps({"mrr": 41200.0}),
                json.dumps(["r1"]),
            ),
        )
        await conn.execute(
            "INSERT INTO kpi_daily VALUES (%s, '2026-06-14', 41200, 0.29, 0.16, 880) "
            "ON CONFLICT DO NOTHING",
            (TENANT,),
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with db.pool.connection() as conn:  # type: ignore[union-attr]
        await conn.execute("DELETE FROM anomaly_log WHERE tenant_id = %s", (TENANT,))
        await conn.execute("DELETE FROM kpi_daily WHERE tenant_id = %s", (TENANT,))
        await conn.execute("DELETE FROM tenants WHERE tenant_id = %s", (TENANT,))
    await cache.close()
    await db.close()
