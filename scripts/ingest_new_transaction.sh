#!/usr/bin/env bash
# Simulate a new POS transaction landing in a tenant's Postgres schema, so
# the Golang ELT pipeline's watermark incremental load can be demonstrated
# end-to-end (extract -> raw -> staging -> mart).
#
# Usage:
#   ./scripts/ingest_new_transaction.sh [tenant_schema] [customer_id] [store_id] [product_id] [quantity]
#
# Defaults: tenant_2, customer_id=102, store_id=1, product_id=1, quantity=1
#
# The transaction_date is computed as (current max transaction_date in that
# tenant + 1 hour) rather than a hardcoded timestamp or bare now() — this
# guarantees it lands strictly after the pipeline's stored watermark
# regardless of clock drift between the seed data's reference date and the
# container's real wall clock (see conversation notes: inserting with plain
# now() can silently be *older* than the watermark if seed data was
# generated with a future-dated reference "today").
set -euo pipefail

TENANT_SCHEMA="${1:-tenant_2}"
CUSTOMER_ID="${2:-102}"
STORE_ID="${3:-1}"
PRODUCT_ID="${4:-1}"
QUANTITY="${5:-1}"

PG_CONTAINER="parkee-postgres"
PG_USER="parkee"
PG_DB="parkee"

echo "[ingest] tenant=${TENANT_SCHEMA} customer_id=${CUSTOMER_ID} store_id=${STORE_ID} product_id=${PRODUCT_ID} quantity=${QUANTITY}"

docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -c "
  WITH price AS (
    SELECT unit_price FROM ${TENANT_SCHEMA}.products WHERE product_id = ${PRODUCT_ID}
  ),
  next_ts AS (
    SELECT COALESCE(max(transaction_date), now()) + INTERVAL '1 hour' AS ts
    FROM ${TENANT_SCHEMA}.transactions
  ),
  new_tx AS (
    INSERT INTO ${TENANT_SCHEMA}.transactions (customer_id, store_id, transaction_date, total_amount, payment_method, status)
    SELECT ${CUSTOMER_ID}, ${STORE_ID}, next_ts.ts, price.unit_price * ${QUANTITY}, 'cash', 'completed'
    FROM next_ts, price
    RETURNING transaction_id, transaction_date, total_amount
  ),
  new_item AS (
    INSERT INTO ${TENANT_SCHEMA}.transaction_items (transaction_id, product_id, quantity, unit_price, discount, subtotal)
    SELECT new_tx.transaction_id, ${PRODUCT_ID}, ${QUANTITY}, price.unit_price, 0, price.unit_price * ${QUANTITY}
    FROM new_tx, price
    RETURNING transaction_id, item_id, subtotal
  )
  SELECT new_tx.transaction_id, new_tx.transaction_date, new_tx.total_amount, new_item.item_id, new_item.subtotal
  FROM new_tx JOIN new_item ON new_tx.transaction_id = new_item.transaction_id;
"

echo "[ingest] current watermark for ${TENANT_SCHEMA} (before next pipeline run):"
docker exec parkee-airflow-scheduler cat "/opt/airflow/pipeline/state/watermark_${TENANT_SCHEMA}.json" 2>/dev/null || echo "(no watermark file yet)"

echo ""
echo "[ingest] done. Now run the pipeline to pick this up:"
echo "  docker exec parkee-airflow-scheduler /opt/airflow/pipeline/pipeline --config /opt/airflow/pipeline/config/tenants.json --state-dir /opt/airflow/pipeline/state"
