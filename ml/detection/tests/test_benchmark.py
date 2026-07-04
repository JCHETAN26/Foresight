"""Tests for the benchmark harness."""

from __future__ import annotations

import numpy as np

from foresight_detection.benchmark import evaluate, run_benchmark
from foresight_detection.data import DatasetConfig, generate
from foresight_detection.ensemble import EnsembleConfig


def test_evaluate_perfect_scores() -> None:
    labels = np.array([0, 0, 1, 0, 1])
    scores = np.array([0.1, 0.2, 0.9, 0.15, 0.95])  # ranks anomalies top
    m = evaluate(scores, labels)
    assert m["f1"] == 1.0
    assert m["pr_auc"] == 1.0


def test_run_benchmark_table() -> None:
    df = generate(DatasetConfig(n_tenants=8, n_days=60, seed=1))
    table = run_benchmark(df, ensemble_config=EnsembleConfig(epochs=10))

    assert set(table["method"]) == {
        "Ensemble (LSTM+IForest)",
        "IsolationForest",
        "Seasonal z-score",
        "ARIMA residual",
    }
    for col in ["precision", "recall", "f1", "pr_auc"]:
        assert (table[col] >= 0).all() and (table[col] <= 1).all()
    # The ensemble should be a credible detector on this labeled set.
    ens = table.loc[table["method"] == "Ensemble (LSTM+IForest)", "pr_auc"].iloc[0]
    assert ens > 0.4
