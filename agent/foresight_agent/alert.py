"""Alert formatting + optional Slack delivery."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def format_alert(anomaly: dict[str, Any], explanation: str, faithfulness: float) -> dict[str, Any]:
    emoji = {"payment_failure": "💳", "churn_spike": "📉", "infrastructure_issue": "🚨"}.get(
        anomaly.get("anomaly_type", ""), "⚠️"
    )
    text = (
        f"{emoji} *{anomaly.get('anomaly_type', 'anomaly')}* for `{anomaly.get('tenant_id')}` "
        f"on {anomaly.get('metric_date')} (score {anomaly.get('anomaly_score')})\n"
        f"{explanation}"
    )
    return {
        "tenant_id": anomaly.get("tenant_id"),
        "anomaly_type": anomaly.get("anomaly_type"),
        "confidence": anomaly.get("type_confidence"),
        "score": anomaly.get("anomaly_score"),
        "explanation": explanation,
        "faithfulness": faithfulness,
        "text": text,
        "status": "ready",
    }


def post_to_slack(alert: dict[str, Any], webhook_url: str | None = None) -> bool:
    """Post to Slack if a webhook is configured; return whether it was sent."""
    url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return False
    req = urllib.request.Request(
        url,
        data=json.dumps({"text": alert["text"]}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=5)  # noqa: S310 — configured webhook URL
    return True
