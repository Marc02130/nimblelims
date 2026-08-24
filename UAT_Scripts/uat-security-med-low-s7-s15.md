# UAT: Med/Low security remediation (S7–S15)

**Stem:** `security-med-low-s7-s15`  
**Branch:** `security/med-low-s7-s15`  
**Date:** 2026-08-21 (completed live run)  
**Tester:** Tobias  
**Observed:** `security/med-low-s7-s15` @ `e47f1ab` (alembic `0067`; compose down after the beat)  
**Requirements:** [`.docs-review/requirements/security-med-low-s7-s15.md`](../.docs-review/requirements/security-med-low-s7-s15.md)  
**Prerequisite:** High S1–S6 Met  
**Related:** [uat-security-high-s1-s6.md](uat-security-high-s1-s6.md)

## Purpose

Accept that Med/Low findings S7–S15 are fixed before merge to `main`. This stamp is the live UAT pass on the feature branch.

**QA verdict (this run): Accept with residual.** Residual (not a hold): **TC-S11-003** own `created_by` empty tube GET **200** / PATCH **500**. P1–P4 Pass including both S7 beats.

## Environment

| Item | Value |
|------|--------|
| Stack | `docker compose up -d --build` from repo root |
| Frontend | `http://localhost:3000` |
| API | `http://localhost:8000` |
| Branch / SHA | `security/med-low-s7-s15` @ `e47f1ab` (alembic `0067`) |
| After run | Compose **down** after the beat |

Seed / fixture personas used this run (no passwords recorded):

| Username | Role / org | Use |
|----------|------------|-----|
| `alice-tech` | Lab tech / NovaBio (0058) | S7 deny, S9 enter, S11-003 cross-client |
| `bob-tech` | Lab tech / NovaBio (0058) | S7 happy path (`CAR-T-Batch-001`) |
| `david-cro` | CRO Partner | S13 `GET /roles`; empty-tube owner for S11-003 |
| `lab-tech` | Seeded lab technician | S11 execute / S5 regression / S10 cookies |
| `throttle-tech` | Created for this UAT | S15 lockout only |

**Folded cases (agreed, retained from thin script expansion):**

- **S7:** deny (`alice-tech` / unassigned same-client) **and** `bob-tech` happy path.
- **S14:** **run / entry write-back** allowlist — not receive-temperature accessioning.
- **S11-003:** **0064** cross-client empty-tube deny (not only labtech dest INSERT).

Prod overlay check (S12): `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` — DB must not publish host `5432`.

---

## P1 — S8 / S9 / S13 / S14

### TC-S8-001 — Oversized run import (Required)

**Maps to:** S8  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Create / open a LIMS run; note `{id}` | Run exists |
| 2 | `dd` a file **11 MiB**; `POST /v1/lims-runs/{id}/import-file` | **413**, `upload_too_large` |
| 3 | Confirm oversized file is not committed to git | Not in repo |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | 11 MiB `dd` POST `/v1/lims-runs/{id}/import-file` → 413 `upload_too_large`. File not in git. |

### TC-S9-001 — Unauthenticated results validate (Required)

**Maps to:** S9  

| Step | Action | Expected |
|------|--------|----------|
| 1 | `POST /results/validate` with no auth | **401** |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | unauth `POST /results/validate` → 401 |

### TC-S9-002 — Authenticated `result:enter` (Required)

**Maps to:** S9  

| Step | Action | Expected |
|------|--------|----------|
| 1 | As `alice-tech` (`result:enter`), `POST /results/validate` | **200**; body may be `is_valid=false` |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `alice-tech` `result:enter` → 200 `is_valid=false` |

### TC-S13-001 — Client catalog GET (Required)

**Maps to:** S13  

| Step | Action | Expected |
|------|--------|----------|
| 1 | As `david-cro`, `GET /roles` | **403** |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `david-cro` `GET /roles` → 403 |

### TC-S14-001 — Write-back allowlist (run / entry, not receive temp) (Required)

**Maps to:** S14 / OQ-S14  

This case is **entry `write_back_target`**, not accessioning receive-temperature.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Map `write_back_target` = `temperature` | **400** not allowed |
| 2 | Map `write_back_target` = `specimen_biotype_id` | **400** not allowed |
| 3 | Map `due_date` and `report_date` | Allowed (allowlist) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `write_back_target` `temperature` and `specimen_biotype_id` → 400 not allowed; allowlist `due_date`, `report_date`. Receive temp is not this case. |

---

## P2 — S7 / S15

### TC-S7-001 — Unassigned same-client start must fail closed (Required)

**Maps to:** S7 / FR-S7.1–4  

Folded deny path: `alice-tech` is **not** on `project_users` for Bob’s CAR-T project; both users are NovaBio (same client). Fixture **0058** is clean for the same-client beat.

**Other-client beat (0067):** sample name exactly `XYZ-BA-0001` on `Sponsor XYZ - Bioanalytical Services` (PharmaTest CRO; advertised id `proj-cro-sponsor-004`). Status **Available for Testing**. Optional container barcode `XYZ-BA-0001`. No parent / no aliquot. Alice is NovaBio; this sample is CRO — true other-client.

| Step | Action | Expected |
|------|--------|----------|
| 1 | As `alice-tech`, `GET` sample `CAR-T-Batch-001` | **403/404** (no existence oracle preferred: 404) |
| 2 | Start experiment with that sample ID | **403/404** |
| 3 | Link that sample to an experiment | **403/404** |
| 4 | As `alice-tech`, `GET` sample `XYZ-BA-0001` | **403/404** |
| 5 | Start experiment with `XYZ-BA-0001` | **403/404** |
| 6 | Link `XYZ-BA-0001` to an experiment | **403/404** |

**Retest bar (Deiter/Gunter):** unassigned **same-client** start **and** other-client start both **403/404**.

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | Same-client (`9d583ac`): `alice-tech` GET/start/link `CAR-T-Batch-001` → 404/404/404. Other-client (`e47f1ab` / 0067): `alice-tech` GET/start/link `XYZ-BA-0001` → 404/404/404. No payload. Sample present on Sponsor XYZ - Bioanalytical Services. 0067 seed unblocked the other-client beat. Compose down after the beat. |

### TC-S7-002 — Assigned tech happy path (Required, folded)

**Maps to:** S7 (must not block legitimate cohort start)

| Step | Action | Expected |
|------|--------|----------|
| 1 | As `bob-tech`, scan / GET sample `CAR-T-Batch-001` and container `CAR-T-Batch001` | **200** |
| 2 | Start experiment with that sample | **200**; `linked=1`; cohort locked |
| 3 | Confirm deny case did not block Bob | Bob still succeeds |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `bob-tech` scan `CAR-T-Batch-001` / container `CAR-T-Batch001` 200; start 200 `linked=1` `cohort_locked`. Deny did not block bob. |

### TC-S15-001 — Login lockout (Required)

**Maps to:** S15  

Use throwaway `throttle-tech` created for this case.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Four consecutive wrong passwords | **401** × 4 |
| 2 | Fifth (or next in window after N=5) | **429** `login_locked` |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `throttle-tech` (created for this case) 401×4 then 429 `login_locked` |

### TC-S15-002 — Unlock / success clears (Required)

**Maps to:** S15  

| Step | Action | Expected |
|------|--------|----------|
| 1 | After lock window, correct login | **200** |
| 2 | Throttle row | Gone / cleared |
| 3 | Next wrong password | **401** (not still locked) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | After lock window, correct login 200; throttle row gone; next wrong 401 |

---

## P3 — S11 / S12 (+ High S5 smoke)

### TC-S11-001 — Labtech dest execute; no empty committed dest (Required)

**Maps to:** S11 / OQ-S11a  

| Step | Action | Expected |
|------|--------|----------|
| 1 | As `lab-tech`, aliquot dest execute | **200** `success_count=1` |
| 2 | Own dest INSERT | **200** |
| 3 | Confirm no empty committed dest container | No empty tube/plate/box left committed |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | labtech dest execute 200 `success_count=1`; own dest INSERT 200; no empty committed dest |

### TC-S11-002 — FORCE / contents RLS smoke (Required)

**Maps to:** S11 / OQ-S11b  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Sample list as eligible lab user | **200** |
| 2 | Aliquot path still works | **200** |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | sample list + aliquot 200 |

### TC-S11-003 — 0064 cross-client empty-tube deny (Required, folded)

**Maps to:** S11 / migration `0064`  

Folded: **cross-client deny** on empty tube, not only dest INSERT.

| Step | Action | Expected |
|------|--------|----------|
| 1 | As `alice-tech`, GET David’s empty tube | **404** |
| 2 | As `alice-tech`, PATCH that tube | **404** |

**Residual (not a hold):** own `created_by` empty tube GET **200**, PATCH **500** not **403** (Sec10 follow-on).

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `alice-tech` GET/PATCH david empty tube 404/404. Residual: own `created_by` empty tube GET 200, PATCH 500 not 403 (Sec10, not a hold) |

### TC-S5-001 — Off-cohort execute still refused (High regression)

**Maps to:** S5 (spine must stay green)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Execute aliquot with source not in experiment cohort | **400** `source_not_in_cohort` |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | off-cohort execute 400 `source_not_in_cohort` |

### TC-S12-001 — Prod overlay does not publish host 5432 (Required)

**Maps to:** S12  

| Step | Action | Expected |
|------|--------|----------|
| 1 | `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` | `db.ports` **not** published to host `5432` |

**Retest bar:** prod overlay must **actually drop** host `5432` (Compose `ports: []` in overlay does not unset base).

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | Retest `9d583ac`: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` — no host `5432`. |

---

## P4 — S10 cookie AuthN

API / curl this run. **No browser DevTools panel.** Frontend source remains cookie SoT; `localStorage.removeItem('token')`.

### TC-S10-001 — Cookie vs storage (Required; API/source this run)

**Maps to:** S10  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Login | `nimble_access` HttpOnly; `nimble_csrf` **not** HttpOnly |
| 2 | Storage | No `localStorage.token` (SPA cutover) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | API: `nimble_access` HttpOnly; `nimble_csrf` not. No DevTools panel. Frontend source cookie SoT, `localStorage.removeItem` token. |

### TC-S10-002 — Cookie-only `/auth/me` (Required)

**Maps to:** S10  

| Step | Action | Expected |
|------|--------|----------|
| 1 | `GET /auth/me` with cookies only (no `Authorization`) | **200** |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | cookie-only `GET /auth/me` 200 |

### TC-S10-003 — Cookie mutate without CSRF (Required)

**Maps to:** S10  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Cookie-authenticated mutating call, no `X-CSRF-Token` | **403** `csrf_failed` |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | cookie mutate no CSRF → 403 `csrf_failed` |

### TC-S10-004 — Cookie + CSRF mutate (Required)

**Maps to:** S10  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Cookie + matching `X-CSRF-Token` POST | **201** (or success for the chosen create) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | cookie + CSRF POST 201 |

### TC-S10-005 — Logout clears cookies (Required)

**Maps to:** S10  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Logout | **200**; cookies `Max-Age=0` |
| 2 | `GET /auth/me` with no cookie | **401** |

Logout then resent Bearer must **401** (denylist).

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | logout 200 cookies `Max-Age=0`; `/auth/me` no cookie 401. Denylist (`9d583ac`): resent Bearer → 401 |

### TC-S10-006 — Bearer skips CSRF (Required)

**Maps to:** S10  

| Step | Action | Expected |
|------|--------|----------|
| 1 | `Authorization: Bearer` mutate, no CSRF header | **201** (scripts/API clients) |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | Bearer no CSRF 201 |

---

## Honesty / AuthZ

### TC-UX-001 — `hasPermission` is UX only (Required)

**Maps to:** S10 / G4  

| Step | Action | Expected |
|------|--------|----------|
| 1 | Read [`.docs-review/manuals/backend-auth.md`](../.docs-review/manuals/backend-auth.md) | States frontend `hasPermission` is UX only; server RBAC/RLS is AuthZ |

| Result | Pass / Fail | Tester | Date | Notes |
|--------|-------------|--------|------|-------|
| Pass | Pass | Tobias | 2026-08-21 | `.docs-review/manuals/backend-auth.md` hasPermission UX only |

---

## Sign-off

| Phase | Tester | Date | Pass? | Notes |
|-------|--------|------|-------|-------|
| P1 | Tobias | 2026-08-21 | **Pass** | S8 / S9 / S13 / S14 (kept from prior stamp / `9d583ac` retest) |
| P2 | Tobias | 2026-08-21 | **Pass** | Both S7 beats (same-client 404; other-client `XYZ-BA-0001` 404/404/404). S15 lockout. |
| P3 | Tobias | 2026-08-21 | **Pass** | S12 prod overlay no host 5432; S11 / S5 (kept) |
| P4 | Tobias | 2026-08-21 | **Pass** | API/curl; denylist resent Bearer 401 |

| Role | Name | Date | Verdict |
|------|------|------|---------|
| Tester / QA | Tobias | 2026-08-21 | **Accept with residual** |
| Product / Lab Ops (optional) | | | |
| Eng | | | |

**Holds:** none. Prior TC-S7-001 / TC-S12-001 holds cleared on `9d583ac` retest; other-client S7 beat Pass at `e47f1ab` (0067).

**Residuals (not holds):**

- **TC-S11-003** own `created_by` empty tube GET **200** / PATCH **500** (Sec10 follow-on, not a hold). Cross-client deny 404/404 passed.

This stamp is **Accept with residual**. Residual is not a hold.

---

## Retest log (post hold fixes)

**Code:** `0065` (`has_project_access` project_users for lab staff); `docker-compose.prod.yml` `ports: !reset []`; `0066` (`revoked_tokens` / logout jti denylist); `0067` (UAT seed `XYZ-BA-0001` on Sponsor XYZ bioanalytical project).

| ID | Retest bar | Result | Tester | Date | Notes |
|----|------------|--------|--------|------|-------|
| TC-S7-001 | alice GET/start/link CAR-T → 403/404; alice GET/start/link `XYZ-BA-0001` → 403/404; bob still 200 | Pass | Tobias | 2026-08-21 | Same-client (`9d583ac`): CAR-T GET/start/link 404/404/404; bob start 200. Other-client (`e47f1ab` / 0067): `alice-tech` GET/start/link `XYZ-BA-0001` → 404/404/404. No payload. Sample present on Sponsor XYZ - Bioanalytical Services. 0067 seed unblocked the other-client beat. Compose down after the beat. |
| TC-S12-001 | `compose … prod config` — no host 5432 | Pass | Tobias | 2026-08-21 | `9d583ac`: prod overlay no host 5432 |
| TC-S10-005+ | logout → resent Bearer → 401 | Pass | Tobias | 2026-08-21 | `9d583ac`: denylist — resent Bearer 401 |

**Deferred (not this retest):** TC-S11-003 own empty-tube PATCH 500 → Sec10 follow-on.
