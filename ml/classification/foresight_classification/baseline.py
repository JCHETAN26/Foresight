"""TF-IDF + logistic-regression baseline classifier.

A strong, cheap baseline. The LoRA-fine-tuned T5 has to beat this to justify its
cost — and on templated text a bag-of-words model is a genuinely hard baseline.
"""

from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def train_baseline(train_df: pd.DataFrame) -> Pipeline:
    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
            ("clf", LogisticRegression(max_iter=1000, C=4.0)),
        ]
    )
    pipe.fit(train_df["text"], train_df["label"])
    return pipe


def predict(model: Pipeline, texts: list[str]) -> list[str]:
    return list(model.predict(texts))
