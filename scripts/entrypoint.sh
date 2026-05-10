#!/bin/bash
set -e

cd /app

echo "Waiting for Postgres to be ready..."
until python - <<'EOF'
import psycopg2, os, sys
try:
    psycopg2.connect(os.environ.get("DATABASE_URL", "postgresql://postgres:password@postgres:5432/postgres"))
    sys.exit(0)
except Exception:
    sys.exit(1)
EOF
do
  echo "Postgres not ready yet, retrying in 2s..."
  sleep 2
done
echo "Postgres is ready."

# Check if credentials are set before extracting
if [ -z "$CELULA_EMAIL" ] || [ -z "$CELULA_PASSWORD" ]; then
    echo "WARNING: CELULA_EMAIL or CELULA_PASSWORD not set. Skipping extraction."
else
    echo "Running data extraction (scripts/extract.py)..."
    python scripts/extract.py || echo "Extraction failed, continuing anyway..."
fi

echo "Running database migration/seed (scripts/migrate_history.py)..."
python scripts/migrate_history.py

echo "Starting FastAPI server..."
exec "$@"
