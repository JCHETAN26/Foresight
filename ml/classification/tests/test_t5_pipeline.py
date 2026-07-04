"""End-to-end T5 LoRA test — gated behind FORESIGHT_RUN_T5=1.

Skipped in default CI because it downloads t5-small (~240 MB) and trains. Run
locally with the `t5` extra installed:  FORESIGHT_RUN_T5=1 pytest -q
"""

from __future__ import annotations

import os
import tempfile

import pytest

RUN_T5 = os.getenv("FORESIGHT_RUN_T5") == "1"
pytestmark = pytest.mark.skipif(not RUN_T5, reason="set FORESIGHT_RUN_T5=1 to run T5 tests")


def test_train_and_predict_valid_labels() -> None:
    from foresight_classification import LABELS
    from foresight_classification.classifier import T5Classifier
    from foresight_classification.data import DatasetConfig, generate, train_test_split
    from foresight_classification.train_lora import train_lora

    df = generate(DatasetConfig(n_per_class=40, seed=1))
    train, test = train_test_split(df, test_frac=0.25, seed=0)

    with tempfile.TemporaryDirectory() as d:
        adapter = train_lora(train, d, epochs=1, batch_size=16)
        clf = T5Classifier.from_pretrained(adapter)
        preds = clf.predict(test["text"].tolist()[:8])

    assert len(preds) == 8
    assert all(p in LABELS for p in preds)
