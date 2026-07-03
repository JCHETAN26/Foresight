-- The gold grain is one row per (tenant_id, metric_date). Fail if duplicated.
select
    tenant_id,
    metric_date,
    count(*) as n
from {{ ref('fct_kpi_timeseries') }}
group by tenant_id, metric_date
having count(*) > 1
