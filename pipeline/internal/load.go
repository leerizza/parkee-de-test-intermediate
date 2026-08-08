package internal

import (
	"context"
	"database/sql/driver"
	"fmt"
	"strings"

	"github.com/ClickHouse/clickhouse-go/v2"
)
func RawTableName(tenant, table string) string {
	return fmt.Sprintf("raw_%s__%s", tenant, table)
}

func EnsureRawTable(ctx context.Context, conn clickhouse.Conn, database, tenant, table string, columns []string) error {
	cols := make([]string, len(columns))
	for i, c := range columns {
		cols[i] = fmt.Sprintf("`%s` Nullable(String)", c)
	}
	cols = append(cols, "`_tenant` LowCardinality(String)", "`_loaded_at` DateTime DEFAULT now()")

	ddl := fmt.Sprintf(
		"CREATE TABLE IF NOT EXISTS %s.%s (%s) ENGINE = ReplacingMergeTree(_loaded_at) ORDER BY (`%s`) SETTINGS allow_nullable_key = 1",
		database, RawTableName(tenant, table), strings.Join(cols, ", "), columns[0],
	)
	return conn.Exec(ctx, ddl)
}

// load data di click house
func LoadRows(ctx context.Context, conn clickhouse.Conn, database, tenant, table string, extracted *ExtractedRows) error {
	if len(extracted.Rows) == 0 {
		return nil
	}

	colNames := append(append([]string{}, extracted.Columns...), "_tenant")
	quoted := make([]string, len(colNames))
	for i, c := range colNames {
		quoted[i] = "`" + c + "`"
	}

	insertSQL := fmt.Sprintf("INSERT INTO %s.%s (%s)", database, RawTableName(tenant, table), strings.Join(quoted, ", "))
	batch, err := conn.PrepareBatch(ctx, insertSQL)
	if err != nil {
		return fmt.Errorf("prepare batch: %w", err)
	}

	for _, row := range extracted.Rows {
		values := make([]any, 0, len(row)+1)
		for _, v := range row {
			values = append(values, toClickHouseString(v))
		}
		values = append(values, tenant)
		if err := batch.Append(values...); err != nil {
			return fmt.Errorf("append row: %w", err)
		}
	}

	return batch.Send()
}

func toClickHouseString(v any) *string {
	if v == nil {
		return nil
	}
	if valuer, ok := v.(driver.Valuer); ok {
		if dv, err := valuer.Value(); err == nil && dv != nil {
			s := fmt.Sprintf("%v", dv)
			return &s
		}
	}
	s := fmt.Sprintf("%v", v)
	return &s
}
