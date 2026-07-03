# Foresight

Real-time revenue intelligence for SaaS founders and e-commerce operators.
Ingests live Stripe/Shopify events, detects metric anomalies with an ML
ensemble, classifies the anomaly type with a fine-tuned model, and delivers a
grounded plain-English explanation to Slack — in under 3 seconds from event to
alert.

See [`build-plan.md`](build-plan.md) for the full architecture and milestones.

## Build status

| Milestone | Status |
|---|---|
| **M0 — Foundation** | 🟡 In progress |
| M1 — Data Pipeline | ⚪ Not started |
| M2 — ML Models | ⚪ Not started |
| M3 — LangGraph Agent | ⚪ Not started |
| M4 — Backend + Auth | ⚪ Not started |
| M5 — Frontend | ⚪ Not started |
| M6 — Beta + Benchmarks | ⚪ Not started |

## Repository layout

```
.
├── docker-compose.yml        # local stack: Kafka, Postgres, Redis, ingestion
├── services/
│   └── ingestion/            # FastAPI: Stripe webhook → Kafka (per-tenant topics)
├── infra/terraform/          # Azure IaC: Event Hubs, Databricks, ADLS, AKS, OpenAI
└── .github/workflows/ci.yml  # lint · type-check · test · terraform validate · docker build
```

## Local development

Prerequisites: Docker, Python 3.11+.

```bash
cp .env.example .env          # then set STRIPE_WEBHOOK_SECRET
docker compose up -d          # Kafka (:9092), Postgres (:5432), Redis (:6379),
                              # Kafka UI (:8080), ingestion (:8000)
```

Verify the ingestion service:

```bash
curl localhost:8000/health
```

### Wiring up Stripe test webhooks

Use the Stripe CLI to forward test events to the local receiver:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
# copy the printed whsec_... into .env as STRIPE_WEBHOOK_SECRET, then:
stripe trigger payment_intent.succeeded
```

The event lands on the Kafka topic `stripe.events.<tenant_id>` (or
`stripe.events.unknown` for platform events). Inspect it in the Kafka UI at
<http://localhost:8080>.

### Running the ingestion tests

```bash
cd services/ingestion
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && mypy app && pytest -q
```

## Infrastructure

```bash
cd infra/terraform
terraform init
terraform apply    # provisions the full Azure stack
```

> Azure OpenAI (`modules/openai`) requires an approved subscription. Request
> access early — it is not instant and is a dependency for M3.
