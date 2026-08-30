with source as (
    select * from {{source("raw", "plans")}}
),

cleaned as (
    select plan_id,trim(plan_name) as plan_name,lower(trim(tier)) as tier,monthly_price::numeric(10,2) as monthly_price,
    lower(trim(billing_interval)) as billing_interval from source
)

select * from cleaned