with bounds as (
    select
        toDate(min(transaction_date)) as min_date,
        toDate(max(transaction_date)) as max_date
    from {{ ref('stg_transactions') }}
),

spine as (
    select addDays(min_date, number) as date_day
    from bounds
    array join range(toUInt32(dateDiff('day', min_date, max_date)) + 1) as number
)

select
    toString(date_day) as date_key,
    date_day as date_day,
    toYear(date_day) as year,
    toMonth(date_day) as month,
    toDayOfMonth(date_day) as day,
    toDayOfWeek(date_day) as day_of_week,
    formatDateTime(date_day, '%W') as day_name,
    toStartOfMonth(date_day) as month_start,
    toISOWeek(date_day) as iso_week
from spine
