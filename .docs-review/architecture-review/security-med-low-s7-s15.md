# Architecture Review: Med/Low security remediation (S7–S15)

**Date:** 2026-08-21  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs-review/tech-sketch/security-med-low-s7-s15.md`](../tech-sketch/security-med-low-s7-s15.md)  
**Schema:** [`.docs-review/schema-changes/security-med-low-s7-s15.md`](../schema-changes/security-med-low-s7-s15.md)

## Ask results

| # | Ask | Status |
|---|-----|--------|
| 1 | S7 access via RLS/session not dual business rules | **Accept** |
| 2 | S8 server + nginx 10 MB | **Accept** |
| 3 | S9 auth on validate | **Accept** |
| 4 | S11 FORCE RLS + OQ on contents/containers | **Accept — conditions** |
| 5 | S12 prod overlay without published 5432 | **Accept** |
| 6 | S15 Postgres `login_throttle` | **Accept** (OQ-S15 Decided) |
| 7 | S10 httpOnly cookies | **Accept with conditions** — CSRF + SameSite design before code (OQ-S10 expanded) |

## Architecture notes

```
P1: routers (upload, validate, roles) + entry allowlist constants
P2: experiment_service / lims_run start + login_throttle
P3: Alembic FORCE RLS + compose.prod.yml
P4: httpOnly cookie AuthN + SameSite=Lax + double-submit CSRF (OQ-S10 expanded)
```

S7 must not invent a second authorization model: prefer “query Sample under current GUC / lims_app” so RLS remains SoT.

## Conditions

| ID | Condition |
|----|-----------|
| **A1** | No migrator/owner connection on request path for start/link sample resolution. |
| **A2** | FORCE RLS only after confirming background jobs use owner URL or explicit privilege. |
| **A3** | S15 in-memory documented as single-process; multi-replica → follow-up. |
| **A4** | OQ-S11a/b decided before P3 migration merges. |
| **A5** | Schema doc updated with revision ids when implemented. |

## Verdict

**Accept with conditions A1–A5.**
