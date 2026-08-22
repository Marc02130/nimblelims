#!/bin/bash
set -e

# Owner/migrator URL (superuser/table owner). Runtime app uses DATABASE_URL (lims_app).
export MIGRATE_DATABASE_URL="${MIGRATE_DATABASE_URL:-postgresql://lims_user:lims_password@db:5432/lims_db}"

echo "Waiting for database to be ready..."
until python -c "import os, psycopg2; psycopg2.connect(os.environ['MIGRATE_DATABASE_URL'])" 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready - running migrations (owner)..."
# Alembic must use owner credentials, not lims_app
DATABASE_URL="${MIGRATE_DATABASE_URL}" python run_migrations.py

echo "Ensuring lims_app role (Option C)..."
python ensure_lims_app_role.py

echo "Starting server (DATABASE_URL should be lims_app)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
