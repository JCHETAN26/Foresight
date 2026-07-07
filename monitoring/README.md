# Foresight — Observability

Prometheus + Grafana over the platform, plus Redis for API rate limiting and
response caching.

## What's instrumented

- **API** (`services/api`) — Prometheus middleware records request count, in-flight
  gauge, and a latency histogram labelled by method + **route template** (not the
  raw path, so `/kpis/{tenant_id}` is one series). Plus cache hit/miss and
  rate-limit counters. Exposed at `/metrics`.
- **Ingestion** (`services/ingestion`) — events received/published, publish errors,
  publish-latency histogram (from M1). Also `/metrics`.

## Redis (`services/api`)

- **Rate limiting** — fixed-window per client (`RATE_LIMIT_PER_MIN`, default 100),
  returns 429 over the limit.
- **Response cache** — `/anomalies` cached with a TTL (`CACHE_TTL_SECONDS`,
  default 60). Both degrade to no-ops when `REDIS_URL` is unset.

## Grafana dashboard

`monitoring/grafana/dashboards/foresight.json` (auto-provisioned) — API request
rate, p50/p95/p99 latency, 5xx error rate, rate-limited req/s, cache hit ratio,
and ingestion throughput. Datasource + dashboard are provisioned from
`monitoring/grafana/provisioning/`.

## Run it

```bash
docker compose up -d postgres redis kafka ingestion api prometheus grafana
```

- Prometheus: <http://localhost:9090> (scrapes `api:8001` and `ingestion:8000`)
- Grafana: <http://localhost:3001> (anonymous admin; dashboard "Foresight —
  Platform Observability")

Generate traffic against the API, then watch the panels populate.
