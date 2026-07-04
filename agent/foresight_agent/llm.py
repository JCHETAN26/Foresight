"""Provider-agnostic generation.

`ClaudeGenerator` calls the Anthropic API (Claude Opus 4.8). `StubGenerator`
composes a grounded explanation deterministically from the record + retrieved
context — no network, no key — so the graph is fully testable in CI. The plan's
Azure OpenAI path is a drop-in third implementation of the same `Generator`
protocol.
"""

from __future__ import annotations

from typing import Any, Protocol


class Generator(Protocol):
    def generate(self, system: str, prompt: str) -> str: ...


class ClaudeGenerator:
    """Grounded explanation via Claude. Reads ANTHROPIC_API_KEY from the env."""

    def __init__(self, model: str = "claude-opus-4-8", max_tokens: int = 1024) -> None:
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, system: str, prompt: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()


class StubGenerator:
    """Deterministic, grounded generator for tests/CI.

    Uses only values present in the record and retrieved context, so the
    faithfulness gate passes without a live model.
    """

    def generate(self, system: str, prompt: str) -> str:
        ctx = _parse_prompt(prompt)
        drivers = ", ".join(ctx["drivers"]) if ctx["drivers"] else "multiple metrics"
        lead = ctx["runbook"].split(".")[0] if ctx["runbook"] else ""
        return (
            f"Tenant {ctx['tenant']} shows a {ctx['type']} anomaly on "
            f"{ctx['date']} (score {ctx['score']}). The main drivers were "
            f"{drivers}. {lead}."
        ).strip()


def build_reason_prompt(anomaly: dict[str, Any], retrieved: list[dict[str, Any]]) -> str:
    """Assemble the grounded-generation prompt (shared by real + stub)."""
    drivers = ", ".join(f"{m} ({z:+.2f}sd)" for m, z in anomaly.get("top_contributors", []))
    context = "\n".join(f"- {d['text']}" for d in retrieved)
    return (
        f"TENANT: {anomaly.get('tenant_id')}\n"
        f"DATE: {anomaly.get('metric_date')}\n"
        f"ANOMALY TYPE: {anomaly.get('anomaly_type')} "
        f"(confidence {anomaly.get('type_confidence')})\n"
        f"SCORE: {anomaly.get('anomaly_score')}\n"
        f"DRIVERS: {drivers}\n"
        f"METRICS: {anomaly.get('metrics')}\n\n"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        "Explain, in 2-3 sentences, what most likely happened. Ground every claim "
        "in the drivers, metrics, or retrieved context above. Do not invent "
        "numbers that are not shown."
    )


REASON_SYSTEM = (
    "You are Foresight's revenue-intelligence analyst. Write concise, grounded "
    "explanations of detected anomalies for a founder. Never fabricate metric "
    "values; use only the numbers provided."
)


def _parse_prompt(prompt: str) -> dict[str, Any]:
    """Extract fields from a build_reason_prompt() string (stub-only helper)."""
    fields: dict[str, Any] = {
        "tenant": "", "date": "", "type": "", "score": "", "drivers": [], "runbook": "",
    }
    for line in prompt.splitlines():
        if line.startswith("TENANT:"):
            fields["tenant"] = line.split(":", 1)[1].strip()
        elif line.startswith("DATE:"):
            fields["date"] = line.split(":", 1)[1].strip()
        elif line.startswith("ANOMALY TYPE:"):
            fields["type"] = line.split(":", 1)[1].split("(")[0].strip()
        elif line.startswith("SCORE:"):
            fields["score"] = line.split(":", 1)[1].strip()
        elif line.startswith("DRIVERS:"):
            drivers = line.split(":", 1)[1].strip()
            fields["drivers"] = [d.strip() for d in drivers.split(",") if d.strip()]
        elif line.strip().startswith("- ") and not fields["runbook"]:
            fields["runbook"] = line.strip()[2:]
    return fields
