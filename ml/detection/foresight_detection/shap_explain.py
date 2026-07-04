"""SHAP feature attribution for detected anomalies.

Answers "which metrics drove this anomaly score?" — the explanation the agent
(M3) surfaces alongside each alert. Uses a KernelExplainer over the
IsolationForest anomaly score (works for the non-tree IF ensemble).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from foresight_detection.data import METRICS


def top_contributing_metrics(
    df: pd.DataFrame, row_indices: list[int], *, k: int = 3, seed: int = 0
) -> list[list[tuple[str, float]]]:
    """Return the top-k (metric, shap_value) pairs for each requested row.

    `df` must be sorted by (tenant_id, day); `row_indices` are positional.
    """
    import shap

    df = df.sort_values(["tenant_id", "day"]).reset_index(drop=True)

    z = np.empty((len(df), len(METRICS)), dtype=float)
    for _, idx in df.groupby("tenant_id").groups.items():
        rows = df.loc[idx, METRICS].to_numpy(dtype=float)
        mean, std = rows.mean(axis=0), rows.std(axis=0)
        std[std == 0] = 1.0
        z[df.index.get_indexer(idx)] = (rows - mean) / std

    iso = IsolationForest(contamination=0.05, random_state=seed, n_estimators=200)
    iso.fit(z)

    background = shap.sample(z, 50, random_state=seed)
    explainer = shap.KernelExplainer(lambda x: -iso.decision_function(x), background)

    targets = z[row_indices]
    shap_values = explainer.shap_values(targets, nsamples=100, silent=True)

    results: list[list[tuple[str, float]]] = []
    for sv in np.atleast_2d(shap_values):
        ranked = sorted(zip(METRICS, sv, strict=False), key=lambda p: abs(p[1]), reverse=True)
        results.append([(m, float(v)) for m, v in ranked[:k]])
    return results
