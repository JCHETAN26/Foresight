"""Adapt the M1 gold KPI table to the detector's feature schema.

The detection ensemble watches four metrics: mrr, conversion_rate, refund_rate,
checkout_volume. Gold (`fct_kpi_timeseries`) carries the first three directly and
splits checkout into completed/expired, so we reconstruct volume. `metric_date`
becomes an integer `day` per tenant (the ordering the windowing needs).
"""

from __future__ import annotations

import duckdb
import pandas as pd
from foresight_detection.data import METRICS

GOLD_QUERY = "select * from marts.fct_kpi_timeseries order by tenant_id, metric_date"


def adapt_gold(gold: pd.DataFrame) -> pd.DataFrame:
    """Map a gold-schema frame to the detector's feature schema.

    Returns columns: tenant_id, metric_date, day, + METRICS.
    """
    df = gold.copy()
    if "checkout_volume" not in df.columns:
        completed = df.get("checkouts_completed", 0)
        expired = df.get("checkouts_expired", 0)
        df["checkout_volume"] = pd.to_numeric(completed, errors="coerce").fillna(0) + (
            pd.to_numeric(expired, errors="coerce").fillna(0)
        )

    df = df.sort_values(["tenant_id", "metric_date"]).reset_index(drop=True)
    df["day"] = df.groupby("tenant_id").cumcount()

    missing = [m for m in METRICS if m not in df.columns]
    if missing:
        raise ValueError(f"gold frame missing required metrics: {missing}")

    # A metric can be null when undefined for a day (e.g. conversion with no
    # checkouts). Treat as 0 so per-tenant standardization stays finite.
    for m in METRICS:
        df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0.0)

    return df[["tenant_id", "metric_date", "day", *METRICS]]


def load_gold_from_duckdb(duckdb_path: str) -> pd.DataFrame:
    """Read the gold KPI table from the dbt-built DuckDB and adapt it."""
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        gold = con.execute(GOLD_QUERY).df()
    finally:
        con.close()
    return adapt_gold(gold)
