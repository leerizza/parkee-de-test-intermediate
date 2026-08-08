with unioned as (
    select * from raw.raw_tenant_1__products FINAL
    union all
    select * from raw.raw_tenant_2__products FINAL
    union all
    select * from raw.raw_tenant_3__products FINAL
)

select
    toInt64(product_id) as product_id,
    _tenant as tenant_id,
    product_name as product_name,
    category as category,
    brand as brand,
    toDecimal64(unit_price, 2) as unit_price,
    toUInt8(is_active = 'true') as is_active,
    parseDateTimeBestEffort(created_at) as created_at
from unioned
