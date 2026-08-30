with source as (
    select * from {{ source('raw', 'subscription_events') }}
),

cleaned as (
    select
        event_id,
        subscription_id,
        lower(trim(event_type)) as event_type,
        event_date::date as event_date,
        nullif(trim(previous_plan_id), '') as previous_plan_id,
        nullif(trim(new_plan_id), '') as new_plan_id
    from source
)

select * from cleaned