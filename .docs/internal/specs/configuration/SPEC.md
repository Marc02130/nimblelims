# Spec: Configuration framework

**PRD:** [../../prd/configuration/PRD.md](../../prd/configuration/PRD.md)  
**Date:** 2026-08-30  
**Status:** Working contracts for the four-layer spine. **Not an implement packet.** P2 merge held. Dest-type mint Hold.

Product rules live in the PRD. This file names tables, APIs, and UI. Do not fork a second execute API.

---

## 0. Layers

| Layer | Config home | Execute / write |
|-------|-------------|-----------------|
| Accessioning | Lists, Field Management, name templates | `POST /samples/receive` |
| Asked-for | Analyses, `analysis_param_defs` | `POST /v1/asked-for` |
| Routing | `routing_map` (TAT + ordered process definitions) | `POST /v1/asked-for/{id}/route` |
| Execution | Process definitions + steps; ExperimentTemplates; Analyses / parsers | Process / Experiment / LimsRun start |

Accepted **inbound sample types** are execution config on the **process-definition step**, not on Experiment, LimsRun, Analysis, or the routing map.

---

## 1. Accessioning

### Tables / catalogs

| Object | Role |
|--------|------|
| `list_entries` (sample_type, project, container type, …) | Sticky receive choices |
| Field Definitions (`entity_type=sample`) | OOB + custom sample fields |
| Name templates | Lab sample ID |

Intake **profiles** are deferred (FW-1: OOB = atomic receive).

### HTTP

```
POST /api/samples/receive
```

Non-empty `analysis_ids` → **422**. Omit or `[]`. Zero Tests.

### UI

`/receive` — Sample Mgmt → Receive. Stay on the form after commit.

### AuthZ

`sample:create` + project access. Client **403**. Mutate lists/fields = `config:edit`.

---

## 2. Asked-for

### Tables

| Object | Role |
|--------|------|
| `analyses` | Assay catalog; `turnaround_time` may default TAT |
| `analysis_param_defs` | Order-capture keys on the analysis |
| `asked_for` | Request row: sample, analysis, TAT, `params` jsonb, status |

### HTTP

```
POST   /api/v1/asked-for
GET    /api/v1/asked-for
POST   /api/v1/asked-for/{id}/cancel
GET    /api/v1/analyses/{id}/param-defs
PUT    /api/v1/analyses/{id}/param-defs    # config:edit
```

Create leaves `COUNT(tests)` and `COUNT(work_orders)` unchanged. P1 writes `requested` / `cancelled` only.

### UI

`/asked-for` — later look-up, not the after-receive click. No Start / Execute.

### AuthZ

Write: `test:assign` + dual-belt `has_project_access`. List: same belt, not RLS-only. Client cannot write (**403**).

---

## 3. Routing

### Tables

| Object | Role |
|--------|------|
| `routing_map` | TAT range + `process_definition_ids[]`. No analysis field and no sample-type field as authoring (proposed after `8cfa2a9`) |
| `work_orders` | Snapshot of the ordered list at Route. Zero Tests |

Types and analyses on a map **read** are derived from the chain’s process-definition steps (first-step types, all LimsRun `analysis_id`s, emerging types).

### HTTP

```
GET/POST/PATCH/DELETE /api/v1/routing-map     # config:edit mutate
POST /api/v1/asked-for/{id}/route             # test:assign
POST /api/v1/asked-for/route                  # batch
GET  /api/v1/work-orders
POST /api/v1/work-orders/{id}/start           # experiment:manage; chain[0] only
```

Route: TAT candidates → keep rows whose first process first typed step accepts current type **and** whose chain has a LimsRun for the asked-for analysis. Zero → **422**. Two that both accept type **and** analysis → **409**. Exactly one snapshots the list.

Map save **409**: overlapping TAT ∩ first-step types ∩ LimsRun analyses.  
Map save **422**: process *x* emerging type not accepted by *x+1* first step.

### UI

`/admin/routing-map` — TAT + sortable processes. Display each process’s step types, LimsRun analyses, emerging types. No type picker. No analysis picker.

---

## 4. Execution

### 4.1 Process definition (always defined)

| Table | Role |
|-------|------|
| `eln_process_definitions` | Reusable SOP pack |
| `eln_process_definition_steps` | Ordered `eln_experiment` \| `lims_run` |
| `eln_process_definition_step_accepted_sample_types` | **SoT for inbound types** (one row per step × sample_type) |

Experiment step: `experiment_template_id`.  
LimsRun step: `analysis_id`.  
Both: accepted type list on the step.

### HTTP (types)

```
GET /api/v1/eln-process-definitions/{id}/steps/{step_id}/accepted-sample-types
PUT /api/v1/eln-process-definitions/{id}/steps/{step_id}/accepted-sample-types
```

PUT body: `{ "sample_type_ids": ["uuid", ...] }`. Empty list fails closed at Route / Start.

Today PUT is `experiment:manage` (process-definition authoring). Catalog-wide mutate elsewhere is `config:edit`. Do not silently move this permission in this draft.

### UI

`/experiments/processes` — Definitions tab. Per step: kind, template **or** analysis, **Accepted sample types**, label. That Autocomplete is the type config. There is no accepted-type control on Experiment template UI or LimsRun / analysis UI.

### Instance

`eln_processes` / `eln_process_steps` snapshot the definition. `work_order_id` + `work_order_route_position` unique when started from a work order. First Start = process[0] only. Later Start = next pending. Each start type-gates **current** sample type against **that** step’s list → `422 route_sample_type` if empty or mismatch.

### 4.2 Experiment

| Object | Role |
|--------|------|
| `experiment_templates` | Entries, FieldDefinitions, aliquot/pool `default_dest_sample_type` (emerging type for handoff) |
| `experiments` | Instance; ad hoc or from template |

**No** `accepted_sample_types` on template or instance.

### 4.2b AI draft vs live LimsRun

AI SOP authoring (north star, gate CLOSED) writes **definition** rows, not instances.

| Draft | Table | Live later |
|-------|-------|------------|
| Process + `lims_run` step | `eln_process_definitions`, `eln_process_definition_steps.analysis_id`, step accepted types | `POST /work-orders/{id}/start` then Start step → `lims_runs` |
| Parser | `data_parsers` `active=false`, unbound | Human activate; import on the live run, no LLM |
| Experiment step | `experiment_templates` + `eln_experiment` step | Instantiate experiment from the template |

Human edit of an AI draft is the existing process-definition editor (`PUT` steps + accepted types) and parser dry-run/activate. No separate “LimsRun template” object.

MCP tools are draft-only: no activate, no `routing_map`, no mint Test, no publish. One SOP → one definition; a two-method job may draft two definitions; a human orders them on the map.

### 4.3 LimsRun

| Object | Role |
|--------|------|
| `lims_runs` | Instance; `analysis_id` required (WO-4) |
| `analyses` | Assay identity, analytes, param defs, parser bind |
| `data_parsers` | analysis × (instrument XOR CRO) |

**No** LimsRun template. **No** accepted types on the run or the analysis.  
`lims_runs.experiment_template_id` is historical (lifecycle / worklist). Do not grow it into a LimsRun template.

**Parsers vs process authoring:** an analysis may have **many** parsers (different instruments / CRO exports of the same test). `parser_analyses` is M2M; at most one `is_default` per (analysis, source) among active versions. The process-definition LimsRun step stores **`analysis_id` only** — not `parser_id`. Parser is resolved at **import** (`lims_run_imports`): tech picks instrument XOR CRO; engine uses the active parser linked to `run.analysis_id` (default if set, else the first active); explicit `parser_id` must match analysis + source. Lineage is the version FK on that import. Day-to-day import: no LLM. Manual results: no parser.

WO-7: Test at LimsRun start of the asked-for analysis. Publish **422** `test_missing` if any cohort Test is missing.

### 4.4 Sibling maps (not work routing)

`sample_type_transitions` — aliquot/pool dest legality. Dest-type **mint** Hold. Handoff 422 reads declared dest on the last experiment of process *x*; it does not mint a daughter.

---

## 5. Failure modes (config)

| Case | Behavior |
|------|----------|
| Receive non-empty `analysis_ids` | **422** |
| Asked-for duplicate open `(sample, analysis)` | **409** |
| Route, zero acceptable (type or analysis-in-chain) | **422** `route_sample_type` |
| Route, two rows accept this type and this analysis | **409** |
| Map save, TAT ∩ first-step types ∩ LimsRun analyses | **409** |
| Map save, process *x* emerging not accepted by *x+1* | **422** |
| Step start, empty or incompatible accepted list | **422** `route_sample_type` |
| Process step with no accepted types | Fail closed for Route/Start that need that step |
| Ad hoc Experiment / LimsRun (no process) | Not gated by step accepted types |

---

## 6. Permissions

| Action | Permission |
|--------|------------|
| Mutate lists, fields, analyses, param defs, routing map, parsers | `config:edit` |
| Record / cancel asked-for; Route | `test:assign` + project access |
| Author process definitions and step accepted types (today) | `experiment:manage` |
| Start process / LimsRun | `experiment:manage` |
| Publish LimsRun | `experiment:publish` |

Configuration never bypasses RLS.

---

## 7. Out of this spec

LimsRunTemplate. Moving accepted types onto ExperimentTemplate or Analysis. Intake-profile engine. Dest-type mint. Second workflow engine. Rewriting signed P2 UAT.
