#!/usr/bin/env python3
"""Generate realistic dummy POS data for each tenant schema in Postgres.

Usage: python generate_seed.py
Env: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""
import os
import random
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values

random.seed(42)

PG_HOST = os.environ.get("POSTGRES_HOST", "localhost")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_DB = os.environ.get("POSTGRES_DB", "parkee")
PG_USER = os.environ.get("POSTGRES_USER", "parkee")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "parkee_secret")

TENANTS = ["tenant_1", "tenant_2", "tenant_3"]

CITIES = ["Jakarta", "Bandung", "Surabaya", "Semarang", "Yogyakarta", "Medan", "Makassar", "Denpasar"]
PROVINCES = {
    "Jakarta": "DKI Jakarta", "Bandung": "Jawa Barat", "Surabaya": "Jawa Timur",
    "Semarang": "Jawa Tengah", "Yogyakarta": "DI Yogyakarta", "Medan": "Sumatera Utara",
    "Makassar": "Sulawesi Selatan", "Denpasar": "Bali",
}
CATEGORIES = ["Minuman", "Makanan Ringan", "Sembako", "Perawatan Diri", "Rumah Tangga", "Rokok", "Bayi & Anak", "Frozen Food"]
BRANDS = ["Indofood", "Unilever", "Wings", "Mayora", "Nestle", "Danone", "P&G", "ABC", "Sido Muncul", "Local"]
PAYMENT_METHODS = ["cash", "debit", "credit", "e-wallet"]
STORE_TYPES = ["minimarket", "supermarket", "express"]
PROMO_TYPES = ["discount", "bundle", "cashback"]
GENDERS = ["male", "female"]

N_CUSTOMERS = 250
N_PRODUCTS = 120
N_STORES = 4
N_TRANSACTIONS = 6000
N_PROMOTIONS = 12
N_SUPPLIERS = 8

TODAY = datetime(2026, 8, 6)
TX_START = TODAY - timedelta(days=365)


def conn():
    return psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD)


def rand_datetime(start, end):
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def gen_customers(n):
    rows = []
    for i in range(1, n + 1):
        created = rand_datetime(TX_START - timedelta(days=200), TODAY)
        rows.append((f"Customer {i}", f"08{random.randint(100000000, 999999999)}",
                      f"customer{i}@example.com", random.choice(GENDERS), random.choice(CITIES), created))
    return rows


def gen_products(n):
    rows = []
    for i in range(1, n + 1):
        cat = random.choice(CATEGORIES)
        price = round(random.uniform(2000, 150000), -2)
        created = rand_datetime(TX_START - timedelta(days=300), TODAY)
        rows.append((f"{cat} Produk {i}", cat, random.choice(BRANDS), price, True, created))
    return rows


def gen_stores(n):
    rows = []
    for i in range(1, n + 1):
        city = random.choice(CITIES)
        opened = (TX_START - timedelta(days=random.randint(200, 900))).date()
        rows.append((f"Parkee Mart {city} {i}", city, PROVINCES[city], random.choice(STORE_TYPES), opened, True))
    return rows


def gen_promotions(n):
    rows = []
    for i in range(1, n + 1):
        start = TX_START + timedelta(days=random.randint(0, 300))
        end = start + timedelta(days=random.randint(7, 45))
        rows.append((f"Promo {i}", random.choice(PROMO_TYPES), round(random.uniform(5, 30), 2),
                      start.date(), end.date(), round(random.choice([0, 20000, 50000, 100000]), 2)))
    return rows


def gen_suppliers(n):
    rows = []
    for i in range(1, n + 1):
        city = random.choice(CITIES)
        created = rand_datetime(TX_START - timedelta(days=300), TODAY)
        rows.append((f"Supplier {i}", f"PIC Supplier {i}", city, "Indonesia", created))
    return rows


def seed_tenant(cur, schema):
    print(f"[seed] {schema}: generating...")

    customers = gen_customers(N_CUSTOMERS)
    execute_values(cur, f"INSERT INTO {schema}.customers (name, phone, email, gender, city, created_at) VALUES %s", customers)
    cur.execute(f"SELECT customer_id FROM {schema}.customers")
    customer_ids = [r[0] for r in cur.fetchall()]

    products = gen_products(N_PRODUCTS)
    execute_values(cur, f"INSERT INTO {schema}.products (product_name, category, brand, unit_price, is_active, created_at) VALUES %s", products)
    cur.execute(f"SELECT product_id, unit_price FROM {schema}.products")
    product_rows = cur.fetchall()

    stores = gen_stores(N_STORES)
    execute_values(cur, f"INSERT INTO {schema}.stores (store_name, city, province, store_type, opened_at, is_active) VALUES %s", stores)
    cur.execute(f"SELECT store_id FROM {schema}.stores")
    store_ids = [r[0] for r in cur.fetchall()]

    promotions = gen_promotions(N_PROMOTIONS)
    execute_values(cur, f"INSERT INTO {schema}.promotions (promo_name, promo_type, discount_pct, start_date, end_date, min_purchase) VALUES %s", promotions)
    cur.execute(f"SELECT promo_id, start_date, end_date FROM {schema}.promotions")
    promo_rows = cur.fetchall()

    suppliers = gen_suppliers(N_SUPPLIERS)
    execute_values(cur, f"INSERT INTO {schema}.suppliers (supplier_name, contact_name, city, country, created_at) VALUES %s", suppliers)

    # Transactions + items
    tx_rows = []
    for _ in range(N_TRANSACTIONS):
        tx_date = rand_datetime(TX_START, TODAY)
        status = random.choices(["completed", "voided", "pending"], weights=[92, 5, 3])[0]
        tx_rows.append((random.choice(customer_ids), random.choice(store_ids), tx_date,
                         0, random.choice(PAYMENT_METHODS), status))

    tx_result = execute_values(
        cur,
        f"INSERT INTO {schema}.transactions (customer_id, store_id, transaction_date, total_amount, payment_method, status) VALUES %s RETURNING transaction_id, transaction_date",
        tx_rows, fetch=True,
    )

    item_rows = []
    tx_totals = {}
    for tx_id, tx_date in tx_result:
        n_items = random.randint(1, 6)
        total = 0
        for _ in range(n_items):
            product_id, unit_price = random.choice(product_rows)
            qty = random.randint(1, 5)
            discount = random.choice([0, 0, 0, 5, 10])
            subtotal = round(float(unit_price) * qty * (1 - discount / 100), 2)
            total += subtotal
            item_rows.append((tx_id, product_id, qty, unit_price, discount, subtotal))
        tx_totals[tx_id] = round(total, 2)

    execute_values(cur, f"INSERT INTO {schema}.transaction_items (transaction_id, product_id, quantity, unit_price, discount, subtotal) VALUES %s", item_rows)

    # Update transaction totals to match summed items
    execute_values(
        cur,
        f"UPDATE {schema}.transactions AS t SET total_amount = v.total FROM (VALUES %s) AS v(tx_id, total) WHERE t.transaction_id = v.tx_id",
        [(tx_id, total) for tx_id, total in tx_totals.items()],
    )

    # transaction_promotions: ~25% of completed transactions within an active promo window
    tp_rows = []
    for tx_id, tx_date in tx_result:
        if random.random() > 0.25:
            continue
        eligible = [p for p in promo_rows if p[1] <= tx_date.date() <= p[2]]
        if not eligible:
            continue
        promo_id, _, _ = random.choice(eligible)
        discount_applied = round(tx_totals.get(tx_id, 0) * random.uniform(0.05, 0.25), 2)
        tp_rows.append((tx_id, promo_id, discount_applied))

    if tp_rows:
        execute_values(cur, f"INSERT INTO {schema}.transaction_promotions (transaction_id, promo_id, discount_applied) VALUES %s", tp_rows)

    print(f"[seed] {schema}: {len(customers)} customers, {len(products)} products, {len(store_ids)} stores, "
          f"{len(tx_rows)} transactions, {len(item_rows)} items, {len(promotions)} promotions, {len(tp_rows)} promo usages")


def main():
    c = conn()
    c.autocommit = False
    try:
        with c.cursor() as cur:
            for schema in TENANTS:
                seed_tenant(cur, schema)
        c.commit()
        print("[seed] done, committed.")
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


if __name__ == "__main__":
    main()
