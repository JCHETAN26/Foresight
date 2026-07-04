"""Turn an anomaly's metric context into a natural-language description.

The description reflects which metrics moved and how — it is what the classifier
reads to assign a type, and what the M3 agent later grounds its explanation on.
Phrasing intentionally mirrors the classifier's training vocabulary.
"""

from __future__ import annotations

_PCT_METRICS = {"conversion_rate", "refund_rate"}  # reported as percentages of value


def _fragment(metric: str, value: float, mean: float) -> str:
    up = value > mean
    pct = abs((value - mean) / mean) * 100 if mean else 0.0
    if metric == "mrr":
        return (
            f"MRR rose {pct:.0f}% above its usual level."
            if up
            else f"MRR fell {pct:.0f}% below its usual level."
        )
    if metric == "refund_rate":
        return (
            f"Refund rate climbed to {value:.1%}, well above normal."
            if up
            else f"Refund rate dropped to {value:.1%}."
        )
    if metric == "conversion_rate":
        return (
            f"Conversion rate rose to {value:.1%}."
            if up
            else f"Conversion rate slipped to {value:.1%}."
        )
    if metric == "checkout_volume":
        return (
            f"Checkout volume jumped {pct:.0f}% above baseline."
            if up
            else f"Checkout volume dropped {pct:.0f}% below baseline."
        )
    return f"{metric} shifted from its baseline."


def describe_anomaly(
    metrics: dict[str, float],
    baseline_mean: dict[str, float],
    top_contributors: list[tuple[str, float]],
    top_k: int = 2,
) -> str:
    """Compose a description from the top-k contributing metrics."""
    fragments = [
        _fragment(metric, metrics[metric], baseline_mean[metric])
        for metric, _ in top_contributors[:top_k]
        if metric in metrics and metric in baseline_mean
    ]
    return " ".join(fragments) if fragments else "Metrics deviated from baseline."
