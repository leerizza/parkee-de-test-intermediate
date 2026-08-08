from fastapi import APIRouter

from db import query

router = APIRouter(prefix="/api", tags=["analytics"])

MARTS = "analytics_marts"


@router.get("/top-products-by-category")
def top_products_by_category():
    """Q1 — top 5 products per category by total quantity sold."""
    sql = f"""
        with ranked as (
            select
                p.category as category,
                p.product_name as product_name,
                sum(s.quantity) as total_quantity,
                row_number() over (partition by p.category order by sum(s.quantity) desc) as rn
            from {MARTS}.fact_sales s
            inner join {MARTS}.dim_product p on s.product_key = p.product_key
            group by p.category, p.product_name
        )
        select category, product_name, total_quantity
        from ranked
        where rn <= 5
        order by category, total_quantity desc
    """
    return query(sql)


@router.get("/monthly-revenue-trend")
def monthly_revenue_trend():
    """Q2 — total revenue per month."""
    sql = f"""
        select
            toStartOfMonth(transaction_date) as month,
            sum(subtotal) as total_revenue
        from {MARTS}.fact_sales
        group by month
        order by month
    """
    return query(sql)


@router.get("/payment-method-distribution")
def payment_method_distribution():
    """Q3 — percentage distribution of transactions by payment method."""
    sql = f"""
        with by_method as (
            select payment_method, count(distinct transaction_key) as tx_count
            from {MARTS}.fact_sales
            group by payment_method
        ),
        total as (
            select sum(tx_count) as total_tx from by_method
        )
        select
            b.payment_method as payment_method,
            b.tx_count as transaction_count,
            round(b.tx_count * 100.0 / t.total_tx, 2) as pct
        from by_method b, total t
        order by transaction_count desc
    """
    return query(sql)


@router.get("/revenue-by-store")
def revenue_by_store():
    """Q4 — revenue per store per month, last 6 months of data."""
    sql = f"""
        with bounds as (
            select max(transaction_date) as max_date from {MARTS}.fact_sales
        )
        select
            st.store_name as store_name,
            st.city as city,
            toStartOfMonth(s.transaction_date) as month,
            sum(s.subtotal) as revenue
        from {MARTS}.fact_sales s
        inner join {MARTS}.dim_store st on s.store_key = st.store_key
        cross join bounds b
        where s.transaction_date >= addMonths(b.max_date, -6)
        group by store_name, city, month
        order by store_name, month
    """
    return query(sql)


@router.get("/promotion-effectiveness")
def promotion_effectiveness():
    """Q5 — total discount per promo, and avg transaction value promo vs non-promo."""
    discount_sql = f"""
        select
            pr.promo_name as promo_name,
            pr.promo_type as promo_type,
            sum(u.discount_applied) as total_discount,
            count(*) as usage_count
        from {MARTS}.fact_promotion_usage u
        inner join {MARTS}.dim_promotion pr on u.promo_key = pr.promo_key
        group by promo_name, promo_type
        order by total_discount desc
    """
    avg_sql = f"""
        select
            if(promo_key is not null, 'promo_active', 'no_promo') as segment,
            round(avg(transaction_total_amount), 2) as avg_transaction_value,
            count(distinct transaction_key) as transaction_count
        from {MARTS}.fact_sales
        group by segment
    """
    return {
        "by_promo": query(discount_sql),
        "promo_vs_baseline": query(avg_sql),
    }


@router.get("/top-products-by-city")
def top_products_by_city():
    """Q6 — top 3 products per city by revenue."""
    sql = f"""
        with ranked as (
            select
                st.city as city,
                p.product_name as product_name,
                sum(s.subtotal) as revenue,
                row_number() over (partition by st.city order by sum(s.subtotal) desc) as rn
            from {MARTS}.fact_sales s
            inner join {MARTS}.dim_product p on s.product_key = p.product_key
            inner join {MARTS}.dim_store st on s.store_key = st.store_key
            group by st.city, p.product_name
        )
        select city, product_name, revenue
        from ranked
        where rn <= 3
        order by city, revenue desc
    """
    return query(sql)


@router.get("/customer-segments")
def customer_segments():
    """Q7 — High/Medium/Low spender segmentation, count per segment per city."""
    # Segment boundaries are derived from the actual spend distribution
    # (33rd/66th percentile) rather than hardcoded absolute amounts, so the
    # split stays meaningful as seed volume/scale changes instead of every
    # customer collapsing into one bucket (e.g. a fixed "High >= 2,000,000"
    # threshold breaks the moment realistic spend is higher than that).
    sql = f"""
        with customer_spend as (
            select
                c.customer_key as customer_key,
                c.city as city,
                sum(s.subtotal) as total_spend
            from {MARTS}.fact_sales s
            inner join {MARTS}.dim_customer c on s.customer_key = c.customer_key
            group by c.customer_key, c.city
        ),
        thresholds as (
            select
                quantile(0.33)(total_spend) as low_cutoff,
                quantile(0.66)(total_spend) as high_cutoff
            from customer_spend
        ),
        segmented as (
            select
                cs.city as city,
                cs.customer_key as customer_key,
                cs.total_spend as total_spend,
                case
                    when cs.total_spend >= t.high_cutoff then 'High'
                    when cs.total_spend >= t.low_cutoff then 'Medium'
                    else 'Low'
                end as segment
            from customer_spend cs
            cross join thresholds t
        )
        select city, segment, count(*) as customer_count
        from segmented
        group by city, segment
        order by city, segment
    """
    return query(sql)


@router.get("/transactions-by-day")
def transactions_by_day():
    """Q8 — busiest day of week by transaction count and revenue."""
    sql = f"""
        select
            formatDateTime(transaction_date, '%W') as day_name,
            toDayOfWeek(transaction_date) as day_of_week,
            count(distinct transaction_key) as transaction_count,
            sum(subtotal) as revenue
        from {MARTS}.fact_sales
        group by day_name, day_of_week
        order by day_of_week
    """
    return query(sql)
