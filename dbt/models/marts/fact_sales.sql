-- Grain: one row per transaction item, enriched with store/customer/promo context.
with items as (
    select * from {{ ref('stg_transaction_items') }}
),

transactions as (
    select * from {{ ref('stg_transactions') }}
),

promo_usage as (
    select
        tenant_id,
        transaction_id,
        promo_id,
        discount_applied
    from {{ ref('stg_transaction_promotions') }}
)

select
    concat(t.tenant_id, '-', toString(i.item_id)) as sale_key,
    concat(t.tenant_id, '-', toString(i.transaction_id)) as transaction_key,
    t.tenant_id as tenant_id,
    concat(t.tenant_id, '-', toString(t.customer_id)) as customer_key,
    concat(t.tenant_id, '-', toString(i.product_id)) as product_key,
    concat(t.tenant_id, '-', toString(t.store_id)) as store_key,
    toString(toDate(t.transaction_date)) as date_key,
    if(p.promo_id is not null, concat(t.tenant_id, '-', toString(p.promo_id)), NULL) as promo_key,
    t.transaction_date as transaction_date,
    t.payment_method as payment_method,
    i.quantity as quantity,
    i.unit_price as unit_price,
    i.discount as line_discount_pct,
    i.subtotal as subtotal,
    coalesce(p.discount_applied, 0) as promo_discount_applied,
    t.total_amount as transaction_total_amount
from items i
inner join transactions t
    on i.transaction_id = t.transaction_id and i.tenant_id = t.tenant_id
left join promo_usage p
    on t.transaction_id = p.transaction_id and t.tenant_id = p.tenant_id
