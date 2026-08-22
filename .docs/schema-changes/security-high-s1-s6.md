# Schema changes: security-high-s1-s6

**Feature / cycle:** High security remediation (S1–S6)  
**Phases covered:** P0a–P0d  
**Status:** Draft — ready for architecture review  
**Alembic revisions:** `0061` (`must_change_password` + seed bcrypt rehash) — P0b. P0d role `lims_app` via entrypoint `ensure_lims_app_role.py` (no Alembic companion).  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Tech sketch:** [`.docs/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)  
**Architecture review:** [`.docs/architecture-review/security-high-s1-s6.md`](../architecture-review/security-high-s1-s6.md)

## 1. Summary

This cycle is primarily **roles, grants, and application AuthN/AuthZ**, plus a small **users** column for first-login password change. Expected DB work: `users.must_change_password`, create runtime role `lims_app`, grants, password_hash rehash for seeds.

## 2. Delta (authoritative list)

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| — | None | — |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| `users` | **ADD** `must_change_password BOOLEAN NOT NULL DEFAULT true` | Q7 — cleared after successful change-password; backfill existing users `false` except known seed usernames if still on published passwords |
| `users` | Optional data update: `password_hash` values | Rehash seeds / login upgrade; confirm `String(255)` fits bcrypt; widen if needed |

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| — | None required for S1–S6 | — |

### 2.4 Enums / types

| Type | Change |
|------|--------|
| — | None |

### 2.5 Roles / grants (DB objects)

| Object | Change | Why |
|--------|--------|-----|
| Role `lims_app` | CREATE LOGIN role | S1 runtime non-owner |
| Grants on `public` tables/sequences | SELECT, INSERT, UPDATE, DELETE, USAGE | App least privilege |
| Privileges | No SUPERUSER, no BYPASSRLS, not OWNER | So FORCE RLS applies |

Password bootstrap: **Q1 Decided = Option C** (entrypoint ensure; create-once password from `LIMS_APP_PASSWORD`; no alter on every start). Alembic may add grants; ensure script is authoritative for upgrades.

## 3. RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| Existing policies | **No rewrite required** for S1–S6 | Making app role non-owner is the fix |
| FORCE RLS | Keep as-is on ELN/entry tables | Already present; ineffective today for owner |
| GUC bind | Application `set_config(..., true)` | Not a DDL change |

**Explicitly deferred to Med follow-up (S11):** FORCE RLS on samples/tests/results; fix `is_admin() OR true`; contents RLS.

## 4. Data migration / backfill

- [x] None for schema shape  
- [ ] Optional: UPDATE seed users’ `password_hash` to bcrypt when `ALLOW_DEV_SEED_USERS`  
- [ ] Login-time upgrade for legacy SHA256 (app-layer, not Alembic)

## 5. Rollback

- Role `lims_app`: DROP ROLE after revoking grants (forward-only preferred in prod).  
- Password hashes: bcrypt-only is forward-compatible; keep SHA256 verify until all users upgraded, then remove.

## 6. Explicitly out of scope (this cycle)

- New audit event tables  
- Changing RLS policy expressions (S11)  
- Dropping published port 5432 (S12)  
- Altering entry/aliquot table columns  

## 7. Open schema blockers

- None for P0d bootstrap path — **Q1/Q2 decided**. Implement ensure script + grants; optional Alembic companion revision.

## 8. Implementation checklist

- [ ] Migration(s) match this doc  
- [ ] Models unchanged (or `password_hash` length only)  
- [ ] RLS tested with `lims_app`  
- [ ] This file updated with revision id(s)  
