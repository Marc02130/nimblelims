# UAT: Med/Low security remediation (S7–S15)

**Branch:** `security/med-low-s7-s15`  
**Requirements:** `.docs/requirements/security-med-low-s7-s15.md`  
**Prerequisite:** High S1–S6 Met

## Environment

- `docker compose up -d --build` (or local equivalent)
- Seeded users: `admin`, `lab-tech`, `lab-manager`, `client`
- Prod overlay check (S12): `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` — DB must not publish `5432`

---

## P1 — S8 / S9 / S13 / S14

| ID | Steps | Expected |
|----|-------|----------|
| TC-S8-001 | Upload file &gt; 10 MB to import-file or SOP parse | 413/400; clear error |
| TC-S9-001 | `POST /results/validate` without auth | 401 |
| TC-S9-002 | Same with lab-tech (`result:enter`) | 200/valid response |
| TC-S13-001 | Client user `GET /roles` | 403 |
| TC-S14-001 | Attempt write-back biotype/temperature | Rejected / not applied |

## P2 — S7 / S15

| ID | Steps | Expected |
|----|-------|----------|
| TC-S7-001 | User A starts experiment with sample ID only visible to User B’s client | 404/403 |
| TC-S15-001 | 5 wrong passwords for same username | 429 lockout |
| TC-S15-002 | Correct password after lock window / success clears | Login OK; counter cleared |

## P3 — S11 / S12

| ID | Steps | Expected |
|----|-------|----------|
| TC-S11-001 | Labtech aliquot dest create (container + contents) | 200; no empty committed container |
| TC-S11-002 | FORCE RLS / contents RLS still allow eligible lab paths | Smoke sample list + aliquot |
| TC-S12-001 | Prod compose config | No host `5432` publish |

## P4 — S10 cookie AuthN

| ID | Steps | Expected |
|----|-------|----------|
| TC-S10-001 | Browser login as `lab-tech` | `nimble_access` httpOnly cookie set; **no** `localStorage.token` |
| TC-S10-002 | Refresh `/dashboard` | Session restored via cookie (`/auth/me`) |
| TC-S10-003 | Mutating API call without `X-CSRF-Token` (cookie only) | 403 `csrf_failed` |
| TC-S10-004 | Normal UI create/update (SPA) | Succeeds (interceptor sends CSRF) |
| TC-S10-005 | Logout | Cookies cleared; `/auth/me` → 401; redirected to login |
| TC-S10-006 | Script/curl with `Authorization: Bearer` from login JSON | Works without CSRF (API clients) |

### DevTools checks (TC-S10-001)

1. Application → Cookies → `nimble_access` has **HttpOnly**; `nimble_csrf` does **not**.  
2. Application → Local Storage → no `token` key after login.  
3. Network → API requests include cookies; mutating requests include `X-CSRF-Token`.

---

## Honesty / AuthZ

| ID | Check |
|----|-------|
| TC-UX-001 | Confirm manuals state `hasPermission` is UX only; server RBAC/RLS is AuthZ |

## Sign-off

| Phase | Tester | Date | Pass? |
|-------|--------|------|-------|
| P1 | | | |
| P2 | | | |
| P3 | | | |
| P4 | | | |
