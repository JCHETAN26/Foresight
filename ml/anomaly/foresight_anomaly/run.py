"""Demo/CLI: run the anomaly pipeline over gold KPIs or synthetic data.

    # against the dbt-built gold table
    python -m foresight_anomaly.run --duckdb ../../pipelines/dbt/foresight/target/foresight.duckdb

    # against synthetic KPI history (no infra needed)
    python -m foresight_anomaly.run --synthetic --limit 5
"""

from __future__ import annotations

import argparse
import json

from foresight_detection.data import METRICS, DatasetConfig, generate

from foresight_anomaly.pipeline import AnomalyPipeline


def _synthetic_features():
    df = generate(DatasetConfig())
    return df[["tenant_id", "day", *METRICS]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--duckdb", help="Path to the dbt-built gold DuckDB.")
    src.add_argument("--synthetic", action="store_true", help="Use synthetic KPI history.")
    parser.add_argument("--threshold", type=float, default=0.95)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    if args.duckdb:
        from foresight_anomaly.gold_adapter import load_gold_from_duckdb

        features = load_gold_from_duckdb(args.duckdb)
    else:
        features = _synthetic_features()

    records = AnomalyPipeline(threshold=args.threshold).run(features)
    print(f"detected {len(records)} anomalies (threshold={args.threshold})\n")
    for r in records[: args.limit]:
        print(
            f"[{r.tenant_id} @ {r.metric_date}] score={r.anomaly_score:.3f} "
            f"type={r.anomaly_type} ({r.type_confidence:.0%})"
        )
        print(f"    {r.description}")
        print(f"    drivers: {json.dumps(r.top_contributors)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
