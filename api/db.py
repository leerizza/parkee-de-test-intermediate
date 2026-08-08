import os

import clickhouse_connect

CLICKHOUSE_HOST = os.environ.get("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_HTTP_PORT = int(os.environ.get("CLICKHOUSE_HTTP_PORT", "8123"))
CLICKHOUSE_USER = os.environ.get("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "clickhouse_secret")
CLICKHOUSE_DB = os.environ.get("CLICKHOUSE_ANALYTICS_DB", "analytics")


def get_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_HTTP_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DB,
    )


def query(sql: str, params: dict | None = None) -> list[dict]:
    client = get_client()
    try:
        result = client.query(sql, parameters=params or {})
        columns = result.column_names
        return [dict(zip(columns, row)) for row in result.result_rows]
    finally:
        client.close()
