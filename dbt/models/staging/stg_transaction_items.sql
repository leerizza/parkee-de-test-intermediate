with unioned as (
    select * from raw.raw_tenant_1__transaction_items FINAL
    union all
    select * from raw.raw_tenant_2__transaction_items FINAL
    union all
    select * from raw.raw_tenant_3__transaction_items FINAL
)

select
    toInt64(item_id)                as item_id,
    _tenant                         as tenant_id,
    toInt64(transaction_id)         as transaction_id,
    toInt64(product_id)             as product_id,
    toInt32(quantity)               as quantity,
    toDecimal64(unit_price, 2)      as unit_price,
    toDecimal64(discount, 2)        as discount,
    toDecimal64(subtotal, 2)        as subtotal
from unioned
