"""Numenta Anomaly Benchmark (NAB) loader — real labeled time series.

Downloads a subset of NAB's `realKnownCause` streams (NYC taxi demand, machine
temperature, CPU/EC2 metrics — real-world data with documented anomaly causes)
plus the combined-window labels, and marks each timestamp anomalous if it falls
inside a labeled anomaly window. Cached under outputs/nab/.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

BASE = "https://raw.githubusercontent.com/numenta/NAB/master"

# Real-world, known-cause streams (univariate: timestamp, value).
NAB_FILES = [
    "realKnownCause/nyc_taxi.csv",
    "realKnownCause/machine_temperature_system_failure.csv",
    "realKnownCause/ambient_temperature_system_failure.csv",
    "realKnownCause/cpu_utilization_asg_misconfiguration.csv",
    "realKnownCause/ec2_request_latency_system_failure.csv",
    "realKnownCause/rogue_agent_key_hold.csv",
]


def _download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 — fixed NAB host
        dest.write_bytes(resp.read())


def ensure_downloaded(cache_dir: str = "outputs/nab") -> Path:
    """Fetch the NAB data files + labels into the cache; return the cache path."""
    cache = Path(cache_dir)
    _download(f"{BASE}/labels/combined_windows.json", cache / "combined_windows.json")
    for name in NAB_FILES:
        _download(f"{BASE}/data/{name}", cache / name)
    return cache


def load_series(name: str, cache_dir: str = "outputs/nab") -> tuple[np.ndarray, np.ndarray]:
    """Return (values, is_anomaly) for one NAB file, labelling by anomaly window."""
    cache = Path(cache_dir)
    df = pd.read_csv(cache / name, parse_dates=["timestamp"])
    windows = json.loads((cache / "combined_windows.json").read_text())[name]

    is_anomaly = np.zeros(len(df), dtype=int)
    ts = df["timestamp"]
    for start, end in windows:
        mask = (ts >= pd.Timestamp(start)) & (ts <= pd.Timestamp(end))
        is_anomaly[mask.to_numpy()] = 1

    return df["value"].to_numpy(dtype=float), is_anomaly
