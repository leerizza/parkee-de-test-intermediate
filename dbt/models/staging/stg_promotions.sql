with unioned as (
    select * from raw.raw_tenant_1__promotions FINAL
    union all
    select * from raw.raw_tenant_2__promotions FINAL
    union all
    select * from raw.raw_tenant_3__promotions FINAL
)

select
    toInt64(promo_id)                    as promo_id,
    _tenant                              as tenant_id,
    promo_name                           as promo_name,
    promo_type                           as promo_type,
    toDecimal64(discount_pct, 2)         as discount_pct,
    parseDateTimeBestEffort(start_date)  as start_date,
    parseDateTimeBestEffort(end_date)    as end_date,
    toDecimal64(min_purchase, 2)         as min_purchase
from unioned
