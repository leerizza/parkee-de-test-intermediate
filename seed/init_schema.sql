-- Parkee POS OLTP schema, replicated identically into 3 tenant schemas.
-- DO NOT change column names/types — dbt staging models depend on this exact shape.

CREATE OR REPLACE FUNCTION create_parkee_schema(schema_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.customers (
            customer_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            email VARCHAR(100),
            gender VARCHAR(10),
            city VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    $f$, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.products (
            product_id SERIAL PRIMARY KEY,
            product_name VARCHAR(150) NOT NULL,
            category VARCHAR(50),
            brand VARCHAR(50),
            unit_price NUMERIC(12,2) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    $f$, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.stores (
            store_id SERIAL PRIMARY KEY,
            store_name VARCHAR(100) NOT NULL,
            city VARCHAR(50),
            province VARCHAR(50),
            store_type VARCHAR(30),
            opened_at DATE,
            is_active BOOLEAN DEFAULT TRUE
        )
    $f$, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.transactions (
            transaction_id SERIAL PRIMARY KEY,
            customer_id INT REFERENCES %I.customers(customer_id),
            store_id INT,
            transaction_date TIMESTAMP NOT NULL,
            total_amount NUMERIC(14,2) NOT NULL,
            payment_method VARCHAR(30),
            status VARCHAR(20) DEFAULT 'completed'
        )
    $f$, schema_name, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.transaction_items (
            item_id SERIAL PRIMARY KEY,
            transaction_id INT REFERENCES %I.transactions(transaction_id),
            product_id INT REFERENCES %I.products(product_id),
            quantity INT NOT NULL,
            unit_price NUMERIC(12,2) NOT NULL,
            discount NUMERIC(5,2) DEFAULT 0,
            subtotal NUMERIC(14,2) NOT NULL
        )
    $f$, schema_name, schema_name, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.promotions (
            promo_id SERIAL PRIMARY KEY,
            promo_name VARCHAR(100),
            promo_type VARCHAR(30),
            discount_pct NUMERIC(5,2),
            start_date DATE,
            end_date DATE,
            min_purchase NUMERIC(12,2) DEFAULT 0
        )
    $f$, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.transaction_promotions (
            id SERIAL PRIMARY KEY,
            transaction_id INT REFERENCES %I.transactions(transaction_id),
            promo_id INT REFERENCES %I.promotions(promo_id),
            discount_applied NUMERIC(12,2)
        )
    $f$, schema_name, schema_name, schema_name);

    EXECUTE format($f$
        CREATE TABLE IF NOT EXISTS %I.suppliers (
            supplier_id SERIAL PRIMARY KEY,
            supplier_name VARCHAR(100),
            contact_name VARCHAR(100),
            city VARCHAR(50),
            country VARCHAR(50) DEFAULT 'Indonesia',
            created_at TIMESTAMP DEFAULT NOW()
        )
    $f$, schema_name);

    -- Add columns useful for incremental watermarking (idempotent).
    EXECUTE format('ALTER TABLE %I.customers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()', schema_name);
    EXECUTE format('ALTER TABLE %I.products ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()', schema_name);
END;
$$ LANGUAGE plpgsql;

SELECT create_parkee_schema('tenant_1');
SELECT create_parkee_schema('tenant_2');
SELECT create_parkee_schema('tenant_3');
