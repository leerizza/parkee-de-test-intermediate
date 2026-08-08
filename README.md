## Deskripsi & Skenario Bisnis

Parkee mengoperasikan beberapa minimarket (`stores`) di beberapa kota, masing-masing dijalankan sebagai tenant terpisah (disimulasikan sebagai 3 schema Postgres: `tenant_1`, `tenant_2`, `tenant_3`). Setiap tenant mencatat transaksi kasir (`transactions` + `transaction_items`), pelanggan (`customers`), katalog produk (`products`), serta promosi yang berjalan (`promotions` + `transaction_promotions`). Data ini diambil, ditransformasi menjadi star schema, dan divisualisasikan untuk menjawab pertanyaan bisnis seputar penjualan, promosi, dan segmentasi pelanggan.

## Arsitektur

```
Postgres (OLTP, 3 tenant schema)
        │  Golang ELT (goroutine per tenant, incremental via watermark)
        ▼
ClickHouse: raw.raw_<tenant>__<table>
        │  dbt run --select staging.*
        ▼
ClickHouse: analytics_staging.stg_*
        │  dbt run --select marts.*
        ▼
ClickHouse: analytics_marts.dim_* / fact_*
        │
        ▼
FastAPI (8 endpoint) ──► Dashboard (Chart.js)

Airflow mengorkestrasi seluruh alur di atas:
extract_load_golang_binary → dbt_run_staging → dbt_test_staging → dbt_run_mart → dbt_test_mart
```

Diagram ERD lengkap (OLTP + star schema) ada di [`docs/erd.md`](docs/erd.md).

## Tech Stack

| Komponen | Tools |
|---|---|
| Source DB | PostgreSQL 15 |
| Pipeline | Golang 1.21, goroutine + `sync.WaitGroup` per tenant |
| Transformasi | dbt Core (adapter `dbt-clickhouse`) |
| Orkestrasi | Apache Airflow 2.7 |
| Data Warehouse | ClickHouse |
| Visualisasi | FastAPI + dashboard HTML/JS (Chart.js) |
| Containerisasi | Docker & Docker Compose |

## Struktur Repo

```
parkee-de-test/
├── seed/            # DDL OLTP + generator data dummy
├── pipeline/         # Golang ELT (multi-tenant, incremental)
├── dbt/               # staging + mart models, schema.yml (docs + tests)
├── airflow/          # DAG orkestrasi
├── api/                # FastAPI, 8 endpoint analitik
├── dashboard/     # Dashboard statis (Chart.js)
└── docs/erd.md    # ERD OLTP + star schema (Mermaid)
```

## Cara Setup dari Nol

1. **Clone & siapkan environment**
   ```bash
   cp .env.example .env
   # sesuaikan password/port jika perlu
   ```

2. **Jalankan seluruh stack**
   ```bash
   docker compose up -d --build
   ```
   Ini akan menjalankan: Postgres (auto-create 3 schema tenant lewat `seed/init_schema.sql`), service `seeder` (populate data dummy sekali jalan), ClickHouse, Airflow (webserver + scheduler + metadata DB), FastAPI, dan dashboard (nginx static).

3. **Cek seeding selesai**
   ```bash
   docker compose logs -f seeder
   ```
   Kalau butuh re-seed manual: `./seed/run_seed.sh` (perlu `psql` & `python3` di host, terhubung ke Postgres via port 5432).

4. **Trigger pipeline via Airflow**
   - Buka `http://localhost:8080` (login `admin` / `admin`, atau sesuai `.env`).
   - Un-pause & trigger DAG `parkee_elt_dag`. Task order: `extract_load_golang_binary → dbt_run_staging → dbt_test_staging → dbt_run_mart → dbt_test_mart`.
   - Setelah semua task hijau, mart tables (`analytics_marts.*`) siap dipakai FastAPI.

5. **Cek API**
   - Swagger: `http://localhost:8000/docs`

6. **Buka dashboard**
   - `http://localhost:8081`

### Port default

| Service | Port |
|---|---|
| Postgres | 5434 (host) → 5432 (container); override with `POSTGRES_HOST_PORT` |
| ClickHouse (HTTP / native) | 8124 → 8123, 9000 → 9000 (host → container); override with `CLICKHOUSE_HTTP_HOST_PORT` / `CLICKHOUSE_NATIVE_HOST_PORT` |
| Airflow webserver | 8080 |
| FastAPI | 8000 |
| Dashboard (nginx) | 8081 |

## Tutorial Lengkap: Full Load Awal vs Proses Data Baru

Bagian ini menjelaskan dua skenario yang paling sering ditanya: **bagaimana data pertama kali masuk**
(full load) dan **bagaimana data baru diproses** setelahnya (incremental run). Perintah di bawah
mengasumsikan stack sudah jalan (`docker compose up -d --build`).

### A. Full Load Awal (First Run)

Kondisi awal: belum ada file watermark sama sekali, database `raw`/`analytics_staging`/`analytics_marts`
masih kosong.

1. **Seeder mengisi Postgres** — otomatis jalan sekali saat `docker compose up`, atau manual:
   ```bash
   docker compose run --rm seeder
   ```
   Ini populate 3 tenant schema: ~250 customers, ~120 products, 4 stores, 6.000 transactions,
   ~21.000 transaction_items, dst — per tenant.

2. **Trigger DAG `parkee_elt_dag`** di Airflow (`http://localhost:8080`), atau jalankan manual tahap-per-tahap:
   ```bash
   docker compose exec airflow-scheduler /opt/airflow/pipeline/pipeline \
     --config /opt/airflow/pipeline/config/tenants.json --state-dir /opt/airflow/pipeline/state
   ```
   Karena `state/watermark_tenant_*.json` belum ada, `LoadWatermark()` di `pipeline/internal/watermark.go`
   mengembalikan watermark kosong (`time.Time{}` / zero value) untuk setiap tabel — jadi query ke Postgres
   otomatis `WHERE updated_at > '0001-01-01'`, alias **ambil semua baris**. Ini yang disebut full load:
   bukan mode terpisah, tapi konsekuensi alami dari watermark yang belum pernah diisi.

3. **dbt run + test** membangun staging (view) dan mart (table) dari raw yang baru saja penuh terisi:
   ```bash
   docker compose exec airflow-scheduler dbt run --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
   docker compose exec airflow-scheduler dbt test --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
   ```

4. **Verifikasi** — `fact_sales` harus berisi seluruh transaksi `completed` dari 3 tenant:
   ```bash
   docker compose exec clickhouse clickhouse-client --user default --password clickhouse_secret \
     --query "SELECT count() FROM analytics_marts.fact_sales"
   ```

Setelah run pertama ini, `state/watermark_tenant_1.json` (dst) sudah terisi nilai timestamp terbaru per
tabel — pipeline sekarang tahu "sudah sampai mana" untuk setiap tenant.

> **Catatan path**: `state/` di atas adalah path *di dalam* container `airflow-scheduler`
> (`/opt/airflow/pipeline/state`), bukan folder di host. Volume-nya adalah named volume Docker
> (`pipeline_state`), bukan bind mount — jadi tidak akan muncul sebagai folder `state/` di root repo.
> Untuk inspect isinya dari host (tanpa exec ke container):
> ```bash
> docker run --rm -v parkee-de-test_pipeline_state:/data alpine cat /data/watermark_tenant_1.json
> ```
> (ganti `parkee-de-test` di depan nama volume kalau nama folder project kamu berbeda — cek dengan `docker volume ls`).

### B. Proses Data Baru (Incremental Run)

Skenario: kasir di `tenant_1` mencatat transaksi baru setelah full load pertama selesai. Begini alurnya
sampai transaksi itu muncul di dashboard.

1. **Simulasikan data baru masuk ke Postgres** — insert manual lewat `psql` (ganti port sesuai `.env` kamu, default `5434`):
   ```bash
   PGPASSWORD=parkee_secret psql -h localhost -p 5434 -U parkee -d parkee -c "
     INSERT INTO tenant_1.transactions (customer_id, store_id, transaction_date, total_amount, payment_method, status)
     VALUES (1, 1, now(), 150000, 'cash', 'completed')
     RETURNING transaction_id;
   "
   ```
   (Di dunia nyata, ini datang dari aplikasi kasir yang menulis langsung ke Postgres — bukan manual insert.)

2. **Trigger ulang DAG** (atau jalankan pipeline binary lagi). Yang terjadi di tiap task:

   | Task | Yang terjadi dengan data baru |
   |---|---|
   | `extract_load_golang_binary` | Baca watermark lama dari `state/watermark_tenant_1.json`. Untuk tabel `transactions` (punya `watermark_column`), query jadi `WHERE transaction_date > <watermark_lama>` — **hanya** transaksi baru yang ke-extract. Tabel tanpa watermark (`stores`, `promotions`, dst) tetap full re-extract, tapi aman dari duplikat karena raw table pakai `ReplacingMergeTree` + staging query pakai `FINAL` (lihat Bagian "Catatan Pendekatan"). Setelah sukses, watermark di-update ke timestamp transaksi baru itu. |
   | `dbt_run_staging` | Staging model itu **view**, jadi otomatis "lihat" baris baru di raw table begitu di-query — tidak perlu rebuild apa pun. |
   | `dbt_test_staging` | Test jalan ulang atas seluruh data (lama + baru) di staging. |
   | `dbt_run_mart` | ⚠️ **Full-refresh**, bukan incremental. Karena `dim_*`/`fact_*` materialized sebagai `table`, dbt **drop & rebuild total** dari staging (yang isinya sudah gabungan data lama + baru). Transaksi baru otomatis ikut masuk, tapi seluruh mart tetap dihitung ulang dari nol setiap run — bukan cuma delta-nya. |
   | `dbt_test_mart` | Test ulang atas mart yang baru saja di-rebuild. |

3. **Verifikasi transaksi baru sudah nyampe ke mart:**
   ```bash
   docker compose exec clickhouse clickhouse-client --user default --password clickhouse_secret \
     --query "SELECT * FROM analytics_marts.fact_sales WHERE tenant_id = 'tenant_1' ORDER BY transaction_date DESC LIMIT 3"
   ```

4. Refresh dashboard (`http://localhost:8081`) — chart yang relevan (misal Q2 tren revenue bulanan) akan
   otomatis mencerminkan angka baru, karena API query langsung ke mart tiap kali dashboard di-load (tidak
   ada cache).

### Kenapa "incremental" di sini cuma setengah jalan (dan itu OK)

Poin yang sering bikin bingung: **incremental watermark cuma berlaku di tahap extract (Postgres → raw)**.
Begitu masuk ke dbt, mart tetap di-**full-refresh** setiap run karena materialized sebagai `table`, bukan
`incremental`. Jadi:

- ✅ **Hemat**: query ke Postgres tidak perlu tarik ulang jutaan baris lama tiap hari.
- ⚠️ **Belum hemat**: `dbt run --select marts.*` tetap menghitung ulang seluruh star schema dari nol tiap
  kali dipanggil — biayanya tumbuh seiring volume data raw makin besar.

Ini trade-off yang wajar untuk skala data di project ini (puluhan ribu baris). Kalau volume sudah jutaan
baris dan `dbt run` mart mulai terasa lambat, langkah lanjutannya adalah mengubah materialization mart
jadi `incremental` (pakai `is_incremental()` + filter berdasarkan `_loaded_at` atau `transaction_date`) —
di luar scope Intermediate, tapi ini arah upgrade yang natural.

## Pertanyaan Analitik → Endpoint

| # | Pertanyaan | Endpoint |
|---|---|---|
| Q1 | Top 5 produk terlaris per kategori | `GET /api/top-products-by-category` |
| Q2 | Tren revenue bulanan | `GET /api/monthly-revenue-trend` |
| Q3 | Distribusi metode pembayaran | `GET /api/payment-method-distribution` |
| Q4 | Revenue per toko per bulan (6 bulan terakhir) | `GET /api/revenue-by-store` |
| Q5 | Efektivitas promosi | `GET /api/promotion-effectiveness` |
| Q6 | Top 3 produk terlaris per kota | `GET /api/top-products-by-city` |
| Q7 | Segmentasi pelanggan per kota | `GET /api/customer-segments` |
| Q8 | Hari paling ramai dalam seminggu | `GET /api/transactions-by-day` |

## Bonus

### Unit test Golang
`pipeline/internal/watermark_test.go` dan `pipeline/internal/load_test.go` meng-cover logic murni yang
tidak butuh koneksi database: watermark load/save/round-trip per tenant, dan konversi nilai Postgres
(termasuk tipe numeric via `driver.Valuer`) ke string untuk insert ke ClickHouse.
```bash
cd pipeline && go test ./... -v
```

### dbt docs sebagai static site
Task `dbt_docs_generate` di akhir DAG (`airflow/dags/parkee_elt_dag.py`) menjalankan `dbt docs generate`,
menulis `catalog.json`/`manifest.json`/`index.html` ke volume `dbt_docs` (dipakai bersama antara
`airflow-scheduler` dan service `dbt-docs`). Akses langsung di `http://localhost:8082` setelah DAG jalan
minimal sekali, atau generate manual:
```bash
docker exec parkee-airflow-scheduler bash -c \
  "cd /opt/airflow/dbt && dbt docs generate --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt"
```

## Link Video Walkthrough
https://drive.google.com/file/d/1JpTMqk-3ajmmxyBofBBeBI5S75AFLU3h/view?usp=sharing