"""Bronze transform — Kafka envelope bytes → bronze lakehouse rows.

Kept as a pure DataFrame→DataFrame function (no Kafka/Iceberg I/O) so the
projection logic is unit-testable with a plain batch DataFrame. The streaming
job in `bronze_ingest.py` wires this between the Kafka source and Iceberg sink.
"""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# Scalar fields of the Foresight ingestion envelope. `data` is intentionally
# omitted here and captured verbatim as a JSON string (`payload`) to preserve
# the raw Stripe object with full type fidelity — the essence of a bronze layer.
ENVELOPE_SCHEMA = StructType(
    [
        StructField("id", StringType()),
        StructField("source", StringType()),
        StructField("tenant_id", StringType()),
        StructField("event_type", StringType()),
        StructField("livemode", BooleanType()),
        StructField("created", LongType()),
        StructField("api_version", StringType()),
    ]
)

# Column order of the bronze Iceberg table.
BRONZE_COLUMNS = [
    "event_id",
    "source",
    "tenant_id",
    "event_type",
    "livemode",
    "created_epoch",
    "api_version",
    "payload",
    "ingested_at",
    "event_date",
]


def to_bronze(raw: DataFrame) -> DataFrame:
    """Project a Kafka source DataFrame (with a `value` column) to bronze rows.

    Parses the envelope's scalar fields via a typed schema, extracts the raw
    Stripe object (`data.object`) as a JSON string, and adds ingestion lineage
    (`ingested_at`) plus the partition column (`event_date`).
    """
    parsed = raw.select(
        F.from_json(F.col("value").cast("string"), ENVELOPE_SCHEMA).alias("e"),
        F.col("value").cast("string").alias("_raw"),
    )

    return parsed.select(
        F.col("e.id").alias("event_id"),
        F.col("e.source").alias("source"),
        F.col("e.tenant_id").alias("tenant_id"),
        F.col("e.event_type").alias("event_type"),
        F.col("e.livemode").alias("livemode"),
        F.col("e.created").alias("created_epoch"),
        F.col("e.api_version").alias("api_version"),
        F.get_json_object(F.col("_raw"), "$.data.object").alias("payload"),
        F.current_timestamp().alias("ingested_at"),
        F.to_date(F.timestamp_seconds(F.col("e.created"))).alias("event_date"),
    )
