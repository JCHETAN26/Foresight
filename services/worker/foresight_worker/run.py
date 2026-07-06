"""Detection worker: KPI store → real detection + agent → anomaly_log.

    python -m foresight_worker.run --dsn postgresql://... --top-k 6

Uses Claude when ANTHROPIC_API_KEY is set (loaded from .env), else the stub.
"""

from __future__ import annotations

import argparse
import json
import os

import psycopg
from foresight_agent.graph import build_graph
from foresight_agent.knowledge import KNOWLEDGE
from foresight_agent.llm import ClaudeGenerator, StubGenerator
from foresight_agent.retrieval import HybridRetriever
from foresight_agent.run import _load_dotenv
from foresight_anomaly.pipeline import AnomalyPipeline
from foresight_detection.ensemble import EnsembleConfig

from foresight_worker.features import build_features

_KPI_QUERY = (
    "SELECT tenant_id, metric_date, mrr, conversion_rate, refund_rate, checkout_volume "
    "FROM kpi_daily ORDER BY tenant_id, metric_date"
)

_UPSERT = """
INSERT INTO anomaly_log
    (tenant_id, metric_date, anomaly_type, anomaly_score, type_confidence,
     top_contributors, metrics, explanation, faithfulness, sources, status)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (tenant_id, metric_date, anomaly_type) DO UPDATE SET
    anomaly_score = EXCLUDED.anomaly_score, type_confidence = EXCLUDED.type_confidence,
    top_contributors = EXCLUDED.top_contributors, metrics = EXCLUDED.metrics,
    explanation = EXCLUDED.explanation, faithfulness = EXCLUDED.faithfulness,
    sources = EXCLUDED.sources, status = EXCLUDED.status, detected_at = now()
"""


def run(dsn: str, *, threshold: float, top_k: int, epochs: int) -> int:
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(_KPI_QUERY).fetchall()
    if not rows:
        print("no KPI history in the store — nothing to detect")
        return 0

    features = build_features(rows)
    records = AnomalyPipeline(
        detection_config=EnsembleConfig(epochs=epochs), threshold=threshold
    ).run(features)[:top_k]

    generator = ClaudeGenerator() if os.getenv("ANTHROPIC_API_KEY") else StubGenerator()
    app = build_graph(HybridRetriever(KNOWLEDGE), generator)

    with psycopg.connect(dsn) as conn:
        for rec in records:
            final = app.invoke({"anomaly": rec.to_dict()})
            alert = final["alert"]
            conn.execute(
                _UPSERT,
                (
                    rec.tenant_id, rec.metric_date, rec.anomaly_type, rec.anomaly_score,
                    rec.type_confidence, json.dumps(rec.top_contributors),
                    json.dumps(rec.metrics), alert["explanation"],
                    round(final["faithfulness"], 3),
                    json.dumps([d["id"] for d in final["retrieved"]]),
                    alert["status"],
                ),
            )
        conn.commit()

    kind = "Claude" if os.getenv("ANTHROPIC_API_KEY") else "stub"
    print(f"detected + explained {len(records)} anomalies ({kind}) -> anomaly_log")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--epochs", type=int, default=25)
    args = parser.parse_args(argv)
    _load_dotenv()
    return run(args.dsn, threshold=args.threshold, top_k=args.top_k, epochs=args.epochs)


if __name__ == "__main__":
    raise SystemExit(main())
