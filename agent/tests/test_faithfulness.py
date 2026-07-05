"""Tests for the numeric-grounding faithfulness gate."""

from __future__ import annotations

from foresight_agent.faithfulness import faithfulness_score

ANOMALY = {
    "tenant_id": "acct_1",
    "anomaly_score": 0.99,
    "metrics": {"mrr": 9000.0, "refund_rate": 0.18},
    "top_contributors": [["refund_rate", 10.49]],
}
RETRIEVED = [{"text": "Refund rate rose above normal."}]


def test_no_numbers_is_faithful() -> None:
    assert faithfulness_score("Refunds rose sharply.", ANOMALY, RETRIEVED) == 1.0


def test_grounded_numbers_pass() -> None:
    exp = "Refund rate reached 0.18 and MRR fell to 9000 (score 0.99)."
    assert faithfulness_score(exp, ANOMALY, RETRIEVED) == 1.0


def test_fabricated_number_lowers_score() -> None:
    exp = "Refund rate hit 0.42 and 317 customers churned."  # neither is in source
    assert faithfulness_score(exp, ANOMALY, RETRIEVED) < 0.85


def test_unicode_minus_and_thousands_separator() -> None:
    # Models emit U+2212 and comma-grouped numbers; both must ground.
    anomaly = {"top_contributors": [["mrr", -6.1]], "metrics": {"mrr": 28800.0}}
    exp = "MRR fell −6.10sd to $28,800."
    assert faithfulness_score(exp, anomaly, []) == 1.0
