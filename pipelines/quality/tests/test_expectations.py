"""Tests for the Great Expectations gates — valid data passes, bad data fails."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from foresight_quality.expectations import validate_bronze, validate_gold


def _valid_gold() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "tenant_id": ["acct_a", "acct_a"],
            "metric_date": [dt.date(2026, 6, 1), dt.date(2026, 6, 2)],
            "mrr": [150.0, 200.0],
            "active_subscriptions": [2, 3],
            "churn_rate": [None, 0.0],  # null allowed where undefined
            "refund_rate": [0.0, 0.4],
            "payment_failure_rate": [0.0, 0.5],
            "conversion_rate": [0.6667, None],
        }
    )


def test_valid_gold_passes() -> None:
    result = validate_gold(_valid_gold())
    assert result.success


def test_gold_with_null_mrr_fails() -> None:
    df = _valid_gold()
    df.loc[0, "mrr"] = None
    result = validate_gold(df)
    assert not result.success


def test_gold_with_out_of_range_rate_fails() -> None:
    df = _valid_gold()
    df.loc[1, "conversion_rate"] = 1.5  # > 1
    result = validate_gold(df)
    assert not result.success


def test_valid_bronze_passes() -> None:
    df = pd.DataFrame(
        {
            "event_id": ["evt_1", "evt_2"],
            "tenant_id": ["acct_a", "acct_b"],
            "event_type": ["invoice.paid", "charge.refunded"],
            "payload": ['{"id":"in_1"}', '{"id":"ch_1"}'],
        }
    )
    assert validate_bronze(df).success


def test_bronze_with_null_event_id_fails() -> None:
    df = pd.DataFrame(
        {
            "event_id": ["evt_1", None],
            "tenant_id": ["acct_a", "acct_b"],
            "event_type": ["invoice.paid", "charge.refunded"],
            "payload": ['{"id":"in_1"}', '{"id":"ch_1"}'],
        }
    )
    assert not validate_bronze(df).success
