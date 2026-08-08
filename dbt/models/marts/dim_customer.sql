select
    concat(tenant_id, '-', toString(customer_id)) as customer_key,
    customer_id,
    tenant_id,
    customer_name,
    phone,
    email,
    gender,
    city,
    created_at
from {{ ref('stg_customers') }}
