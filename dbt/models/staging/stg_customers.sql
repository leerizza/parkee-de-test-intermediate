-- Cleans & unions the per-tenant raw customer tables.
with unioned as (
    select * from raw.raw_tenant_1__customers FINAL
    union all
    select * from raw.raw_tenant_2__customers FINAL
    union all
    select * from raw.raw_tenant_3__customers FINAL
)

select
    toInt64(customer_id) as customer_id,
    _tenant as tenant_id,
    name as customer_name,
    phone as phone,
    email as email,
    gender as gender,
    city as city,
    parseDateTimeBestEffort(created_at) as created_at
from unioned
