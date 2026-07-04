"""Tests for the detection ensemble — it must separate anomalies from normal."""

from __future__ import annotations

import numpy as np

from foresight_detection.data import DatasetConfig, generate
from foresight_detection.ensemble import DetectionEnsemble, EnsembleConfig


def test_fit_score_shape_and_range() -> None:
    df = generate(DatasetConfig(n_tenants=6, n_days=50)).sort_values(
        ["tenant_id", "day"]
    ).reset_index(drop=True)
    scores = DetectionEnsemble(EnsembleConfig(epochs=5)).fit_score(df)
    assert scores.shape == (len(df),)
    assert np.all(np.isfinite(scores))
    assert scores.min() >= 0.0 and scores.max() <= 1.0


def test_anomalies_score_higher_than_normal() -> None:
    df = generate(DatasetConfig(n_tenants=10, n_days=80, seed=3)).sort_values(
        ["tenant_id", "day"]
    ).reset_index(drop=True)
    scores = DetectionEnsemble(EnsembleConfig(epochs=15, seed=0)).fit_score(df)
    labels = df["is_anomaly"].to_numpy()

    mean_anom = scores[labels == 1].mean()
    mean_normal = scores[labels == 0].mean()
    # Anomalous days should be scored clearly higher on average.
    assert mean_anom > mean_normal + 0.1
