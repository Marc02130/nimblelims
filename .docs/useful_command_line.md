# Clean Restart Containers 
docker-compose down
docker system prune -a
docker-compose up -d --build

# Export container logs
docker-compose logs backend > ./.docs/backend.logs
docker-compose logs frontend > ./.docs/frontend.logs
docker-compose logs db > ./.docs/db.logs

# Dump everything
docker exec lims-db pg_dump -U lims_user -d lims_db \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  > ./.docs/schema_dump.sql

# Dump Data
docker exec lims-db pg_dump -U lims_user -d lims_db \
  --data-only \
  --no-owner \
  --no-privileges \
  --inserts \
  > ./.docs/schema_data.sql

# Dump Schema
docker exec lims-db pg_dump -U lims_user -d lims_db \
  --schema-only \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
> ./.docs/schema_ddl.sql

# Dump Functions
docker exec -i lims-db psql -U lims_user -d lims_db <<EOF > ./.docs/schema_functions.sql
-- Header for clean import
SET client_min_messages = warning;

-- Generate CREATE FUNCTION statements
SELECT pg_get_functiondef(oid) || ';'
FROM pg_proc
WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')  -- Adjust schema if not 'public'
  AND proname NOT LIKE 'pg_%'  
ORDER BY proname;
EOF

# Dump RLS
docker exec -i lims-db psql -U lims_user -d lims_db <<EOF > ./.docs/schema_rls.sql
-- Header for clean import
SET client_min_messages = warning;
SET row_security = off;

-- Generate CREATE POLICY statements
SELECT 'CREATE POLICY "' || polname || '" ON "' || nspname || '"."' || relname || '" '
       || CASE WHEN polroles = '{0}' THEN 'FOR ALL ' ELSE 'TO ' || string_agg(pg_get_userbyid(polroles[i]), ', ') END
       || ' USING (' || polqual || ')'
       || COALESCE(' WITH CHECK (' || polwithcheck || ')', '')
       || ';'
FROM (
  SELECT polname, polroles, polqual, polwithcheck,
         (SELECT relname FROM pg_class WHERE oid = polrelid) AS relname,
         (SELECT nspname FROM pg_namespace WHERE oid = relnamespace) AS nspname
  FROM pg_policy
) AS policies
GROUP BY polname, polqual, polwithcheck, relname, nspname, polroles
ORDER BY nspname, relname, polname;
EOF

# Dump Triggers
docker exec -i lims-db psql -U lims_user -d lims_db <<EOF > ./.docs/schema_triggers.sql
-- Header for clean import
SET client_min_messages = warning;

-- Generate CREATE TRIGGER statements
SELECT 'CREATE TRIGGER "' || tgname || '" '
       || CASE WHEN tgtype & 1 = 1 THEN 'BEFORE' ELSE 'AFTER' END
       || CASE WHEN tgtype & 2 = 2 THEN ' INSERT' ELSE '' END
       || CASE WHEN tgtype & 4 = 4 THEN ' OR DELETE' ELSE '' END
       || CASE WHEN tgtype & 8 = 8 THEN ' OR UPDATE' ELSE '' END
       || CASE WHEN tgtype & 16 = 16 THEN ' OR TRUNCATE' ELSE '' END
       || ' ON "' || nspname || '"."' || relname || '" '
       || CASE WHEN tgtype & 64 = 64 THEN 'FOR EACH ROW ' ELSE 'FOR EACH STATEMENT ' END
       || 'EXECUTE FUNCTION ' || proname || '();'
FROM (
  SELECT tgname, tgtype, tgrelid, tgfoid,
         (SELECT nspname FROM pg_namespace WHERE oid = relnamespace) AS nspname,
         (SELECT relname FROM pg_class WHERE oid = tgrelid) AS relname,
         (SELECT proname FROM pg_proc WHERE oid = tgfoid) AS proname
  FROM pg_trigger
  WHERE NOT tgisinternal  -- Exclude system/internal triggers
) AS triggers
ORDER BY nspname, relname, tgname;
EOF