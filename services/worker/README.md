# Foresight — Detection Worker (M4)

The compute half of the backend. Reads `kpi_daily` from Postgres, runs the real
detection + classification + grounded agent, and upserts results into
`anomaly_log`. After it runs, the anomalies the API serves are the genuine output
of the pipeline — not a preloaded bundle.

```
kpi_daily → detect (ensemble) → classify → describe
          → retrieve → reason (Claude) → evaluate → anomaly_log
```

## Run it

The worker needs the pipeline packages installed in one environment:

```bash
# from repo root, into one venv:
pip install -e ml/detection -e ml/classification -e ml/anomaly -e agent[llm] \
            -e services/worker

DATABASE_URL=postgresql://foresight:foresight@localhost:5432/foresight \
  python -m foresight_worker.run --top-k 6 --epochs 25
```

Uses Claude when `ANTHROPIC_API_KEY` is set (loaded from `.env`), else the stub.

## What a live run actually produces (honest)

On the seeded KPI history, the worker's **detection correctly surfaces the true
anomaly days** for every tenant. But **classification frequently mislabels the
type** (e.g. a payment_failure day whose largest metric move is a checkout drop
gets tagged `seasonal_dip`), and most alerts come back `held_for_review` because
the classifier's confidence is low.

This is the M2 finding in production: **metrics under-determine anomaly type.**
The driver-derived description feeds a classifier that can only guess from the
numbers, and when the dominant movement isn't the type-defining one, it guesses
wrong — so the human-in-the-loop gate correctly withholds the alert. Detection is
strong; type attribution needs the richer context (recent deploys, pricing
changes) that M3's RAG is built to retrieve.

The curated `frontend/public/demo-data.json` bundle is the "verified" view
(hand-checked types + real explanations); this worker is the raw pipeline.
