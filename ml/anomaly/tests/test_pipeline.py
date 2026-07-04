"""End-to-end integration test: KPI history -> typed anomaly records."""

from __future__ import annotations

from foresight_classification import LABELS
from foresight_detection.data import METRICS, DatasetConfig, generate
from foresight_detection.ensemble import EnsembleConfig

from foresight_anomaly.describe import describe_anomaly
from foresight_anomaly.pipeline import AnomalyPipeline
from foresight_anomaly.records import AnomalyRecord


def _features():
    df = generate(DatasetConfig(n_tenants=8, n_days=70, seed=2))
    return df[["tenant_id", "day", *METRICS]]


def test_pipeline_produces_typed_records() -> None:
    pipe = AnomalyPipeline(
        detection_config=EnsembleConfig(epochs=8), threshold=0.97
    )
    records = pipe.run(_features())

    assert len(records) > 0
    for r in records:
        assert isinstance(r, AnomalyRecord)
        assert r.anomaly_type in LABELS
        assert 0.0 <= r.type_confidence <= 1.0
        assert r.description and r.description != ""
        assert len(r.top_contributors) <= 3
        assert 0.0 <= r.anomaly_score <= 1.0


def test_records_sorted_by_score_desc() -> None:
    pipe = AnomalyPipeline(detection_config=EnsembleConfig(epochs=6), threshold=0.95)
    records = pipe.run(_features())
    scores = [r.anomaly_score for r in records]
    assert scores == sorted(scores, reverse=True)


def test_describe_reflects_moved_metric() -> None:
    # A refund-rate spike should surface refund language for the classifier.
    metrics = {"mrr": 9000.0, "conversion_rate": 0.3, "refund_rate": 0.18, "checkout_volume": 500.0}
    baseline = {
        "mrr": 10000.0, "conversion_rate": 0.3, "refund_rate": 0.03, "checkout_volume": 500.0,
    }
    contribs = [("refund_rate", 4.0), ("mrr", -1.0)]
    text = describe_anomaly(metrics, baseline, contribs)
    assert "refund" in text.lower()
