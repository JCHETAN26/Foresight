"""Faithfulness gate — numeric grounding.

Every number in the explanation must be traceable to the anomaly record or the
retrieved context; a fabricated metric value is the failure mode this catches.
Deterministic (no model), so it runs in CI and pins the behavior. In production
this pairs with an LLM-as-judge (LangSmith) for semantic faithfulness; the
numeric check is the hard floor.
"""

from __future__ import annotations

import re
from typing import Any

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
FAITHFULNESS_THRESHOLD = 0.85


def _numbers(text: str) -> list[float]:
    out = []
    for tok in _NUM.findall(text):
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


def _grounded(value: float, sources: list[float]) -> bool:
    for s in sources:
        if abs(value - s) < 1e-6:
            return True
        if s != 0 and abs(value - s) / abs(s) < 1e-3:
            return True
    return False


def faithfulness_score(
    explanation: str, anomaly: dict[str, Any], retrieved: list[dict[str, Any]]
) -> float:
    """Fraction of numbers in the explanation grounded in the source material."""
    exp_numbers = _numbers(explanation)
    if not exp_numbers:
        return 1.0

    source_text = str(anomaly) + " " + " ".join(d.get("text", "") for d in retrieved)
    sources = _numbers(source_text)

    grounded = sum(1 for n in exp_numbers if _grounded(n, sources))
    return grounded / len(exp_numbers)
