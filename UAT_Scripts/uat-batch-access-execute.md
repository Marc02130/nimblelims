# UAT: batch_access_status execute

Stem: `batch-access-execute`. Migration `0101_revoke_probe_execute` (revises `0100_calendar_dates`).

`public.batch_access_status(uuid)` is owned by the migration role. Creating it records that role's `EXECUTE` in the function ACL when `PUBLIC` is revoked. Only `lims_app` may execute it.

## TC-PROBE-EXEC-001

1. `alembic upgrade head` from an empty database.
2. `has_function_privilege` for the migration role on `public.batch_access_status(uuid)` is false when that role is not a superuser. `SET ROLE` to that role and calling the function is permission denied.
3. `lims_app` can still execute it. A cross-client `GET /batches/{id}` is **403** `{"code":"batch_forbidden","message":"Access denied"}`. The caller's own batch still returns **200**.
4. Downgrade of `0101_revoke_probe_execute` does not grant `EXECUTE` back.
