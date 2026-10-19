# Database roles

Three jobs, three roles. The Compose bootstrap superuser is not one of the runtime or migration roles.

| Role | Who sets it | Attributes | Job |
|------|-------------|------------|-----|
| `POSTGRES_USER` (local example: `lims_bootstrap`) | Compose, first init only | Superuser, because the Postgres image requires that | Creates the database, extensions, and the roles below. Does not run Alembic. Does not own application tables, functions, or sequences after init. |
| `lims_migrate` | `db/zz-roles.sh`, then Alembic | `LOGIN`, `NOSUPERUSER`, `BYPASSRLS`, not `CREATEDB` or `CREATEROLE` | Owns the database, `public`, `lims`, and the application objects. `MIGRATE_DATABASE_URL` points here. `backend/start.sh` runs Alembic as this role. |
| `lims_app` | `db/zz-roles.sh` and `ensure_lims_app_role.py` | `LOGIN`, `NOSUPERUSER`, `NOBYPASSRLS` | The only role the API uses (`DATABASE_URL`). Row security applies, including forced policies. |
| `lims_user` | `db/zz-roles.sh` on a new volume | `NOLOGIN`, `NOSUPERUSER`, `NOBYPASSRLS` | Historical grant target from early migrations. It is not a login and it does not own objects. `EXECUTE` on `batch_access_status(uuid)` is revoked. |  <!-- pragma: allowlist secret -->

`schema_apply` is a `NOLOGIN` role with no bypass. It owns the UI schema `SECURITY DEFINER` functions. The bootstrap script creates it and grants it to `lims_migrate` so Alembic can `ALTER ... OWNER TO schema_apply` without `CREATEROLE`. Those functions stay owned by `schema_apply` when a superuser runs the ownership migration.

`BYPASSRLS` on `lims_migrate` is required. Tables such as `batches` use `FORCE ROW LEVEL SECURITY`, so the owner does not skip policies. `batch_access_status` is `SECURITY DEFINER` and has to see every batch to answer `not_found`, `forbidden`, or `visible`. Migration seeds also write those tables without an `app.current_user_id` setting. `lims_app` does not get `BYPASSRLS`.

`EXECUTE` on `public.batch_access_status(uuid)` is revoked from `PUBLIC`, from `lims_migrate`, and from `lims_user` when that role exists. It is granted to `lims_app`. A superuser still passes `has_function_privilege` for every function, which is why the bootstrap user must not be `lims_migrate` or `lims_user`.  <!-- pragma: allowlist secret -->

On a new volume, `has_function_privilege('lims_migrate', 'public.batch_access_status(uuid)', 'EXECUTE')` is false, and the same check is false for `lims_user`.  <!-- pragma: allowlist secret -->

Copy `.env.example` to `.env` before `docker compose up`. Passwords live only in that untracked file.

Check the runtime role with `db/scripts/uat_privilege_snapshot.sql`. It raises if `lims_app.rolsuper` or `lims_app.rolbypassrls` is not false. UAT steps are in `UAT_Scripts/uat-db-roles.md`.

An existing data directory that was initialized with the historical role as `POSTGRES_USER` is a different cluster. Init scripts do not re-run there. Recreate it with `docker compose down -v`. There is no in-place upgrade script. Migration `0103_migration_role_owner` moves ownership when it is applied by a superuser, creates `lims_migrate` with `LOGIN`, and alters an existing `NOLOGIN` `lims_migrate` to `LOGIN`. It does not drop objects.
