"""KPI-rows → detector feature schema. Kept dependency-light (pandas only) so it
is unit-testable in CI without pulling in torch / the agent."""

from __future__ import annotations

from typing import Any

import pandas as pd

# Mirrors foresight_detection.data.METRICS (kept local to avoid a heavy import).
METRICS = ["mrr", "conversion_rate", "refund_rate", "checkout_volume"]


def build_features(rows: list[tuple[Any, ...]]) -> pd.DataFrame:
    """Rows from kpi_daily → feature schema with a per-tenant 0-based day index."""
    df = pd.DataFrame(rows, columns=["tenant_id", "metric_date", *METRICS])
    df["metric_date"] = df["metric_date"].astype(str)
    df = df.sort_values(["tenant_id", "metric_date"]).reset_index(drop=True)
    df["day"] = df.groupby("tenant_id").cumcount()
    return df[["tenant_id", "metric_date", "day", *METRICS]]
