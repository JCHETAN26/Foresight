"""Generate the frontend demo bundle: representative anomalies → real Claude
explanations → JSON the dashboard loads at build time.

Records mirror the shape `ml/anomaly` produces in the running pipeline; the
explanations are real agent output (live Claude when ANTHROPIC_API_KEY is set,
else the deterministic stub). Precomputing the bundle lets the demo page load
instantly with no API calls.

    python -m foresight_agent.gen_demo_bundle --out ../frontend/public/demo-data.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from foresight_agent.graph import build_graph
from foresight_agent.knowledge import KNOWLEDGE
from foresight_agent.llm import ClaudeGenerator, StubGenerator
from foresight_agent.retrieval import HybridRetriever
from foresight_agent.run import _load_dotenv

# Representative anomalies across types (same fields the pipeline emits).
RECORDS = [
    {
        "tenant_id": "acct_016", "metric_date": "2026-06-14",
        "anomaly_score": 0.982, "anomaly_type": "payment_failure", "type_confidence": 0.71,
        "top_contributors": [["refund_rate", 9.8], ["mrr", -3.2]],
        "description": "Refund rate spiked while MRR dipped.",
        "metrics": {
            "mrr": 41200.0, "refund_rate": 0.16, "conversion_rate": 0.29, "checkout_volume": 880.0,
        },
    },
    {
        "tenant_id": "acct_042", "metric_date": "2026-06-15",
        "anomaly_score": 0.958, "anomaly_type": "churn_spike", "type_confidence": 0.68,
        "top_contributors": [["mrr", -6.1], ["conversion_rate", -0.9]],
        "description": "MRR fell sharply as many subscriptions cancelled.",
        "metrics": {
            "mrr": 28800.0, "refund_rate": 0.03, "conversion_rate": 0.31, "checkout_volume": 640.0,
        },
    },
    {
        "tenant_id": "acct_007", "metric_date": "2026-06-15",
        "anomaly_score": 0.991, "anomaly_type": "infrastructure_issue", "type_confidence": 0.63,
        "top_contributors": [["checkout_volume", -7.4], ["conversion_rate", -2.1]],
        "description": "Checkout volume collapsed with a conversion drop.",
        "metrics": {
            "mrr": 33500.0, "refund_rate": 0.02, "conversion_rate": 0.11, "checkout_volume": 40.0,
        },
    },
    {
        "tenant_id": "acct_023", "metric_date": "2026-06-13",
        "anomaly_score": 0.903, "anomaly_type": "seasonal_dip", "type_confidence": 0.55,
        "top_contributors": [["checkout_volume", -2.8]],
        "description": "Checkout volume softened over the weekend.",
        "metrics": {
            "mrr": 19100.0, "refund_rate": 0.02, "conversion_rate": 0.30, "checkout_volume": 310.0,
        },
    },
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../frontend/public/demo-data.json")
    args = parser.parse_args(argv)

    _load_dotenv()
    generator = ClaudeGenerator() if os.getenv("ANTHROPIC_API_KEY") else StubGenerator()
    app = build_graph(HybridRetriever(KNOWLEDGE), generator)

    anomalies = []
    for record in RECORDS:
        final = app.invoke({"anomaly": record})
        alert = final["alert"]
        anomalies.append(
            {
                "tenant_id": record["tenant_id"],
                "metric_date": record["metric_date"],
                "anomaly_type": record["anomaly_type"],
                "anomaly_score": record["anomaly_score"],
                "type_confidence": record["type_confidence"],
                "top_contributors": record["top_contributors"],
                "metrics": record["metrics"],
                "explanation": alert["explanation"],
                "faithfulness": round(final["faithfulness"], 3),
                "sources": [d["id"] for d in final["retrieved"]],
                "status": alert["status"],
            }
        )

    bundle = {
        "generated_with": "Claude Opus 4.8" if os.getenv("ANTHROPIC_API_KEY") else "stub",
        "anomalies": anomalies,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2))
    print(f"wrote {len(anomalies)} anomalies -> {out}  ({bundle['generated_with']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
