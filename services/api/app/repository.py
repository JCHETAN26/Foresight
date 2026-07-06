"""Read queries backing the API routes."""

from __future__ import annotations

from typing import Any

from app.db import Database
from app.models import Anomaly, KpiPoint, Tenant


async def list_anomalies(database: Database, limit: int = 50) -> list[Anomaly]:
    rows = await database.fetch(
        """
        SELECT tenant_id, metric_date, anomaly_type, anomaly_score, type_confidence,
               top_contributors, metrics, explanation, faithfulness, sources, status
        FROM anomaly_log
        ORDER BY anomaly_score DESC
        LIMIT %s
        """,
        (limit,),
    )
    return [_to_anomaly(r) for r in rows]


async def get_kpis(database: Database, tenant_id: str, days: int = 90) -> list[KpiPoint]:
    rows = await database.fetch(
        """
        SELECT metric_date, mrr, conversion_rate, refund_rate, checkout_volume
        FROM kpi_daily
        WHERE tenant_id = %s
        ORDER BY metric_date DESC
        LIMIT %s
        """,
        (tenant_id, days),
    )
    return [KpiPoint(**r) for r in reversed(rows)]


async def list_tenants(database: Database) -> list[Tenant]:
    rows = await database.fetch("SELECT tenant_id, name FROM tenants ORDER BY tenant_id")
    return [Tenant(**r) for r in rows]


def _to_anomaly(r: dict[str, Any]) -> Anomaly:
    return Anomaly(
        tenant_id=r["tenant_id"],
        metric_date=str(r["metric_date"]),
        anomaly_type=r["anomaly_type"],
        anomaly_score=r["anomaly_score"],
        type_confidence=r["type_confidence"],
        top_contributors=[tuple(c) for c in r["top_contributors"]],
        metrics=r["metrics"],
        explanation=r["explanation"],
        faithfulness=r["faithfulness"],
        sources=r["sources"],
        status=r["status"],
    )
