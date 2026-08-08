set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    source "$ROOT_DIR/.env"
    set +a
fi

export POSTGRES_HOST="${POSTGRES_HOST_ADDR:-localhost}"
export POSTGRES_PORT="${POSTGRES_HOST_PORT:-5434}"
export POSTGRES_DB="${POSTGRES_DB:-parkee}"
export POSTGRES_USER="${POSTGRES_USER:-parkee}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-parkee_secret}"

echo "[run_seed] applying schema DDL..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$SCRIPT_DIR/init_schema.sql"

echo "[run_seed] installing python deps..."
python3 -m pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo "[run_seed] generating dummy data..."
python3 "$SCRIPT_DIR/generate_seed.py"

echo "[run_seed] done."
