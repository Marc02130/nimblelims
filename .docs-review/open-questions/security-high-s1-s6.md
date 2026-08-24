# Open questions: security-high-s1-s6

**Status:** Living decision log  
**Date:** 2026-08-20 · **Updated:** 2026-08-20  
**Requirements:** [`.docs-review/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Blocks:** P0d unblocked (Q1 decided); P0b includes Q2/Q7 password policy

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| Q1 | How to bootstrap `lims_app` password in Docker? | **Decided** | P0d | **Option C — idempotent ensure script** in backend entrypoint (owner URL): if `lims_app` missing → `CREATE ROLE … PASSWORD` from `LIMS_APP_PASSWORD` + grants; if exists → **do not** alter password (only ensure grants). Password set on **first create** only; rotation via explicit one-shot flag/script later. Optional Alembic grants migration as supplement; not initdb-only (B). Prod: password from secret (E wrapper). Local: may share a known app password only with insecure/dev flags. | 2026-08-20 | Eng + Arch |
| Q2 | Production seed / starter users (LIMS vendor)? | **Decided** | P0b | **Vendor profiles:** (1) Always seed **roles/permissions**. (2) **dev / demo / UAT:** persona users allowed when `ALLOW_DEV_SEED_USERS=true` (or `DEPLOYMENT_PROFILE=demo\|uat`). (3) **production:** no well-known README passwords; **bootstrap/wizard** creates admin (and optional staff) with customer-controlled secrets. (4) **All** seeded/bootstrap users: `must_change_password=true` until first successful change. See **Q7** for complexity. | 2026-08-20 | Product |
| Q3 | May `ENVIRONMENT=development` alone allow default JWT, or require explicit `ALLOW_INSECURE_DEFAULTS=true`? | **Decided (provisional)** | P0a | **Require both** `ENVIRONMENT=development` (or `test`) **and** `ALLOW_INSECURE_DEFAULTS=true` for default secret. Compose local sets both. Production never sets the flag. | 2026-08-20 | Security |
| Q4 | bcrypt vs argon2? | **Decided (provisional)** | P0b | **bcrypt** — README/UAT/tests already assume bcrypt (`$2b$`). | 2026-08-20 | Eng |
| Q5 | S5 refuse-null amount: confirm product OK to fail execute when contents.amount is null? | **Decided (provisional)** | P0c | **Yes** — fail closed; lab must set tracked amount before execute. Aligns audit S5. | 2026-08-20 | Product / Security |
| Q6 | Include any Med (S7–S12) quick wins in this branch? | **Decided** | — | **No** — High only; Med follow-up packet. Exception: docs comments that falsely claim RLS works (S10 doc hygiene) may update with S1. | 2026-08-20 | CEO |
| Q7 | Password change-on-first-login + complexity rules? | **Decided** | P0b | **Must change on first login** for seeded/bootstrap users (`users.must_change_password`). Until cleared, login returns a constrained token/response that only allows `POST /auth/change-password` (or equivalent); all other API routes return **403** `password_change_required`. **Complexity (all new/changed passwords):** min **12** chars; ≥1 upper, ≥1 lower, ≥1 digit, ≥1 symbol; must not equal username (case-insensitive); must not equal current password. History / breach-list deferred. | 2026-08-20 | Product + Security |

## Gate rule

- **P0a:** done (S3/S4).  
- **P0b:** includes bcrypt + Q2/Q7 (must-change + complexity); unblocked.  
- **P0c:** unblocked (reviews Accept).  
- **P0d:** **unblocked** (Q1 = C ensure script; Q2 decided).  
- New blockers discovered in implement → add rows here; pause that phase.

## Decision detail — Q1 (Option C)

```text
entrypoint:
  1. migrate with MIGRATE_DATABASE_URL (owner)
  2. ensure_lims_app_role.py with owner connection:
       IF role missing → CREATE LOGIN + PASSWORD from LIMS_APP_PASSWORD + GRANTs
       ELSE            → GRANT idempotent only (NO ALTER PASSWORD)
  3. start uvicorn with DATABASE_URL (lims_app)
```

| Event | Password |
|-------|----------|
| First run / upgrade when role missing | Set from `LIMS_APP_PASSWORD` |
| Normal restart / image update | Unchanged |
| Intentional rotation | Separate one-shot (`ENSURE_LIMS_APP_PASSWORD_ROTATE=true` or admin script) — not default |

## Decision detail — Q2 + Q7 (vendor LIMS)

Nimble is sold as a LIMS. Starter users are required for demos/UAT and onboarding, but production must not rely on published passwords.

| Profile | Users | Passwords |
|---------|-------|-----------|
| development | Persona seeds OK when `ALLOW_DEV_SEED_USERS` | Well-known OK; seeds set `must_change_password=true` (same code path as prod) |
| demo / UAT | Persona seeds OK | Demo-kit passwords; must-change + complexity enforced |
| production | Bootstrap/wizard admin (+ optional named users) | Customer secret; must-change + complexity; **no** README passwords |

**Mechanism:** column `users.must_change_password` (default `true` for seeds/bootstrap). Cleared only after successful `change-password` that passes complexity. Automated tests may create users with `must_change_password=false` so existing login fixtures keep working.
