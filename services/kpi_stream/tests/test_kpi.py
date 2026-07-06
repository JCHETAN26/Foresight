"""Cross-validate the live KPI math against the dbt gold model's assertions.

These are the same acct_alpha events the dbt seed generates; the expected KPIs
match `assert_alpha_known_kpis.sql` in pipelines/dbt. If the streaming path and
the batch path ever diverge, this fails.
"""

from __future__ import annotations

from foresight_kpi.kpi import DailyKpi, compute_daily_kpis

DAY1, DAY2, DAY3 = 1780308000, 1780394400, 1780480800  # 2026-06-01/02/03 UTC


def _ev(etype: str, created: int, amount: int, tenant: str = "acct_alpha") -> dict:
    return {
        "tenant_id": tenant,
        "event_type": etype,
        "created": created,
        "data": {"object": {"amount": amount}},
    }


# acct_alpha's three-day event stream (mirrors the dbt bronze seed).
EVENTS = [
    _ev("customer.subscription.created", DAY1 + 60, 5000),
    _ev("customer.subscription.created", DAY1 + 120, 10000),
    _ev("invoice.paid", DAY1 + 180, 5000),
    _ev("invoice.paid", DAY1 + 240, 10000),
    _ev("checkout.session.completed", DAY1 + 300, 5000),
    _ev("checkout.session.completed", DAY1 + 360, 10000),
    _ev("checkout.session.expired", DAY1 + 420, 5000),
    _ev("customer.subscription.created", DAY2 + 60, 5000),
    _ev("invoice.paid", DAY2 + 120, 5000),
    _ev("invoice.payment_failed", DAY2 + 180, 10000),
    _ev("charge.refunded", DAY2 + 240, 2000),
    _ev("checkout.session.completed", DAY2 + 300, 5000),
    _ev("checkout.session.expired", DAY2 + 360, 5000),
    _ev("customer.subscription.deleted", DAY3 + 60, 5000),
    _ev("invoice.paid", DAY3 + 120, 10000),
    _ev("checkout.session.completed", DAY3 + 240, 5000),
]


def test_matches_dbt_gold_kpis() -> None:
    kpis = {k.metric_date: k for k in compute_daily_kpis(EVENTS)}

    d1 = kpis["2026-06-01"]
    assert d1.mrr == 150.0  # 5000 + 10000 cents → $150
    assert d1.refund_rate == 0.0
    assert d1.conversion_rate == round(2 / 3, 4)  # 2 completed / (2+1)
    assert d1.checkout_volume == 3.0

    d2 = kpis["2026-06-02"]
    assert d2.mrr == 200.0  # +5000
    assert d2.refund_rate == 0.4  # 2000 / 5000
    assert d2.conversion_rate == 0.5  # 1 / (1+1)

    d3 = kpis["2026-06-03"]
    assert d3.mrr == 150.0  # -5000 (churn)
    assert d3.conversion_rate == 1.0  # 1 / (1+0)


def test_per_tenant_isolation() -> None:
    events = [
        _ev("customer.subscription.created", DAY1, 20000, tenant="acct_beta"),
        _ev("customer.subscription.created", DAY1, 5000, tenant="acct_gamma"),
    ]
    out = {k.tenant_id: k for k in compute_daily_kpis(events)}
    assert out["acct_beta"].mrr == 200.0
    assert out["acct_gamma"].mrr == 50.0


def test_empty() -> None:
    assert compute_daily_kpis([]) == []
    assert isinstance(compute_daily_kpis(EVENTS)[0], DailyKpi)
