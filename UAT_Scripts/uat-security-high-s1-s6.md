# UAT: High security remediation (S1–S6)

**Stem:** `security-high-s1-s6`  
**Branch:** `security/high-s1-s6`  
**Date:** 2026-08-20  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../.docs/requirements/security-high-s1-s6.md)  
**Source audit:** [`.docs/security-review/codebase.md`](../.docs/security-review/codebase.md)  
**Related:** [uat-security-rbac.md](uat-security-rbac.md) (broader RBAC; this script is High-finding focused)

## Purpose

Accept that production-blocking High findings S1–S6 are fixed before merge to `main`:

| ID | Theme |
|----|--------|
| S1 | App DB role `lims_app` so RLS can apply |
| S2 | bcrypt + must-change password + complexity |
| S3 | JWT secret env; refuse defaults |
| S4 | No request body logging |
| S5 | Aliquot execute: cohort + null amount refuse + transactional |
| S6 | Entry upsert/write-back only for experiment cohort |

---

## Environment / preconditions

### Stack

| Item | Value |
|------|-------|
| App | `docker compose up -d --build` from repo root (or equivalent staging) |
| Frontend | `http://localhost:3000` |
| API | `http://localhost:8000` |
| Branch / build | Includes P0a–P0d on `security/high-s1-s6` |

### Local / UAT flags (required for dogfood)

Compose **development** profile should set:

```text
ENVIRONMENT=development
ALLOW_INSECURE_DEFAULTS=true
ALLOW_DEV_SEED_USERS=true
SECRET_KEY=<placeholder ok only with flags above>
DATABASE_URL=postgresql://lims_app:…@db:5432/lims_db
MIGRATE_DATABASE_URL=postgresql://lims_user:…@db:5432/lims_db
LIMS_APP_PASSWORD=…
```

**Do not** run production-like UAT with well-known JWT secrets or `ALLOW_INSECURE_DEFAULTS=true`.

### Seed / bootstrap users

| Profile | Users |
|---------|--------|
| Local compose with `ALLOW_DEV_SEED_USERS` | `admin` / temporary password (e.g. `admin123`) — **must change on first login** |
| After first login | Complex password (≥12, upper, lower, digit, symbol) |

### Throwaway UAT users (recommended — does not reset admin)

If seed `admin` already completed must-change, create throwaway personas:

```bash
docker compose exec lims-backend python create_uat_users.py
```

| Username | Role / org | Password | Use for |
|----------|------------|----------|---------|
| `uat-admin` | Administrator / System | `UatTemp1!xxxx` | **TC-S2-001** (`must_change_password=true`) |
| `uat-labtech` | Lab Technician / System | `UatTemp1!xxxx` | **TC-S5 / S6** live |
| `uat-client-a` | Client / UAT Client A | `UatTemp1!xxxx` | **TC-S1-002** |
| `uat-client-b` | Client / UAT Client B | `UatTemp1!xxxx` | **TC-S1-002** |

Script is idempotent (resets those four usernames’ passwords only).

### Tools

- Browser (hard-refresh after deploy)
- Optional: `curl`, Docker logs (`docker compose logs backend --tail=200`)
- Lab user with `experiment:manage` for entry/aliquot cases

### Pass criteria

- Every **Required** case Pass  
- No password plaintext in backend logs during login  
- Document residual Fail only if deferred Med (S7+) — not S1–S6  

---

## TC-S3-001 — JWT secret configuration (Required)

**Maps to:** S3  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Confirm compose/env: `SECRET_KEY` set (and/or `JWT_SECRET_KEY` alias) | App starts |
| 2 | Temporarily set `ENVIRONMENT=production`, clear `ALLOW_INSECURE_DEFAULTS`, set `SECRET_KEY=your-secret-key-change-in-production`, restart backend | Process **refuses to start** / fatal message about default JWT secret |
| 3 | Restore development flags + secret; restart | Backend healthy (`GET /health` → 200) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S4-001 — No body logging on login (Required)

**Maps to:** S4  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Tail backend logs: `docker compose logs -f backend` | Logging active |
| 2 | Log in via UI with username `admin` and a temporary password | Login succeeds or must-change screen appears |
| 3 | Inspect log lines for the login request | Method/path may appear; **no** request body; **no** password string; no `Body:` dump |
| 4 | Stop tail | — |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S2-001 — Must-change password + complexity (Required)

**Maps to:** S2 / Q7  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Log out if needed; open `/login` | Login form |
| 2 | Sign in as seeded `admin` with temporary password | **Change password** screen (app shell blocked) |
| 3 | Try new password `short` | Rejected; complexity errors shown |
| 4 | Try new password equal to username (padded) if applicable | Rejected |
| 5 | Set valid password (e.g. `AdminChange1!xx`) confirming match | Success; redirected into app |
| 6 | Log out; log in with **old** temporary password | 401 / login failed |
| 7 | Log in with **new** password | Success; **no** change-password gate |
| 8 | Optional API: `GET /auth/me` | `must_change_password: false` |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S2-002 — bcrypt / legacy upgrade smoke (Required)

**Maps to:** S2  

| Step | Action | Expected |
|------|--------|----------|
| 1 | After TC-S2-001, in DB (optional): `SELECT left(password_hash,4) FROM users WHERE username='admin'` | Starts with `$2b$` or `$2a$` (bcrypt) |
| 2 | Automated: `pytest tests/test_password_policy_p0b.py -q` | Pass |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S3-002 — Reject token forged with known default secret (Required if feasible)

**Maps to:** S3  

Use only when staging runs with a **non-default** `SECRET_KEY`.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Mint a JWT offline with payload `sub`/`username`/`role` signed using `your-secret-key-change-in-production` | Token string obtained |
| 2 | `GET /auth/me` with `Authorization: Bearer <forged>` | **401** |
| 3 | Same call with a real token from login | **200** |

| Result | Pass / Fail / N/A | Tester | Date | Notes |
|--------|-------------------|--------|------|-------|
| | | | | |

---

## TC-S1-001 — Runtime role is `lims_app` (Required)

**Maps to:** S1 / P0d  

| Step | Action | Expected |
|------|--------|----------|
| 1 | On backend start logs, find ensure + server start | “Ensuring lims_app role”; uvicorn starts |
| 2 | `docker compose exec db psql -U lims_user -d lims_db -c "\du lims_app"` | Role exists; **not** Superuser |
| 3 | Confirm backend env `DATABASE_URL` user is `lims_app` (compose) | Not `lims_user` for runtime |
| 4 | Confirm `MIGRATE_DATABASE_URL` uses `lims_user` | Migrations still owner |
| 5 | Restart backend twice | Second start: role already exists; **password not rotated** (unless rotate flag set) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S1-002 — Client isolation smoke under app role (Required)

**Maps to:** S1 (RLS felt by app)  

Prefer two client orgs if available (see [uat-security-rbac.md](uat-security-rbac.md) isolation cases). Minimum:

| Step | Action | Expected |
|------|--------|----------|
| 1 | As System/lab admin, note a sample belonging to Client A’s project | Sample ID known |
| 2 | Log in as a **Client** user scoped to Client B (or user without project access to A) | Session OK |
| 3 | `GET /samples` or UI Samples list | Does **not** show Client A’s confidential sample |
| 4 | Direct `GET /samples/{id}` for Client A sample as Client B user | **404** or empty / forbidden — not full payload |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S6-001 — Entry upsert rejects non-cohort sample (Required)

**Maps to:** S6  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Create/open an experiment; start with cohort sample **S1** only (or link S1 via start/assign) | Cohort = {S1} |
| 2 | Open a sample-scoped entry; note a field_definition_id | — |
| 3 | `PUT /v1/entries/{id}/values` with `sample_id` = **S2** (not in cohort) and a text value | **400**, `detail.code` = `sample_not_in_cohort` |
| 4 | Same call with `sample_id` = **S1** | **200**; value saved |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S6-002 — Cohort write-back / submit regression (Required)

**Maps to:** S6 / QA Q6  

| Step | Action | Expected |
|------|--------|----------|
| 1 | On cohort sample S1, save entry values (draft) | Success |
| 2 | Submit entry if write-back mapped | Success; sample updated only for S1 |
| 3 | Confirm no write-back applied to off-cohort samples | No unexpected Sample column changes |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S5-001 — Aliquot execute: source not in cohort (Required)

**Maps to:** S5  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Experiment with aliquot/pool plan entry; sample **S_out** has contents/amount but is **not** on cohort | — |
| 2 | `POST /v1/entries/{plan}/execute` with line `source_sample_id=S_out` | **400**, `source_not_in_cohort` |
| 3 | Confirm no new aliquot samples created | DB/UI unchanged |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S5-002 — Aliquot execute: null source amount (Required)

**Maps to:** S5  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Cohort sample with contents row where `amount` is **null** | — |
| 2 | Execute plan transferring mass from that source | **400**, `source_amount_null` |
| 3 | Set amount; re-execute happy path (optional) | Success; source amount reduced |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S5-003 — Aliquot execute: insufficient amount fails closed (Required)

**Maps to:** S5  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Cohort sample amount = 5; request transfer 99 | — |
| 2 | Execute (not dry-run) | **400**; message includes insufficient amount |
| 3 | Confirm source amount still 5; no dest sample | No partial commit |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-S5-004 — Aliquot execute happy path (Required regression)

**Maps to:** S5  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Cohort sample amount = 50; execute by_mass transfer 15 | **200**; `success_count` = 1 |
| 2 | Source amount | 35 |
| 3 | Dest sample | Exists; parent = source |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| | | | | |

---

## TC-PROD-001 — Production-like refuse insecure defaults (Required before prod claim)

**Maps to:** S3 + S2 bootstrap  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Staging with `ENVIRONMENT=production`, strong `SECRET_KEY`, strong `LIMS_APP_PASSWORD`, **no** `ALLOW_INSECURE_DEFAULTS` / **no** `ALLOW_DEV_SEED_USERS` | Starts |
| 2 | Default placeholder `SECRET_KEY` | Refuses start |
| 3 | Admin create without `BOOTSTRAP_ADMIN_PASSWORD` when no users | Fails closed (create_admin / docs) |

| Result | Pass / Fail / N/A | Tester | Date | Notes |
|--------|-------------------|--------|------|-------|
| | | | | |

---

## Automated complement (run with UAT)

```bash
cd backend
ENVIRONMENT=test ALLOW_INSECURE_DEFAULTS=true SECRET_KEY=pytest-secret-key-not-for-production \
  python3 -m pytest \
  tests/test_security_config_s3_s4.py \
  tests/test_password_policy_p0b.py \
  tests/test_security_p0c_cohort.py \
  tests/test_aliquot_plan.py \
  tests/test_ensure_lims_app_role.py \
  -q
```

| Suite | Pass / Fail | Notes |
|-------|-------------|-------|
| Above pytest set | | |

---

## Sign-off

| Role | Name | Date | Verdict |
|------|------|------|---------|
| Tester | | | Pass / Fail |
| Product / Lab Ops (optional) | | | |
| Eng | | | |

**Merge to `main` only if Required cases Pass** (or Fail with written waiver — not recommended for High).

After Pass: update [`.docs/security-review/codebase.md`](../.docs/security-review/codebase.md) S1–S6 → **Met**, then merge.
