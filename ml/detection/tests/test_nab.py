"""Tests for the NAB loader (labelling) and benchmark math — no network."""

from __future__ import annotations

import json

import numpy as np

from foresight_detection.nab import load_series
from foresight_detection.nab_benchmark import benchmark_file


def test_load_series_labels_by_window(tmp_path) -> None:
    (tmp_path / "realKnownCause").mkdir(parents=True)
    (tmp_path / "realKnownCause" / "s.csv").write_text(
        "timestamp,value\n"
        "2014-01-01 00:00:00,10\n"
        "2014-01-01 01:00:00,11\n"
        "2014-01-01 02:00:00,99\n"
        "2014-01-01 03:00:00,12\n"
    )
    (tmp_path / "combined_windows.json").write_text(
        json.dumps({"realKnownCause/s.csv": [["2014-01-01 01:30:00", "2014-01-01 02:30:00"]]})
    )

    values, labels = load_series("realKnownCause/s.csv", cache_dir=str(tmp_path))
    assert list(values) == [10.0, 11.0, 99.0, 12.0]
    # only the 02:00 point falls inside the [01:30, 02:30] window
    assert list(labels) == [0, 0, 1, 0]


def test_benchmark_detects_obvious_spike() -> None:
    rng = np.random.default_rng(0)
    values = rng.normal(50, 1, 400)
    labels = np.zeros(400, dtype=int)
    values[200:205] += 25  # a clear anomaly segment
    labels[200:205] = 1

    res = benchmark_file(values, labels, window=24, epochs=5, max_train=300, seed=0)
    assert set(res) == {
        "Ensemble (LSTM+IForest)",
        "IsolationForest",
        "Seasonal z-score",
        "ARIMA residual",
    }
    # the ensemble should clearly separate an obvious spike
    assert res["Ensemble (LSTM+IForest)"]["pr_auc"] > 0.5
