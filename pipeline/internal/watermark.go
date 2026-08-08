package internal

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"
)

// baca watermark kapan terkahir di akses
type Watermark struct {
	Values map[string]time.Time `json:"values"`
}

func watermarkPath(stateDir, tenant string) string {
	return filepath.Join(stateDir, "watermark_"+tenant+".json")
}

//untuk baca load watermark file
func LoadWatermark(stateDir, tenant string) (*Watermark, error) {
	path := watermarkPath(stateDir, tenant)
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return &Watermark{Values: map[string]time.Time{}}, nil
	}
	if err != nil {
		return nil, err
	}
	var w Watermark
	if err := json.Unmarshal(data, &w); err != nil {
		return nil, err
	}
	if w.Values == nil {
		w.Values = map[string]time.Time{}
	}
	return &w, nil
}

// simpan setiap watermark state file
func (w *Watermark) Save(stateDir, tenant string) error {
	if err := os.MkdirAll(stateDir, 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(w, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(watermarkPath(stateDir, tenant), data, 0o644)
}

// Get returns the stored watermark for a table, or zero time if unset.
func (w *Watermark) Get(table string) time.Time {
	return w.Values[table]
}

// Set updates the in-memory watermark untuk tiap table
func (w *Watermark) Set(table string, t time.Time) {
	w.Values[table] = t
}
