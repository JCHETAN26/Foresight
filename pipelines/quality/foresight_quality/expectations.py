"""Great Expectations suites for the Foresight lakehouse.

These gates run *independently* of dbt's own tests: dbt tests assert the
transform logic; Great Expectations validates the data that lands in bronze and
the KPIs that come out of gold (schema, nullability, value ranges, row counts).
Airflow runs these after every dbt build and fails the DAG on a breach.

Uses the fluent, ephemeral-context API so no on-disk GE project is required.
"""

from __future__ import annotations

import great_expectations as gx
import pandas as pd
from great_expectations.core.expectation_validation_result import (
    ExpectationSuiteValidationResult,
)

_RATE_COLUMNS = ("churn_rate", "refund_rate", "payment_failure_rate", "conversion_rate")


def _validator(df: pd.DataFrame) -> gx.validator.validator.Validator:
    """Build an ephemeral validator over an in-memory DataFrame."""
    context = gx.get_context()
    source = context.sources.add_pandas("foresight_ephemeral")
    asset = source.add_dataframe_asset(name="asset")
    batch_request = asset.build_batch_request(dataframe=df)
    suite = context.add_or_update_expectation_suite("foresight_suite")
    return context.get_validator(batch_request=batch_request, expectation_suite=suite)


def validate_gold(df: pd.DataFrame) -> ExpectationSuiteValidationResult:
    """Validate the gold KPI time series (`fct_kpi_timeseries`)."""
    v = _validator(df)
    v.expect_table_row_count_to_be_between(min_value=1)

    for col in ("tenant_id", "metric_date", "mrr", "active_subscriptions"):
        v.expect_column_to_exist(col)

    v.expect_column_values_to_not_be_null("tenant_id")
    v.expect_column_values_to_not_be_null("metric_date")
    v.expect_column_values_to_not_be_null("mrr")

    # Counts are non-negative; rates are fractions in [0, 1] (nulls allowed
    # where a rate is undefined, e.g. conversion with no checkouts).
    v.expect_column_values_to_be_between("active_subscriptions", min_value=0)
    for col in _RATE_COLUMNS:
        v.expect_column_values_to_be_between(col, min_value=0, max_value=1)

    return v.validate()


def validate_bronze(df: pd.DataFrame) -> ExpectationSuiteValidationResult:
    """Validate the raw bronze events (`bronze_stripe_events`)."""
    v = _validator(df)
    v.expect_table_row_count_to_be_between(min_value=1)

    for col in ("event_id", "tenant_id", "event_type", "payload"):
        v.expect_column_to_exist(col)

    v.expect_column_values_to_not_be_null("event_id")
    v.expect_column_values_to_not_be_null("tenant_id")
    v.expect_column_values_to_not_be_null("event_type")

    return v.validate()
