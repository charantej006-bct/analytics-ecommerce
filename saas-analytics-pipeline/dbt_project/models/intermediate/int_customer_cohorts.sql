with customers as (
    select * from {{ref('stg_customers')}}
),
subscriptions as (
    select * from {{ref('stg_subscriptions')}}
), 

plans as (
    select * from {{ref('stg_plans')}}
), 

first_subscription as (
    select 
    s.customer_id,s.plan_id,p.tier as initial_tier,p.monthly_price as initial_mrr,ROW_NUMBER() over(PARTITION by s.customer_id order by s.start_date asc) as rn 
    from subscriptions as s
    inner join plans as p
    on s.plan_id = p.plan_id
),

cohort_base as (
    select 
    c.customer_id,c.signup_date,date_trunc('month',c.signup_date) :: date as cohort_month,
    c.acquisition_channel,c.country,c.company_size,fs.initial_tier,fs.initial_mrr
    from customers as c
    left join first_subscription as fs 
    on c.customer_id = fs.customer_id
    and fs.rn = 1
)

select * from cohort_base