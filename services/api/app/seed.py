"""Seed the operational store from the real anomaly bundle.

Loads the agent-generated anomalies (real Claude explanations) into anomaly_log,
and synthesizes a realistic ~120-day KPI history per tenant so the dashboard has
trend context and the live detector has a baseline. Idempotent.

    python -m app.seed --bundle ../../frontend/public/demo-data.json
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg

from app.config import settings

HISTORY_DAYS = 120


def _baseline(anomaly: dict) -> dict[str, float]:
    """A plausible 'normal' baseline for a tenant, given its anomalous day."""
    m = anomaly["metrics"]
    return {
        "mrr": max(m["mrr"], 1000.0),
        "conversion_rate": 0.30,
        "refund_rate": 0.025,
        "checkout_volume": max(m["checkout_volume"], 200.0) * 1.6,
    }


def _history(anomaly: dict, rng: random.Random) -> list[tuple]:
    tenant = anomaly["tenant_id"]
    end = datetime.strptime(anomaly["metric_date"], "%Y-%m-%d").date()
    base = _baseline(anomaly)
    rows = []
    for i in range(HISTORY_DAYS):
        d: date = end - timedelta(days=HISTORY_DAYS - 1 - i)
        weekend = d.weekday() >= 5
        if d == end:
            m = anomaly["metrics"]
            row = (
                tenant, d, m["mrr"], m["conversion_rate"], m["refund_rate"], m["checkout_volume"],
            )
        else:
            growth = 1 + 0.0008 * i
            conv = base["conversion_rate"] * (0.9 if weekend else 1.0) * rng.uniform(0.95, 1.05)
            vol = base["checkout_volume"] * (0.75 if weekend else 1.0) * rng.uniform(0.9, 1.1)
            row = (
                tenant,
                d,
                round(base["mrr"] * growth * rng.uniform(0.99, 1.01), 2),
                round(conv, 4),
                round(base["refund_rate"] * rng.uniform(0.7, 1.3), 4),
                round(vol, 1),
            )
        rows.append(row)
    return rows


def seed(bundle_path: str, dsn: str) -> None:
    bundle = json.loads(Path(bundle_path).read_text())
    anomalies = bundle["anomalies"]
    rng = random.Random(7)

    with psycopg.connect(dsn) as conn:
        conn.execute((Path(__file__).parent / "schema.sql").read_text())
        for a in anomalies:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name) VALUES (%s, %s) "
                "ON CONFLICT (tenant_id) DO NOTHING",
                (a["tenant_id"], a["tenant_id"].replace("acct_", "Tenant ")),
            )
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO kpi_daily
                        (tenant_id, metric_date, mrr, conversion_rate, refund_rate, checkout_volume)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tenant_id, metric_date) DO UPDATE SET
                        mrr = EXCLUDED.mrr, conversion_rate = EXCLUDED.conversion_rate,
                        refund_rate = EXCLUDED.refund_rate,
                        checkout_volume = EXCLUDED.checkout_volume
                    """,
                    _history(a, rng),
                )
            conn.execute(
                """
                INSERT INTO anomaly_log
                    (tenant_id, metric_date, anomaly_type, anomaly_score, type_confidence,
                     top_contributors, metrics, explanation, faithfulness, sources, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, metric_date, anomaly_type) DO UPDATE SET
                    explanation = EXCLUDED.explanation, faithfulness = EXCLUDED.faithfulness,
                    status = EXCLUDED.status
                """,
                (
                    a["tenant_id"], a["metric_date"], a["anomaly_type"], a["anomaly_score"],
                    a["type_confidence"], json.dumps(a["top_contributors"]),
                    json.dumps(a["metrics"]), a["explanation"], a["faithfulness"],
                    json.dumps(a["sources"]), a["status"],
                ),
            )
        conn.commit()
    print(f"seeded {len(anomalies)} anomalies + {HISTORY_DAYS}d KPI history per tenant")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="../../frontend/public/demo-data.json")
    parser.add_argument("--dsn", default=settings.database_url)
    args = parser.parse_args(argv)
    seed(args.bundle, args.dsn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
