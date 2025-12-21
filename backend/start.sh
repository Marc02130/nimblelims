#!/bin/bash
set -e

echo "Waiting for database to be ready..."
until python -c "import psycopg2; psycopg2.connect('postgresql://lims_user:lims_password@db:5432/lims_db')" 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready - running migrations..."
python run_migrations.py

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

