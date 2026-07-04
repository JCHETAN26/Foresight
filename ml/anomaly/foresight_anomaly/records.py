"""The anomaly record — the contract between detection/classification and the
downstream agent + alerting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AnomalyRecord:
    tenant_id: str
    metric_date: str
    anomaly_score: float  # ensemble score in [0, 1]
    anomaly_type: str  # classifier label
    type_confidence: float  # classifier probability for the chosen label
    top_contributors: list[tuple[str, float]]  # (metric, signed deviation in sd)
    description: str  # natural-language summary fed to the classifier + agent
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
