# Architecture Review: High security remediation (S1–S6)

**Date:** 2026-08-20  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)  
**Schema:** [`.docs/schema-changes/security-high-s1-s6.md`](../schema-changes/security-high-s1-s6.md)  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)

## Ask results

| # | Ask | Status |
|---|-----|--------|
| 1 | Single JWT secret resolution + refuse defaults | **Accept** |
| 2 | Remove body logging | **Accept** |
| 3 | bcrypt + SHA256 login upgrade | **Accept** |
| 4 | Cohort checks in EntryService | **Accept** |
| 5 | Aliquot execute one transaction + null amount refuse | **Accept** |
| 6 | `lims_app` role + `set_config` LOCAL GUCs | **Accept — conditions A1–A5** |

## Architecture

```
Migrator URL (owner) ──► Alembic / DDL
App URL (lims_app)   ──► FastAPI Session
                           │
                           ├─ set_config(app.current_user_id, …, is_local=true)
                           ├─ set_config(app.client_id, …, is_local=true) when needed
                           └─ RLS policies apply (FORCE on ELN tables)

AuthN: SECRET_KEY ← env; bcrypt passwords
AuthZ (app-layer): cohort membership on entry write + aliquot source
AuthZ (DB-layer): RLS for client isolation once S1 lands
```

## Conditions

| ID | Condition |
|----|-----------|
| **A1** | App role must **not** own tables and must **not** have `BYPASSRLS`. |
| **A2** | Use transaction-local `set_config(..., true)` tied to request/session transaction; document interaction with `get_db` commit boundaries. |
| **A3** | Entrypoint: migrate with owner URL, run app with app URL — never flip at runtime mid-request. |
| **A4** | No business table DDL in this cycle except optional `password_hash` length increase if bcrypt strings exceed 255. |
| **A5** | P0d migration blocked until open-questions **Q1** (bootstrap) decided; grants list must be enumerated in migration PR (table-by-table or schema-wide with comment). |
| **A6** | S5: single `commit` at end of successful execute; tests must prove rollback leaves zero orphan samples/containers. |
| **A7** | S6: reuse `_experiment_sample_ids`; do not invent a second cohort source of truth. |

## Deferred (not this cycle)

- Policy expression rewrites (`is_admin() OR true`) — S11  
- FORCE RLS rollout to samples/tests/results — S11  
- Port publish / start.sh DATABASE_URL — S12  

## Verdict

**Accept with conditions A1–A7.** Schema delta is role/grants-only; application changes are localized and reviewable.
