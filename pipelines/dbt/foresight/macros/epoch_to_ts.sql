{#
    epoch_to_ts(column) — convert a unix-epoch-seconds column to a timestamp.
    Engine-specific, dispatched so models stay identical:
      - DuckDB:            to_timestamp(col)
      - Spark/Databricks:  timestamp_seconds(col)
#}

{% macro epoch_to_ts(column) %}
    {{ return(adapter.dispatch('epoch_to_ts', 'foresight')(column)) }}
{% endmacro %}

{% macro default__epoch_to_ts(column) %}
    timestamp_seconds({{ column }})
{% endmacro %}

{% macro duckdb__epoch_to_ts(column) %}
    to_timestamp({{ column }})
{% endmacro %}
