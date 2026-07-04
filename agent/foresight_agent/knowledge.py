"""Seed knowledge base for retrieval.

In production LlamaIndex ingests business runbooks, metric definitions, and past
anomaly reports; here we seed a small representative corpus. Each document has a
`recency_minutes` field so the retriever can apply freshness weighting (recent
operational events outrank stale reference docs for the same query).
"""

from __future__ import annotations

from typing import Any

# recency_minutes: minutes since the document/event was produced.
KNOWLEDGE: list[dict[str, Any]] = [
    {
        "id": "runbook_payment_failure",
        "kind": "runbook",
        "recency_minutes": 20_000,
        "text": (
            "Payment failure playbook. A spike in refund rate together with an MRR "
            "dip usually means card declines or a failing payment provider. Check "
            "Stripe webhook delivery and the dunning queue; involuntary churn rises "
            "when renewals fail."
        ),
    },
    {
        "id": "runbook_churn_spike",
        "kind": "runbook",
        "recency_minutes": 21_000,
        "text": (
            "Churn spike playbook. A sharp MRR drop with many cancelled "
            "subscriptions indicates voluntary churn. Correlate with recent pricing "
            "changes, onboarding regressions, or a competitor launch."
        ),
    },
    {
        "id": "runbook_infra_issue",
        "kind": "runbook",
        "recency_minutes": 22_000,
        "text": (
            "Infrastructure incident playbook. A near-total collapse in checkout "
            "volume with elevated errors points to an outage or a bad deploy. Check "
            "the status page, recent deploys, and API error rates before assuming a "
            "demand problem."
        ),
    },
    {
        "id": "metric_def_mrr",
        "kind": "metric_definition",
        "recency_minutes": 40_000,
        "text": (
            "MRR (monthly recurring revenue) is the sum of active subscription "
            "amounts. It falls when subscriptions are cancelled or downgraded and "
            "rises on new subscriptions and upgrades."
        ),
    },
    {
        "id": "metric_def_refund_rate",
        "kind": "metric_definition",
        "recency_minutes": 41_000,
        "text": (
            "Refund rate is refunded amount divided by gross revenue for the day. A "
            "sustained rise often accompanies payment failures or disputed charges."
        ),
    },
    {
        "id": "past_anomaly_deploy_outage",
        "kind": "past_anomaly",
        "recency_minutes": 8,  # very recent operational signal
        "text": (
            "Recent event: a deploy at 14:02 caused checkout 500 errors for tenant "
            "traffic; checkout volume dropped over 90% for ~40 minutes before "
            "rollback. Classified as infrastructure_issue, not acquisition_drop."
        ),
    },
    {
        "id": "past_anomaly_price_change",
        "kind": "past_anomaly",
        "recency_minutes": 12,
        "text": (
            "Recent event: a pricing change went live this morning; conversion "
            "softened while MRR rose as average deal size increased. Classified as "
            "pricing_effect."
        ),
    },
]
