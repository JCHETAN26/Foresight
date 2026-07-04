"""Synthetic labeled anomaly-description dataset.

Each example is a short natural-language description of a detected anomaly (the
kind of text produced from the metric context + SHAP attribution) paired with
its type label. Templates carry deliberate lexical overlap between classes
(e.g. "MRR dropped" appears for both churn_spike and pricing_effect) so the task
is genuinely learned, not solved by a single keyword.

Deterministic given a seed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from foresight_classification import LABELS

# Template banks per label. `{p}` = a percentage, `{n}` = a count, `{d}` = a day.
_TEMPLATES: dict[str, list[str]] = {
    "payment_failure": [
        "Refund rate jumped to {p}% after {n} card payments were declined.",
        "{n} recurring charges failed on {d}; involuntary churn is climbing.",
        "A spike in failed payment intents ({n} in one day) drove refunds up {p}%.",
        "Dunning emails surged as {n} subscriptions hit payment failures.",
        "Card declines rose sharply, pushing the failed-payment rate to {p}%.",
        "MRR dipped because {n} invoices went unpaid after payment errors.",
    ],
    "churn_spike": [
        "MRR fell {p}% as {n} customers cancelled their subscriptions on {d}.",
        "Churn rate spiked to {p}%; {n} accounts voluntarily downgraded to free.",
        "A wave of {n} cancellations wiped out {p}% of recurring revenue.",
        "Subscription deletions jumped to {n}, the highest this quarter.",
        "Net revenue churn hit {p}% after {n} customers left this week.",
        "Active subscriptions dropped by {n} as churn accelerated.",
    ],
    "seasonal_dip": [
        "Checkout volume dropped {p}% over the holiday weekend as expected.",
        "Typical weekend slowdown: orders down {p}% versus weekday baseline.",
        "Seasonal lull pulled checkout volume down {p}% around {d}.",
        "End-of-month dip: transactions fell {p}% before payday recovery.",
        "Traffic and orders softened {p}% during the seasonal off-period.",
        "Volume declined {p}% in line with the usual holiday pattern.",
    ],
    "acquisition_drop": [
        "New signups fell {p}% as top-of-funnel traffic dried up on {d}.",
        "Conversion rate declined {p}% with fewer new checkouts starting.",
        "Acquisition stalled: {n} fewer trials began compared to baseline.",
        "New-customer volume dropped {p}%, hurting pipeline for next month.",
        "Fewer visitors converted; signup conversion slipped to {p}%.",
        "Marketing traffic cooled and new checkouts fell by {n}.",
    ],
    "pricing_effect": [
        "After the price increase, conversion dropped {p}% but ARPU rose.",
        "The new pricing tier shifted mix; MRR grew despite {p}% lower conversion.",
        "Plan repricing lifted revenue per account while checkout conversion fell {p}%.",
        "Following the {p}% price hike, upgrades slowed but revenue held.",
        "A pricing change caused MRR to jump while trial conversion dipped {p}%.",
        "New packaging raised average deal size; conversion softened {p}%.",
    ],
    "infrastructure_issue": [
        "Checkout errors spiked during a {n}-minute API outage on {d}.",
        "A deploy caused 500 errors, and {p}% of checkouts failed to complete.",
        "Payment page downtime dropped completed checkouts by {p}%.",
        "Elevated latency and {n} timeout errors broke the checkout flow.",
        "An infrastructure incident took checkout volume down {p}% for hours.",
        "Service degradation caused {n} failed sessions before recovery.",
    ],
}

# Harder, terser, deliberately ambiguous phrasings that share verbs and metric
# nouns across classes and imply the mechanism rather than naming it — this is
# what makes the benchmark discriminate between a bag-of-words model and one
# that reads context.
_HARD_TEMPLATES: dict[str, list[str]] = {
    "payment_failure": [
        "Revenue slipped {p}% and refunds ticked up on {d}.",
        "More charges bounced than usual; involuntary losses rose.",
        "Collections struggled this week — several renewals didn't go through.",
    ],
    "churn_spike": [
        "Recurring revenue slid {p}% as the active base shrank.",
        "A handful of accounts went away, and the run-rate dropped.",
        "The book of business contracted after cancellations picked up.",
    ],
    "seasonal_dip": [
        "Orders were quiet, down {p}% around {d} — normal for the calendar.",
        "Volume softened this period, nothing unusual for the time of year.",
        "The expected lull arrived; throughput eased off {p}%.",
    ],
    "acquisition_drop": [
        "The top of the funnel thinned and fewer people started checkout.",
        "Growth in new accounts stalled {p}% with weaker inbound interest.",
        "Fresh demand cooled; the pipeline for next month looks lighter.",
    ],
    "pricing_effect": [
        "Revenue and conversion moved in opposite directions after the plan update.",
        "Deal sizes shifted following the change to packaging on {d}.",
        "Fewer signed up but each was worth more once the tiers changed.",
    ],
    "infrastructure_issue": [
        "Checkouts failed to load for a stretch on {d}.",
        "The flow broke for {n} sessions before things recovered.",
        "A technical hiccup interrupted purchases for part of the day.",
    ],
}

_FILLERS = ["Alert: ", "Heads up — ", "FYI: ", "Note: ", "Observed: "]


def _augment(text: str, rng: np.random.Generator, noise: float) -> str:
    """Light, realistic text noise so surface tokens aren't a free giveaway."""
    if rng.random() < noise:
        text = _FILLERS[int(rng.integers(len(_FILLERS)))] + text
    if rng.random() < noise:
        # Swap two adjacent characters in a longer word (a plausible typo).
        words = text.split()
        long_idx = [i for i, w in enumerate(words) if len(w) > 4]
        if long_idx:
            i = long_idx[int(rng.integers(len(long_idx)))]
            w = list(words[i])
            j = int(rng.integers(len(w) - 1))
            w[j], w[j + 1] = w[j + 1], w[j]
            words[i] = "".join(w)
            text = " ".join(words)
    if rng.random() < noise * 0.5:
        text = text.lower()
    return text


@dataclass(frozen=True)
class DatasetConfig:
    n_per_class: int = 350  # 6 classes -> ~2,100 examples
    hard_frac: float = 0.5  # fraction drawn from the ambiguous template bank
    noise: float = 0.3  # per-augmentation probability
    seed: int = 11


def generate(config: DatasetConfig | None = None) -> pd.DataFrame:
    """Return a shuffled DataFrame with columns [text, label]."""
    cfg = config or DatasetConfig()
    rng = np.random.default_rng(cfg.seed)
    days = ["Monday", "Tuesday", "Friday", "the 1st", "the weekend", "March 3rd"]

    rows: list[dict[str, str]] = []
    for label in LABELS:
        easy, hard = _TEMPLATES[label], _HARD_TEMPLATES[label]
        for _ in range(cfg.n_per_class):
            bank = hard if rng.random() < cfg.hard_frac else easy
            tmpl = bank[int(rng.integers(len(bank)))]
            text = tmpl.format(
                p=int(rng.integers(8, 62)),
                n=int(rng.integers(3, 240)),
                d=days[int(rng.integers(len(days)))],
            )
            rows.append(
                {
                    "text": _augment(text, rng, cfg.noise),
                    "label": label,
                    "template": tmpl,  # unfilled pattern, for template-holdout eval
                }
            )

    df = pd.DataFrame(rows)
    return df.sample(frac=1.0, random_state=cfg.seed).reset_index(drop=True)


def train_test_split(
    df: pd.DataFrame, test_frac: float = 0.2, seed: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified split by label (test phrasings may repeat training templates)."""
    rng = np.random.default_rng(seed)
    train_parts, test_parts = [], []
    for _, g in df.groupby("label"):
        idx = rng.permutation(len(g))
        n_test = int(len(g) * test_frac)
        test_parts.append(g.iloc[idx[:n_test]])
        train_parts.append(g.iloc[idx[n_test:]])
    train = pd.concat(train_parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    test = pd.concat(test_parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return train, test


def template_holdout_split(
    df: pd.DataFrame, n_holdout_per_class: int = 2, seed: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split so the test set uses templates never seen in training.

    Measures generalization to *unseen phrasings* rather than to unseen fills of
    seen phrasings — the harder, more honest test, and the one where a semantic
    model can differ from surface n-gram matching.
    """
    rng = np.random.default_rng(seed)
    holdout_templates: set[str] = set()
    for _, g in df.groupby("label"):
        templates = g["template"].unique()
        rng.shuffle(templates)
        holdout_templates.update(templates[:n_holdout_per_class])

    is_test = df["template"].isin(holdout_templates)
    train = df[~is_test].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    test = df[is_test].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return train, test
