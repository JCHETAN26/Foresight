"""Bronze ingest — Spark Structured Streaming job.

Reads the per-tenant Stripe event streams from Kafka / Azure Event Hubs and
appends them, immutably, to the Iceberg bronze table partitioned by
(tenant_id, event_date). Business normalization happens downstream in dbt;
this job's only job is durable, exactly-once landing of raw events.

Run on Databricks (or spark-submit with the Kafka + Iceberg packages):

    spark-submit \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,\
org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2 \
      foresight_streaming/bronze_ingest.py
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession

from foresight_streaming.config import config
from foresight_streaming.transform import to_bronze


def build_spark() -> SparkSession:
    """SparkSession with the Iceberg catalog configured.

    On Databricks the catalog is typically pre-wired via Unity Catalog; these
    settings make the job self-contained for spark-submit as well.
    """
    return (
        SparkSession.builder.appName("foresight-bronze-ingest")
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config(
            f"spark.sql.catalog.{config.catalog}",
            "org.apache.iceberg.spark.SparkCatalog",
        )
        .config(f"spark.sql.catalog.{config.catalog}.type", "hadoop")
        .getOrCreate()
    )


def read_kafka(spark: SparkSession) -> DataFrame:
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", config.bootstrap_servers)
        .option("subscribePattern", config.subscribe_pattern)
        .option("startingOffsets", config.starting_offsets)
        .option("maxOffsetsPerTrigger", config.max_offsets_per_trigger)
        .load()
    )


def run() -> None:
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    bronze = to_bronze(read_kafka(spark))

    query = (
        bronze.writeStream.format("iceberg")
        .outputMode("append")
        .option("checkpointLocation", config.checkpoint_location)
        .option("fanout-enabled", "true")  # many tenant partitions per micro-batch
        .trigger(processingTime=config.trigger_interval)
        .toTable(config.bronze_table)
    )
    query.awaitTermination()


if __name__ == "__main__":
    run()
