"""Tests for Prometheus metrics, rate limiting, and response caching.

The rate-limit + cache tests require Redis (REDIS_URL) — skipped otherwise so the
core suite still runs without it.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app import config
from app.cache import cache

needs_redis = pytest.mark.skipif(
    not config.settings.redis_url, reason="set REDIS_URL to test rate limiting + cache"
)


async def test_metrics_endpoint(client: AsyncClient) -> None:
    await client.get("/anomalies")  # generate a request to record
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "foresight_api_requests_total" in body
    assert "foresight_api_request_duration_seconds" in body


@needs_redis
async def test_rate_limit_returns_429(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(config.settings, "rate_limit_per_min", 3)
    statuses = [(await client.get("/anomalies")).status_code for _ in range(5)]
    assert 429 in statuses
    assert statuses[:3] == [200, 200, 200]


@needs_redis
async def test_response_is_cached(client: AsyncClient) -> None:
    await client.get("/anomalies")  # miss → stored
    assert await cache.get("anomalies:50") is not None  # cached in Redis
    resp = await client.get("/anomalies")  # served from cache
    assert resp.status_code == 200
