"""Foresight API — serves KPI history and the anomaly log to the dashboard."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import __version__
from app.cache import cache, cached_json, enforce_rate_limit, store_json
from app.config import settings
from app.db import db
from app.metrics import CACHE, RATE_LIMITED, PrometheusMiddleware
from app.models import Anomaly, KpiPoint, Tenant
from app.repository import get_kpis, list_anomalies, list_tenants


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await db.connect()
    await cache.connect()
    try:
        yield
    finally:
        await cache.close()
        await db.close()


app = FastAPI(title="Foresight API", version=__version__, lifespan=lifespan)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.url.path not in ("/health", "/metrics"):
        client = request.headers.get("x-forwarded-for", "") or (
            request.client.host if request.client else "unknown"
        )
        if await enforce_rate_limit(client):
            RATE_LIMITED.inc()
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    return await call_next(request)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/metrics", tags=["ops"])
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/anomalies", response_model=list[Anomaly], tags=["anomalies"])
async def anomalies(limit: int = 50) -> list[Anomaly]:
    key = f"anomalies:{limit}"
    hit = await cached_json(key)
    if hit is not None:
        CACHE.labels("hit").inc()
        return [Anomaly(**a) for a in hit]
    CACHE.labels("miss").inc()
    rows = await list_anomalies(db, limit=limit)
    await store_json(key, [a.model_dump() for a in rows])
    return rows


@app.get("/tenants", response_model=list[Tenant], tags=["tenants"])
async def tenants() -> list[Tenant]:
    return await list_tenants(db)


@app.get("/kpis/{tenant_id}", response_model=list[KpiPoint], tags=["kpis"])
async def kpis(tenant_id: str, days: int = 90) -> list[KpiPoint]:
    return await get_kpis(db, tenant_id, days=days)
