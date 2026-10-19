#!/bin/bash
set -e

# Alembic runs as lims_migrate (MIGRATE_DATABASE_URL). The Compose bootstrap
# superuser does not migrate and does not own application objects.
# Runtime uvicorn uses DATABASE_URL (lims_app).
if [ -z "${MIGRATE_DATABASE_URL:-}" ]; then
  echo "FATAL: MIGRATE_DATABASE_URL is required. Point it at lims_migrate, not the bootstrap superuser." >&2
  exit 1
fi

echo "Waiting for database to be ready..."
until python -c "import os, psycopg2; psycopg2.connect(os.environ['MIGRATE_DATABASE_URL'])" 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready - ensuring lims_app role before migrations..."
# 0083 GRANTs to lims_app with no IF EXISTS. The role has to exist first.
# The second call below grants on tables the migrations have just created.
python ensure_lims_app_role.py

echo "Running migrations (lims_migrate)..."
DATABASE_URL="${MIGRATE_DATABASE_URL}" python run_migrations.py

echo "Ensuring lims_app grants after migrations..."
python ensure_lims_app_role.py

echo "Replaying UI schema DDL log..."
DATABASE_URL="${MIGRATE_DATABASE_URL}" python -c "from app.services.ui_schema_replay import replay_ui_schema; replay_ui_schema()"

echo "Starting server (DATABASE_URL should be lims_app)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
