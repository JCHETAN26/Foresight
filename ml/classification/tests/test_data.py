"""Tests for the anomaly-description dataset."""

from __future__ import annotations

from foresight_classification import LABELS
from foresight_classification.data import DatasetConfig, generate, train_test_split


def test_balanced_and_labeled() -> None:
    df = generate(DatasetConfig(n_per_class=50))
    assert len(df) == 50 * len(LABELS)
    assert set(df["label"].unique()) == set(LABELS)
    assert (df["label"].value_counts() == 50).all()
    assert df["text"].str.len().min() > 0


def test_deterministic() -> None:
    a = generate(DatasetConfig(n_per_class=20, seed=5))
    b = generate(DatasetConfig(n_per_class=20, seed=5))
    assert a.equals(b)


def test_stratified_split() -> None:
    df = generate(DatasetConfig(n_per_class=50))
    train, test = train_test_split(df, test_frac=0.2, seed=0)
    assert len(test) == int(0.2 * 50) * len(LABELS)
    # every class present in both splits
    assert set(train["label"]) == set(LABELS)
    assert set(test["label"]) == set(LABELS)
