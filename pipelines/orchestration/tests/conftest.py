"""Isolate Airflow config/state into a throwaway home for the test run."""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("AIRFLOW_HOME", tempfile.mkdtemp(prefix="foresight_airflow_"))
os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")
os.environ.setdefault("AIRFLOW__CORE__UNIT_TEST_MODE", "True")
os.environ.setdefault("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", "sqlite://")
