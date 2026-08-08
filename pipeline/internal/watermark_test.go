package internal

import (
	"path/filepath"
	"testing"
	"time"
)

func TestLoadWatermark_MissingFileReturnsEmpty(t *testing.T) {
	dir := t.TempDir()

	w, err := LoadWatermark(dir, "tenant_1")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got := w.Get("transactions"); !got.IsZero() {
		t.Fatalf("expected zero time for unseen table, got %v", got)
	}
}

func TestWatermark_SaveThenLoadRoundTrips(t *testing.T) {
	dir := t.TempDir()
	ts := time.Date(2026, 8, 7, 15, 56, 27, 0, time.UTC)

	w := &Watermark{Values: map[string]time.Time{}}
	w.Set("transactions", ts)
	if err := w.Save(dir, "tenant_1"); err != nil {
		t.Fatalf("save: %v", err)
	}

	loaded, err := LoadWatermark(dir, "tenant_1")
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if got := loaded.Get("transactions"); !got.Equal(ts) {
		t.Fatalf("expected %v, got %v", ts, got)
	}
}

func TestWatermark_SetOverwritesExistingTable(t *testing.T) {
	older := time.Date(2026, 8, 1, 0, 0, 0, 0, time.UTC)
	newer := time.Date(2026, 8, 7, 0, 0, 0, 0, time.UTC)

	w := &Watermark{Values: map[string]time.Time{"transactions": older}}
	w.Set("transactions", newer)

	if got := w.Get("transactions"); !got.Equal(newer) {
		t.Fatalf("expected %v, got %v", newer, got)
	}
}

func TestWatermark_GetUnknownTableReturnsZero(t *testing.T) {
	w := &Watermark{Values: map[string]time.Time{"transactions": time.Now()}}

	if got := w.Get("stores"); !got.IsZero() {
		t.Fatalf("expected zero time for table never set, got %v", got)
	}
}

func TestWatermarkPath_PerTenantFileNaming(t *testing.T) {
	got := watermarkPath("/state", "tenant_2")
	want := filepath.Join("/state", "watermark_tenant_2.json")
	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func TestWatermark_SaveCreatesStateDirIfMissing(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "nested", "state")

	w := &Watermark{Values: map[string]time.Time{"products": time.Now()}}
	if err := w.Save(dir, "tenant_3"); err != nil {
		t.Fatalf("save into missing dir: %v", err)
	}

	if _, err := LoadWatermark(dir, "tenant_3"); err != nil {
		t.Fatalf("load after save: %v", err)
	}
}
