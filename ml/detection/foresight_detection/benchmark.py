"""Benchmark the ensemble against baseline detectors on labeled data.

Reports, per method: precision / recall / F1 at the F1-optimal threshold, plus
threshold-independent PR-AUC (average precision) — the fair summary for an
imbalanced detection task. All numbers are *measured* on the synthetic labeled
set, never hard-coded.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_recall_curve

from foresight_detection.data import METRICS
from foresight_detection.ensemble import DetectionEnsemble, EnsembleConfig


def evaluate(scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """Precision/recall/F1 at the best-F1 threshold, plus PR-AUC."""
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    # precision_recall_curve returns one more P/R point than thresholds.
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) > 0,
    )
    best = int(np.argmax(f1[:-1])) if len(f1) > 1 else 0
    return {
        "precision": float(precision[best]),
        "recall": float(recall[best]),
        "f1": float(f1[best]),
        "pr_auc": float(average_precision_score(labels, scores)),
        "threshold": float(thresholds[best]) if len(thresholds) else 0.0,
    }


def _standardize_per_tenant(df: pd.DataFrame) -> np.ndarray:
    z = np.empty((len(df), len(METRICS)), dtype=float)
    for _, idx in df.groupby("tenant_id").groups.items():
        rows = df.loc[idx, METRICS].to_numpy(dtype=float)
        mean, std = rows.mean(axis=0), rows.std(axis=0)
        std[std == 0] = 1.0
        z[df.index.get_indexer(idx)] = (rows - mean) / std
    return z


def isolation_forest_only(df: pd.DataFrame, seed: int = 0) -> np.ndarray:
    z = _standardize_per_tenant(df)
    iso = IsolationForest(contamination=0.05, random_state=seed, n_estimators=200)
    iso.fit(z)
    return -iso.decision_function(z)


def seasonal_zscore(df: pd.DataFrame) -> np.ndarray:
    scores = np.zeros(len(df))
    for _, g in df.groupby("tenant_id"):
        pos = df.index.get_indexer(g.index)
        per_metric = []
        for m in METRICS:
            s = pd.Series(g[m].to_numpy(dtype=float))
            mean = s.rolling(7, min_periods=1).mean()
            std = s.rolling(7, min_periods=1).std().fillna(1.0)
            std[std == 0] = 1.0
            per_metric.append(np.abs((s - mean) / std).to_numpy())
        scores[pos] = np.max(per_metric, axis=0)
    return scores


def arima_residual(df: pd.DataFrame) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA

    scores = np.zeros(len(df))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for _, g in df.groupby("tenant_id"):
            pos = df.index.get_indexer(g.index)
            per_metric = []
            for m in METRICS:
                s = g[m].to_numpy(dtype=float)
                try:
                    resid = np.abs(ARIMA(s, order=(2, 0, 0)).fit().resid)
                    resid = (resid - resid.mean()) / (resid.std() + 1e-9)
                except Exception:
                    resid = np.zeros_like(s)
                per_metric.append(resid)
            scores[pos] = np.max(per_metric, axis=0)
    return scores


def run_benchmark(
    df: pd.DataFrame, ensemble_config: EnsembleConfig | None = None
) -> pd.DataFrame:
    """Run every method and return a comparison table sorted by F1."""
    df = df.sort_values(["tenant_id", "day"]).reset_index(drop=True)
    labels = df["is_anomaly"].to_numpy()
    regime = df["regime"].to_numpy() if "regime" in df.columns else np.array([""] * len(df))
    point_mask = regime == "point"
    ctx_mask = regime == "contextual"

    methods = {
        "Ensemble (LSTM+IForest)": DetectionEnsemble(ensemble_config).fit_score(df),
        "IsolationForest": isolation_forest_only(df),
        "Seasonal z-score": seasonal_zscore(df),
        "ARIMA residual": arima_residual(df),
    }

    rows = []
    for name, scores in methods.items():
        m = evaluate(scores, labels)
        # Per-regime recall at the F1-optimal threshold — shows which detector
        # catches point vs sustained anomalies.
        predicted = scores >= m["threshold"]
        m["recall_point"] = (
            float(predicted[point_mask].mean()) if point_mask.any() else float("nan")
        )
        m["recall_contextual"] = (
            float(predicted[ctx_mask].mean()) if ctx_mask.any() else float("nan")
        )
        rows.append({"method": name, **m})
    table = pd.DataFrame(rows).sort_values("f1", ascending=False).reset_index(drop=True)
    return table
