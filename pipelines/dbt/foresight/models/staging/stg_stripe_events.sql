-- Silver: typed, deduplicated, normalized Stripe events.
-- One row per delivered event. Parses the raw JSON payload into typed columns
-- and derives the event timestamp/date. Webhook re-deliveries (same event_id)
-- are deduped, keeping the first-ingested copy.

with source as (
    select * from {{ source('lakehouse', 'bronze_stripe_events') }}
),

deduped as (
    select
        *,
        row_number() over (
            partition by event_id
            order by ingested_at asc
        ) as _rn
    from source
),

renamed as (
    select
        event_id,
        tenant_id,
        event_type,
        {{ epoch_to_ts('created_epoch') }} as event_ts,
        cast({{ epoch_to_ts('created_epoch') }} as date) as event_date,
        {{ json_get('payload', 'id') }} as object_id,
        {{ json_get('payload', 'customer') }} as customer_id,
        {{ json_get('payload', 'subscription') }} as subscription_id,
        {{ json_get('payload', 'status') }} as status,
        {{ json_get('payload', 'currency') }} as currency,
        cast({{ json_get('payload', 'amount') }} as bigint) as amount_cents,
        livemode
    from deduped
    where _rn = 1
)

select * from renamed
