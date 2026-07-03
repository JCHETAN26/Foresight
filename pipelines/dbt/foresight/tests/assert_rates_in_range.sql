-- All rate KPIs must be fractions in [0, 1] (or null when undefined).
select tenant_id, metric_date
from {{ ref('fct_kpi_timeseries') }}
where (churn_rate is not null and (churn_rate < 0 or churn_rate > 1))
   or (refund_rate is not null and (refund_rate < 0 or refund_rate > 1))
   or (payment_failure_rate is not null and (payment_failure_rate < 0 or payment_failure_rate > 1))
   or (conversion_rate is not null and (conversion_rate < 0 or conversion_rate > 1))
