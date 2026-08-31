with movements as (
    select * from {{ ref('int_mrr_movements') }}
),

monthly_bridge as (
    select
        event_month,
        sum(case when movement_type = 'new' then new_mrr else 0 end) as new_mrr,
        sum(case when movement_type = 'expansion' then mrr_change else 0 end) as expansion_mrr,
        sum(case when movement_type = 'reactivation' then new_mrr else 0 end) as reactivation_mrr,
        sum(case when movement_type = 'contraction' then abs(mrr_change) else 0 end) as contraction_mrr,
        sum(case when movement_type = 'churn' then previous_mrr else 0 end) as churned_mrr,
        sum(
            case 
                when movement_type in ('new', 'reactivation') then new_mrr
                when movement_type = 'expansion' then mrr_change
                when movement_type = 'contraction' then mrr_change
                when movement_type = 'churn' then -previous_mrr
                else 0 
            end
        ) as net_mrr_change
    from movements
    group by event_month
)

select
    event_month,
    new_mrr,
    expansion_mrr,
    reactivation_mrr,
    contraction_mrr,
    churned_mrr,
    net_mrr_change,
    sum(net_mrr_change) over (order by event_month rows between unbounded preceding and current row) as ending_mrr
from monthly_bridge
order by event_month asc