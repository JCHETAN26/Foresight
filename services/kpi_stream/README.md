# Foresight — KPI Stream (M4)

The last pipeline link: consumes Stripe event envelopes from Kafka (produced by
the ingestion service) and computes the per-tenant, per-day KPIs the detector
watches — MRR, conversion rate, refund rate, checkout volume — into Postgres
`kpi_daily`. This is the live equivalent of the dbt bronze→gold transformation.

```
Stripe webhook → ingestion → Kafka (stripe.events.*)
   → kpi-stream → kpi_daily → detection worker → anomaly_log → API → dashboard
```

## Cross-validated against dbt

The KPI math (`kpi.py`) is a pure function, unit-tested against the **exact same
values the dbt gold model asserts** (`assert_alpha_known_kpis.sql`): MRR
150→200→150 as subscriptions churn, refund_rate 0.4, conversion 0.67/0.5/1.0. If
the streaming path and the batch path ever diverge, CI fails. That's the guard
against two implementations of "what is MRR" drifting apart.

## Run it

```bash
cd services/kpi_stream
pip install -e ".[dev]"
pytest -q                     # KPI math (no infra needed)

# live: needs Kafka + Postgres (docker compose up kafka postgres kpi-stream)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
DATABASE_URL=postgresql://foresight:foresight@localhost:5432/foresight \
  python -m foresight_kpi
```

## Real Stripe end to end

With a Stripe test key + `stripe listen --forward-to localhost:8000/webhooks/stripe`,
a real `stripe trigger payment_intent.succeeded` (or invoice/subscription events)
flows: Stripe → ingestion → Kafka → this consumer → `kpi_daily`. Then the
detection worker turns accumulated KPI history into explained anomalies. Note:
real subscription MRR needs `items[].price.unit_amount` extraction upstream (this
reads a normalized `amount`).
