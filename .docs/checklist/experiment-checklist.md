# Experiments Refactor — Checklist

**Branch:** `refactor/experiments`  
**Last updated:** 2026-07-11  
**Primary requirements:** [`.docs/requirements/experiment-processes-entries.md`](../requirements/experiment-processes-entries.md)

## Status legend

- [ ] not started
- [~] in progress
- [x] done
- [-] deferred / out of scope for this phase

---

## Context (already shipped)

- [x] ELN Experiments + templates API (CRUD, sample links, lineage, workflow actions)
- [x] Experiment Templates UI + SOP/AI parse + sign-off
- [x] Experiment Runs + dose-response + CRO lifecycle
- [x] FieldDefinitions + lists hard cutover (merged from `refactor/jsonb`)
- [x] Design docs, gap analysis, CEO / design / security reviews
- [x] Model sketches: `Entry`, `Process` / `ELNProcessStep`, `ProcessSample`, `FieldDefinition`

---

## Naming decisions (locked)

| Concept | ELN (this work) | LIMS (existing) |
|---------|-----------------|-----------------|
| Process entity | `eln_processes` table, API `/v1/eln-processes` | `experiment_processes` under runs |
| Process steps | `eln_process_steps` | `process_steps` |
| Sample assignment | `eln_process_samples` | N/A (per-run) |
| Permission | `experiment:manage` (Phase 1) | same |

Legacy `experiment_link` via `ExperimentDetail` **coexists** in Phase 1; no forced migration of existing links.

---

## Phase 1 — Process MVP

**Goal:** First-class ordered multi-experiment processes with sample assignment. No Entries UI yet.

### 1.1 Data model + migration

- [x] Finalize SQLAlchemy models (`ELNProcess`, `ELNProcessStep`, `ELNProcessSample`)
- [x] Migration `0047`: create `eln_processes`, `eln_process_steps`, `eln_process_samples`
- [x] Indexes: process id, template id, sample id, sort_order, created_by
- [x] Unique: `(process_id, sample_id)` on samples; uniqueness on `(process_id, sort_order)` for steps
- [x] Audit columns + triggers (`set_audit_timestamps` / `update_modified_at_column`)
- [x] RLS + `FORCE ROW LEVEL SECURITY` (client-scoped via `created_by`, same pattern as 0042)
- [x] Add FK `field_definitions.process_id` → `eln_processes.id` (deferred column from 0046)
- [x] Document coexistence with `experiment_link` (no bulk data migration in Phase 1)

### 1.2 API / service layer

- [x] Pydantic schemas (`app/schemas/eln_process.py`)
- [x] Repository (`app/repositories/eln_process_repository.py`)
- [x] Service (`app/services/eln_process_service.py`)
- [x] Router (`app/routers/eln_processes.py`) registered in `main.py`
- [x] CRUD: create / list / get / update / soft-delete process
- [x] Steps: add / list / remove / reorder
- [x] Samples: assign / list / remove
- [x] Sample progression (basic): set current step / advance to next step
- [x] Step instantiate: create Experiment from step template
- [x] Sample list filters (`current_step_id`, `sample_status`)
- [x] Seed `eln_process_status` list for optional process status_id
- [x] Permission gate: `experiment:manage`

### 1.3 Tests

- [x] API tests: process CRUD, step order, sample assign/remove/advance (`tests/test_eln_processes.py`)
- [x] Auth: client role denied without `experiment:manage`
- [x] 404/400 validation (missing template, duplicate sample, bad reorder)
- [x] RLS isolation tests for eln_* tables (`test_rls_experiment_isolation.py`)

### 1.4 Docs

- [x] This checklist
- [x] Point planning / requirements at Phase 1 API paths
- [x] Update `.docs/processes.md` with ELN table names + endpoints
- [x] README / api_endpoints note (follow-up polish)
- [x] Frontend `apiService` ELN process methods (UI still Phase 2)

### Phase 1 exit criteria

- [x] Migration written on top of 0046 (`0047_eln_processes.py`)
- [x] Can create a process with ordered templates, assign samples, advance sample step
- [x] Tests green for new router
- [x] No collision with LIMS `/v1/processes/*` routes

---

## Phase 2 — Entries + process-aware UI

- [x] Entries tables migration (`entries`, `entry_field_definitions`, `entry_field_values`) — `0048`
- [x] Instantiate entries from ExperimentTemplate (`template_definition.entries`; auto on experiment create + process step instantiate)
- [x] Sample data / experiment detail value capture APIs (`/v1/entries`, upsert values)
- [x] Write-back rules + audit for Sample attributes (allowlist + last-write-wins + `write_back_previous`)
- [x] Process builder UI + sample queues + overview (`ProcessesManagement` at `/experiments/processes`)
- [x] Entry forms driven by FieldDefinitions (EntryCapturePanel on experiment detail Entries tab)
- [x] Workflow actions: `create_process`, `add_step_to_process`, `assign_samples_to_process`, `instantiate_process_step`

---

## Phase 3 — Templates + cross-system visibility

**Gate:** Do not start Phase 3 coding until open questions **#1, #6, #7** (and ideally #8, #10) are **Decided** in [`.docs/open-questions/experiments.md`](../open-questions/experiments.md).

- [ ] Reusable Process Templates
- [ ] Sample journey view across Processes / Experiments / Runs / Batches
- [ ] Optional link or promotion path between ELN Process steps and LIMS Runs
- [ ] Advanced reporting / “samples currently in step X”

---

## Open questions

**Canonical doc (not this checklist):** [`.docs/open-questions/experiments.md`](../open-questions/experiments.md)

Rule: no new phase / major feature until blocking questions for that work are resolved. See `AGENTS.md` → *Open questions gate*.

---

## Related docs

| Doc | Role |
|-----|------|
| [open-questions/experiments.md](../open-questions/experiments.md) | **Open questions + decisions** |
| [requirements/experiment-processes-entries.md](../requirements/experiment-processes-entries.md) | Consolidated requirements |
| [processes.md](../processes.md) | Process concept |
| [experiments.md](../experiments.md) | ELN Experiments |
| [experiment-runs.md](../experiment-runs.md) | LIMS Runs boundary |
| [gap-analysis-process-and-experiment.md](../gap-analysis-process-and-experiment.md) | Gaps |
| [experiment-rework-prerequisites.md](../experiment-rework-prerequisites.md) | Pre-rework issues |
| [ceo-review/process-and-experiment.md](../ceo-review/process-and-experiment.md) | CEO review |
| [design-review/process-and-experiment.md](../design-review/process-and-experiment.md) | Design review |
| [security-review/process-and-experiment.md](../security-review/process-and-experiment.md) | Security review |
| [experiment-planning.md](../experiment-planning.md) | Chunk 1–2 history |

---

## Implementation log

| Date | Note |
|------|------|
| 2026-07-11 | Checklist created; Phase 1 started on `refactor/experiments` |
| 2026-07-11 | Phase 1 backend landed: models, migration 0047, `/v1/eln-processes` API, tests |
| 2026-07-11 | Phase 1 polish: docs, apiService, instantiate, status seed, RLS tests |
| 2026-07-11 | Phase 2 started: entries 0048, APIs, Process UI, workflow actions |
| 2026-07-11 | Entry capture UI: EntryCapturePanel on experiment detail |
| 2026-07-11 | Open questions moved to .docs/open-questions/; Phase 3 gated on Q#1,6,7 |
