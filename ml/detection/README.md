# Foresight — Anomaly Detection (M2)

An ensemble that flags anomalous tenant-days across four metrics (MRR,
conversion rate, refund rate, checkout volume), benchmarked against classical
baselines on a labeled synthetic SaaS dataset.

## Approach

| Component | Role |
|---|---|
| **LSTM autoencoder** (PyTorch) | Learns each tenant's normal *temporal* pattern; high reconstruction error = anomalous window. |
| **IsolationForest** (scikit-learn) | Catches *point* outliers the temporal model misses. |
| **Ensemble** | Blends both on a robust rank-percentile scale (`lstm_weight` tunable). |

Metrics are standardized **per tenant**, so anomalies are judged against each
tenant's own baseline — MRR ranging from thousands to millions across tenants
would otherwise swamp a global model.

- **Optuna** tunes `window`, `hidden_size`, `lstm_weight`, `contamination`
  (maximizing PR-AUC on a tenant-disjoint tune split).
- **Weights & Biases** tracks every trial (offline by default — no account
  needed; set `WANDB_MODE=online` to sync).
- **SHAP** (`shap_explain.py`) attributes each anomaly to its top-3 metrics —
  the explanation the agent surfaces in M3.

## Honest evaluation

Numbers are **measured on a tenant-disjoint holdout split**, never hard-coded.
Precision/recall/F1 are at the F1-optimal threshold; PR-AUC is the
threshold-independent summary. `recall_point` / `recall_contextual` break recall
down by anomaly regime. Regenerate with `python -m foresight_detection.train`.

| Method | Precision | Recall | F1 | PR-AUC | Recall (point) | Recall (contextual) |
|---|---|---|---|---|---|---|
| **Ensemble (LSTM+IForest)** | 0.354 | **0.657** | **0.460** | 0.482 | 0.892 | **0.57** |
| IsolationForest | 0.586 | 0.372 | 0.455 | 0.512 | 0.811 | 0.21 |
| ARIMA residual | 0.432 | 0.438 | 0.435 | 0.444 | **0.973** | 0.24 |
| Seasonal z-score | 0.662 | 0.314 | 0.426 | 0.425 | 0.811 | 0.13 |

### What the numbers actually say (read this, not the marketing)

- **The ensemble is the best-balanced detector (top F1 and recall) because it is
  the only one that catches sustained/contextual anomalies** — 57% recall vs
  13–24% for the point-only methods (2–4×). That is precisely the LSTM
  autoencoder earning its place; IsolationForest and ARIMA are near-blind to
  temporal pattern breaks.
- **On point anomalies alone, the classical baselines win** — ARIMA recalls 97%.
  An earlier point-only benchmark had IsolationForest and ARIMA *beating* the
  ensemble outright; the ensemble's value only appears once the eval includes
  the temporal anomalies it was built for.
- **Contextual anomaly detection is genuinely hard**: absolute precision is low
  (~0.35) and no method approaches the ">88% precision / >85% recall" figures
  that appear in early project notes. Those numbers are **not** supported by this
  measurement and should not be used on a résumé. The honest, defensible claim
  is the per-regime one above.

## Real-data benchmark: NAB

The synthetic benchmark above controls the anomaly regimes; this one uses real
data. **NAB** (Numenta Anomaly Benchmark) `realKnownCause` streams — NYC taxi
demand, machine temperature, CPU/EC2 metrics — with documented anomaly windows.
Point-wise precision/recall/F1 (F1-optimal threshold) + PR-AUC, averaged over 6
streams. Measured, not asserted:

| Method | Precision | Recall | F1 | PR-AUC |
|---|---|---|---|---|
| **IsolationForest** | 0.251 | 0.654 | **0.324** | **0.292** |
| Ensemble (LSTM+IForest) | 0.210 | 0.680 | 0.278 | 0.232 |
| ARIMA residual | 0.135 | 0.866 | 0.221 | 0.128 |
| Seasonal z-score | 0.129 | 0.601 | 0.189 | 0.114 |

### What the real numbers say

- **On real NAB data, plain IsolationForest beats the LSTM ensemble** (F1 0.32 vs
  0.28, PR-AUC 0.29 vs 0.23). This is *consistent* with the synthetic finding:
  the LSTM earns its place only on sustained/contextual anomalies, and NAB's
  `realKnownCause` anomalies are mostly point/collective spikes on univariate
  streams — IsolationForest's home turf. The honest conclusion holds across both
  datasets: **ship IsolationForest as the core; the LSTM is a contextual-anomaly
  specialist, not a universal win.**
- **Absolute numbers are low (F1 ~0.3)** because this is strict *point-wise*
  scoring against sparse anomaly windows — deliberately conservative, and **not**
  NAB's own lenient application-profile score. PR-AUC is the fair comparison.

Regenerate: `python -m foresight_detection.nab_benchmark --epochs 20`
(downloads NAB into `outputs/nab/`, writes `outputs/nab_benchmark.csv`).

## Run it

```bash
cd ml/detection
python -m venv .venv && source .venv/bin/activate
pip install -e ".[train,dev]"
pytest -q                              # fast suite (trains small models)
python -m foresight_detection.train --trials 15 --epochs 30
```
