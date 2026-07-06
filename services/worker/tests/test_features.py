"""Tests for the KPI-rows → feature-schema transform (no DB, no models)."""

from __future__ import annotations

import datetime as dt

from foresight_worker.features import METRICS, build_features


def test_build_features_shape_and_day_index() -> None:
    rows = [
        ("acct_a", dt.date(2026, 6, 1), 100.0, 0.30, 0.02, 500.0),
        ("acct_a", dt.date(2026, 6, 2), 110.0, 0.28, 0.03, 480.0),
        ("acct_b", dt.date(2026, 6, 1), 200.0, 0.35, 0.01, 800.0),
    ]
    df = build_features(rows)

    assert list(df.columns) == ["tenant_id", "metric_date", "day", *METRICS]
    # per-tenant day is a 0-based ordinal in date order
    assert df.loc[df.tenant_id == "acct_a", "day"].tolist() == [0, 1]
    assert df.loc[df.tenant_id == "acct_b", "day"].tolist() == [0]
    # dates are stringified for the record's metric_date
    assert df.iloc[0]["metric_date"] == "2026-06-01"
