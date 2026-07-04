"""CLI: run the Great Expectations gates against the dbt-built lakehouse.

Reads bronze + gold from the DuckDB database produced by `dbt build` (or, in
production, from Databricks) and exits non-zero if any suite fails — so Airflow
and CI can gate on it.
"""

from __future__ import annotations

import argparse
import sys

import duckdb

from foresight_quality.expectations import validate_bronze, validate_gold

BRONZE_QUERY = "select * from lakehouse.bronze_stripe_events"
GOLD_QUERY = "select * from marts.fct_kpi_timeseries"


def _load(db_path: str, query: str):
    con = duckdb.connect(db_path, read_only=True)
    try:
        return con.execute(query).df()
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Foresight data-quality gates.")
    parser.add_argument(
        "--duckdb",
        default="../dbt/foresight/target/foresight.duckdb",
        help="Path to the DuckDB database built by dbt.",
    )
    args = parser.parse_args(argv)

    checks = [
        ("bronze_stripe_events", validate_bronze, BRONZE_QUERY),
        ("fct_kpi_timeseries", validate_gold, GOLD_QUERY),
    ]

    failed = False
    for name, validate, query in checks:
        df = _load(args.duckdb, query)
        result = validate(df)
        n = len(result.results)
        passed = sum(1 for r in result.results if r.success)
        status = "PASS" if result.success else "FAIL"
        print(f"[{status}] {name}: {passed}/{n} expectations passed ({len(df)} rows)")
        if not result.success:
            failed = True
            for r in result.results:
                if not r.success:
                    print(f"    ✗ {r.expectation_config.expectation_type} "
                          f"{r.expectation_config.kwargs}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
