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
- [x] Permission gate: `experiment:manage`

### 1.3 Tests

- [x] API tests: process CRUD, step order, sample assign/remove/advance (`tests/test_eln_processes.py`)
- [x] Auth: client role denied without `experiment:manage`
- [x] 404/400 validation (missing template, duplicate sample, bad reorder)

### 1.4 Docs

- [x] This checklist
- [x] Point planning / requirements at Phase 1 API paths
- [x] Update `.docs/processes.md` with ELN table names + endpoints
- [ ] README / api_endpoints note (follow-up polish)

### Phase 1 exit criteria

- [x] Migration written on top of 0046 (`0047_eln_processes.py`)
- [x] Can create a process with ordered templates, assign samples, advance sample step
- [x] Tests green for new router
- [x] No collision with LIMS `/v1/processes/*` routes

---

## Phase 2 — Entries + process-aware UI

- [ ] Entries tables migration (`entries`, `entry_field_definitions`, `entry_field_values`)
- [ ] Instantiate entries from ExperimentTemplate
- [ ] Sample data / experiment detail value capture APIs
- [ ] Write-back rules + audit for Sample attributes
- [ ] Process builder UI + sample queues + overview
- [ ] Entry forms driven by FieldDefinitions
- [ ] Workflow actions: `create_process`, `add_experiment_to_process`, etc.

---

## Phase 3 — Templates + cross-system visibility

- [ ] Reusable Process Templates
- [ ] Sample journey view across Processes / Experiments / Runs / Batches
- [ ] Optional link or promotion path between ELN Process steps and LIMS Runs
- [ ] Advanced reporting / “samples currently in step X”

---

## Open questions (track until closed)

| # | Question | Decision |
|---|----------|----------|
| 1 | Can a Process reference LIMS Runs? | Open — Phase 1: ELN templates only |
| 2 | Process status: own list vs derived? | Phase 1: optional `status_id` list FK; seed later if needed |
| 3 | Can Process override entry config from templates? | Phase 2 |
| 4 | Write-back conflict rules | Phase 2 |
| 5 | Workflow integration depth | Phase 2 minimum: new actions only |
| 6 | Process Templates timing | Phase 3 (reviews lean defer) |
| 7 | Progress visibility for non-admins | Phase 2+ UI |

---

## Related docs

| Doc | Role |
|-----|------|
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
