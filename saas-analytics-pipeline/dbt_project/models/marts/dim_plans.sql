with plans as (
    select * from {{ ref('stg_plans') }}
)

select
    plan_id,
    plan_name,
    tier,
    monthly_price,
    billing_interval
from plans