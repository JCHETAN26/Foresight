{#
    json_get(column, key) — extract a top-level string value from a JSON column.

    Bronze stores each event's raw Stripe `data.object` as a JSON string, so the
    silver layer parses fields out of it. The extraction function differs per
    engine, so we dispatch on the adapter and keep the model SQL identical:
      - DuckDB (local/CI):   json_extract_string(col, '$.key')
      - Spark/Databricks:    get_json_object(col, '$.key')
#}

{% macro json_get(column, key) %}
    {{ return(adapter.dispatch('json_get', 'foresight')(column, key)) }}
{% endmacro %}

{% macro default__json_get(column, key) %}
    get_json_object({{ column }}, '$.{{ key }}')
{% endmacro %}

{% macro duckdb__json_get(column, key) %}
    json_extract_string({{ column }}, '$.{{ key }}')
{% endmacro %}

{% macro spark__json_get(column, key) %}
    get_json_object({{ column }}, '$.{{ key }}')
{% endmacro %}

{% macro databricks__json_get(column, key) %}
    get_json_object({{ column }}, '$.{{ key }}')
{% endmacro %}
