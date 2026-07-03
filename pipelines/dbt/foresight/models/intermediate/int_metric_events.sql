-- Intermediate: map each normalized event to its KPI contributions.
-- One row per event, with signed/indicator columns the gold layer sums per
-- tenant-day. Keeping the classification here (not in gold) means the KPI
-- definitions live in exactly one place.

with events as (
    select * from {{ ref('stg_stripe_events') }}
)

select
    tenant_id,
    event_date,
    event_ts,
    event_id,
    event_type,

    -- MRR movement: new subscriptions add, cancellations remove.
    case
        when event_type = 'customer.subscription.created' then amount_cents
        when event_type = 'customer.subscription.deleted' then -amount_cents
        else 0
    end as mrr_delta_cents,

    case when event_type = 'customer.subscription.created' then 1 else 0 end as is_new_sub,
    case when event_type = 'customer.subscription.deleted' then 1 else 0 end as is_churned_sub,

    -- Revenue & payment reliability.
    case when event_type = 'invoice.paid' then amount_cents else 0 end as gross_revenue_cents,
    case when event_type = 'invoice.paid' then 1 else 0 end as is_successful_payment,
    case when event_type = 'invoice.payment_failed' then 1 else 0 end as is_failed_payment,

    -- Refunds.
    case when event_type = 'charge.refunded' then amount_cents else 0 end as refund_cents,

    -- Checkout conversion.
    case when event_type = 'checkout.session.completed' then 1 else 0 end as is_checkout_completed,
    case when event_type = 'checkout.session.expired' then 1 else 0 end as is_checkout_expired

from events
