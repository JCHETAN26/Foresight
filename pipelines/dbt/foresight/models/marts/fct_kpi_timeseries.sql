-- Gold: per-tenant, per-day KPI time series.
-- MRR and active-subscription counts are running (stateful) totals; revenue,
-- refund, payment, and conversion metrics are daily. Monetary values are in
-- dollars; rates are fractions in [0, 1] rounded to 4 dp.

with metric_events as (
    select * from {{ ref('int_metric_events') }}
),

daily as (
    select
        tenant_id,
        event_date as metric_date,
        sum(mrr_delta_cents) as mrr_delta_cents,
        sum(is_new_sub) as new_subscriptions,
        sum(is_churned_sub) as churned_subscriptions,
        sum(gross_revenue_cents) as gross_revenue_cents,
        sum(refund_cents) as refund_cents,
        sum(is_successful_payment) as successful_payments,
        sum(is_failed_payment) as failed_payments,
        sum(is_checkout_completed) as checkouts_completed,
        sum(is_checkout_expired) as checkouts_expired
    from metric_events
    group by tenant_id, event_date
),

running as (
    select
        *,
        sum(mrr_delta_cents) over (
            partition by tenant_id
            order by metric_date
            rows between unbounded preceding and current row
        ) as mrr_cents_cum,
        sum(new_subscriptions - churned_subscriptions) over (
            partition by tenant_id
            order by metric_date
            rows between unbounded preceding and current row
        ) as active_subscriptions
    from daily
)

select
    tenant_id,
    metric_date,

    -- Recurring revenue & subscription state (running).
    round(mrr_cents_cum / 100.0, 2) as mrr,
    active_subscriptions,
    new_subscriptions,
    churned_subscriptions,
    -- Churn rate against subscriptions active at the start of the day.
    round(
        churned_subscriptions
        / nullif(active_subscriptions - new_subscriptions + churned_subscriptions, 0),
        4
    ) as churn_rate,

    -- Revenue & refunds (daily).
    round(gross_revenue_cents / 100.0, 2) as gross_revenue,
    round(refund_cents / 100.0, 2) as refund_amount,
    round(refund_cents / nullif(gross_revenue_cents, 0), 4) as refund_rate,

    -- Payment reliability (daily).
    successful_payments,
    failed_payments,
    round(
        failed_payments / nullif(failed_payments + successful_payments, 0), 4
    ) as payment_failure_rate,

    -- Checkout conversion (daily).
    checkouts_completed,
    checkouts_expired,
    round(
        checkouts_completed / nullif(checkouts_completed + checkouts_expired, 0), 4
    ) as conversion_rate

from running
