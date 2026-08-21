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
| **S9** | Add `Depends(get_current_user)` + `require_any_permission(["result:enter","result:review","result:read"])` on `POST /results/validate`. |
| **S13** | `GET /roles`, `GET /permissions` → `require_any_permission(["user:manage","config:edit"])`. `verify-email`: if stub, return generic message always; gate behind `ENVIRONMENT!=production` or require signed token; rate-limit with S15 helper if available. |
| **S14** | Remove `specimen_biotype_id` and `temperature` from `SAMPLE_WRITE_BACK_COLUMNS` **or** from system-RO labeling per OQ-S14; fail closed in `_apply_write_back` if somehow linked. |

### P2 — Access & abuse

| Finding | Approach |
|---------|----------|
| **S7** | In `ExperimentService.start_experiment` / `link_sample_to_experiment` / lims run start: after sample fetch, assert access using existing RLS (query sample as current user—if invisible, 404) **or** explicit `has_project_access` check mirroring DB function. Prefer “select sample under current session GUC” so RLS is single source of truth. Same for run cohort start. |
| **S15** | In-memory dict `(username_normalized → {count, locked_until})` + optional Redis later. On failed login increment; on success clear. Config: `LOGIN_MAX_FAILURES=5`, `LOGIN_LOCKOUT_MINUTES=15`. Return 429 with `Retry-After` when locked. |

### P3 — Platform

| Finding | Approach |
|---------|----------|
| **S11** | Alembic: `ALTER TABLE … FORCE ROW LEVEL SECURITY` for tenant tables that have policies but FORCE off (`samples`, `tests`, `results`, `projects`, `batches`, `containers`, …). Migrator stays table owner/superuser path. Re-test RLS suite as `lims_app` / `app_test_role`. Resolve OQ-S11a/b (containers created_by scope; contents RLS). |
| **S12** | Add `docker-compose.prod.yml` (or profile `prod`) that omits `db.ports` and requires secrets; keep base compose for local with published 5432 + warning in README. |

### P4 — Honesty

| Finding | Approach |
|---------|----------|
| **S10** | Update `manuals/backend-auth.md`, README security bullets, `UserContext.hasPermission` comment, apiService interceptor comment. |

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

## 4. S15 sketch

```python
# app/core/login_throttle.py
class LoginThrottle:
    def check(self, username: str) -> None:  # raises 429 if locked
    def record_failure(self, username: str) -> None
    def record_success(self, username: str) -> None
```

Wire in `auth.login` only; no password in keys/logs.

## 5. S11 containers residual (0062)

**Option A (tighten):** policy USING for SELECT stays project/contents OR admin; WITH CHECK for INSERT = created_by OR admin; UPDATE/DELETE require project link or admin.  
**Option B (accept):** document that creator can always see containers they created even without contents yet—acceptable for aliquot dest lifecycle.

Default recommendation: **A** if cheap; else **B** Deferred with residual on codebase.md.

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
