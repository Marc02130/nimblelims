# Requirements: High security remediation (S1–S6)

**Date:** 2026-08-20  
**Status:** **Ready for reviews** — security-focused packet (CEO · Architecture · Security · QA)  
**Branch:** `security/high-s1-s6`  
**Source audit:** [`.docs/review/security-review/codebase.md`](../security-review/codebase.md)  
**Idea:** `.docs/internal/ideas/security-high-s1-s6.md`  
**Tech sketch:** [`.docs/review/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)  
**Schema changes:** [`.docs/review/schema-changes/security-high-s1-s6.md`](../schema-changes/security-high-s1-s6.md)  
**Open questions:** [`.docs/review/open-questions/security-high-s1-s6.md`](../open-questions/security-high-s1-s6.md)  
**Checklist:** [`.docs/review/checklist/security-high-s1-s6.md`](../checklist/security-high-s1-s6.md)

## Review packet

| Review | Doc | Gate |
|--------|-----|------|
| CEO / product | [ceo-review/security-high-s1-s6.md](../ceo-review/security-high-s1-s6.md) | Required |
| Architecture | [architecture-review/security-high-s1-s6.md](../architecture-review/security-high-s1-s6.md) | Required |
| Security (CSO) | [security-review/security-high-s1-s6.md](../security-review/security-high-s1-s6.md) | Required |
| QA / Testing | [qa-review/security-high-s1-s6.md](../qa-review/security-high-s1-s6.md) | **Required** (security) |
| Lab Ops / UI | — | **Skipped** this cycle (no intentional bench UX redesign; S5–S6 are fail-closed eng) |

**Production gate:** codebase audit blocks production until S1–S6. Merge to `main` only after implement + tests + UAT script for this stem.

---

## 1. Problem

NimbleLIMS claims client isolation (RLS) and controlled lab write paths (entries, aliquot execute). On HEAD:

1. **S1** — App connects as PostgreSQL owner/superuser-equivalent (`lims_user`); RLS and `FORCE ROW LEVEL SECURITY` are not enforced for FastAPI.  
2. **S2** — Passwords hashed with unsalted SHA256; migrations seed well-known credentials (`admin`/`admin123`, etc.).  
3. **S3** — Compose sets `JWT_SECRET_KEY`; app reads `SECRET_KEY` with hardcoded default → forgeable JWTs.  
4. **S4** — Middleware logs request bodies (login passwords appear in logs).  
5. **S5** — Aliquot execute can partial-commit; source need not be on experiment; null source amount still creates destinations.  
6. **S6** — Entry upsert/write-back accepts arbitrary `sample_id` not constrained to experiment cohort (grid/export already cohort-scoped).

## 2. Goals

| ID | Goal |
|----|------|
| G1 | App DB role feels RLS; client isolation is real for FastAPI queries |
| G2 | Passwords use modern KDF; known UAT passwords only when explicitly enabled for non-prod |
| G3 | JWT signing key from one env name; process refuses known/default secrets outside explicit local-dev override |
| G4 | No request body logging in default middleware |
| G5 | Aliquot execute is transactional, cohort-bound, amount-safe |
| G6 | Entry save/submit write-back and sample-scoped upsert only for cohort samples |

## 3. Non-goals (this cycle)

- S7–S15 (Med/Low) except where a one-line fix is unavoidable while doing S1–S6  
- Changing frontend `localStorage` token storage (document only; S10)  
- Publishing Postgres port policy beyond documenting S12 for follow-up  
- New multi-tenant org model  
- Full audit-event table for submit/execute (prior packet S7 — track, do not expand)

---

## 4. Functional / security requirements

### FR-S1 — Application database role + RLS context

| ID | Requirement |
|----|-------------|
| FR-S1.1 | System shall connect FastAPI with a **non-owner, non-superuser** PostgreSQL role (e.g. `lims_app`) that is subject to RLS / FORCE RLS. |
| FR-S1.2 | Migrations / DDL shall continue to use an elevated role (owner/migrator); runtime app traffic shall not use that role. |
| FR-S1.3 | On authenticated requests, the app shall set session GUCs used by RLS policies (at minimum `app.current_user_id`; `app.client_id` where policies require it) via `SET LOCAL` (or equivalent transaction-scoped bind) before business queries. |
| FR-S1.4 | Unauthenticated / background paths shall not inherit another user’s GUC; default must fail closed (no rows / explicit denial), not “see all.” |
| FR-S1.5 | Docker Compose / `.env.example` shall document `DATABASE_URL` for the **app** role separately from migrator credentials (`MIGRATE_DATABASE_URL` + `LIMS_APP_PASSWORD`). |
| FR-S1.6 | Automated tests shall demonstrate RLS isolation using the app role (extend existing `test_rls_*` patterns). |
| FR-S1.7 | **Q1 Option C:** Backend entrypoint shall idempotently ensure role `lims_app`: create with password from `LIMS_APP_PASSWORD` only when missing; if role exists, ensure grants only and **do not** change password on normal starts. Explicit rotate is out-of-band / one-shot. |

### FR-S2 — Password hashing, seeds, first-login change, complexity

| ID | Requirement |
|----|-------------|
| FR-S2.1 | `get_password_hash` / `verify_password` shall use **bcrypt** (Q4). |
| FR-S2.2 | System shall verify existing SHA256 hex hashes for a **one-time upgrade path** on successful login (rehash to bcrypt) **or** migrate known seed hashes; no plaintext passwords in migrations. |
| FR-S2.3 | **Deployment profiles (Q2):** always seed roles/permissions. Persona users with well-known passwords only when `ALLOW_DEV_SEED_USERS=true` (dev/demo/UAT). Production uses bootstrap/wizard admin with customer-controlled secret — not README passwords. |
| FR-S2.4 | Production shall not rely on published default passwords; startup checks / docs per tech sketch. |
| FR-S2.5 | **Must change password (Q7):** `users.must_change_password` boolean. Seeded and bootstrap users created with `true`. While `true`, after successful credential check the API issues only a constrained session (or equivalent) that may call **change-password**; all other authenticated routes return **403** with code `password_change_required`. |
| FR-S2.6 | Successful change-password clears `must_change_password` and returns a normal access token. |
| FR-S2.7 | **Complexity (Q7)** on every password set/change (bootstrap, admin reset, self-change): minimum **12** characters; at least one uppercase, one lowercase, one digit, one symbol; must not equal username (case-insensitive); must not equal current password. Clear error messages listing failed rules (no password echoed). |
| FR-S2.8 | Frontend: on `password_change_required`, route user to change-password screen; block navigation to the app shell until cleared. |

### FR-S3 — JWT secret configuration

| ID | Requirement |
|----|-------------|
| FR-S3.1 | App shall read **one** primary env var for the HMAC secret: prefer `SECRET_KEY`, accept `JWT_SECRET_KEY` as alias if `SECRET_KEY` unset (document precedence). |
| FR-S3.2 | Compose, `.env.example`, and backend `.env.example` shall set the **same** variable name(s) the app reads. |
| FR-S3.3 | If the resolved secret is empty or equals a known default (`your-secret-key-change-in-production`, `your-secret-key-here`, etc.), startup shall **fail** unless an explicit local-dev flag allows it (`ALLOW_INSECURE_DEFAULTS=true` or `ENVIRONMENT=development` with documented exception). |
| FR-S3.4 | Tests shall cover: missing/default secret refused in production-like env; alias env works. |

### FR-S4 — No body logging

| ID | Requirement |
|----|-------------|
| FR-S4.1 | Default request logging middleware shall **not** read or log request bodies. |
| FR-S4.2 | Method, path, status, duration (optional) may remain; never Authorization header values or bodies. |
| FR-S4.3 | If debug body logging is ever reintroduced, it must be behind an explicit flag defaulting **off** and must redact `/auth/login` and password fields. |

### FR-S5 — Aliquot execute integrity

| ID | Requirement |
|----|-------------|
| FR-S5.1 | Execute shall run in **one DB transaction**; any failure rolls back all sample/container/contents mutations for that execute call. |
| FR-S5.2 | Every `source_sample_id` shall be a member of the experiment cohort (`experiment_sample_executions` or equivalent) for the entry’s experiment; otherwise **400/403**, no mutation. |
| FR-S5.3 | If source contents `amount` is **null**, execute shall **refuse** (no silent create-dest-without-debit). |
| FR-S5.4 | Insufficient amount remains fail-closed (already partially present). |
| FR-S5.5 | Destination creations and source debits commit together or not at all. |

### FR-S6 — Cohort-bound upsert / write-back

| ID | Requirement |
|----|-------------|
| FR-S6.1 | For sample-scoped entry types, upsert of `entry_field_values` with a `sample_id` shall require that sample ∈ experiment cohort; otherwise reject. |
| FR-S6.2 | Submit / write-back paths shall apply the same cohort check before mutating Sample columns. |
| FR-S6.3 | Grid/export cohort scoping already present shall remain; this FR closes the write hole. |
| FR-S6.4 | Negative tests: foreign `sample_id` cannot receive values or write-back via experiment entry APIs. |

---

## 5. Non-functional

| ID | Requirement |
|----|-------------|
| NFR-1 | No intentional API shape break for happy-path lab UX except clearer 4xx errors on abuse. |
| NFR-2 | Dev experience: documented one-command local setup still works with **explicit** insecure defaults only. |
| NFR-3 | Backward compatible login for existing bcrypt hashes if any; SHA256 upgrade path must not lock out all users without a plan. |
| NFR-4 | Changes covered by pytest (auth, RLS app-role, entry cohort, aliquot execute). |
| NFR-5 | UAT script `UAT_Scripts/uat-security-high-s1-s6.md` (create or extend existing security UAT). |

---

## 6. Phasing

| Phase | Scope | Exit |
|-------|--------|------|
| **P0a** | S3 JWT secret + S4 body logging | App refuses default secret in prod-like config; no body logs |
| **P0b** | S2 password KDF + seed gating | bcrypt verify; SHA256 upgrade or migrate; seeds gated |
| **P0c** | S5 + S6 cohort / txn | Tests red→green for abuse cases |
| **P0d** | S1 app role + SET LOCAL | App uses `lims_app`; RLS tests via app role |
| **Follow-up** | S7–S15 | Separate packet |

**Implement order recommendation:** P0a → P0b → P0c → P0d (fastest risk reduction first; S1 has largest ops blast radius).

---

## 7. Acceptance criteria (release)

1. Codebase audit S1–S6 marked **Met** (or **Met with documented residual**) in [security-review/codebase.md](../security-review/codebase.md) after ship.  
2. Pytest green for new/updated suites.  
3. UAT script executed on branch/staging before merge to `main`.  
4. README / manuals/backend-auth / docker-compose env docs updated.  
5. Production checklist: no default JWT; no published well-known admin password; app not connecting as table owner.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| S1 breaks local/dev if role grants incomplete | Migration grants SELECT/INSERT/UPDATE/DELETE as needed; smoke compose |
| Rehash locks users | Login upgrade path + seed-only rewrite for known hashes |
| S5 refuse-null amount breaks labs with null contents | Product-correct fail-closed; document data fix (set amount) before execute |
| Compose dual credentials confuse operators | Clear `.env.example` + manuals |

---

## 9. Open questions gate

See [open-questions/security-high-s1-s6.md](../open-questions/security-high-s1-s6.md). **Do not start P0d (S1) until Q1–Q2 decided.** P0a–P0c may proceed once reviews Accept.
