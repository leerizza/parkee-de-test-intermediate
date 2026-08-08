with unioned as (
    select * from raw.raw_tenant_1__suppliers FINAL
    union all
    select * from raw.raw_tenant_2__suppliers FINAL
    union all
    select * from raw.raw_tenant_3__suppliers FINAL
)

select
    toInt64(supplier_id)                as supplier_id,
    _tenant                             as tenant_id,
    supplier_name                       as supplier_name,
    contact_name                        as contact_name,
    city                                as city,
    country                             as country,
    parseDateTimeBestEffort(created_at) as created_at
from unioned
