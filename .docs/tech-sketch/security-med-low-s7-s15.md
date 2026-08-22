# Tech sketch: Med/Low security remediation (S7–S15)

**Date:** 2026-08-21  
**Status:** Draft for architecture / security review  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)  
**Schema:** [`.docs/schema-changes/security-med-low-s7-s15.md`](../schema-changes/security-med-low-s7-s15.md)  
**Audit:** [`.docs/security-review/codebase.md`](../security-review/codebase.md)

## 1. Context

High S1–S6 Met on `security/high-s1-s6`. This sketch is *how* to close S7–S15 in phases P1–P4.

## 2. Phase mapping → code touchpoints

### P1 — Quick harden

| Finding | Approach |
|---------|----------|
| **S8** | Shared helper `assert_upload_max_bytes(file, max=10_485_760)` used by `lims_runs.import-file`, `sop_parse` uploads; nginx `client_max_body_size 10m` on API location. |
| **S9** | Add `Depends(get_current_user)` + `require_any_permission(["result:enter","result:review"])` on `POST /results/validate`. |
| **S13** | `GET /roles`, `GET /permissions` → `require_any_permission(["user:manage","config:edit"])`. `verify-email`: if stub, return generic message always; gate behind `ENVIRONMENT!=production` or require signed token; rate-limit with S15 helper if available. |
| **S14** | Remove `specimen_biotype_id` and `temperature` from `SAMPLE_WRITE_BACK_COLUMNS`; keep in `SAMPLE_SYSTEM_FIELDS` as display. Fail closed in `_apply_write_back`. |

### P2 — Access & abuse

| Finding | Approach |
|---------|----------|
| **S7** | In `ExperimentService.start_experiment` / `link_sample_to_experiment` / lims run start: after sample fetch, assert access using existing RLS (query sample as current user—if invisible, 404) **or** explicit `has_project_access` check mirroring DB function. Prefer “select sample under current session GUC” so RLS is single source of truth. Same for run cohort start. |
| **S15** | Table `login_throttle` (username PK/unique, failure_count, window_started_at, locked_until). On failed login upsert/increment; on success delete/clear. Config: `LOGIN_MAX_FAILURES=5`, `LOGIN_LOCKOUT_MINUTES=15`. Return **429** + `Retry-After` when locked. |

### P3 — Platform

| Finding | Approach |
|---------|----------|
| **S11** | FORCE RLS on tenant tables with policies. Tighten containers: `created_by` on **INSERT WITH CHECK** only; SELECT via admin/project/contents. Aliquot dest: one txn, rollback if no contents. Enable **contents** RLS + policy (sample/project). Re-test as `lims_app`. |
| **S12** | `docker-compose.prod.yml` overlay omits `db.ports`; requires secrets. Local compose may keep 5432. |

### P4 — Cookie AuthN (expanded S10)

| Finding | Approach |
|---------|----------|
| **S10** | Issue JWT (or opaque session) in **httpOnly Secure SameSite** cookie on login; stop storing token in `localStorage`. Axios `withCredentials`. CSRF strategy (SameSite=Lax + careful mutations, or CSRF token). Logout clears cookie. Docs: `hasPermission` remains UX only. |

## 3. S7 access check (preferred)

```
start_experiment(sample_ids):
  for sid in sample_ids:
    sample = db.query(Sample).filter(Sample.id == sid).first()
    # With lims_app + GUC set, RLS already filters; if None → 404
    if not sample:
      raise 404
    # existing Decision #24 eligibility…
```

If any code path uses migrator URL or bypasses GUC, add explicit service-layer check—do not rely on “sample exists” via owner connection.

## 4. S15 sketch (Postgres)

```sql
CREATE TABLE login_throttle (
  username_normalized TEXT PRIMARY KEY,
  failure_count INT NOT NULL DEFAULT 0,
  window_started_at TIMESTAMPTZ NOT NULL,
  locked_until TIMESTAMPTZ NULL
);
```

Service: `check` / `record_failure` / `record_success` in `auth.login`. No password stored.

## 5. S11 containers + empty-container product rule (Decided)

- **INSERT WITH CHECK:** `is_admin() OR created_by = current_user_id()`  
- **USING (SELECT/UPDATE/DELETE):** `is_admin() OR EXISTS (contents→sample→has_project_access)`  
- Aliquot execute: single transaction; if contents insert fails → rollback (no committed empty container).

## 6. Tests

| Finding | Test |
|---------|------|
| S7 | Lab user cannot start with other-client sample UUID |
| S8 | Upload 10MB+1 → 413/400 |
| S9 | No auth → 401; with auth → 200 |
| S13 | Client role GET /roles → 403 |
| S14 | write-back forbidden column rejected |
| S15 | 5 failures → lock; success clears |
| S11 | FORCE true on listed tables; RLS tests still pass as app role |
| S12 | Compose config lint / doc checklist |

## 7. Rollout / UAT

New script: `UAT_Scripts/uat-security-med-low-s7-s15.md` (per phase).  
Do not regress High UAT spine.
