"""Stripe events → per-tenant, per-day KPIs.

Pure functions (no Kafka, no DB) so the KPI math is unit-tested in isolation and
cross-checked against the dbt gold model's exact-value assertions. Mirrors the
dbt logic: subscriptions move MRR, invoices are revenue, refunds/gross give the
refund rate, and checkout completed/expired give conversion.

Event shape (the ingestion envelope): ``{tenant_id, event_type, created (epoch),
data: {object: {amount, ...}}}``. `amount` is in cents. (Real Stripe subscription
amounts live in items[].price.unit_amount — extracted upstream; here we read a
normalized `amount`.)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class _DayAgg:
    mrr_delta_cents: int = 0
    gross_cents: int = 0
    refund_cents: int = 0
    completed: int = 0
    expired: int = 0


@dataclass
class DailyKpi:
    tenant_id: str
    metric_date: str
    mrr: float
    conversion_rate: float
    refund_rate: float
    checkout_volume: float


def _amount(event: dict) -> int:
    obj = event.get("data", {}).get("object", {})
    try:
        return int(obj.get("amount") or 0)
    except (TypeError, ValueError):
        return 0


def _date(event: dict) -> str:
    created = event.get("created")
    if isinstance(created, str):
        return created[:10]
    return datetime.fromtimestamp(int(created), tz=UTC).date().isoformat()


def compute_daily_kpis(events: list[dict]) -> list[DailyKpi]:
    """Aggregate a tenant's Stripe events into a daily KPI series (MRR running)."""
    by_day: dict[tuple[str, str], _DayAgg] = {}
    tenants: dict[str, set[str]] = {}

    for e in events:
        tenant = e["tenant_id"]
        day = _date(e)
        agg = by_day.setdefault((tenant, day), _DayAgg())
        etype = e["event_type"]
        amt = _amount(e)

        if etype == "customer.subscription.created":
            agg.mrr_delta_cents += amt
        elif etype == "customer.subscription.deleted":
            agg.mrr_delta_cents -= amt
        elif etype == "invoice.paid":
            agg.gross_cents += amt
        elif etype == "charge.refunded":
            agg.refund_cents += amt
        elif etype == "checkout.session.completed":
            agg.completed += 1
        elif etype == "checkout.session.expired":
            agg.expired += 1
        tenants.setdefault(tenant, set()).add(day)

    out: list[DailyKpi] = []
    for tenant, days in tenants.items():
        running_mrr_cents = 0
        for day in sorted(days):
            agg = by_day[(tenant, day)]
            running_mrr_cents += agg.mrr_delta_cents
            checkouts = agg.completed + agg.expired
            conversion = agg.completed / checkouts if checkouts else 0.0
            refund_rate = agg.refund_cents / agg.gross_cents if agg.gross_cents else 0.0
            out.append(
                DailyKpi(
                    tenant_id=tenant,
                    metric_date=day,
                    mrr=round(running_mrr_cents / 100.0, 2),
                    conversion_rate=round(conversion, 4),
                    refund_rate=round(refund_rate, 4),
                    checkout_volume=float(checkouts),
                )
            )
    return out
