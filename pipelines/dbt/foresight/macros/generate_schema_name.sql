{#
    Use custom schema names literally (bronze/staging/intermediate/marts) instead
    of dbt's default "<target_schema>_<custom>" concatenation. This keeps the
    local DuckDB layout aligned with the declared source schema (`lakehouse`) and
    mirrors the medallion schemas we use on Databricks.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
