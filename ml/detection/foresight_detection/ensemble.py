"""Detection ensemble: LSTM autoencoder (temporal) + IsolationForest (point).

Scores are combined on a robust rank-percentile scale so the two very different
score distributions can be blended without one dominating. Metrics are
standardized *per tenant* so anomalies are judged against each tenant's own
baseline, not a global one — essential in a multi-tenant platform where MRR
ranges from thousands to millions across tenants.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from foresight_detection.data import METRICS
from foresight_detection.lstm_autoencoder import (
    make_windows,
    reconstruction_error,
    train_autoencoder,
)


def _rank_percentile(x: np.ndarray) -> np.ndarray:
    """Map values to [0, 1] by rank — robust to the anomalies' own magnitude."""
    if len(x) <= 1:
        return np.zeros_like(x, dtype=float)
    order = np.argsort(np.argsort(x))
    return order / (len(x) - 1)


@dataclass
class EnsembleConfig:
    window: int = 7
    hidden_size: int = 32
    latent_size: int = 16
    epochs: int = 30
    lr: float = 1e-2
    contamination: float = 0.05
    lstm_weight: float = 0.5
    seed: int = 0


class DetectionEnsemble:
    """Fit-and-score anomaly detector over a labeled/unlabeled metric frame."""

    def __init__(self, config: EnsembleConfig | None = None) -> None:
        self.cfg = config or EnsembleConfig()

    def _standardize_per_tenant(self, df: pd.DataFrame) -> np.ndarray:
        z = np.empty((len(df), len(METRICS)), dtype=np.float32)
        for _, idx in df.groupby("tenant_id").groups.items():
            rows = df.loc[idx, METRICS].to_numpy(dtype=np.float32)
            mean = rows.mean(axis=0)
            std = rows.std(axis=0)
            std[std == 0] = 1.0
            z[df.index.get_indexer(idx)] = (rows - mean) / std
        return z

    def fit_score(self, df: pd.DataFrame) -> np.ndarray:
        """Return a per-row ensemble anomaly score. `df` must be sorted by
        (tenant_id, day)."""
        df = df.reset_index(drop=True)
        z = self._standardize_per_tenant(df)
        cfg = self.cfg

        # --- LSTM autoencoder: train globally on all tenants' windows ---
        all_windows: list[np.ndarray] = []
        per_tenant_slices: list[tuple[np.ndarray, int]] = []
        for _, idx in df.groupby("tenant_id").groups.items():
            positions = df.index.get_indexer(idx)
            series = z[positions]
            w = make_windows(series, cfg.window)
            per_tenant_slices.append((positions, len(w)))
            all_windows.append(w)

        stacked = np.concatenate(all_windows, axis=0)
        model = train_autoencoder(
            stacked,
            n_features=len(METRICS),
            hidden_size=cfg.hidden_size,
            latent_size=cfg.latent_size,
            epochs=cfg.epochs,
            lr=cfg.lr,
            seed=cfg.seed,
        )

        lstm_day = np.zeros(len(df), dtype=float)
        cursor = 0
        for positions, n_w in per_tenant_slices:
            err = reconstruction_error(model, stacked[cursor : cursor + n_w])
            cursor += n_w
            # Window ending at day t (t >= window-1) scores day t; backfill the
            # warm-up days with the first available error.
            day_scores = np.empty(len(positions), dtype=float)
            day_scores[cfg.window - 1 :] = err
            day_scores[: cfg.window - 1] = err[0] if len(err) else 0.0
            lstm_day[positions] = day_scores

        # --- IsolationForest: point outliers on standardized day features ---
        iso = IsolationForest(
            contamination=cfg.contamination, random_state=cfg.seed, n_estimators=200
        )
        iso.fit(z)
        # Higher = more anomalous.
        if_score = -iso.decision_function(z)

        # --- Robust rank-percentile blend ---
        ensemble = cfg.lstm_weight * _rank_percentile(lstm_day) + (
            1 - cfg.lstm_weight
        ) * _rank_percentile(if_score)
        return ensemble
