"""Evaluation utilities shared by the baseline and the T5 classifier."""

from __future__ import annotations

from sklearn.metrics import accuracy_score, f1_score

from foresight_classification import LABELS


def evaluate(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    """Accuracy plus macro/weighted F1 over the fixed label set."""
    macro = f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    weighted = f1_score(y_true, y_pred, labels=LABELS, average="weighted", zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(macro),
        "weighted_f1": float(weighted),
    }


def per_class_f1(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    scores = f1_score(y_true, y_pred, labels=LABELS, average=None, zero_division=0)
    return {label: float(s) for label, s in zip(LABELS, scores, strict=True)}
