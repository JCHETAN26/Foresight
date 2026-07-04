"""End-to-end graph tests with the deterministic stub generator."""

from __future__ import annotations

from foresight_agent.graph import build_graph
from foresight_agent.knowledge import KNOWLEDGE
from foresight_agent.llm import StubGenerator
from foresight_agent.retrieval import HybridRetriever

ANOMALY = {
    "tenant_id": "acct_016",
    "metric_date": "day-96",
    "anomaly_score": 0.995,
    "anomaly_type": "payment_failure",
    "type_confidence": 0.71,
    "top_contributors": [["refund_rate", 10.49], ["mrr", -4.43]],
    "description": "Refund rate climbed sharply while MRR fell.",
    "metrics": {"mrr": 9000.0, "refund_rate": 0.18},
}


def _app():
    return build_graph(HybridRetriever(KNOWLEDGE), StubGenerator())


def test_end_to_end_produces_ready_alert() -> None:
    final = _app().invoke({"anomaly": ANOMALY})
    assert final["explanation"]
    assert final["retrieved"]
    assert final["faithfulness"] >= 0.85
    alert = final["alert"]
    assert alert["status"] == "ready"
    assert alert["anomaly_type"] == "payment_failure"
    assert "payment_failure" in alert["text"]


def test_low_confidence_is_withheld() -> None:
    low = {**ANOMALY, "type_confidence": 0.4}
    final = _app().invoke({"anomaly": low})
    assert final["alert"]["status"] == "held_for_review"


def test_faithfulness_gate_holds_ungrounded_explanation() -> None:
    class Hallucinator:
        def generate(self, system: str, prompt: str) -> str:
            return "Revenue cratered by 73% and 4210 accounts churned overnight."

    app = build_graph(HybridRetriever(KNOWLEDGE), Hallucinator(), max_retries=1)
    final = app.invoke({"anomaly": ANOMALY})
    assert final["faithfulness"] < 0.85
    assert final["alert"]["status"] == "held_low_faithfulness"
