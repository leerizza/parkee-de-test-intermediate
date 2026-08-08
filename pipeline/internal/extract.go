package internal

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
)

//ekstrak rows
type ExtractedRows struct {
	Columns []string
	Rows    [][]any
	MaxSeen time.Time 
}

// ExtractTable pulls rows dari schema dengan incremental method
func ExtractTable(ctx context.Context, dsn, schema, table, watermarkCol string, since time.Time) (*ExtractedRows, error) {
	conn, err := pgx.Connect(ctx, dsn)
	if err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}
	defer conn.Close(ctx)

	query := fmt.Sprintf("SELECT * FROM %s.%s", schema, table)
	args := []any{}
	if watermarkCol != "" {
		query += fmt.Sprintf(" WHERE %s > $1", watermarkCol)
		args = append(args, since)
	}

	rows, err := conn.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query %s.%s: %w", schema, table, err)
	}
	defer rows.Close()

	fields := rows.FieldDescriptions()
	columns := make([]string, len(fields))
	watermarkIdx := -1
	for i, f := range fields {
		columns[i] = string(f.Name)
		if watermarkCol != "" && columns[i] == watermarkCol {
			watermarkIdx = i
		}
	}

	result := &ExtractedRows{Columns: columns, MaxSeen: since}
	for rows.Next() {
		vals, err := rows.Values()
		if err != nil {
			return nil, fmt.Errorf("scan %s.%s: %w", schema, table, err)
		}
		result.Rows = append(result.Rows, vals)
		if watermarkIdx >= 0 {
			if t, ok := vals[watermarkIdx].(time.Time); ok && t.After(result.MaxSeen) {
				result.MaxSeen = t
			}
		}
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate %s.%s: %w", schema, table, err)
	}
	return result, nil
}
