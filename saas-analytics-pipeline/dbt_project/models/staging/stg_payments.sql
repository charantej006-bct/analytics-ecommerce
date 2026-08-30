with source as (
    select * from {{ source('raw', 'payments') }}
),

cleaned as (
    select
        payment_id,
        subscription_id,
        amount::numeric(10, 2) as amount,
        upper(trim(currency)) as currency,
        lower(trim(status)) as status,
        payment_date::date as payment_date
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by payment_id
            order by payment_date desc
        ) as rn
    from cleaned
)

select
    payment_id,
    subscription_id,
    amount,
    currency,
    status,
    payment_date
from deduped
where rn = 1