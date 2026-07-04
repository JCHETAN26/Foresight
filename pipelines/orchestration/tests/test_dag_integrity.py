"""DAG integrity tests — the standard Airflow safety net.

Loads every DAG in the folder and asserts: no import errors, the expected DAG
exists with the expected tasks, wiring is correct, and retries are configured.
"""

from __future__ import annotations

from pathlib import Path

from airflow.models import DagBag

DAGS_DIR = str(Path(__file__).resolve().parents[1] / "dags")


def _dagbag() -> DagBag:
    return DagBag(dag_folder=DAGS_DIR, include_examples=False)


def test_no_import_errors() -> None:
    assert _dagbag().import_errors == {}


def test_pipeline_dag_structure() -> None:
    # Read from the parsed in-memory collection (no metadata DB round-trip).
    dag = _dagbag().dags["foresight_pipeline"]
    assert {t.task_id for t in dag.tasks} == {
        "dbt_build",
        "quality_gates",
        "ready_for_detection",
    }


def test_pipeline_task_wiring() -> None:
    dag = _dagbag().dags["foresight_pipeline"]
    assert dag.get_task("quality_gates").upstream_task_ids == {"dbt_build"}
    assert dag.get_task("ready_for_detection").upstream_task_ids == {"quality_gates"}


def test_tasks_have_retries() -> None:
    dag = _dagbag().dags["foresight_pipeline"]
    assert dag.get_task("dbt_build").retries == 2
