# Tech sketch: High security remediation (S1–S6)

**Date:** 2026-08-20  
**Status:** Draft for architecture / security review  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Schema:** [`.docs/schema-changes/security-high-s1-s6.md`](../schema-changes/security-high-s1-s6.md)  
**Audit:** [`.docs/security-review/codebase.md`](../security-review/codebase.md)

## 1. Problem / link

Ship code changes that make S1–S6 **Met**. This sketch is *how*, not product justification.

## 2. Technical goals / non-goals

**Goals:** Correct AuthN secrets & password KDF; stop credential logging; enforce cohort + transactional aliquot; make RLS bite the FastAPI role.

**Non-goals:** Rewrite all policies (S11 Med); unpublish `:5432` (S12 Med) beyond notes; frontend token storage redesign.

---

## 3. Proposed components

```
┌─────────────────┐     DATABASE_URL (lims_app)      ┌──────────────────┐
│ FastAPI backend │ ────────────────────────────────►│ PostgreSQL       │
│  + SET LOCAL    │     RLS / FORCE RLS applies      │ lims_app role    │
│    GUCs         │                                  │ lims_migrator /  │
└─────────────────┘                                  │ lims_user owner  │
        │                                            └──────────────────┘
        │ SECRET_KEY / JWT_SECRET_KEY alias
        │ bcrypt verify + optional SHA256→bcrypt upgrade
        │ LoggingMiddleware: no body
        │ EntryService: cohort check on upsert/WB
        │ AliquotPlanService.execute: txn + cohort + amount
```

---

## 4. S3 — JWT secret

**File:** `backend/app/core/config.py` (+ startup hook in `main.py`)

1. Resolve secret: `os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY")`.  
2. Known-bad set: `your-secret-key-change-in-production`, `your-secret-key-here`, empty, whitespace.  
3. If bad and not (`ENVIRONMENT in {development, test}` **and** `ALLOW_INSECURE_DEFAULTS=true`): **raise SystemExit** at import/startup.  
4. Align `docker-compose.yml` backend env: set `SECRET_KEY` (keep `JWT_SECRET_KEY` as duplicate same value for compatibility during transition).  
5. Update `.env.example`, `backend/.env.example`.

---

## 5. S4 — Body logging

**File:** `backend/app/main.py` `LoggingMiddleware`

- Remove `await request.body()` and body log lines.  
- Log: method, path, client host (optional), status code after call.  
- Do not log `Authorization`.

---

## 6. S2 — Password hashing

**File:** `backend/app/core/security.py`

- Use `passlib` bcrypt (or `bcrypt` library). Prefer passlib `CryptContext(schemes=["bcrypt"], deprecated="auto")`.  
- `verify_password`:  
  - If hash looks like bcrypt (`$2b$` / `$2a$`), verify bcrypt.  
  - Else if 64-char hex, treat as legacy SHA256; on success return True and caller **rehashes** (login path updates `user.password_hash`).  
- Seed migrations:  
  - **Do not rewrite historical migration hashes in place** if already applied in the wild; add a **new** migration or seed gate:  
    - Dev/UAT: `ALLOW_DEV_SEED_USERS=true` (compose default for local) continues to ensure known users exist with **bcrypt** hashes of known passwords.  
    - Production compose profile: omit seed users or require random passwords from secrets manager.  
- Update `0058` / any future seeds to use `get_password_hash` only after bcrypt lands.  
- Tests in `test_auth.py` already expect `$2b$` — align implementation with tests.

---

## 7. S6 — Cohort upsert / write-back

**File:** `backend/app/services/entry_service.py`

- Helper already exists: `_experiment_sample_ids(experiment_id)`.  
- In `upsert_values` (name as in code): when `item.sample_id` is set and entry is sample-scoped (or write-back will run), **require** `item.sample_id in set(_experiment_sample_ids(...))`.  
- In `submit_entry` / `_apply_write_back`: same check before Sample mutation.  
- Error: `400` with clear detail (`sample_id not in experiment cohort`).  
- No schema change.

---

## 8. S5 — Aliquot execute

**File:** `backend/app/services/aliquot_plan_service.py`

1. Wrap `execute` body in explicit transaction (`begin` / nested if needed); on any `HTTPException` or unexpected error → rollback. Avoid mid-loop `commit()`.  
2. Before transfers: load cohort IDs for entry’s experiment; every `source_sample_id` must be ∈ cohort.  
3. In `_execute_transfer`: if `content.amount is None` → `400` refuse (remove “still create dest” path).  
4. Tests: unbound source; null amount; failure mid-batch leaves no orphan samples.

---

## 9. S1 — App role + SET LOCAL

### 9.1 Roles

| Role | Use |
|------|-----|
| `lims_user` (or rename clarity later) | DB owner / migrations (elevated) |
| `lims_app` | Runtime FastAPI `DATABASE_URL` |

Migration (Alembic):

- `CREATE ROLE lims_app LOGIN PASSWORD …` (password from env at migrate time or compose init script).  
- `GRANT CONNECT`, `USAGE` on schema, `SELECT/INSERT/UPDATE/DELETE` on app tables; **no** BYPASSRLS; **not** SUPERUSER; **not** table owner.  
- `GRANT USAGE, SELECT` on sequences.  
- Ensure FORCE RLS tables stay FORCE’d.

### 9.2 Session GUC

- In `get_db` dependency or auth dependency after `get_current_user`:  
  `SET LOCAL app.current_user_id = '<uuid>'`  
  and where needed `SET LOCAL app.client_id = '<uuid>'`.  
- Use SQLAlchemy `Session.execute(text("SELECT set_config('app.current_user_id', :v, true)"))` (third arg `true` = local to transaction) — preferred over raw SET for driver safety.  
- Confirm policies in `0003_rls_policies.py` / later migrations match these GUC names (tests already mention `app.current_user_id`).

### 9.3 Compose

```yaml
# backend runtime
DATABASE_URL: postgresql://lims_app:${LIMS_APP_PASSWORD}@db:5432/lims_db
# migrate job / entrypoint uses owner URL
MIGRATE_DATABASE_URL: postgresql://lims_user:${POSTGRES_PASSWORD}@db:5432/lims_db
```

Entrypoint: run Alembic with migrator URL, then start uvicorn with app URL.

### 9.4 Risk note

Some code paths may assume owner privileges (e.g. creating extensions). Those stay on migrator. If app needs a privilege it lacks, **grant least privilege**, do not elevate app to owner.

---

## 10. Phase mapping

| Phase | Deliverables |
|-------|----------------|
| P0a | S3 + S4 code + compose/env docs |
| P0b | S2 bcrypt + login upgrade + seed gate |
| P0c | S5 + S6 service guards + tests |
| P0d | S1 role migration + SET LOCAL + compose dual URL + RLS tests on app role |

---

## 11. Open technical risks → open-questions

| Risk | OQ |
|------|-----|
| Exact role/password bootstrap in Docker init vs Alembic | Q1 |
| Production seed user policy (delete vs randomize) | Q2 |
| bcrypt vs argon2 | **Provisional: bcrypt** (align docs/tests) |
| Whether `ENVIRONMENT=development` alone allows insecure JWT | Q3 |

---

## 12. Test plan (eng)

| Area | Tests |
|------|-------|
| Config | Default secret rejected when `ENVIRONMENT=production` |
| Auth | bcrypt hash; SHA256 login upgrades; wrong password |
| Middleware | No body in log captures (unit or monkeypatch logger) |
| Entry | Upsert foreign sample_id → 400; write-back same |
| Aliquot | Null amount → 400; non-cohort source → 400; rollback on mid failure |
| RLS | Queries as `lims_app` with GUC A cannot see client B rows |
