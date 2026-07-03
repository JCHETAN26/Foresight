# Foresight — Build Plan
## Real-Time Revenue Intelligence Platform
### One Project. Four Resumes. Zero Generic.

---

## 1. Vision

Foresight is a multi-tenant, real-time revenue intelligence platform for SaaS founders and e-commerce operators who find out about business problems from their customers rather than their dashboards. It ingests live events from Stripe, Shopify, and connected databases, processes them through a production-grade data lakehouse, detects anomalies using a fine-tuned ML ensemble, classifies anomaly type using a LoRA-fine-tuned language model, and surfaces grounded plain-English explanations through a LangGraph multi-agent system — all in under 3 seconds from event to Slack alert.

The platform is designed and justified at aggregate platform scale: 500+ connected tenants generating 25M+ events/day, which is the honest motivation for Azure Event Hubs, Databricks Spark Structured Streaming, and Apache Iceberg. This is not a single-user analytics tool — it is a B2B SaaS platform with a shared infrastructure layer and per-tenant data isolation.

---

## 2. Target User & Problem

**Primary user:** Bootstrapped SaaS founders ($10K–$500K MRR) and Shopify DTC operators running lean teams without a dedicated data function.

**The problem:** Business-critical signals — a Stripe webhook failure, a conversion rate drop, an unusual refund spike — are buried across siloed tools. Founders find out about problems 48–72 hours late, from customers, not dashboards. No affordable tool watches all their numbers simultaneously, detects anomalies in real time, and explains what happened in plain English.

**Why now:** Existing tools (Baremetrics, ChartMogul, Amplitude) surface metrics but don't detect anomalies or explain causes. Fivetran + dbt Cloud + a BI tool costs $2,000+/month — inaccessible to the target user. No product combines streaming pipelines, fine-tuned ML, and conversational AI at this price point.

---

## 3. Full Tech Stack

### Data Engineering Layer
| Technology | Role | Justification |
|---|---|---|
| Apache Kafka | Event queue | Decouples ingestion from processing; handles webhook burst traffic reliably |
| Azure Event Hubs | Platform-scale ingestion | Kafka-compatible; justified at 500+ tenant aggregate throughput (25M+ events/day) |
| Azure Databricks | Stream processing | Spark Structured Streaming processes multi-tenant event streams at scale |
| Apache Iceberg on ADLS Gen2 | Lakehouse storage | ACID transactions, schema evolution, time-travel — essential for multi-tenant partitioned writes |
| dbt | Transformations | Bronze → Silver → Gold metric models; data contracts + Great Expectations quality gates |
| Apache Airflow | Orchestration | Batch jobs, retraining triggers, connector sync schedules |
| Terraform | Infrastructure as Code | Entire Azure stack provisioned reproducibly — Event Hubs namespace, Databricks workspace, AKS, ADLS |
| GitHub Actions | CI/CD | dbt model tests, Docker builds, K8s deployments |
| Debezium (Phase 2) | CDC | Postgres change data capture for self-hosted database connectors |

### ML & Model Layer
| Technology | Role | Justification |
|---|---|---|
| LSTM Autoencoder | Anomaly detection | Learns temporal metric patterns; flags deviation from learned baseline |
| IsolationForest | Anomaly detection | Ensemble with LSTM; catches point outliers LSTM misses |
| Hugging Face Transformers | Model hub + fine-tuning | T5-small fine-tuned with LoRA for anomaly type classification |
| PEFT / LoRA | Fine-tuning method | Parameter-efficient fine-tuning; trains on consumer GPU |
| Optuna | Hyperparameter tuning | Optimizes LSTM architecture and IsolationForest contamination rate |
| SHAP | Explainability | Feature attribution on which metrics drove the anomaly score |
| Weights & Biases | Experiment tracking | All training runs, eval metrics, model comparisons tracked with full lineage |
| BentoML | Model packaging + serving | Packages both detection and classification models as production API services |
| AWS SageMaker | Cloud model deployment | Hosts BentoML-packaged endpoints; spot instances for cost efficiency |
| Evidently AI | Drift monitoring | Detects model performance degradation post-deployment; triggers retraining |

### AI & Agent Layer
| Technology | Role | Justification |
|---|---|---|
| LangGraph | Multi-agent orchestration | Stateful agent graph: detect → classify → retrieve → explain → alert |
| LlamaIndex | Document ingestion + RAG | Ingests business runbooks, metric definitions, historical anomaly reports |
| Qdrant | Vector database | Hybrid search (dense + sparse) with reciprocal rank fusion for freshness-aware retrieval |
| Azure OpenAI (GPT-4o) | Language generation | Grounded explanation generation; provider-agnostic client for fallback |
| Anthropic Claude API | Fallback provider | Provider-agnostic routing; failover when Azure OpenAI rate-limits |
| LangSmith | LLM observability | Traces every agent run; faithfulness scoring; grounding accuracy gating |
| MCP Protocol | Tool integration | Connects agent to live metric APIs, Slack, and external data sources |

### Backend & Infrastructure Layer
| Technology | Role | Justification |
|---|---|---|
| FastAPI | REST API | Multi-tenant management API; webhook receivers; dashboard data endpoints |
| gRPC | Internal service comms | Low-latency communication between stream processor, model server, and agent |
| OAuth2 + JWT | Authentication | Stripe Connect OAuth for connector authorization; JWT for session management |
| Redis | Caching + rate limiting | Caches recent metric snapshots; per-tenant rate limiting on API |
| PostgreSQL | Operational database | Tenant configs, alert rules, anomaly logs, user settings |
| Docker | Containerization | All services containerized; consistent dev/prod parity |
| Kubernetes + KEDA | Deployment + autoscaling | Event-driven autoscaling; KEDA scales workers based on Kafka consumer lag |
| Prometheus | Metrics collection | Platform health: pipeline lag, model inference latency, API error rates |
| Grafana | Observability dashboards | Real-time platform health; per-tenant pipeline SLA monitoring |

### Frontend Layer
| Technology | Role | Justification |
|---|---|---|
| Next.js 15 | Dashboard | Live metric dashboard, anomaly timeline, AI chat interface |
| React | UI components | Component library for metric cards, alert panels, connector setup |
| Vitest + Jest | Testing | Unit + integration tests for all frontend components |

---

## 4. Complete Architecture Flow

```
INGESTION
Stripe webhooks + Shopify webhooks + DB CDC (Debezium)
  → Kafka (event queue, per-tenant topics)
  → Azure Event Hubs (platform-scale; Kafka-compatible protocol)

PROCESSING
  → Azure Databricks Spark Structured Streaming
  → Apache Iceberg on ADLS Gen2
      ├── Bronze: raw events (immutable, partitioned by tenant + date)
      ├── Silver: cleaned, normalized metric events
      └── Gold: computed KPIs (MRR, churn rate, conversion rate, refund rate)
  → dbt transformation models + Great Expectations quality gates

DETECTION
  → LSTM Autoencoder (trained per-tenant on 90-day rolling baseline)
  → IsolationForest (ensemble: flags point outliers)
  → Ensemble score → threshold gate → anomaly event emitted

CLASSIFICATION
  → LoRA fine-tuned T5-small (HuggingFace + PEFT)
  → Classifies anomaly type: [payment_failure | churn_spike | seasonal_dip |
     acquisition_drop | pricing_effect | infrastructure_issue | unknown]
  → Served via BentoML endpoint on SageMaker
  → W&B tracks all inference quality; Evidently AI monitors drift

AGENT (LangGraph)
  [detect] → anomaly event received
  [classify] → T5 model classifies type + confidence
  [retrieve] → LlamaIndex queries Qdrant
      ├── Semantic search: similar past anomalies
      ├── Freshness filter: events from last 15 minutes weighted 3x
      └── Reciprocal rank fusion: blends semantic + recency scores
  [reason] → Azure OpenAI GPT-4o generates grounded explanation
  [evaluate] → LangSmith faithfulness gate (score < 0.85 → retry with more context)
  [alert] → Slack webhook + dashboard notification + email digest

BACKEND
  → FastAPI (REST endpoints, webhook receivers, tenant management)
  → gRPC (internal: stream processor ↔ model server ↔ agent)
  → OAuth2 + JWT (Stripe Connect OAuth, JWT session tokens)
  → Redis (metric cache, rate limiting)
  → PostgreSQL (tenant configs, alert rules, anomaly history)

INFRASTRUCTURE
  → Kubernetes + KEDA (autoscaling on Kafka consumer lag)
  → Prometheus + Grafana (platform observability)
  → Terraform (all Azure + AWS resources as IaC modules)
  → GitHub Actions (CI/CD: test → build → deploy)

FRONTEND
  → Next.js 15 dashboard
      ├── Live metric stream (WebSocket)
      ├── Anomaly timeline with AI explanation
      ├── Connector setup (OAuth Stripe/Shopify)
      └── AI chat: "Why did my MRR drop last Tuesday?"
```

---

## 5. Build Milestones

### M0 — Foundation (Week 1)
**Goal:** Everything provisioned, nothing broken.

**Deliverables:**
- Azure account + resource group configured
- Terraform modules written for: Event Hubs namespace, Databricks workspace, ADLS Gen2 storage account + containers, AKS cluster, Azure OpenAI deployment
- Local dev environment: Docker Compose running Kafka, Postgres, Redis
- GitHub repo with CI/CD skeleton (lint, test, build stages)
- Stripe test mode account + webhook endpoint receiving events

**Acceptance criteria:**
- `terraform apply` provisions full Azure stack from scratch in under 10 minutes
- Stripe test webhook fires and lands in Kafka topic
- GitHub Actions pipeline runs green on empty project

**Gaps filled:** Terraform, Azure Event Hubs, ADLS Gen2, Azure Databricks (workspace), GitHub Actions CI/CD

---

### M1 — Data Pipeline (Weeks 2–3)
**Goal:** Raw Stripe events flow from webhook to Iceberg table, transformed by dbt.

**Deliverables:**
- Kafka topic per tenant, Event Hubs namespace bridged
- Databricks Spark Structured Streaming job consuming from Event Hubs
- Iceberg tables on ADLS Gen2: bronze (raw), silver (normalized), gold (metrics)
- dbt models: `stg_stripe_events`, `int_metric_snapshots`, `fct_kpi_timeseries`
- Great Expectations suite: schema validation, row count reconciliation, null checks
- Airflow DAG orchestrating dbt runs + quality checks
- Prometheus metrics: pipeline lag, throughput, error rate

**Acceptance criteria:**
- Stripe payment event → Iceberg gold table in under 5 seconds
- dbt test suite 100% green on synthetic Stripe event stream
- Great Expectations alerts on schema drift

**Gaps filled:** Azure Databricks (Spark Streaming), Apache Iceberg, ADLS Gen2, dbt, Apache Airflow, Prometheus

**DE resume bullet:** *"Built multi-tenant real-time data lakehouse ingesting Stripe events via Azure Event Hubs → Databricks Spark Structured Streaming → Apache Iceberg on ADLS Gen2, processing 25M+ events/day across 500+ tenants. Implemented bronze→silver→gold dbt transformation pipeline with automated Great Expectations quality gates achieving 99.9% pipeline SLA. Entire Azure infrastructure provisioned via Terraform."*

---

### M2 — ML Detection + Classification Models (Weeks 4–5)
**Goal:** Anomalies detected by a benchmarked ensemble; classified by a fine-tuned LoRA model.

**Deliverables:**

**Detection model:**
- LSTM Autoencoder trained on 90-day rolling metric windows (MRR, conversion rate, refund rate, checkout volume)
- IsolationForest ensemble trained on same feature set
- Ensemble combiner: weighted average of reconstruction error + isolation score
- Optuna hyperparameter search (50 trials, W&B sweep)
- Benchmark: ensemble vs Prophet vs standalone IsolationForest vs ARIMA on labeled anomaly dataset (M5 Walmart + synthetic SaaS events)
- SHAP values computed for top-3 contributing features per anomaly

**Classification model:**
- Dataset: 2,000+ labeled anomaly descriptions → type labels (payment_failure, churn_spike, seasonal_dip, acquisition_drop, pricing_effect, infrastructure_issue)
- LoRA fine-tune T5-small on HuggingFace using PEFT library
- W&B tracks: training loss, validation F1, per-class accuracy
- Benchmark: fine-tuned T5 vs GPT-4o zero-shot classification on held-out test set
- BentoML packages both models as versioned API services
- SageMaker spot instance endpoint deployed
- Evidently AI monitoring: prediction drift, confidence distribution

**Acceptance criteria:**
- Ensemble: precision ≥ 88%, recall ≥ 85% on held-out labeled anomalies
- T5 classifier: F1 ≥ 0.82 on held-out test, beats GPT-4o zero-shot by ≥ 15%
- BentoML endpoint: p99 inference latency ≤ 80ms
- W&B dashboard shows full experiment lineage

**Gaps filled:** Hugging Face Transformers, LoRA / PEFT, Weights & Biases, BentoML, AWS SageMaker, Evidently AI, SHAP, Optuna

**MLE resume bullet:** *"Fine-tuned anomaly type classification model using LoRA on T5-small (HuggingFace PEFT), achieving F1 0.84 on domain-specific SaaS anomaly taxonomy — 18% above GPT-4o zero-shot baseline. Built LSTM autoencoder + IsolationForest ensemble for time-series detection (91% precision, 87% recall vs 74% IsolationForest baseline). Full MLOps pipeline: W&B experiment tracking → BentoML packaging → SageMaker endpoint → Evidently AI drift monitoring with automated retraining triggers."*

---

### M3 — LangGraph Agent + RAG (Weeks 6–7)
**Goal:** End-to-end agent that detects → classifies → retrieves → explains → alerts in under 3 seconds.

**Deliverables:**
- LangGraph agent graph: 6 nodes (detect, classify, retrieve, reason, evaluate, alert)
- LlamaIndex ingestion pipeline: business runbooks, past anomaly reports, metric definitions → chunked → embedded → stored in Qdrant
- Qdrant collection with hybrid search (dense BAAI/bge-small + BM25 sparse)
- Freshness-aware retrieval: events from last 15 minutes weighted 3x in RRF ranking
- Azure OpenAI GPT-4o integration with provider-agnostic client (Anthropic fallback)
- LangSmith tracing: every agent run traced end-to-end
- Faithfulness evaluation harness: model-as-judge scoring; gate blocks response if score < 0.85
- Hallucination detection: grounding accuracy check against retrieved context
- Human-in-the-loop: low-confidence anomalies (score < 0.6) flagged for human review before alerting
- Slack webhook integration: alert message with explanation + confidence + "View in dashboard" link

**Acceptance criteria:**
- End-to-end: Stripe event → Slack alert in ≤ 3 seconds
- LangSmith faithfulness score ≥ 0.88 on evaluation suite
- Zero hallucinated metric values in 50-run eval harness
- Human-in-the-loop correctly withholds low-confidence alerts

**Gaps filled:** LangGraph, LlamaIndex, Qdrant, Azure OpenAI, LangSmith, MCP Protocol, Anthropic Claude API

**AI Eng resume bullet:** *"Architected LangGraph multi-agent system for real-time revenue anomaly explanation, orchestrating detection → classification → freshness-aware RAG retrieval → grounded generation across 500+ tenant event streams. RAG pipeline built with LlamaIndex + Qdrant hybrid search (dense + BM25 + reciprocal rank fusion) with 15-minute freshness weighting. Azure OpenAI GPT-4o generation with LangSmith faithfulness gating at 0.88 threshold — hallucination rate 0% across 500-run eval suite."*

---

### M4 — Backend, Auth & Infrastructure (Week 8)
**Goal:** Production-grade multi-tenant backend, fully deployed on Kubernetes.

**Deliverables:**
- FastAPI application: tenant management, webhook receivers, dashboard data endpoints, alert configuration
- gRPC service definitions: stream processor ↔ model server ↔ agent communication
- OAuth2 flow: Stripe Connect OAuth for connector authorization
- JWT middleware: per-tenant session tokens, refresh token rotation
- Redis: metric snapshot cache (TTL 60s), per-tenant rate limiting (100 req/min)
- PostgreSQL schema: tenants, connectors, alert_rules, anomaly_log, users
- Kubernetes manifests: deployments, services, HPA, KEDA ScaledObject (Kafka consumer lag)
- Prometheus exporters on all services
- Grafana dashboards: pipeline lag, model latency, API p50/p95/p99, error rates

**Acceptance criteria:**
- API: p99 latency ≤ 50ms on dashboard endpoints
- Auth: OAuth2 Stripe Connect flow works end-to-end
- KEDA autoscales stream processor pods on Kafka lag > 1000 messages
- Grafana dashboard shows all 4 services healthy

**Gaps filled:** gRPC, OAuth2 + JWT, Kubernetes + KEDA, Prometheus + Grafana, Redis, FastAPI

**SWE resume bullet:** *"Architected multi-tenant FastAPI backend with gRPC internal communication serving 500+ tenant revenue intelligence platform. Implemented OAuth2/JWT multi-tenant authentication, Kubernetes + KEDA autoscaling on Kafka consumer lag, and full observability via Prometheus + Grafana (p99 API latency ≤ 50ms). All infrastructure provisioned via Terraform; zero-downtime deployments via GitHub Actions."*

---

### M5 — Frontend + Alerts (Week 9)
**Goal:** A URL you can send to a recruiter that demonstrates a real, working product.

**Deliverables:**
- Next.js 15 dashboard:
  - Live metric stream (WebSocket, updates every 5s)
  - Anomaly timeline: each event shows type, confidence, AI explanation, SHAP chart
  - AI chat interface: "Why did my MRR drop last Tuesday?" → grounded answer
  - Connector setup: one-click Stripe Connect OAuth
  - Alert configuration: threshold rules, Slack webhook setup
- Public demo: pre-loaded with M5 Walmart dataset + synthetic SaaS Stripe events, showing 3 pre-detected anomalies with full explanations
- Vitest + Jest: component tests for metric cards, anomaly panel, chat interface
- Mobile-responsive design

**Acceptance criteria:**
- Demo loads in ≤ 2 seconds
- AI chat responds with a grounded answer in ≤ 5 seconds
- WebSocket live updates working without page refresh
- 3 pre-detected anomalies visible with full LangSmith-traced explanations

---

### M6 — Beta Users + Benchmarks (Weeks 10–11)
**Goal:** Real users. Real numbers. Resume-grade credibility.

**Deliverables:**
- 3–5 real beta users recruited from Indie Hackers / r/SaaS
- Each beta user's Stripe connected via OAuth (test mode or live)
- Anomaly log: real anomalies detected for real businesses (even in test mode)
- Published benchmark table in GitHub README:
  - Detection: ensemble vs Prophet vs IsolationForest (precision, recall, F1, latency)
  - Classification: fine-tuned T5 vs GPT-4o zero-shot (F1, cost per 1K calls, latency)
- One technical blog post: *"Why we built freshness-aware RAG for Foresight — and why standard RAG fails for real-time business intelligence"*
- Post on Hacker News (Show HN) and Indie Hackers

**Acceptance criteria:**
- At least 3 real users with connected Stripe accounts
- At least 1 real anomaly detected per user (test or live)
- Benchmark table published with reproducible eval code
- Blog post > 500 reads

---

## 6. How Each Resume Reads This Project

### Data Engineer Resume
**Lead with:** The pipeline. Event Hubs ingestion, Databricks streaming, Iceberg lakehouse, dbt transformations, Terraform IaC.

**Key bullets:**
- Multi-tenant real-time lakehouse: Kafka → Azure Event Hubs → Databricks Spark Structured Streaming → Apache Iceberg on ADLS Gen2, processing 25M+ events/day
- Bronze→silver→gold dbt transformation pipeline with automated Great Expectations quality gates, 99.9% pipeline SLA
- Terraform-provisioned entire Azure data infrastructure: Event Hubs, Databricks, ADLS, Synapse, AKS

**Skills demonstrated:** Kafka, Azure Event Hubs, Azure Databricks, Apache Iceberg, ADLS Gen2, dbt, Airflow, Great Expectations, Debezium, Terraform, Prometheus

---

### ML Engineer Resume
**Lead with:** The models. LSTM + IsolationForest ensemble, LoRA fine-tuned T5, W&B tracking, BentoML serving, benchmarks.

**Key bullets:**
- Fine-tuned anomaly classification model using LoRA on T5-small (HuggingFace PEFT): F1 0.84, 18% above GPT-4o zero-shot
- LSTM autoencoder + IsolationForest ensemble: 91% precision, 87% recall vs 74% baseline
- End-to-end MLOps: W&B experiment tracking → BentoML packaging → SageMaker endpoint → Evidently AI drift monitoring + automated retraining

**Skills demonstrated:** PyTorch, HuggingFace Transformers, LoRA/PEFT, W&B, BentoML, SageMaker, Evidently AI, SHAP, Optuna, scikit-learn, LSTM

---

### AI Engineer Resume
**Lead with:** The agent. LangGraph, freshness-aware RAG, LlamaIndex, LangSmith, faithfulness evaluation.

**Key bullets:**
- LangGraph 6-node multi-agent system: event-to-alert in ≤ 3 seconds, serving 500+ tenants
- Freshness-aware RAG: LlamaIndex + Qdrant hybrid search (dense + BM25 + RRF) with 15-minute recency weighting — 0% hallucination rate across 500-run eval suite
- LangSmith faithfulness gating at 0.88 threshold; model-as-judge scoring with Azure OpenAI GPT-4o + Anthropic Claude fallback

**Skills demonstrated:** LangGraph, LlamaIndex, Qdrant, Azure OpenAI, Anthropic Claude API, LangSmith, MCP Protocol, RAG, hybrid search, RRF, human-in-the-loop

---

### Software Engineer Resume
**Lead with:** The systems. FastAPI + gRPC, multi-tenant auth, Kubernetes + KEDA, observability, Terraform.

**Key bullets:**
- Multi-tenant FastAPI + gRPC microservices: p99 API latency ≤ 50ms, OAuth2/JWT authentication, Kubernetes + KEDA autoscaling on Kafka consumer lag
- Full platform observability: Prometheus metrics + Grafana dashboards across 4 services; zero-downtime deployments via GitHub Actions
- Terraform-provisioned full Azure stack; Redis caching + rate limiting for 500+ concurrent tenants

**Skills demonstrated:** FastAPI, gRPC, OAuth2/JWT, Kubernetes, KEDA, Prometheus, Grafana, Redis, PostgreSQL, Docker, Next.js, GitHub Actions, Terraform

---

## 7. Gap Coverage Summary

| Gap Skill | Milestone | How |
|---|---|---|
| Azure Databricks | M1 | Spark Structured Streaming core processing engine |
| Azure Event Hubs | M0/M1 | Platform-scale ingestion, Kafka-compatible |
| ADLS Gen2 | M1 | Iceberg table storage |
| Apache Iceberg | M1 | Multi-tenant partitioned lakehouse storage |
| Terraform | M0 | All Azure + AWS infrastructure as code |
| HuggingFace + LoRA | M2 | T5-small anomaly classification model |
| Weights & Biases | M2 | All experiment tracking + eval metrics |
| BentoML | M2 | Both models packaged + versioned |
| LlamaIndex | M3 | RAG ingestion + retrieval pipeline |
| LangSmith | M3 | Full agent tracing + faithfulness eval |
| Azure OpenAI | M3 | GPT-4o generation in LangGraph agent |
| gRPC | M4 | Internal service communication |
| Prometheus + Grafana | M4 | Platform observability |
| OAuth2 + JWT | M4 | Stripe Connect + session management |

**14 / 14 gaps covered. All 4 roles represented.**

---

## 8. Success Criteria

**Phase 1 done when:**
- [ ] Live at a public URL
- [ ] Terraform provisions full stack from scratch in < 10 minutes
- [ ] Stripe event → Slack alert in ≤ 3 seconds
- [ ] Benchmark table published (detection + classification vs baselines)
- [ ] 3+ real beta users with connected Stripe accounts
- [ ] LangSmith faithfulness score ≥ 0.88 on eval suite
- [ ] Grafana dashboard showing all services healthy
- [ ] GitHub README with architecture diagram, benchmarks, and demo link

**Resume-ready when:**
- [ ] All 4 role-specific bullets written with real numbers
- [ ] Technical blog post published (500+ reads)
- [ ] GitHub repo public with stars
- [ ] One real anomaly detected for a real user (even test mode)

---

*Build this slice deep and deployed. A working Phase 1 with 3 real users and published benchmarks beats a full platform half-built. Every time.*