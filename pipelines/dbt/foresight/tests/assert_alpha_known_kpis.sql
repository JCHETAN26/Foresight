-- Correctness anchor: assert the exact KPI values for tenant acct_alpha across
-- the three seeded days. Any drift in the MRR / churn / refund / payment /
-- conversion logic fails this test. Returns offending rows (test passes on 0).
with expected (
    metric_date, mrr, churn_rate, refund_rate, payment_failure_rate, conversion_rate
) as (
    values
        (date '2026-06-01', 150.0, cast(null as double), 0.0, 0.0, 0.6667),
        (date '2026-06-02', 200.0, 0.0, 0.4, 0.5, 0.5),
        (date '2026-06-03', 150.0, 0.3333, 0.0, 0.5, 1.0)
),

actual as (
    select *
    from {{ ref('fct_kpi_timeseries') }}
    where tenant_id = 'acct_alpha'
)

select
    e.metric_date,
    e.mrr as expected_mrr,
    a.mrr as actual_mrr,
    e.churn_rate as expected_churn,
    a.churn_rate as actual_churn
from expected e
left join actual a on a.metric_date = e.metric_date
where a.metric_date is null
   or a.mrr is distinct from e.mrr
   or a.churn_rate is distinct from e.churn_rate
   or a.refund_rate is distinct from e.refund_rate
   or a.payment_failure_rate is distinct from e.payment_failure_rate
   or a.conversion_rate is distinct from e.conversion_rate
