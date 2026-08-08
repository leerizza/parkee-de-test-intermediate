select
    concat(tenant_id, '-', toString(promo_id)) as promo_key,
    promo_id,
    tenant_id,
    promo_name,
    promo_type,
    discount_pct,
    start_date,
    end_date,
    min_purchase
from {{ ref('stg_promotions') }}
