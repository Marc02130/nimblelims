#!/bin/bash
# Bootstrap only. The POSTGRES_USER superuser creates roles and hands
# ownership to lims_migrate. It does not run Alembic and does not keep
# application objects.
set -euo pipefail

if [ -z "${LIMS_MIGRATE_PASSWORD:-}" ] || [ -z "${LIMS_APP_PASSWORD:-}" ]; then
  echo "FATAL: LIMS_MIGRATE_PASSWORD and LIMS_APP_PASSWORD are required" >&2
  exit 1
fi

case "${POSTGRES_USER}" in
  lims_migrate|lims_app|lims_user)  # pragma: allowlist secret
    echo "FATAL: POSTGRES_USER must be a bootstrap superuser, not ${POSTGRES_USER}" >&2
    exit 1
    ;;
esac

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -v migrate_password="$LIMS_MIGRATE_PASSWORD" \
  -v app_password="$LIMS_APP_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE lims_migrate LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT BYPASSRLS',
    :'migrate_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_migrate')
\gexec

SELECT format(
    'CREATE ROLE lims_app LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT',
    :'app_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_app')
\gexec

SELECT 'CREATE ROLE lims_user NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT'  -- pragma: allowlist secret
WHERE NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'lims_user')  -- pragma: allowlist secret
\gexec

ALTER ROLE lims_migrate NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS;
ALTER ROLE lims_app NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
ALTER ROLE lims_user NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;  -- pragma: allowlist secret

ALTER DATABASE lims_db OWNER TO lims_migrate;
ALTER SCHEMA public OWNER TO lims_migrate;
ALTER SCHEMA lims OWNER TO lims_migrate;
SQL
