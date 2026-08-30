with sub as (
    select * from {{ref('stg_subscriptions')}}
),

plans as (
    select * from {{ref('stg_plans.sql')}}
),

subscription_period as (
    
)