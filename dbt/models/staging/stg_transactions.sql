-- Only completed transactions flow downstream into fact_sales.
with unioned as (
    select * from raw.raw_tenant_1__transactions FINAL
    union all
    select * from raw.raw_tenant_2__transactions FINAL
    union all
    select * from raw.raw_tenant_3__transactions FINAL
)

select
    toInt64(transaction_id)                as transaction_id,
    _tenant                                as tenant_id,
    toInt64(customer_id)                   as customer_id,
    toInt64(store_id)                      as store_id,
    parseDateTimeBestEffort(transaction_date) as transaction_date,
    toDecimal64(total_amount, 2)           as total_amount,
    payment_method                         as payment_method,
    status                                 as status
from unioned
where status = 'completed'
