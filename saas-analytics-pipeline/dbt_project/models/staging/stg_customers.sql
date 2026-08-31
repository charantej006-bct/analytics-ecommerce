with source as (
    select * from {{source("raw","customers")}}
),

cleaned as (
    select customer_id,signup_date::date as signup_date,COALESCE(trim(acquisition_channel , '') ,'unknown') as acquisition_channel,
    trim(country) as country,
    trim(company_size) as company_size,
    from source
)

select * from cleaned

