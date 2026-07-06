"""Benchmark the ensemble on real NAB data (not synthetic).

Runs the same method family — LSTM autoencoder + IsolationForest ensemble vs
IsolationForest, seasonal z-score, and ARIMA baselines — on NAB's real-world
labeled streams, and reports precision/recall/F1 (at the F1-optimal threshold)
plus PR-AUC, averaged across files.

Methodology note: this uses standard point-wise metrics against NAB's labeled
anomaly *windows* — NOT NAB's own application-profile scoring. NAB anomalies are
sparse, so point-wise F1 is intentionally conservative; PR-AUC is the fairer,
threshold-independent summary.
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from foresight_detection.benchmark import evaluate
from foresight_detection.lstm_autoencoder import (
    make_windows,
    reconstruction_error,
    train_autoencoder,
)
from foresight_detection.nab import NAB_FILES, ensure_downloaded, load_series


def _rank_pct(x: np.ndarray) -> np.ndarray:
    if len(x) <= 1:
        return np.zeros_like(x, dtype=float)
    return np.argsort(np.argsort(x)) / (len(x) - 1)


def _if_scores(values: np.ndarray, seed: int) -> np.ndarray:
    iso = IsolationForest(contamination=0.05, random_state=seed, n_estimators=200)
    iso.fit(values.reshape(-1, 1))
    return -iso.decision_function(values.reshape(-1, 1))


def _lstm_scores(
    values: np.ndarray, window: int, epochs: int, max_train: int, seed: int
) -> np.ndarray:
    z = (values - values.mean()) / (values.std() or 1.0)
    windows = make_windows(z.reshape(-1, 1).astype("float32"), window)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(windows), size=min(max_train, len(windows)), replace=False)
    model = train_autoencoder(windows[idx], n_features=1, epochs=epochs, seed=seed)
    err = reconstruction_error(model, windows)

    scores = np.empty(len(values), dtype=float)
    scores[window - 1 :] = err
    scores[: window - 1] = err[0] if len(err) else 0.0
    return scores


def _zscore(values: np.ndarray, w: int = 48) -> np.ndarray:
    s = pd.Series(values)
    mean = s.rolling(w, min_periods=1).mean()
    std = s.rolling(w, min_periods=1).std().fillna(1.0)
    std[std == 0] = 1.0
    return np.abs((s - mean) / std).to_numpy()


def _arima(values: np.ndarray) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            resid = np.abs(ARIMA(values, order=(2, 0, 0)).fit().resid)
            return (resid - resid.mean()) / (resid.std() + 1e-9)
        except Exception:
            return np.zeros_like(values)


def benchmark_file(
    values: np.ndarray, labels: np.ndarray, *, window: int, epochs: int, max_train: int, seed: int
) -> dict[str, dict[str, float]]:
    lstm = _rank_pct(_lstm_scores(values, window, epochs, max_train, seed))
    iforest_pct = _rank_pct(_if_scores(values, seed))
    methods = {
        "Ensemble (LSTM+IForest)": 0.5 * lstm + 0.5 * iforest_pct,
        "IsolationForest": _if_scores(values, seed),
        "Seasonal z-score": _zscore(values),
        "ARIMA residual": _arima(values),
    }
    return {name: evaluate(scores, labels) for name, scores in methods.items()}


def run(
    *,
    window: int = 48,
    epochs: int = 20,
    max_train: int = 3000,
    cache_dir: str = "outputs/nab",
    seed: int = 0,
) -> pd.DataFrame:
    ensure_downloaded(cache_dir)
    per_method: dict[str, list[dict[str, float]]] = {}
    for name in NAB_FILES:
        values, labels = load_series(name, cache_dir)
        for method, metrics in benchmark_file(
            values, labels, window=window, epochs=epochs, max_train=max_train, seed=seed
        ).items():
            per_method.setdefault(method, []).append(metrics)

    rows = [
        {
            "method": method,
            "precision": float(np.mean([r["precision"] for r in results])),
            "recall": float(np.mean([r["recall"] for r in results])),
            "f1": float(np.mean([r["f1"] for r in results])),
            "pr_auc": float(np.mean([r["pr_auc"] for r in results])),
        }
        for method, results in per_method.items()
    ]
    return pd.DataFrame(rows).sort_values("pr_auc", ascending=False).reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--window", type=int, default=48)
    parser.add_argument("--out", default="outputs/nab_benchmark.csv")
    args = parser.parse_args(argv)

    table = run(window=args.window, epochs=args.epochs)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)
    print(f"NAB real-data benchmark ({len(NAB_FILES)} streams):")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
