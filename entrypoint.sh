#!/usr/bin/env bash
set -e


wait_for_db() {
  echo "Waiting for database connection..."
  python - <<PY
import os, sys, time
import psycopg2
from psycopg2 import OperationalError

required_vars = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
missing = [v for v in required_vars if not os.environ.get(v)]
if missing:
    print(f" Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

try:
    host = os.environ["DB_HOST"]
    port = int(os.environ["DB_PORT"])
    user = os.environ["DB_USER"]
    pwd = os.environ["DB_PASSWORD"]
    dbname = os.environ["DB_NAME"]
except Exception as e:
    print(f" Error loading environment variables: {e}", file=sys.stderr)
    sys.exit(1)


for i in range(60):
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=dbname)
        conn.close()
        print("Database is up!")
        sys.exit(0)
    except OperationalError as e:
        print(f"DB not ready yet ({i+1}/60): {e}")
        time.sleep(1)
print("Timed out waiting for the database.", file=sys.stderr)
sys.exit(1)
PY
}

command -v python >/dev/null 2>&1 || { echo "python not found"; exit 1; }

wait_for_db

# Initialize migrations folder if not present, then migrate/upgrade
if [ ! -d "migrations" ]; then
  echo "migrations folder not found — initializing Flask-Migrate..."
  flask db init || true
fi

echo "Running flask db migrate..."
flask db migrate -m "auto-migration from container" || true

echo "Running flask db upgrade..."
flask db upgrade || true

echo "Starting Flask app..."
flask run --host=0.0.0.0 --port=5000
