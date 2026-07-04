"""Tests for the gold -> feature-schema adapter."""

from __future__ import annotations

import pandas as pd
from foresight_detection.data import METRICS

from foresight_anomaly.gold_adapter import adapt_gold


def test_adapt_derives_checkout_volume_and_day() -> None:
    gold = pd.DataFrame(
        {
            "tenant_id": ["a", "a", "b"],
            "metric_date": ["2026-06-01", "2026-06-02", "2026-06-01"],
            "mrr": [100.0, 110.0, 200.0],
            "conversion_rate": [0.3, 0.28, 0.35],
            "refund_rate": [0.02, 0.03, 0.01],
            "checkouts_completed": [40, 35, 80],
            "checkouts_expired": [10, 15, 20],
        }
    )
    out = adapt_gold(gold)
    for col in ["tenant_id", "metric_date", "day", *METRICS]:
        assert col in out.columns
    # checkout_volume = completed + expired
    assert out.loc[out["tenant_id"] == "a", "checkout_volume"].tolist() == [50.0, 50.0]
    # day is a per-tenant ordinal
    assert out.loc[out["tenant_id"] == "a", "day"].tolist() == [0, 1]


def test_adapt_fills_null_metrics() -> None:
    # conversion_rate is null when a tenant-day had no checkouts.
    gold = pd.DataFrame(
        {
            "tenant_id": ["b", "b"],
            "metric_date": ["2026-06-01", "2026-06-02"],
            "mrr": [200.0, 200.0],
            "conversion_rate": [None, None],
            "refund_rate": [0.0, 0.0],
            "checkout_volume": [0.0, 0.0],
        }
    )
    out = adapt_gold(gold)
    assert out["conversion_rate"].notna().all()
    assert out["conversion_rate"].tolist() == [0.0, 0.0]
