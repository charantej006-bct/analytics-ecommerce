with payments as (
    select * from {{ ref('stg_payments') }}
),

subscriptions as (
    select * from {{ ref('stg_subscriptions') }}
)

select
    p.payment_id,
    p.subscription_id,
    s.customer_id,
    p.payment_date,
    date_trunc('month', p.payment_date)::date as payment_month,
    p.amount,
    p.currency,
    p.status,
    case when p.status = 'succeeded' then 1 else 0 end as is_successful_payment,
    case when p.status = 'failed' then 1 else 0 end as is_failed_payment,
    case when p.status = 'refunded' then 1 else 0 end as is_refunded_payment
from payments p
left join subscriptions s
    on p.subscription_id = s.subscription_id