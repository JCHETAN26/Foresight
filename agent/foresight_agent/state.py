"""Shared graph state."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Input: an AnomalyRecord (as a dict) from the ml/anomaly layer.
    anomaly: dict[str, Any]

    # Populated as the graph runs.
    anomaly_type: str
    type_confidence: float
    query: str
    retrieved: list[dict[str, Any]]  # [{id, text, score, ...}]
    explanation: str
    faithfulness: float
    faithful: bool
    retries: int
    alert: dict[str, Any]
