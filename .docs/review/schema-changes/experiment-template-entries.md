# Schema changes: Experiment template entries

**Date:** 2026-07-28 · **Updated:** 2026-08-12  
**Status:** Foundation locked + multi-row experiment_data shipped  
Kinds are logical (`entry_type`); storage remains `entries` / `entry_field_definitions` / `entry_field_values`.  
**Tech sketch:** [`.docs/review/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)

## 1. Scope

Template-declared entry blocks; multi-row experiment_data tables; entry field catalogs separate from Custom Fields (DB entities).

## 2. Delta table

| Change | Detail | Status |
|--------|--------|--------|
| JSONB `template_definition.entries[]` | Declaration of entries + sample_columns + field ids | Shipped |
| `entry_field_values.row_key` | Multi-row free tables for experiment_data | **Shipped** migration `0057` |
| Partial unique indexes | row_key / sample_id / legacy null variants | `0057` |
| FieldDefinitions `entity_type` | `experiment_sample_data`, `experiment_data` for entry columns | App convention (no new table) |
| New tables | None | — |

### 2.1 Schema used

```
entries (entry_type, config JSONB, predefined_entry_key, …)
entry_field_definitions (field_definition_id, write_back_target, …)
entry_field_values (sample_id, row_key, value_*, …)   -- 0057 adds row_key
field_definitions (entity_type = experiment_sample_data | experiment_data for entry cols)
experiment_templates.template_definition JSONB        -- entries[] declaration
```

## 3. RLS

No new tenant tables in `0057`. Existing entry/sample RLS paths apply.

## 4. Backfill / dual-write

None required for `row_key`. Legacy single cells (null `row_key` + null `sample_id`) still readable; capture UI migrates them into one free row on load.

## 5. Rollback

`0057` downgrade drops `row_key` and restores prior unique indexes.

## 6. Out of scope (schema)

- Process sample ↔ execution auto-link tables  
- Materialized columns for entry field types  
- Multi-tenant columns  

## 7. Multi-tenant readiness

Lab-global config (templates/entries) same as today. Sample data remains RLS-scoped. No tenant_id this cycle.

## 8. Links

- Tech sketch (flows, API, phases)  
- Open questions Q11–Q14 in [experiments.md](../open-questions/experiments.md)
