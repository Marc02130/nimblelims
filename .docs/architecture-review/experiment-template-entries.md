# Architecture Review: Experiment template entries

**Date:** 2026-07-29  
**Verdict date:** 2026-07-29  
**Status:** **Accepted with conditions**  
**Tech sketch:** [`.docs/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)  
**Schema changes:** [`.docs/schema-changes/experiment-template-entries.md`](../schema-changes/experiment-template-entries.md)  
**CEO / UI:** accepted with conditions  

## Ask results

| # | Ask | Status |
|---|-----|--------|
| 1 | No new tables for P0 | **Accept** |
| 2 | `sample_roster` type | **Accept** (Q12 Decided) |
| 3 | Validate entries[] on template write | **Accept — required** |
| 4 | Roster API B server projection | **Accept — required** |
| 5 | Sample column allowlist fail-closed | **Accept** (Q13) |
| 6 | RLS / no visibility widen | **Accept — verify query** |
| 7 | Single instantiate path | **Accept** |

## What already exists (reuse)

| Sub-problem | Existing | Plan reuses? |
|-------------|----------|--------------|
| Entry shells from template | `EntryService.instantiate_from_template` | **Yes** |
| sample_data / experiment_detail capture | `EntryCapturePanel`, upsert values | **Yes** |
| Write-back allowlist | `SAMPLE_WRITE_BACK_COLUMNS` | **Yes** (unchanged) |
| display_table write reject | `upsert_values` blocks `display_table` | **Extend to sample_roster** |
| Template JSON storage | `template_definition` JSONB | **Yes** |
| FieldDefinitions | Field Management | **Yes** for editable columns |
| Auth gate | `require_experiment_manage` on entries router | **Yes** for P0 |

## Architecture diagram

```
                    ┌────────────────────────────┐
                    │ ExperimentTemplatesManagement│
                    │  Tables & forms tab         │
                    └─────────────┬──────────────┘
                                  │ PATCH template_definition.entries
                                  │ (Pydantic validate)
                                  ▼
                    ┌────────────────────────────┐
                    │ experiment_templates       │
                    │  template_definition JSONB │
                    └─────────────┬──────────────┘
                                  │ create_experiment /
                                  │ process start_step
                                  ▼
                    ┌────────────────────────────┐
                    │ EntryService.instantiate_  │
                    │ from_template              │
                    │  → entries rows            │
                    │  → config snapshot         │
                    │  → field links (editable)  │
                    └─────────────┬──────────────┘
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   sample_roster            sample_data            experiment_detail
   GET .../roster           PUT .../values         PUT .../values
          │                       │
          │                 ExperimentSampleExecution
          └────────── sample_ids ─┘
```

## Snapshot rule (important)

On instantiate, `Entry.config` copies template declaration **at create time**. Later template edits must **not** rewrite in-flight experiment entries (matches process definition snapshot philosophy). Document in service comments.

Re-instantiate with `skip_if_exists=true` leaves existing entries alone (current behavior). Do not auto-sync template→instance in P0.

## Data flow: roster (happy + shadow)

```
GET /v1/entries/{id}/roster
  │
  ├─ entry missing → 404
  ├─ entry.entry_type != sample_roster → 400
  ├─ load experiment + sample_executions
  │     empty executions → { columns, rows: [] }
  ├─ load samples by ids (batch, RLS)
  │     missing sample → omit row or null cells (prefer omit + log)
  ├─ project config.sample_columns via allowlist
  │     unknown key in config → ignore key + log warning OR fail closed at author time only
  └─ resolve list FKs → display names
```

**Author-time:** unknown `sample_columns` keys → **400 on template save**.  
**Read-time:** tolerate soft-deleted list entries (show id or “—”).

## Type system

```
ENTRY_TYPES += sample_roster

upsert_values:
  reject display_table | sample_roster   # CRITICAL condition A1

sample_data: require sample_id
experiment_detail: forbid sample_id
```

## Schema re-verify

| Item | Result |
|------|--------|
| New tables | **None** |
| `entries.config` for roster columns | **OK** |
| `entry_field_definitions` unused for roster | **OK** |
| Migration | **None** unless we add CHECK (prefer app-only) |
| Rollback | App revert |

## Error & rescue registry

| Codepath | Failure | HTTP / action | User sees |
|----------|---------|---------------|-----------|
| Template PATCH | Invalid entry_type | 400 validation | Field error |
| Template PATCH | Bad sample_column | 400 | Named key invalid |
| Template PATCH | Missing field_definition_id | 400 | Named field |
| instantiate | No template | 400 (existing) | Message |
| instantiate | Unknown type skipped? | **Must not silently skip** — fail or reject whole list | Clear error |
| roster GET | Wrong type | 400 | Message |
| roster GET | Forbidden sample | RLS hides; no row | Partial roster only if some visible |
| upsert roster | Write attempt | 400 | Cannot write |
| upsert sample_data | No sample_id | 400 (existing) | Message |
| write-back | Column not allowlisted | skip write-back (existing) | Value saved on entry only |

**Condition A2:** Instantiation must **reject** invalid entry declarations rather than silently skipping bad entries (today code `continue`s on bad types—tighten for author path; for instantiate prefer fail if any entry invalid).

## Performance

| Risk | Mitigation |
|------|------------|
| N+1 sample loads in roster | **Batch** `WHERE id IN (...)` once |
| N+1 list name resolution | Prefetch list entries for FK ids in set |
| Large cohort (500 samples) | Acceptable for P0; document soft limit 500 rows |

## Test diagram (required coverage)

```
CODE PATHS
  template_entries schema validate
    ├── [REQ] valid 3-block template
    ├── [REQ] reject unknown type
    ├── [REQ] reject bad sample_column
    └── [REQ] reject write_back not in allowlist
  instantiate_from_template
    ├── [REQ] creates sample_roster with config, no field links
    ├── [REQ] creates sample_data with field links
    └── [REQ] skip_if_exists leaves rows
  GET roster
    ├── [REQ] empty samples → empty rows
    ├── [REQ] projects client_sample_id + list name
    ├── [REQ] wrong type → 400
    └── [REQ] client role without manage → 403
  PUT values
    ├── [REQ] sample_roster → 400
    └── [REQ] sample_data happy path (existing)

USER FLOWS (UAT)
  Author entries → save template → create experiment → link samples
    → see roster → edit sample_data → save
```

Test plan artifact: `~/.gstack/projects/.../eng-review-test-plan-experiment-template-entries.md` (also mirrored under UAT later).

## Parallelization (impl)

| Lane | Work | Depends |
|------|------|---------|
| A | Backend types, validation, roster API, tests | — |
| B | Template Entries UI | A contracts (or mock) |
| C | EntryCapturePanel roster + labels | A roster API |
| D | Docs / UAT script | A+B+C |

Launch A first; B+C after API shape stable; D last.

## Conditions

| ID | Condition | Severity |
|----|-----------|----------|
| **A1** | `upsert_values` rejects `sample_roster` same as `display_table` | **Critical** |
| **A2** | Template write validation Pydantic; fail closed on columns/types | **Critical** |
| **A3** | Roster = `GET /v1/entries/{id}/roster` server projection (API B) | **Critical** |
| **A4** | Batch sample load + list resolution; no N+1 | High |
| **A5** | Entry.config is snapshot; no live template rewrite of instances | High |
| **A6** | Instantiation does not silently skip invalid declared entries when validating new templates | Medium |
| **A7** | Tests in §Test diagram green before merge | High |

## NOT in scope

- Normalized template_entry tables  
- Process sample auto-execution link (Q8)  
- Changing Decision #9 / write-back policy  

## Failure modes registry

| Codepath | Mode | Rescued? | Test? | User | Logged? |
|----------|------|----------|-------|------|---------|
| upsert roster | Write | Y 400 | **REQ** | Error | Y |
| roster leak | Wrong sample | RLS | **REQ** | No leak | Y |
| bad column key | Author | Y 400 | **REQ** | Error | — |
| empty executions | — | Y empty | **REQ** | Empty state | — |

Critical gaps if A1/A3 untested: **yes until tests land**.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (A1–A7) |
| **Date** | 2026-07-29 |
| **Schema** | No migration required for P0 |
| **Reversibility** | 5/5 (app-only) |
