with source as (
    select * from {{source("raw","subscriptions")}}
),

cleaned as (
    select subscription_id,
    customer_id,
    plan_id,
    start_date::date as start_date,
    end_date::date as end_date,
    lower(trim(status)) as status

    from source   
)

select * from cleaned