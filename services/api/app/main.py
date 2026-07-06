"""Foresight API — serves KPI history and the anomaly log to the dashboard."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.db import db
from app.models import Anomaly, KpiPoint, Tenant
from app.repository import get_kpis, list_anomalies, list_tenants


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await db.connect()
    try:
        yield
    finally:
        await db.close()


app = FastAPI(title="Foresight API", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/anomalies", response_model=list[Anomaly], tags=["anomalies"])
async def anomalies(limit: int = 50) -> list[Anomaly]:
    return await list_anomalies(db, limit=limit)


@app.get("/tenants", response_model=list[Tenant], tags=["tenants"])
async def tenants() -> list[Tenant]:
    return await list_tenants(db)


@app.get("/kpis/{tenant_id}", response_model=list[KpiPoint], tags=["kpis"])
async def kpis(tenant_id: str, days: int = 90) -> list[KpiPoint]:
    return await get_kpis(db, tenant_id, days=days)
