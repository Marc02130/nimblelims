# UAT: database roles

Stem: `db-roles`. Migration `0103_migration_role_owner` (revises `0102_instant_timestamptz`).

The bootstrap superuser (`POSTGRES_USER`) only creates roles and extensions. `lims_migrate` owns application objects and runs Alembic. `lims_app` is the only runtime role.

## TC-ROLES-001 — Privilege snapshot

1. Copy `.env.example` to `.env` and set the passwords. `POSTGRES_USER` is `lims_bootstrap`, not `lims_user` or `lims_migrate`.  <!-- pragma: allowlist secret -->
2. `docker compose down -v && docker compose up -d --build` on a clean volume.
3. Backend logs show migrations running, then uvicorn. `DATABASE_URL` uses `lims_app`. `MIGRATE_DATABASE_URL` uses `lims_migrate`.
4. From the repo root, run the snapshot. `POSTGRES_USER` in `.env` is the bootstrap role named in the `-U` flag (`lims_bootstrap` in `.env.example`):

```bash
docker compose exec -T db psql -U lims_bootstrap -d lims_db \
  < db/scripts/uat_privilege_snapshot.sql
```

5. `lims_app` shows `rolsuper = f` and `rolbypassrls = f`. The script raises if either is true.
6. `has_function_privilege('lims_migrate', 'public.batch_access_status(uuid)', 'EXECUTE')` is false.
7. If `lims_user` exists, the same `EXECUTE` check is false.  <!-- pragma: allowlist secret -->
8. `pg_class` owner of `samples` is `lims_migrate`, not the bootstrap user.

## TC-ROLES-002 — App still reads as lims_app

1. Sign in as `admin` after `seed_dev_passwords.py --apply`.
2. `GET /batches` returns **200**.
3. A batch id that does not exist is **404**. A batch that exists and this session cannot see is **403** `{"code":"batch_forbidden","message":"Access denied"}`. That split is by design: the status tells the caller whether the id exists. The 403 body has no batch id, client id, or project id.
