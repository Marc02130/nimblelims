# Schema changes: security-med-low-s7-s15

**Feature / cycle:** Med/Low security remediation (S7–S15)  
**Phases covered:** P1–P4 + UAT hold fixes  
**Status:** Implemented on branch  
**Alembic revisions:** `0063` (`login_throttle`); `0064` (FORCE RLS + contents + containers); **`0065`** (`has_project_access` project_users for lab staff); **`0066`** (`revoked_tokens`)  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)  
**Tech sketch:** [`.docs/tech-sketch/security-med-low-s7-s15.md`](../tech-sketch/security-med-low-s7-s15.md)

## 1. Summary

Policy / FORCE RLS / compose / cookie AuthN, plus UAT hold fixes: role-aware `has_project_access`, JWT jti denylist.

## 2. Delta

### 2.1 New tables

| Table | Purpose | Notes |
|-------|---------|-------|
| `login_throttle` | Persist login failures/lockouts (S15) | Postgres, not Redis |
| `revoked_tokens` | JWT `jti` denylist on logout (S10 residual) | `0066` |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| — | None required for P1 | S14 is allowlist code constant |
| Various tenant tables | `FORCE ROW LEVEL SECURITY` | S11 |
| `contents` | ENABLE RLS (+ FORCE) + policy | OQ-S11b Decided |

### 2.3 RLS / functions

| Object | Policy change | Notes |
|--------|---------------|-------|
| `containers` | Tighten 0062: `created_by` on INSERT WITH CHECK only | OQ-S11a Decided |
| `contents` | New policy (sample/project access) | OQ-S11b Decided |
| samples, tests, results, projects, batches, containers, … | FORCE where policies exist | S11 |
| `has_project_access` | Lab staff → `project_users` only; Client keeps same-client | `0065` / TC-S7-001 |

### 2.4 Compose / infra (not Alembic)

| Object | Change |
|--------|--------|
| `docker-compose.prod.yml` | `ports: !reset []` — plain `ports: []` does **not** clear base `5432` |

## 3. Data migration / backfill

- [x] None for P1  
- [ ] S11 FORCE: no data rewrite  
- [ ] Optional S15 table: empty  

## 4. Rollback

FORCE can be reversed with `NO FORCE ROW LEVEL SECURITY` if migrator still owns tables. Prefer forward-only in prod.

## 5. Open schema blockers

See [open-questions/security-med-low-s7-s15.md](../open-questions/security-med-low-s7-s15.md) OQ-S11a, OQ-S11b, OQ-S15.

## 6. Implementation checklist

- [ ] Migration(s) match this doc  
- [ ] RLS tested as `lims_app` / `app_test_role`  
- [ ] Revision id(s) recorded here  
