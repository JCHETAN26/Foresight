"""API tests against a real Postgres (DATABASE_URL). Seeds, asserts, cleans up."""

from __future__ import annotations

import json

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import db
from app.main import app

TENANT = "test_tenant"


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await db.connect()
    async with db.pool.connection() as conn:  # type: ignore[union-attr]
        await conn.execute(
            "INSERT INTO tenants (tenant_id, name) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
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
    await db.close()


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_anomalies_returns_seeded(client: AsyncClient) -> None:
    resp = await client.get("/anomalies")
    assert resp.status_code == 200
    rows = resp.json()
    mine = [a for a in rows if a["tenant_id"] == TENANT]
    assert len(mine) == 1
    a = mine[0]
    assert a["anomaly_type"] == "payment_failure"
    assert a["top_contributors"] == [["refund_rate", 9.8]]
    assert a["status"] == "ready"


async def test_kpis_returns_series(client: AsyncClient) -> None:
    resp = await client.get(f"/kpis/{TENANT}?days=30")
    assert resp.status_code == 200
    points = resp.json()
    assert len(points) == 1
    assert points[0]["refund_rate"] == 0.16
