# Checklist: security-high-s1-s6

**Branch:** `security/high-s1-s6`  
**Last updated:** 2026-08-20  
**Requirements:** [`.docs/review/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)

## Packet gate

- [x] Idea  
- [x] Requirements  
- [x] Tech sketch  
- [x] Schema-changes doc  
- [x] Open questions  
- [x] CEO / Arch / Security / QA reviews drafted (Accept with conditions)  
- [x] Q2 / Q7 decided (vendor seeds + must-change + complexity)  
- [x] Q1 decided (Option C — ensure script, create-once password)  

## P0a — S3 JWT + S4 logging

- [x] Resolve SECRET_KEY / JWT_SECRET_KEY; refuse defaults  
- [x] Align docker-compose + env examples  
- [x] Remove body logging from middleware  
- [x] Tests (`tests/test_security_config_s3_s4.py`)

## P0b — S2 passwords (+ Q2/Q7)

- [x] bcrypt hash/verify + SHA256 upgrade path  
- [x] Gate persona seeds behind ALLOW_DEV_SEED_USERS; prod bootstrap via `BOOTSTRAP_ADMIN_PASSWORD` (`create_admin.py`)  
- [x] `users.must_change_password` migration `0061` + login gate + change-password API  
- [x] Complexity rules (12+ / upper / lower / digit / symbol / ≠ username / ≠ current)  
- [x] Frontend change-password gate  
- [x] Tests (`test_password_policy_p0b.py`)  

## P0c — S5 aliquot + S6 cohort write

- [x] Entry cohort check on upsert / write-back  
- [x] Aliquot execute single transaction (fail → rollback; no partial commit)  
- [x] Source ∈ cohort; refuse null amount  
- [x] Tests (`test_aliquot_plan.py`, `test_security_p0c_cohort.py`)  
- [x] **Sec9:** containers RLS `created_by` INSERT (`0062`) + RLS→403 mapping (`test_containers_rls_sec9.py`)

## P0d — S1 app role

- [x] Q1 decided (C)  
- [x] Entrypoint `ensure_lims_app_role` (create-once + idempotent grants; no password alter by default)  
- [x] Optional Alembic grants companion — skipped (ensure script authoritative)  
- [x] `set_config(..., true)` RLS GUCs via `set_rls_context` + `after_begin`  
- [x] Dual DATABASE_URL + `LIMS_APP_PASSWORD` in compose / env examples  
- [x] Tests (`test_ensure_lims_app_role.py`)

## Docs / UAT / merge

- [x] manuals/backend-auth (+ env examples)  
- [ ] README security claims polish (optional before merge)  
- [ ] Update codebase.md S1–S6 status after ship  
- [x] `UAT_Scripts/uat-security-high-s1-s6.md`  
- [ ] Dogfood local compose  
- [ ] UAT pass  
- [ ] Merge to `main`  
