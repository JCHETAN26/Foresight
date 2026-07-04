"""AnomalyPipeline — gold KPI history in, typed anomaly records out.

    detect (ensemble) -> flag -> attribute (per-metric deviation)
    -> describe -> classify (type + confidence)

This is the concrete M1->M2 integration: the detector runs on the real gold
feature schema, and every flagged anomaly is turned into a self-contained record
the agent/alerting can consume.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from foresight_classification.baseline import train_baseline
from foresight_classification.data import DatasetConfig as ClfDatasetConfig
from foresight_classification.data import generate as generate_clf
from foresight_detection.data import METRICS
from foresight_detection.ensemble import DetectionEnsemble, EnsembleConfig
from sklearn.pipeline import Pipeline

from foresight_anomaly.describe import describe_anomaly
from foresight_anomaly.records import AnomalyRecord


def default_classifier() -> Pipeline:
    """Train the TF-IDF anomaly-type classifier (the M2 production choice)."""
    return train_baseline(generate_clf(ClfDatasetConfig()))


class AnomalyPipeline:
    def __init__(
        self,
        classifier: Pipeline | None = None,
        detection_config: EnsembleConfig | None = None,
        threshold: float = 0.95,
    ) -> None:
        self.classifier = classifier or default_classifier()
        self.detection_config = detection_config
        self.threshold = threshold  # on the ensemble score (rank-percentile in [0,1])

    def _classify(self, text: str) -> tuple[str, float]:
        proba = self.classifier.predict_proba([text])[0]
        idx = int(np.argmax(proba))
        return str(self.classifier.classes_[idx]), float(proba[idx])

    def run(self, feature_df: pd.DataFrame) -> list[AnomalyRecord]:
        """Detect, attribute, describe, and classify anomalies in a KPI frame."""
        df = feature_df.sort_values(["tenant_id", "day"]).reset_index(drop=True)
        scores = DetectionEnsemble(self.detection_config).fit_score(df)

        # Per-tenant baselines for attribution + description.
        stats = df.groupby("tenant_id")[METRICS].agg(["mean", "std"])

        records: list[AnomalyRecord] = []
        for i in np.where(scores >= self.threshold)[0]:
            row = df.iloc[i]
            tenant = row["tenant_id"]
            means = {m: float(stats.loc[tenant, (m, "mean")]) for m in METRICS}
            sds = {m: float(stats.loc[tenant, (m, "std")]) or 1.0 for m in METRICS}
            values = {m: float(row[m]) for m in METRICS}

            # Signed deviation in standard deviations; rank by magnitude.
            contribs = sorted(
                ((m, (values[m] - means[m]) / sds[m]) for m in METRICS),
                key=lambda p: abs(p[1]),
                reverse=True,
            )
            description = describe_anomaly(values, means, contribs)
            atype, confidence = self._classify(description)

            records.append(
                AnomalyRecord(
                    tenant_id=str(tenant),
                    metric_date=str(row.get("metric_date", row["day"])),
                    anomaly_score=float(scores[i]),
                    anomaly_type=atype,
                    type_confidence=confidence,
                    top_contributors=[(m, round(z, 2)) for m, z in contribs[:3]],
                    description=description,
                    metrics={m: round(values[m], 4) for m in METRICS},
                )
            )

        records.sort(key=lambda r: r.anomaly_score, reverse=True)
        return records
