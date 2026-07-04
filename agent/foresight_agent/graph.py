"""The LangGraph pipeline: detect → classify → retrieve → reason → evaluate → alert.

`evaluate` gates on faithfulness and loops back to `retrieve` (with more context)
on a low score, up to `max_retries`. Low-confidence anomalies are withheld from
alerting for human review — the human-in-the-loop safeguard.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from foresight_agent.alert import format_alert, post_to_slack
from foresight_agent.faithfulness import FAITHFULNESS_THRESHOLD, faithfulness_score
from foresight_agent.llm import REASON_SYSTEM, Generator, build_reason_prompt
from foresight_agent.retrieval import HybridRetriever
from foresight_agent.state import AgentState

REVIEW_CONFIDENCE = 0.6  # below this, withhold the alert for human review


def build_graph(
    retriever: HybridRetriever,
    generator: Generator,
    *,
    base_k: int = 3,
    max_retries: int = 1,
    post_slack: bool = False,
):
    def detect(state: AgentState) -> dict[str, Any]:
        return {"retries": 0}

    def classify(state: AgentState) -> dict[str, Any]:
        a = state["anomaly"]
        return {
            "anomaly_type": a.get("anomaly_type", "unknown"),
            "type_confidence": float(a.get("type_confidence", 0.0)),
        }

    def retrieve(state: AgentState) -> dict[str, Any]:
        a = state["anomaly"]
        drivers = " ".join(m for m, _ in a.get("top_contributors", []))
        query = f"{state['anomaly_type']} {drivers} {a.get('description', '')}"
        k = base_k + state.get("retries", 0)  # widen context on retry
        return {"query": query, "retrieved": retriever.search(query, k=k)}

    def reason(state: AgentState) -> dict[str, Any]:
        prompt = build_reason_prompt(state["anomaly"], state["retrieved"])
        explanation = generator.generate(REASON_SYSTEM, prompt)
        return {"explanation": explanation}

    def evaluate(state: AgentState) -> dict[str, Any]:
        score = faithfulness_score(state["explanation"], state["anomaly"], state["retrieved"])
        return {
            "faithfulness": score,
            "faithful": score >= FAITHFULNESS_THRESHOLD,
            "retries": state.get("retries", 0) + 1,
        }

    def alert(state: AgentState) -> dict[str, Any]:
        payload = format_alert(state["anomaly"], state["explanation"], state["faithfulness"])
        if state["type_confidence"] < REVIEW_CONFIDENCE:
            payload["status"] = "held_for_review"  # human-in-the-loop
        elif not state.get("faithful", False):
            payload["status"] = "held_low_faithfulness"
        else:
            payload["status"] = "sent" if (post_slack and post_to_slack(payload)) else "ready"
        return {"alert": payload}

    def route_after_eval(state: AgentState) -> str:
        if state.get("faithful") or state.get("retries", 0) > max_retries:
            return "alert"
        return "retrieve"

    g = StateGraph(AgentState)
    for name, fn in [
        ("detect", detect), ("classify", classify), ("retrieve", retrieve),
        ("reason", reason), ("evaluate", evaluate), ("alert", alert),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "detect")
    g.add_edge("detect", "classify")
    g.add_edge("classify", "retrieve")
    g.add_edge("retrieve", "reason")
    g.add_edge("reason", "evaluate")
    g.add_conditional_edges(
        "evaluate", route_after_eval, {"retrieve": "retrieve", "alert": "alert"}
    )
    g.add_edge("alert", END)
    return g.compile()
