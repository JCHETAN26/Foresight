"""Unit tests for the bronze transform, run on a local SparkSession."""

from __future__ import annotations

import datetime as dt
import json

import pytest
from pyspark.sql import SparkSession

from foresight_streaming.transform import BRONZE_COLUMNS, to_bronze


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    s = (
        SparkSession.builder.master("local[1]")
        .appName("foresight-streaming-tests")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield s
    s.stop()


def _envelope(tenant: str, created: int, obj: dict) -> str:
    return json.dumps(
        {
            "id": "evt_test_1",
            "source": "stripe",
            "tenant_id": tenant,
            "event_type": "invoice.paid",
            "livemode": False,
            "created": created,
            "api_version": "2024-06-20",
            "data": {"object": obj},
        }
    )


def test_to_bronze_projects_envelope(spark: SparkSession) -> None:
    obj = {"id": "in_1", "amount": 5000, "currency": "usd", "subscription": "sub_1"}
    raw = spark.createDataFrame(
        [(_envelope("acct_x", 1780308180, obj).encode(),)], ["value"]
    )

    bronze = to_bronze(raw)
    assert bronze.columns == BRONZE_COLUMNS

    row = bronze.collect()[0]
    assert row["event_id"] == "evt_test_1"
    assert row["source"] == "stripe"
    assert row["tenant_id"] == "acct_x"
    assert row["event_type"] == "invoice.paid"
    assert row["livemode"] is False
    assert row["created_epoch"] == 1780308180
    # created 1780308180 == 2026-06-01 (UTC 10:00)
    assert row["event_date"] == dt.date(2026, 6, 1)
    assert row["ingested_at"] is not None

    # payload is the raw Stripe object as JSON, with types preserved.
    payload = json.loads(row["payload"])
    assert payload == obj
    assert payload["amount"] == 5000


def test_to_bronze_handles_null_data_object(spark: SparkSession) -> None:
    # An envelope whose data.object is absent must still project (payload null),
    # not drop the row — bronze is append-everything.
    env = json.dumps(
        {
            "id": "evt_test_2",
            "source": "stripe",
            "tenant_id": "acct_y",
            "event_type": "ping",
            "livemode": True,
            "created": 1780308180,
            "api_version": "2024-06-20",
            "data": {},
        }
    )
    raw = spark.createDataFrame([(env.encode(),)], ["value"])
    row = to_bronze(raw).collect()[0]
    assert row["event_id"] == "evt_test_2"
    assert row["payload"] is None
