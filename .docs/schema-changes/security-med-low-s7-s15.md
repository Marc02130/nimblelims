# Schema changes: security-med-low-s7-s15

**Feature / cycle:** Med/Low security remediation (S7–S15)  
**Phases covered:** P1–P3 (P4 docs-only)  
**Status:** Draft — ready for architecture review  
**Alembic revisions:** _(fill when implemented)_  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)  
**Tech sketch:** [`.docs/tech-sketch/security-med-low-s7-s15.md`](../tech-sketch/security-med-low-s7-s15.md)

## 1. Summary

Mostly **policy / FORCE RLS / compose**—few or no new business tables. Optional lockout persistence table if not in-memory-only for S15.

## 2. Delta

### 2.1 New tables

| Table | Purpose | Notes |
|-------|---------|-------|
| _(optional)_ `login_throttle` | Persist failures/lockouts across workers | Only if in-memory rejected for multi-replica |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| — | None required for P1 | S14 is allowlist code constant |
| Various tenant tables | `FORCE ROW LEVEL SECURITY` | S11 |

### 2.3 RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| `containers` | Optional tighten of 0062 `created_by` FOR ALL | OQ-S11a |
| `contents` | Optional ENABLE (+ FORCE) + policy | OQ-S11b |
| samples, tests, results, projects, batches, containers, … | FORCE where policies exist | S11 |

### 2.4 Compose / infra (not Alembic)

| Object | Change |
|--------|--------|
| `docker-compose.prod.yml` or profile | No host bind for 5432; secrets required |

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
