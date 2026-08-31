with sub as (
    select * from {{ref('stg_subscriptions')}}
),

plans as (
    select * from {{ref('stg_plans')}}
),

subscription_period as (
    select 
    s.subscription_id,
    s.customer_id,
    s.plan_id,
    p.tier,
    p.monthly_price as mrr,
    s.start_date,
    s.end_date,
    COALESCE(s.end_date,'2099-12-31' :: date) as valid_date,
    s.status
    from sub as s

    inner join plans as p
    on s.plan_id = p.plan_id
)

select * from subscription_period