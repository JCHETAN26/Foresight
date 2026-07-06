# Foresight — API (M4)

FastAPI backend that stores the operational data and serves it to the dashboard.
This turns the pipeline from a set of scripts into one running application:
**Postgres → FastAPI → Next.js**.

## Data model (`app/schema.sql`)

- `tenants` — connected accounts.
- `kpi_daily` — per-tenant, per-day KPIs (the live equivalent of the gold
  `fct_kpi_timeseries`).
- `anomaly_log` — detected anomalies with the agent's grounded explanation,
  faithfulness, and alert status.

## Endpoints

| Route | Returns |
|---|---|
| `GET /health` | liveness |
| `GET /anomalies?limit=` | anomalies (highest score first) — what the dashboard renders |
| `GET /kpis/{tenant_id}?days=` | a tenant's KPI time series |
| `GET /tenants` | connected tenants |

CORS is restricted to `FRONTEND_ORIGINS`.

## Run it

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export DATABASE_URL=postgresql://foresight:foresight@localhost:5432/foresight
python -m app.seed --bundle ../../frontend/public/demo-data.json   # load real anomalies + KPI history
uvicorn app.main:app --port 8001
```

Point the dashboard at it with `NEXT_PUBLIC_API_URL=http://localhost:8001`
(`frontend/.env.local`); the timeline header switches to "live from the API".

Tests run against a real Postgres (`DATABASE_URL`) — a service container in CI:

```bash
DATABASE_URL=... pytest -q
```

## Seeded data is real (mostly)

The seed loads the **real Claude anomaly explanations** from the demo bundle into
`anomaly_log`, and synthesizes a realistic ~120-day KPI history per tenant so the
detector has a baseline and the dashboard has trend context. The live Stripe →
KPI → detection path (real events feeding this store) is the next piece and needs
a Stripe test key.
