# Spec: Sample processing

**Domain:** Processes · Experiments · LIMS runs (+ work orders / routing)  
**PRD:** [../../prd/sample-processing/PRD.md](../../prd/sample-processing/PRD.md)  
**Date:** 2026-08-26 (framework-first)  
**Framework:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)

---

## 0. Framework (stamped direction — not all shipped)

| Layer | Status | Contract sketch |
|-------|--------|-----------------|
| **Order / asked-for** | Weak today | Analysis + TAT + parameter values |
| **Routing map** | Not shipped | `(analysis_id, sample_type_id, tat_days_min/max) → ordered process_definition_ids[]` (WO-2, WO-3); mutate = `config:edit` |
| **work_order** | Not shipped | Backlog entity embedding process chain (WO-1, WO-3) |
| **Process / Experiment / LimsRun** | Shipped | Execute substrate — route *into* these (FW-0 §2.5) |
| **Test** | Shipped | Create at **LimsRun start / ensure-on-publish** (WO-7), not accession |
| **Non-instrument** | Clarify | LimsRun + analysis; manual entry; parser needs instrument\|CRO (WO-4) |
| **sample_type_transitions** | Shipped | Sibling map for aliquot/pool dest types |

Do **not** invent a second workflow engine beside Process/Experiment/LimsRun.

## 1. Scope

Technical contracts for ELN process definitions/instances, experiments + entries, aliquot/pool plan-execute, LimsRuns + parsers + promote-on-publish, and (stamped) work_order / routing. Accessioning and container inventory are adjacent.

## 2. Layer contracts (execute — shipped)

| Layer | Primary tables | Primary APIs |
|-------|----------------|--------------|
| Process definition | `eln_process_definitions`, `*_definition_steps` | `/v1/eln-process-definitions` |
| Process instance | `eln_processes`, `eln_process_steps`, `eln_process_samples`, `eln_process_step_lims_runs` | `/v1/eln-processes` |
| Experiment | `experiments`, `experiment_templates`, `experiment_sample_executions` | `/v1/experiments`, templates under `/v1` |
| Entries | `entries`, `entry_field_definitions`, `entry_field_values` | `/v1/entries/...` |
| LimsRun | `lims_runs`, `lims_run_data`, `lims_run_imports`, `data_parsers`, … | `/v1/lims-runs`, parsers under `/v1` |

**Models:** `backend/models/entry.py`, experiment models, `backend/models/flexible_experiment.py`

## 3. Process definitions vs instances

| Rule | Detail |
|------|--------|
| Definitions always | Decision #6 — experiments may be ad hoc |
| Step kinds | `eln_experiment` \| `lims_run` |
| Instantiate | Snapshot definition steps onto instance |
| Experiment step | Stores `experiment_template_id` + `execution_mode` |
| LimsRun step | **Lazy** create on “Start step”; history via `eln_process_step_lims_runs` |
| Soft advance | Warn if run not complete/published; LimsRun remains instrument SoT |

### Process assignment grain (critical)

**SoT:** a process assignment is **sample in a container** (`Contents`), not a bare sample. A sample may have many containers; only one container-with-sample is on the process.

| Today | Required |
|-------|----------|
| `0077` `container_id` NOT NULL | Contents pair `(container_id, sample_id)` |
| Assign sample with no vessel or ambiguous vessels | **422** `process_container_required` |

After aliquot/pool **execute**: dest container-with-sample status `in_progress`; inbound source assignment `removed`. Later work-order Start uses non-`removed` assignments (those containers), not `work_orders.sample_id`.

### Process-sample status (≠ Sample.status)

| Event | `eln_process_samples.status` |
|-------|------------------------------|
| Assign | `queued` |
| Start experiment (selected) | `in_progress` + `current_step_id` |
| Advance | `queued` on next step |
| Done | `completed` |
| Remove | `removed` (inbound vessel after mint; unassign) |

Journey: `GET /v1/samples/{id}/journey` (sample-scoped). Process membership for “what’s on the bench in this SOP” is **container-with-sample**.

## 4. Experiments & cohort

### Eligibility (Decision #24 — server)

1. `Sample.status` = **Available for Testing**  
2. If under process → on `eln_process_samples` and not `removed` (**that container-with-sample**)  
3. Explicit dual-list select (never auto-start whole process)  
4. After start → cohort **fixed**

### Trackers

| Table | Meaning |
|-------|---------|
| `eln_process_samples` | Container-with-sample in this process / current step (`container_id`, 0077) |
| `ExperimentSampleExecution` | In this experiment cohort |

### Entry kinds (Decision #23)

| Kind | Rows |
|------|------|
| `experiment_sample_data` | One per cohort sample (`sample_id`) |
| `experiment_data` | Multi-row via `row_key` (table only) |

**Save** = values only. **Submit** = complete + Sample write-back allowlist (`SAMPLE_WRITE_BACK_COLUMNS`); last write wins + `write_back_previous`.

### Predefined keys

| Key | Kind | Role |
|-----|------|------|
| `experiment_header` | experiment_data | Start context |
| `samples` | experiment_sample_data | Cohort display |
| `aliquot_pool_plan` | experiment_data | Plan + execute |
| `aliquots_pools` | experiment_sample_data | Post-execute daughters |

Sample-type **gate** for start belongs on **experiment / LimsRun** (product stamp) — not an entry `accepted_sample_types` field as the primary gate.

## 5. Aliquot / pool plan-execute

### Config (on `aliquot_pool_plan` entry)

| Field | Rule |
|-------|------|
| `method` | Concrete METHOD_CATALOG / `METHOD_PROFILES` id → one `mint_op` |
| `default_dest_sample_type` | Optional; blank = Same as parent |
| `plan_lines[]` | Sources + method inputs + optional `dest_sample_type` / inherit flag |

### Resolve at execute

```text
mint_op = catalog[method].mint_op
type_id = line.dest_sample_type
       or entry.default_dest_sample_type
       or source.sample_type
if type_id != source and no sample_type_transitions row: refuse
mint dest sample (parent_sample_id = source)
join eln_process_samples when entry.process_step_id set
populate aliquots_pools.minted_sample_ids
```

### Transitions

Table `sample_type_transitions` (`0068`):  
`(client_id, source_sample_type, operation ∈ {aliquot,pool}, allowed_dest_sample_type)`  

Seeds: Blood×aliquot→DNA; DNA×pool→Pooled DNA.  
Mutate: **`config:edit` only** (S3) — thin admin UI still to land.

### Atomic pair (locked; UI lag)

One “Add aliquot/pool” creates **both** `aliquot_pool_plan` and `aliquots_pools` (template + ad hoc). Dest empty until execute. No plan-only / dest-only add.

### METHOD_CATALOG dual-map (kick-back)

Docs: method select attaches plan columns **and** dest FieldDefinitions on `aliquots_pools` immediately.  

**Open design:** Capture qty fields only on **entry FieldDefinitions** (`experiment_data` / `experiment_sample_data`). Do **not** treat them as live Sample fields during plan/execute. Sample/Contents updates only after the agreed submit/action gate (source volume/status + dest info). Restamp before coding FD attach as closed.

### Bounce bars

Dual mint; mid-flight method change (cancel experiment; do not un-mint); new Sample columns for dest qty; method/type pickers on `aliquots_pools`; CUT methods.

**Code:** `backend/app/services/aliquot_plan_service.py`, `backend/app/schemas/aliquot_plan.py`, `frontend/.../AliquotPlanEditor.tsx`

## 6. LimsRuns & parsers

| Contract | Detail |
|----------|--------|
| Create | `analysis_id` required |
| Lifecycles | Standard vs CRO |
| Import | `running` \| `results_received`; `data_parsers` (instrument XOR CRO) |
| Lineage | `lims_run_imports` stores parser version id |
| Publish | Map JSONB → analytes (+ aliases) → ensure Tests → Results; other-owner conflict → **409** |
| Preview | `GET /v1/lims-runs/{id}/promotion/preview` |
| Day-to-day AI | Forbidden on import; setup-only drafts OK |

Process step references runs; does not merge entities. Entries do not auto-promote to Results.

## 7. End-to-end sequence (Extract-then-Qubit)

```text
1. Accession blood (accessioning domain)
2. Create process instance from definition
   step1 eln_experiment (extract template + aliquot_pool_plan)
   step2 lims_run (Qubit analysis)
3. Assign samples → Start step1 → select cohort → Experiment
4. Method + dest type DNA → Execute → daughters + process join
5. Advance → Start step2 → lazy LimsRun
6. Import file → Publish → Results on daughters
```

## 8. Permissions (typical)

| Surface | Permission |
|---------|------------|
| Manage experiments / execute aliquot | `experiment:manage` |
| Publish | `experiment:publish` (and related) |
| Transition catalog mutate | `config:edit` |
| Config templates / parsers | `config:edit` |

Plus RLS / `has_project_access` / process membership.

## 9. Tests / UAT

- `backend/tests/test_aliquot_plan.py`  
- Experiment / process UAT scripts under `UAT_Scripts/`  
- `UAT_Scripts/uat-extract-hold-dest-type.md`  
- LimsRun promotion tests / preview  

## 10. Implement backlog (regrouped)

| Priority | Item | Blocked? |
|----------|------|----------|
| P0 | Restamp dual-map FD + Sample update timing | **Yes — design kick-back** |
| P1 | Atomic pair add (template + ad hoc) | No (lock clear) |
| P1 | S3 transition CRUD + thin admin UI | No |
| P2 | Docs sync (Hold wording, AC12 entry gate removal) | No |
| P2 | Testdata blood → DNA → Qubit | Separate OQ |
| Later | SOP+AI Apply → process definition | Product gap |
| Later | experiment_link deprecate (#10) | Open |

## 11. Code index

| Area | Path |
|------|------|
| Entries / predefined keys | `backend/models/entry.py` |
| Aliquot service | `backend/app/services/aliquot_plan_service.py` |
| Flexible experiment / runs | `backend/models/flexible_experiment.py` |
| Process routers | `backend/app/routers/eln_processes.py`, `eln_process_definitions.py` |
| Experiments | `backend/app/routers/experiments.py` |
| Lims runs / parsers | `backend/app/routers/lims_runs.py`, `data_parsers.py` |
| Transitions | `0068_sample_type_transitions.py` |
| UI plan editor | `frontend/src/components/experiments/AliquotPlanEditor.tsx` |
| Spine sketch | `.docs/review/tech-sketch/experiment-template-entries.md` |
