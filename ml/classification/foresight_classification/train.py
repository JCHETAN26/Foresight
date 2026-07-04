"""Train + benchmark: LoRA-T5 vs the TF-IDF baseline on held-out test data.

    python -m foresight_classification.train --epochs 3

Prints a comparison table (accuracy, macro-F1) and writes it to outputs/.
The GPT-4o zero-shot comparison from the project plan requires Azure OpenAI
access; a hook for it lives in `benchmark`-adjacent code but is not run here.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import pandas as pd

from foresight_classification.baseline import predict as baseline_predict
from foresight_classification.baseline import train_baseline
from foresight_classification.benchmark import evaluate, per_class_f1
from foresight_classification.data import (
    DatasetConfig,
    generate,
    template_holdout_split,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--n-per-class", type=int, default=350)
    parser.add_argument("--out", default="outputs")
    args = parser.parse_args(argv)

    df = generate(DatasetConfig(n_per_class=args.n_per_class))
    # Template holdout: the test set uses phrasings never seen in training.
    train, test = template_holdout_split(df, n_holdout_per_class=2, seed=0)
    y_true = test["label"].tolist()
    print(f"train={len(train)}  test={len(test)} (unseen templates)")

    # Baseline
    base = train_baseline(train)
    base_pred = baseline_predict(base, test["text"].tolist())
    base_metrics = evaluate(y_true, base_pred)

    # LoRA T5 (heavy imports deferred so the baseline path needs no torch)
    from foresight_classification.classifier import T5Classifier
    from foresight_classification.train_lora import train_lora

    with tempfile.TemporaryDirectory() as d:
        adapter = train_lora(train, d, epochs=args.epochs)
        clf = T5Classifier.from_pretrained(adapter)
        t5_pred = clf.predict(test["text"].tolist())
    t5_metrics = evaluate(y_true, t5_pred)

    table = pd.DataFrame(
        [
            {"model": "TF-IDF + LogReg", **base_metrics},
            {"model": "LoRA T5-small", **t5_metrics},
        ]
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "classification_benchmark.csv", index=False)
    (out / "t5_per_class_f1.json").write_text(json.dumps(per_class_f1(y_true, t5_pred), indent=2))

    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
