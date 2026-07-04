"""Tests for the TF-IDF baseline + evaluation utilities."""

from __future__ import annotations

from foresight_classification.baseline import predict, train_baseline
from foresight_classification.benchmark import evaluate, per_class_f1
from foresight_classification.data import DatasetConfig, generate, train_test_split


def test_baseline_learns() -> None:
    df = generate(DatasetConfig(n_per_class=200))
    train, test = train_test_split(df, test_frac=0.25, seed=0)
    model = train_baseline(train)
    preds = predict(model, test["text"].tolist())
    m = evaluate(test["label"].tolist(), preds)
    # Templated text is learnable, but overlapping vocabulary keeps it non-trivial.
    assert m["accuracy"] > 0.7
    assert m["macro_f1"] > 0.7


def test_evaluate_perfect() -> None:
    from foresight_classification import LABELS

    y = list(LABELS)  # all classes present → perfect macro-F1 over the fixed set
    m = evaluate(y, y)
    assert m["accuracy"] == 1.0 and m["macro_f1"] == 1.0
    pcf = per_class_f1(y, y)
    assert pcf["churn_spike"] == 1.0
