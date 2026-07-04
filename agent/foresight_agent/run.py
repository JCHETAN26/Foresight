"""Demo CLI: run the agent on a sample anomaly.

Uses Claude when ANTHROPIC_API_KEY is set, otherwise the deterministic stub.

    python -m foresight_agent.run
    ANTHROPIC_API_KEY=... python -m foresight_agent.run --live
"""

from __future__ import annotations

import argparse
import json
import os

from foresight_agent.graph import build_graph
from foresight_agent.knowledge import KNOWLEDGE
from foresight_agent.llm import ClaudeGenerator, StubGenerator
from foresight_agent.retrieval import HybridRetriever

SAMPLE = {
    "tenant_id": "acct_016",
    "metric_date": "day-96",
    "anomaly_score": 0.995,
    "anomaly_type": "payment_failure",
    "type_confidence": 0.71,
    "top_contributors": [["refund_rate", 10.49], ["mrr", -4.43]],
    "description": "Refund rate climbed sharply while MRR fell below its usual level.",
    "metrics": {
        "mrr": 9000.0, "refund_rate": 0.18, "conversion_rate": 0.28, "checkout_volume": 500.0,
    },
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Use Claude (needs ANTHROPIC_API_KEY).")
    parser.add_argument("--slack", action="store_true", help="Post to SLACK_WEBHOOK_URL if set.")
    args = parser.parse_args(argv)

    use_claude = args.live or os.getenv("ANTHROPIC_API_KEY")
    generator = ClaudeGenerator() if use_claude else StubGenerator()
    retriever = HybridRetriever(KNOWLEDGE)
    app = build_graph(retriever, generator, post_slack=args.slack)

    final = app.invoke({"anomaly": SAMPLE})

    print(f"generator: {'Claude' if use_claude else 'stub'}")
    print(f"retrieved: {[d['id'] for d in final['retrieved']]}")
    print(f"faithfulness: {final['faithfulness']:.2f}  retries: {final['retries'] - 1}")
    print(json.dumps(final["alert"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
