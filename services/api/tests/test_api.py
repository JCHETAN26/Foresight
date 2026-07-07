"""API tests against a real Postgres. The `client` fixture lives in conftest.py."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import TENANT


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
