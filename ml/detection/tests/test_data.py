"""Tests for the synthetic dataset generator."""

from __future__ import annotations

from foresight_detection.data import METRICS, DatasetConfig, generate


def test_shape_and_columns() -> None:
    cfg = DatasetConfig(n_tenants=5, n_days=40)
    df = generate(cfg)
    assert len(df) == 5 * 40
    for col in ["tenant_id", "day", *METRICS, "is_anomaly", "anomaly_type"]:
        assert col in df.columns


def test_has_labeled_anomalies() -> None:
    df = generate(DatasetConfig(n_tenants=8, n_days=60))
    assert df["is_anomaly"].sum() > 0
    # anomaly_type is set exactly where is_anomaly == 1.
    typed = df["anomaly_type"].notna()
    assert (typed == (df["is_anomaly"] == 1)).all()


def test_deterministic() -> None:
    a = generate(DatasetConfig(n_tenants=4, n_days=30, seed=42))
    b = generate(DatasetConfig(n_tenants=4, n_days=30, seed=42))
    assert a.equals(b)
