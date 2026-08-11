# Experiments Refactor — Checklist

**Branch:** `refactor/experiments` / `run-results`  
**Last updated:** 2026-07-28  
**Primary requirements:** [`.docs/requirements/experiment-processes-entries.md`](../requirements/experiment-processes-entries.md)  
**Template entries tech sketch (in review):** [`.docs/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)

## Status legend

- [ ] not started
- [~] in progress
- [x] done
- [-] deferred / out of scope for this phase

---

## Context (already shipped)

- [x] ELN Experiments + templates API (CRUD, sample links, lineage, workflow actions)
- [x] Experiment Templates UI + SOP/AI parse + sign-off
- [x] LIMS Runs + dose-response + CRO lifecycle
- [x] FieldDefinitions + lists hard cutover (merged from `refactor/jsonb`)
- [x] Design docs, gap analysis, CEO / design / security reviews
- [x] Model sketches: `Entry`, `Process` / `ELNProcessStep`, `ProcessSample`, `FieldDefinition`

---

## Naming decisions (locked)

| Concept | ELN (this work) | LIMS (existing) |
|---------|-----------------|-----------------|
| Process definition | `eln_process_definitions` + `_definition_steps` | N/A |
| Process instance | `eln_processes` table, API `/v1/eln-processes` | LimsRun checklists (`lims_run_checklists`) |
| Process steps | `eln_process_steps` (typed: `eln_experiment` \| `lims_run`) | checklist steps |
| Sample assignment | `eln_process_samples` | N/A (per-run) |
| Permission | `experiment:manage` (manage); journey via sample access | same manage path |

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
- [x] Update `.docs/manuals/processes.md` with ELN table names + endpoints
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

## Phase 3 — Process definitions + cross-system visibility

**Gate:** **Open for Phase 3 implementation.** Decisions **#1, #6, #7** locked.  
**Status:** **Shipped (v1)** — 2026-07-11.

**#6 Decided:** Processes always defined (definitions → instances).  
**#1 Decided:** Typed steps (`eln_experiment` \| `lims_run`) in Phase 3 v1 (**1h-A**); defaults 1a–1g (lazy Run, history, soft gates, Run SoT for instrument data).  
**#7 Decided:** Progress visible to anyone with sample access; no cross-client.

- [x] First-class process definitions + ordered **typed** steps (`step_kind`, template, `execution_mode`) — migration `0051`, models, `/v1/eln-process-definitions`
- [x] Instantiate process instance from definition (snapshot steps; `process_definition_id` on instance)
- [x] Free-form create auto-creates a snapshot definition (Decision #6)
- [x] Definition management UI + “Start process from definition” (`ProcessesManagement` Instances/Definitions tabs)
- [x] Start step: branch create Experiment vs lazy create LimsRun; run history table `eln_process_step_lims_runs`
- [x] Migration backfill: ad hoc `eln_processes` → snapshot definitions (`0051`)
- [x] Sample journey API `GET /v1/samples/{id}/journey` + sample dialog UI (Decision #7)
- [x] Soft advance warnings when lims_run step incomplete/not published
- [x] Tests: `test_eln_process_definitions.py` + updated `test_eln_processes.py`
- [-] Advanced reporting / “samples currently in step X” (filter by step exists; richer reporting deferred)

### Phase 3 exit criteria

- [x] Can create a process definition with mixed `eln_experiment` / `lims_run` steps
- [x] Can instantiate instance (snapshot) and start each step kind
- [x] Sample journey visible with sample access (not only experiment:manage)
- [x] Soft gate on advance returns `warning` without blocking

---

## Phase 4 — Template / experiment entries (ELN building blocks)

**Gate:** Lab Ops **Accept with conditions** (2026-08-10). Continue **CEO → UI → Arch → Security**; implement after chain + L1–L8.  
**Packet:** [tech-sketch/experiment-template-entries.md](../tech-sketch/experiment-template-entries.md) §0  
**Lab ops:** [lab-ops-review/experiment-template-entries.md](../lab-ops-review/experiment-template-entries.md)

### Reviews

| Review | Status | Note |
|--------|--------|------|
| **Lab Ops (SVP)** | **Accept w/ L1–L9** (2026-08-10) | L9: all aliquot/pool methods in v1 (not one-first) |
| CEO | Pending re-review | Scope freeze on v1 spine |
| UI | Pending re-review | Queue, template builder, save/submit |
| Architecture | Pending re-review | Grid/export/submit, aliquot execute |
| Security | Pending re-review | Write-back config, RLS |

### Substrate locked (Decision #23 / tech sketch §0) — 2026-07-29

- [x] Kinds: `experiment_sample_data` (rows = samples **in** experiment) + `experiment_data` (manual/code rows)
- [x] Storage: entries + entry_field_definitions + entry_field_values (typed cells)
- [x] Contracts: `GET …/grid` (wide UI) + `GET …/export` (long report) + `PUT …/values`

### Before re-open full Phase 4 (Lab Ops)

- [ ] Lab workflow brief: 2–3 target SOPs (steps + entry kinds)
- [ ] Entry catalog v1 in requirements (predefined on top of two kinds)
- [ ] Q8 / Q22 process sample population decision
- [ ] Q18 aliquot creates children vs plan-only
- [ ] Q20 entry complete/unlock rules
- [ ] Lab Ops re-review → Accept or Accept with conditions

### P0 eng (blocked on Lab Ops catalog; substrate may be stubbed after catalog lock)

- [ ] *(blocked)* Normalize types + grid + export APIs per §0
- [ ] *(blocked)* Template Tables & forms authoring
- [ ] *(blocked)* First OOTB predefined entries from catalog

---

## Open questions

**Canonical decision log:** [`.docs/open-questions/experiments.md`](../open-questions/experiments.md)

Rule: no new phase / major feature until blocking questions for that work are resolved. See `AGENTS.md` → *Open questions gate*.

---

## Related docs

| Doc | Role |
|-----|------|
| [open-questions/experiments.md](../open-questions/experiments.md) | **Open questions + decisions** |
| [requirements/experiment-processes-entries.md](../requirements/experiment-processes-entries.md) | Consolidated requirements |
| [tech-sketch/experiment-template-entries.md](../tech-sketch/experiment-template-entries.md) | Template entries how (**Lab Ops Hold**) |
| [lab-ops-review/experiment-template-entries.md](../lab-ops-review/experiment-template-entries.md) | **SVP Lab Ops** review |
| [lab-ops-review/README.md](../lab-ops-review/README.md) | Lab ops review role |
| [schema-changes/experiment-template-entries.md](../schema-changes/experiment-template-entries.md) | Schema delta (P0: mostly none) |
| [manuals/processes.md](../manuals/processes.md) | Process concept |
| [manuals/experiments.md](../manuals/experiments.md) | ELN Experiments |
| [manuals/lims-runs.md](../manuals/lims-runs.md) | LIMS Runs boundary |
| [design/gap-analysis-…](../design/gap-analysis-process-and-experiment.md) | Gaps |
| [experiment-rework-prerequisites.md](experiment-rework-prerequisites.md) | Pre-rework issues |
| [ceo-review/process-and-experiment.md](../ceo-review/process-and-experiment.md) | CEO review (Phase 1–3) |
| [ceo-review/experiment-template-entries.md](../ceo-review/experiment-template-entries.md) | CEO review (template entries) |
| [ui-review/experiment-template-entries.md](../ui-review/experiment-template-entries.md) | UI review (template entries) |
| [architecture-review/experiment-template-entries.md](../architecture-review/experiment-template-entries.md) | Architecture review |
| [security-review/experiment-template-entries.md](../security-review/experiment-template-entries.md) | Security review |
| [design/experiment-planning.md](../design/experiment-planning.md) | Chunk 1–2 history |
| [Docs index](../README.md) | Full documentation map |

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
| 2026-07-11 | Decision #6: processes always defined (first-class reusable definitions); experiments ad hoc or templated |
| 2026-07-11 | Decision #7: progress visibility sample-scoped (no cross-client) |
| 2026-07-11 | Decision #1: typed process steps (C) + 1a–1g + 1h-A hybrid in Phase 3 v1 |
| 2026-07-11 | **Phase 3 shipped:** migration 0051, definitions API, typed start-step, soft advance, sample journey, Processes UI + journey on sample dialog |
| 2026-07-28 | **Phase 4 packet ready for review:** template Entries authoring + sample roster tech sketch, schema-changes, CEO/UI/arch/security review stubs, Q11–Q14 |
| 2026-07-29 | Phase 4 tech reviews Accept; then **Lab Ops Hold** — implement gate closed; Q17–Q22; process + lab-ops-review role added |
| 2026-07-29 | SVP Lab Ops review written; Sapio Experiments Guide used as competitive floor; slow-down on ELN entry rush |
| 2026-07-29 | **Decision #23:** lock experiment_sample_data / experiment_data kinds, EAV storage, grid+export contracts (tech sketch §0) |
