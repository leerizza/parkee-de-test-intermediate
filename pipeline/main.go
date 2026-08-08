// Command pipeline runs the Parkee multi-tenant ELT: extract from each
// tenant's Postgres schema and load into the ClickHouse raw layer, in
// parallel per tenant, using a simple JSON watermark for incremental loads.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"log"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"

	"github.com/parkee/de-test/pipeline/internal"
)

type tenantConfig struct {
	Name        string `json:"name"`
	Schema      string `json:"schema"`
	PostgresDSN string `json:"postgres_dsn"`
}

type clickhouseConfig struct {
	Addr     string `json:"addr"`
	Database string `json:"database"`
	Username string `json:"username"`
	Password string `json:"password"`
}

type tableConfig struct {
	Name             string  `json:"name"`
	WatermarkColumn  *string `json:"watermark_column"`
}

type appConfig struct {
	Tenants    []tenantConfig   `json:"tenants"`
	ClickHouse clickhouseConfig `json:"clickhouse"`
	Tables     []tableConfig    `json:"tables"`
}

func loadConfig(path string) (*appConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg appConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func main() {
	configPath := flag.String("config", "config/tenants.json", "path to tenants config JSON")
	stateDir := flag.String("state-dir", "state", "directory for watermark state files")
	flag.Parse()

	cfg, err := loadConfig(*configPath)
	if err != nil {
		log.Fatalf("load config: %v", err)
	}

	chConn, err := clickhouse.Open(&clickhouse.Options{
		Addr: []string{cfg.ClickHouse.Addr},
		Auth: clickhouse.Auth{
			Database: "default",
			Username: cfg.ClickHouse.Username,
			Password: cfg.ClickHouse.Password,
		},
	})
	if err != nil {
		log.Fatalf("connect clickhouse: %v", err)
	}
	defer chConn.Close()

	ctx := context.Background()
	if err := chConn.Exec(ctx, "CREATE DATABASE IF NOT EXISTS "+cfg.ClickHouse.Database); err != nil {
		log.Fatalf("create database %s: %v", cfg.ClickHouse.Database, err)
	}

	var wg sync.WaitGroup
	var hadError atomic.Bool
	for _, tenant := range cfg.Tenants {
		wg.Add(1)
		go func(t tenantConfig) {
			defer wg.Done()
			if !runTenant(ctx, chConn, cfg, t, *stateDir) {
				hadError.Store(true)
			}
		}(tenant)
	}
	wg.Wait()

	if hadError.Load() {
		log.Fatal("[pipeline] completed with errors, see logs above")
	}
	log.Println("[pipeline] all tenants processed")
}

// runTenant returns false if any table failed to extract/load, so callers
// (and Airflow, via the process exit code) can distinguish a real failure
// from a normal run — errors used to be logged and swallowed, leaving the
// process to exit 0 even when every table failed to load.
func runTenant(ctx context.Context, chConn clickhouse.Conn, cfg *appConfig, tenant tenantConfig, stateDir string) bool {
	start := time.Now()
	log.Printf("[%s] starting extract & load", tenant.Name)
	ok := true

	wm, err := internal.LoadWatermark(stateDir, tenant.Name)
	if err != nil {
		log.Printf("[%s] ERROR load watermark: %v", tenant.Name, err)
		return false
	}

	for _, table := range cfg.Tables {
		tableStart := time.Now()
		watermarkCol := ""
		since := time.Time{}
		if table.WatermarkColumn != nil {
			watermarkCol = *table.WatermarkColumn
			since = wm.Get(table.Name)
		}

		extracted, err := internal.ExtractTable(ctx, tenant.PostgresDSN, tenant.Schema, table.Name, watermarkCol, since)
		if err != nil {
			log.Printf("[%s] ERROR extract %s: %v", tenant.Name, table.Name, err)
			ok = false
			continue
		}

		if err := internal.EnsureRawTable(ctx, chConn, cfg.ClickHouse.Database, tenant.Name, table.Name, extracted.Columns); err != nil {
			log.Printf("[%s] ERROR ensure raw table %s: %v", tenant.Name, table.Name, err)
			ok = false
			continue
		}

		if err := internal.LoadRows(ctx, chConn, cfg.ClickHouse.Database, tenant.Name, table.Name, extracted); err != nil {
			log.Printf("[%s] ERROR load %s: %v", tenant.Name, table.Name, err)
			ok = false
			continue
		}

		if watermarkCol != "" {
			wm.Set(table.Name, extracted.MaxSeen)
		}

		log.Printf("[%s] %s: extracted=%d loaded=%d duration=%s",
			tenant.Name, table.Name, len(extracted.Rows), len(extracted.Rows), time.Since(tableStart))
	}

	if err := wm.Save(stateDir, tenant.Name); err != nil {
		log.Printf("[%s] ERROR save watermark: %v", tenant.Name, err)
		ok = false
	}

	log.Printf("[%s] done in %s", tenant.Name, time.Since(start))
	return ok
}
