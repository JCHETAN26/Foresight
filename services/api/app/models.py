"""API response models (mirror the frontend's Anomaly shape)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Anomaly(BaseModel):
    tenant_id: str
    metric_date: str
    anomaly_type: str
    anomaly_score: float
    type_confidence: float
    top_contributors: list[tuple[str, float]]
    metrics: dict[str, float]
    explanation: str
    faithfulness: float
    sources: list[str]
    status: str


class KpiPoint(BaseModel):
    metric_date: date
    mrr: float
    conversion_rate: float
    refund_rate: float
    checkout_volume: float


class Tenant(BaseModel):
    tenant_id: str
    name: str | None = None
