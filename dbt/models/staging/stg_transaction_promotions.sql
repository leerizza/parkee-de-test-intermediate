with unioned as (
    select * from raw.raw_tenant_1__transaction_promotions FINAL
    union all
    select * from raw.raw_tenant_2__transaction_promotions FINAL
    union all
    select * from raw.raw_tenant_3__transaction_promotions FINAL
)

select
    toInt64(id)                       as transaction_promotion_id,
    _tenant                           as tenant_id,
    toInt64(transaction_id)           as transaction_id,
    toInt64(promo_id)                 as promo_id,
    toDecimal64(discount_applied, 2)  as discount_applied
from unioned
