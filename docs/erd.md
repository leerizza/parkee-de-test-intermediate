# ERD — Parkee POS

## OLTP (source, per tenant schema)

```mermaid
erDiagram
    customers ||--o{ transactions : places
    transactions ||--o{ transaction_items : contains
    products ||--o{ transaction_items : sold_as
    transactions ||--o{ transaction_promotions : uses
    promotions ||--o{ transaction_promotions : applied_in
    stores ||--o{ transactions : hosts

    customers {
        int customer_id PK
        varchar name
        varchar phone
        varchar email
        varchar gender
        varchar city
        timestamp created_at
    }
    products {
        int product_id PK
        varchar product_name
        varchar category
        varchar brand
        numeric unit_price
        bool is_active
        timestamp created_at
    }
    stores {
        int store_id PK
        varchar store_name
        varchar city
        varchar province
        varchar store_type
        date opened_at
        bool is_active
    }
    transactions {
        int transaction_id PK
        int customer_id FK
        int store_id FK
        timestamp transaction_date
        numeric total_amount
        varchar payment_method
        varchar status
    }
    transaction_items {
        int item_id PK
        int transaction_id FK
        int product_id FK
        int quantity
        numeric unit_price
        numeric discount
        numeric subtotal
    }
    promotions {
        int promo_id PK
        varchar promo_name
        varchar promo_type
        numeric discount_pct
        date start_date
        date end_date
        numeric min_purchase
    }
    transaction_promotions {
        int id PK
        int transaction_id FK
        int promo_id FK
        numeric discount_applied
    }
    suppliers {
        int supplier_id PK
        varchar supplier_name
        varchar contact_name
        varchar city
        varchar country
        timestamp created_at
    }
```

`suppliers` has no FK into `fact_sales` at Intermediate level — it's staged (`stg_suppliers`) but only becomes relevant via `product_supplier` at Advanced level.

Note: `customer_id`, `product_id`, etc. are `SERIAL` per tenant schema, so raw values collide across tenants (e.g. `tenant_1.customer_id = 1` and `tenant_2.customer_id = 1` are different people). Surrogate keys in the star schema are `tenant_id || '-' || id`.

## Star Schema (marts, ClickHouse)

```mermaid
erDiagram
    dim_customer ||--o{ fact_sales : ""
    dim_product ||--o{ fact_sales : ""
    dim_store ||--o{ fact_sales : ""
    dim_date ||--o{ fact_sales : ""
    dim_promotion ||--o{ fact_sales : ""
    dim_promotion ||--o{ fact_promotion_usage : ""

    dim_customer {
        string customer_key PK
        int customer_id
        string tenant_id
        string customer_name
        string gender
        string city
    }
    dim_product {
        string product_key PK
        int product_id
        string tenant_id
        string product_name
        string category
        string brand
        decimal unit_price
    }
    dim_store {
        string store_key PK
        int store_id
        string tenant_id
        string store_name
        string city
        string province
        string store_type
    }
    dim_promotion {
        string promo_key PK
        int promo_id
        string tenant_id
        string promo_name
        string promo_type
        decimal discount_pct
    }
    dim_date {
        string date_key PK
        date date_day
        int year
        int month
        string day_name
    }
    fact_sales {
        string sale_key PK
        string transaction_key
        string customer_key FK
        string product_key FK
        string store_key FK
        string date_key FK
        string promo_key FK
        int quantity
        decimal subtotal
        string payment_method
    }
    fact_promotion_usage {
        string promotion_usage_key PK
        string transaction_key
        string promo_key FK
        decimal discount_applied
    }
```

## Pipeline architecture

```mermaid
flowchart LR
    subgraph OLTP["Postgres (3 tenant schemas)"]
        T1[tenant_1]
        T2[tenant_2]
        T3[tenant_3]
    end

    subgraph GO["Golang ELT (goroutine per tenant)"]
        EX[extract.go]
        LD[load.go]
        WM[watermark.go]
    end

    subgraph CH["ClickHouse"]
        RAW[(raw.raw_tenant_x__table)]
        STG[(analytics_staging.stg_*)]
        MART[(analytics_marts.dim_* / fact_*)]
    end

    API[FastAPI]
    DASH[Dashboard]
    AF[Airflow orchestrator]

    OLTP --> EX --> LD --> RAW
    WM -.watermark state.- EX
    RAW -->|dbt run staging| STG
    STG -->|dbt run marts| MART
    MART --> API --> DASH
    AF -.orchestrates.-> GO
    AF -.orchestrates.-> STG
    AF -.orchestrates.-> MART
```
