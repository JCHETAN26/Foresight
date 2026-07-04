"""Foresight batch orchestration DAG.

Runs the transform-and-validate cycle on a schedule:

    dbt_build → quality_gates → ready_for_detection

- `dbt_build`      rebuilds silver + gold from bronze (dbt).
- `quality_gates`  runs the Great Expectations suites on bronze + gold and
                   fails the run on any breach — bad data never reaches the
                   detection layer.
- `ready_for_detection` is the handoff point the ML detection/retraining jobs
  (M2) hang off of.

Heavy imports (`foresight_quality`) are done inside the task body so the DAG
file parses even where only Airflow core is installed (e.g. the scheduler).
"""

from __future__ import annotations

import os

import pendulum
from airflow.decorators import task
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

DBT_DIR = os.getenv("FORESIGHT_DBT_DIR", "/opt/foresight/pipelines/dbt/foresight")
DBT_TARGET = os.getenv("FORESIGHT_DBT_TARGET", "databricks")
DUCKDB_PATH = os.getenv("FORESIGHT_DUCKDB", f"{DBT_DIR}/target/foresight.duckdb")

default_args = {
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=5),
}

with DAG(
    dag_id="foresight_pipeline",
    description="Rebuild KPI models and gate on data quality.",
    schedule="@hourly",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    default_args=default_args,
    tags=["foresight", "dbt", "quality"],
) as dag:
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && dbt build --target {DBT_TARGET} --profiles-dir ."
        ),
    )

    @task(task_id="quality_gates")
    def quality_gates() -> None:
        """Run the Great Expectations gates; raise to fail the DAG on breach."""
        from foresight_quality.run_quality import main

        rc = main(["--duckdb", DUCKDB_PATH])
        if rc != 0:
            raise RuntimeError("Great Expectations quality gates failed")

    ready_for_detection = EmptyOperator(task_id="ready_for_detection")

    dbt_build >> quality_gates() >> ready_for_detection
