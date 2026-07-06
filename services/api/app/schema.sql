-- Foresight operational store (M4).

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id  TEXT PRIMARY KEY,
    name       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-tenant, per-day KPIs (the live equivalent of the gold fct_kpi_timeseries).
CREATE TABLE IF NOT EXISTS kpi_daily (
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    metric_date     DATE NOT NULL,
    mrr             DOUBLE PRECISION NOT NULL,
    conversion_rate DOUBLE PRECISION NOT NULL,
    refund_rate     DOUBLE PRECISION NOT NULL,
    checkout_volume DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (tenant_id, metric_date)
);

-- Detected anomalies with their grounded explanation (the agent's output).
CREATE TABLE IF NOT EXISTS anomaly_log (
    id                BIGSERIAL PRIMARY KEY,
    tenant_id         TEXT NOT NULL REFERENCES tenants(tenant_id),
    metric_date       DATE NOT NULL,
    anomaly_type      TEXT NOT NULL,
    anomaly_score     DOUBLE PRECISION NOT NULL,
    type_confidence   DOUBLE PRECISION NOT NULL,
    top_contributors  JSONB NOT NULL DEFAULT '[]',
    metrics           JSONB NOT NULL DEFAULT '{}',
    explanation       TEXT NOT NULL DEFAULT '',
    faithfulness      DOUBLE PRECISION NOT NULL DEFAULT 0,
    sources           JSONB NOT NULL DEFAULT '[]',
    status            TEXT NOT NULL DEFAULT 'ready',
    detected_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, metric_date, anomaly_type)
);

CREATE INDEX IF NOT EXISTS idx_anomaly_score ON anomaly_log (anomaly_score DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_tenant_date ON kpi_daily (tenant_id, metric_date);
