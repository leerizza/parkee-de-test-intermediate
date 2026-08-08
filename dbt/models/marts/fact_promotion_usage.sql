-- Grain: one row per transaction-promotion usage.
select
    concat(tp.tenant_id, '-', toString(tp.transaction_promotion_id)) as promotion_usage_key,
    concat(tp.tenant_id, '-', toString(tp.transaction_id)) as transaction_key,
    concat(tp.tenant_id, '-', toString(tp.promo_id)) as promo_key,
    tp.tenant_id as tenant_id,
    t.transaction_date as transaction_date,
    t.total_amount as transaction_total_amount,
    tp.discount_applied as discount_applied
from {{ ref('stg_transaction_promotions') }} tp
inner join {{ ref('stg_transactions') }} t
    on tp.transaction_id = t.transaction_id and tp.tenant_id = t.tenant_id
