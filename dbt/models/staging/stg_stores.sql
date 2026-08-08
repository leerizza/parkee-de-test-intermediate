with unioned as (
    select * from raw.raw_tenant_1__stores FINAL
    union all
    select * from raw.raw_tenant_2__stores FINAL
    union all
    select * from raw.raw_tenant_3__stores FINAL
)

select
    toInt64(store_id)             as store_id,
    _tenant                       as tenant_id,
    store_name                    as store_name,
    city                          as city,
    province                      as province,
    store_type                    as store_type,
    parseDateTimeBestEffort(opened_at) as opened_at,
    toUInt8(is_active = 'true')   as is_active
from unioned
