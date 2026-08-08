package internal

import (
	"database/sql/driver"
	"testing"
)

func TestRawTableName(t *testing.T) {
	cases := []struct {
		tenant, table, want string
	}{
		{"tenant_1", "transactions", "raw_tenant_1__transactions"},
		{"tenant_2", "transaction_items", "raw_tenant_2__transaction_items"},
	}
	for _, c := range cases {
		if got := RawTableName(c.tenant, c.table); got != c.want {
			t.Errorf("RawTableName(%q, %q) = %q, want %q", c.tenant, c.table, got, c.want)
		}
	}
}

func TestToClickHouseString_Nil(t *testing.T) {
	if got := toClickHouseString(nil); got != nil {
		t.Fatalf("expected nil pointer for nil input, got %v", *got)
	}
}

func TestToClickHouseString_PlainValue(t *testing.T) {
	got := toClickHouseString(42)
	if got == nil || *got != "42" {
		t.Fatalf("expected \"42\", got %v", got)
	}
}

func TestToClickHouseString_String(t *testing.T) {
	got := toClickHouseString("cash")
	if got == nil || *got != "cash" {
		t.Fatalf("expected \"cash\", got %v", got)
	}
}

// numericValuer mimics pgx's decimal/numeric types, which implement
// driver.Valuer to render as plain decimal text (e.g. "60600.00") instead of
// their internal struct representation.
type numericValuer struct{ text string }

func (n numericValuer) Value() (driver.Value, error) { return n.text, nil }

func TestToClickHouseString_UsesDriverValuer(t *testing.T) {
	got := toClickHouseString(numericValuer{text: "60600.00"})
	if got == nil || *got != "60600.00" {
		t.Fatalf("expected \"60600.00\", got %v", got)
	}
}
