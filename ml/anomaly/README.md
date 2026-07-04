# Foresight — Anomaly Intelligence (M1 ↔ M2 integration)

Wires the data pipeline to the models: **gold KPI history in → typed, described
anomaly records out.**

```
gold KPIs (fct_kpi_timeseries)
   │  gold_adapter        map schema → {mrr, conversion_rate, refund_rate, checkout_volume}
   ▼
detection ensemble        per-tenant anomaly score  (M2)
   │  threshold
   ▼
attribution               per-metric deviation (which metrics moved, how far)
   │
   ▼  describe            natural-language summary of the movement
   ▼  classify            anomaly type + confidence  (M2 TF-IDF)
   ▼
AnomalyRecord             tenant, date, score, type, confidence, drivers, description
```

The record is the contract the **M3 agent** consumes to generate a grounded
explanation and fire the Slack alert.

## It runs on real gold

`gold_adapter.load_gold_from_duckdb(...)` reads the actual dbt-built
`fct_kpi_timeseries` and maps it to the detector's feature schema
(`checkout_volume` = completed + expired; `metric_date` → per-tenant `day`;
null metrics → 0). Verified against the real DuckDB gold table.

Detection needs ~90 days of per-tenant history to be meaningful, so the demo
seed (a few rows) is too small to *detect* on — the CLI's `--synthetic` mode
runs the full flow on realistic KPI history, and production runs against the
Databricks gold table.

## Honest limitation (and why M3 exists)

Descriptions are built from **metric movements only**, so the classifier can
distinguish types that show up in the numbers (refund spike → `payment_failure`,
conversion+volume drop → `acquisition_drop`) but **cannot** separate types that
depend on external cause context: a 93% checkout drop looks identical whether
it's an outage (`infrastructure_issue`), a holiday (`seasonal_dip`), or a
marketing collapse (`acquisition_drop`). The confidences (~35–55%) honestly
reflect that ambiguity.

**Metrics under-determine anomaly type.** Resolving it needs retrieved context
(recent deploys, price changes, the calendar) — which is exactly the job of the
M3 agent's freshness-aware RAG. This layer produces the type *prior*; the agent
refines it.

## Run it

```bash
# install the sibling model packages first
pip install -e ../detection -e ../classification -e ".[dev]"

pytest -q
python -m foresight_anomaly.run --synthetic --threshold 0.97 --limit 6
python -m foresight_anomaly.run --duckdb ../../pipelines/dbt/foresight/target/foresight.duckdb
```
