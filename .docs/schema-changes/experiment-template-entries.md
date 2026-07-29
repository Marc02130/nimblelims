# Schema changes: Experiment template entries

**Date:** 2026-07-28  
**Status:** **Accepted** with architecture review (2026-07-29) — no migration for P0  
**Phase covered:** P0 (template Entries authoring + sample roster)  
**Tech sketch:** [`.docs/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)  
**Requirements:** [`.docs/requirements/experiment-processes-entries.md`](../requirements/experiment-processes-entries.md)

## 1. Scope

Make template-declared **entry blocks** (including a sample roster display) first-class in app contracts and UI. Prefer **no new tables** in P0 if existing `entries` / `entry_field_*` / `template_definition` JSONB suffice.

## 2. Delta table

| Change | Detail | P0? |
|--------|--------|-----|
| **App allowlist** | Add `sample_roster` to `ENTRY_TYPES` | Yes |
| **JSONB contract** | Document + validate `template_definition.entries[]` (including `config.sample_columns`) | Yes |
| **New tables** | None expected | — |
| **New columns on `entries`** | None expected (`config` JSONB already holds roster columns) | — |
| **Optional later** | Normalized `template_entry_definitions` tables if JSONB validation/UX becomes painful | Not P0 |

### 2.1 Existing schema used (no migration)

```
entries (
  …,
  entry_type,          -- includes sample_roster
  config JSONB,        -- sample_roster: { sample_columns: string[] }
  …
)
entry_field_definitions (…, write_back_target, …)  -- sample_data / experiment_detail
entry_field_values (…)                             -- writable types only
experiment_templates.template_definition JSONB     -- entries[] declaration
```

## 3. RLS

No new tables → **no new RLS policies** in P0.

Roster endpoint must only return samples already visible under existing sample RLS (via experiment membership / executions). Architecture to verify query path does not widen visibility.

## 4. Backfill / dual-write

None. Existing templates without `entries` remain valid. No rewrite of protocol_steps / transfer_steps.

## 5. Rollback

App-only: revert type allowlist + UI. No DB rollback needed if no migration ships.

If a migration is later added for check constraints on `entry_type`, use expandable CHECK or app-only validation (prefer app-only to avoid migration churn when adding types).

## 6. Out of scope (schema)

- Process sample ↔ execution auto-link tables  
- Write-back allowlist expansion  
- Dropping protocol/transfer from `template_definition`  
- Multi-tenant columns  

## 7. Multi-tenant readiness

Lab-global config (templates/entries) same as today. Sample data remains RLS-scoped. No tenant_id this cycle.

## 8. Links

- Tech sketch (flows, API, phases)  
- Open questions Q11–Q14 in [experiments.md](../open-questions/experiments.md)
