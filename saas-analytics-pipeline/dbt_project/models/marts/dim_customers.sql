with cohorts as (
    select * from {{ ref('int_customer_cohorts') }}
),

subscriptions as (
    select * from {{ ref('stg_subscriptions') }}
),

payments as (
    select * from {{ ref('stg_payments') }}
    where status = 'succeeded'
),

customer_aggregates as (
    select
        c.customer_id,
        c.signup_date,
        c.cohort_month,
        c.acquisition_channel,
        c.country,
        c.company_size,
        c.initial_tier,
        c.initial_mrr,
        count(distinct s.subscription_id) as total_subscriptions,
        coalesce(sum(p.amount), 0) as lifetime_value,
        max(case when s.status = 'active' then 1 else 0 end) = 1 as is_currently_active
    from cohorts c
    left join subscriptions s
        on c.customer_id = s.customer_id
    left join payments p
        on s.subscription_id = p.subscription_id
    group by
        c.customer_id,
        c.signup_date,
        c.cohort_month,
        c.acquisition_channel,
        c.country,
        c.company_size,
        c.initial_tier,
        c.initial_mrr
)

select * from customer_aggregates