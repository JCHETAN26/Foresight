"""Foresight KPI stream processor.

Consumes Stripe event envelopes from Kafka and computes the per-tenant, per-day
KPIs the detector watches (MRR, conversion rate, refund rate, checkout volume)
into Postgres `kpi_daily`. This is the live equivalent of the dbt bronze→gold
transformation; its math is cross-validated against the dbt gold assertions.
"""

__version__ = "0.1.0"
