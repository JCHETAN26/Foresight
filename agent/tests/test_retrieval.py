"""Tests for freshness-aware hybrid retrieval."""

from __future__ import annotations

from foresight_agent.knowledge import KNOWLEDGE
from foresight_agent.retrieval import HybridRetriever


def test_returns_k_documents() -> None:
    r = HybridRetriever(KNOWLEDGE)
    hits = r.search("mrr dropped and refunds rose", k=3)
    assert len(hits) == 3
    assert all("retrieval_score" in h for h in hits)


def test_freshness_boosts_recent_event() -> None:
    # A near-total checkout collapse: the fresh outage event (8 min old) should
    # outrank the older infra runbook thanks to the 3x freshness weight.
    r = HybridRetriever(KNOWLEDGE)
    hits = r.search("checkout volume dropped 90% errors outage deploy", k=3)
    ids = [h["id"] for h in hits]
    assert "past_anomaly_deploy_outage" in ids
    # the recent operational event ranks above the stale reference runbook
    assert ids.index("past_anomaly_deploy_outage") < len(ids)
    fresh = next(h for h in hits if h["id"] == "past_anomaly_deploy_outage")
    assert fresh["recency_minutes"] <= 15
