with movements as (
    select * from {{ ref('int_mrr_movements') }}
),

plans as (
    select * from {{ ref('stg_plans') }}
),

churn_events as (
    select
        m.event_month,
        coalesce(p.tier, 'unknown') as tier,
        count(distinct m.customer_id) as churned_customers,
        sum(m.previous_mrr) as churned_mrr
    from movements m
    left join plans p
        on m.previous_plan_id = p.plan_id
    where m.movement_type = 'churn'
    group by m.event_month, coalesce(p.tier, 'unknown')
)

select * from churn_events