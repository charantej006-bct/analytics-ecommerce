with events as (
    select * from {{ref("stg_subscriptions_events")}}
),

subscriptions as (
    select * from {{ref("stg_subscriptions")}}
),

plans as (
    select * from {{ref("stg_plans")}}
),  

joined_events as (
    select 
    e.event_id,e.subscription_id,s.customer_id,e.event_type,e.event_date,
    date_trunc('month',e.event_date) :: date as event_month,
    e.previous_plan_id,
    prev_p.monthly_price as previous_mrr,
    e.new_plan_id,
    new_p.monthly_price as new_mrr,
    COALESCE(new_p.monthly_price,0) - COALESCE(prev_p.monthly_price,0) as mrr_change,
    from events as e
    inner join subscriptions as s
    on e.subscription_id = s.subscription_id
    left join plans as prev_p
    on e.previous_plan_id = prev_p.plan_id
    left join plans as new_p
    on e.new_plan_id = new_p.plan_id
),

classified_movements as (
    select 
    event_id,subscription_id,customer_id,event_date,event_month,event_type,previous_plan_id,new_plan_id,
    COALESCE(previous_mrr,0) as previous_mrr,
    COALESCE(new_mrr,0) as new_mrr,
    mrr_change,
    CASE
      when event_type = 'created' then 'new'
      when event_type = 'reactivated' then 'reactivation'
      when event_type = 'upgraded' then 'expansion'
      when event_type = 'downgraded' then 'contraction'
      when event_type = 'canceled' then 'churn'
      else 'other'
    end as movement_type

from joined_events

)

select * from classified_movements