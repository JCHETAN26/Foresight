"""Synthetic labeled SaaS metric dataset for the detection benchmark.

Generates per-tenant daily time series for the four metrics the detector
watches — MRR, conversion rate, refund rate, checkout volume — with realistic
trend + weekly seasonality + noise, then injects labeled anomalies of known
types. Deterministic given a seed, so the benchmark is reproducible.

The labels (`is_anomaly`, `anomaly_type`) are used to *evaluate* the otherwise
unsupervised detector; `anomaly_type` also feeds the M2 classification model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

METRICS = ["mrr", "conversion_rate", "refund_rate", "checkout_volume"]

ANOMALY_TYPES = [
    "payment_failure",
    "churn_spike",
    "seasonal_dip",
    "acquisition_drop",
    "pricing_effect",
    "infrastructure_issue",
]


@dataclass(frozen=True)
class DatasetConfig:
    n_tenants: int = 24
    n_days: int = 160
    anomaly_rate: float = 0.04  # fraction of tenant-days that are POINT anomalies
    contextual_runs: int = 2  # sustained (temporal) anomalies per tenant
    contextual_len: tuple[int, int] = (5, 9)  # min/max length of a contextual run
    seed: int = 7


def _baseline_series(rng: np.random.Generator, n_days: int) -> dict[str, np.ndarray]:
    """Normal (anomaly-free) metric series for one tenant."""
    t = np.arange(n_days)
    dow = t % 7
    weekend = np.isin(dow, [5, 6]).astype(float)

    # MRR: steady growth with mild noise.
    mrr0 = rng.uniform(8_000, 60_000)
    growth = rng.uniform(20, 200)
    mrr = mrr0 + growth * t + rng.normal(0, mrr0 * 0.01, n_days)

    # Conversion: ~0.25–0.4, lower on weekends, small noise.
    conv_base = rng.uniform(0.25, 0.40)
    conversion = conv_base - 0.03 * weekend + rng.normal(0, 0.015, n_days)

    # Refund rate: low ~2–4% with noise.
    refund = rng.uniform(0.02, 0.04) + rng.normal(0, 0.004, n_days)

    # Checkout volume: weekly seasonality, lower on weekends.
    vol_base = rng.uniform(300, 1500)
    checkout = vol_base * (1 - 0.25 * weekend) + rng.normal(0, vol_base * 0.05, n_days)

    return {
        "mrr": np.clip(mrr, 1.0, None),
        "conversion_rate": np.clip(conversion, 0.01, 0.95),
        "refund_rate": np.clip(refund, 0.0, 0.5),
        "checkout_volume": np.clip(checkout, 1.0, None),
    }


def _inject(
    rng: np.random.Generator,
    series: dict[str, np.ndarray],
    day: int,
    atype: str,
) -> None:
    """Apply a typed anomaly in place on the given day."""
    if atype == "payment_failure":
        series["refund_rate"][day] *= rng.uniform(4, 7)
        series["mrr"][day] *= rng.uniform(0.85, 0.93)
    elif atype == "churn_spike":
        series["mrr"][day] *= rng.uniform(0.6, 0.78)
    elif atype == "seasonal_dip":
        series["checkout_volume"][day] *= rng.uniform(0.4, 0.6)
    elif atype == "acquisition_drop":
        series["checkout_volume"][day] *= rng.uniform(0.45, 0.65)
        series["conversion_rate"][day] *= rng.uniform(0.55, 0.7)
    elif atype == "pricing_effect":
        series["mrr"][day] *= rng.uniform(1.15, 1.35)
        series["conversion_rate"][day] *= rng.uniform(0.8, 0.9)
    elif atype == "infrastructure_issue":
        series["checkout_volume"][day] *= rng.uniform(0.05, 0.2)
        series["conversion_rate"][day] *= rng.uniform(0.3, 0.5)


def _inject_contextual(
    rng: np.random.Generator, series: dict[str, np.ndarray], start: int, length: int
) -> str:
    """Apply a sustained, temporally-coherent anomaly over [start, start+length).

    Each day's deviation is modest (often within point-noise), but the sustained
    pattern break is what a temporal model is meant to catch.
    """
    end = start + length
    kind = rng.choice(["churn_creep", "conversion_erosion", "sustained_outage"])
    if kind == "churn_creep":
        # Cumulative MRR decline across the run.
        for k in range(length):
            series["mrr"][start + k] *= 1 - 0.035 * (k + 1)
        return "churn_spike"
    if kind == "conversion_erosion":
        series["conversion_rate"][start:end] *= rng.uniform(0.78, 0.88)
        return "acquisition_drop"
    # sustained_outage
    series["checkout_volume"][start:end] *= rng.uniform(0.55, 0.72)
    return "infrastructure_issue"


def generate(config: DatasetConfig | None = None) -> pd.DataFrame:
    """Generate the labeled multi-tenant dataset as a tidy DataFrame.

    Contains both *point* anomalies (single-day spikes/drops — IsolationForest /
    ARIMA territory) and *contextual* anomalies (sustained pattern shifts — the
    LSTM autoencoder's territory), each labeled in the `regime` column so the
    benchmark can report per-regime performance.
    """
    cfg = config or DatasetConfig()
    rng = np.random.default_rng(cfg.seed)
    frames: list[pd.DataFrame] = []

    for ti in range(cfg.n_tenants):
        tenant = f"acct_{ti:03d}"
        series = _baseline_series(rng, cfg.n_days)

        is_anom = np.zeros(cfg.n_days, dtype=int)
        atypes: list[str | None] = [None] * cfg.n_days
        regime: list[str] = [""] * cfg.n_days

        # Point anomalies, away from the 14-day warm-up.
        n_anom = max(1, int(cfg.n_days * cfg.anomaly_rate))
        for day in rng.choice(np.arange(14, cfg.n_days), size=n_anom, replace=False):
            atype = str(rng.choice(ANOMALY_TYPES))
            _inject(rng, series, int(day), atype)
            is_anom[day] = 1
            atypes[day] = atype
            regime[day] = "point"

        # Contextual (sustained) anomalies.
        for _ in range(cfg.contextual_runs):
            length = int(rng.integers(cfg.contextual_len[0], cfg.contextual_len[1] + 1))
            start = int(rng.integers(14, cfg.n_days - length))
            atype = _inject_contextual(rng, series, start, length)
            for d in range(start, start + length):
                is_anom[d] = 1
                atypes[d] = atype
                regime[d] = "contextual"

        df = pd.DataFrame(series)
        df.insert(0, "day", np.arange(cfg.n_days))
        df.insert(0, "tenant_id", tenant)
        df["is_anomaly"] = is_anom
        df["anomaly_type"] = atypes
        df["regime"] = regime
        frames.append(df)

    return pd.concat(frames, ignore_index=True)
