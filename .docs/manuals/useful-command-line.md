# Useful command-line snippets

## Clean restart containers

```bash
docker compose down
docker system prune -af
docker compose up -d --build
```

## Export container logs

Write outside the repo (or into a local ignored directory), not into `.docs/`:

```bash
mkdir -p /tmp/nimblelims-logs
docker compose logs backend > /tmp/nimblelims-logs/backend.logs
docker compose logs frontend > /tmp/nimblelims-logs/frontend.logs
docker compose logs db > /tmp/nimblelims-logs/db.logs
```

## Database dumps

```bash
# Full dump
docker exec lims-db pg_dump -U lims_user -d lims_db \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  > /tmp/nimblelims-schema_dump.sql

# Data only
docker exec lims-db pg_dump -U lims_user -d lims_db \
  --data-only \
  --no-owner \
  --no-privileges \
  --inserts \
  > /tmp/nimblelims-schema_data.sql

# Schema only
docker exec lims-db pg_dump -U lims_user -d lims_db \
  --schema-only \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  > /tmp/nimblelims-schema_ddl.sql
```

## Dump functions

```bash
docker exec -i lims-db psql -U lims_user -d lims_db <<'EOF' > /tmp/nimblelims-schema_functions.sql
SET client_min_messages = warning;
SELECT pg_get_functiondef(p.oid)
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
ORDER BY p.proname;
EOF
```

## Migrations

```bash
docker compose exec backend python run_migrations.py
```

## Health checks

```bash
curl http://localhost:8000/health
curl -I http://localhost:3000
docker compose ps
```

## Related

- [Admin setup](admin-setup.md)
- [Dev setup](dev-setup.md)
- [Docs index](../README.md)
