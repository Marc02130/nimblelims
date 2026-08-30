# Schema changes: post-receive-work-spine

**Feature / cycle:** post-receive work spine  
**Phases covered:** P1 (asked-for) required this cycle; P2 tables specified so architecture can Accept the spine; P3 none; P4 additive FKs; P5 none  
**Status:** Draft for architecture review  
**Alembic revisions:** `0072_asked_for_p1` (P1: `analysis_param_defs` + `asked_for`); `0073_routing_work_orders_p2` (P2: `routing_map`, `work_orders`, step accepted types, nullable LimsRun templates + `analysis_id`, `tests.asked_for_params`); `0074_p2_uat_visibility_publish`; `0075_wo7_freeze_route_position` (`eln_processes.work_order_route_position`); `0076_route_analysis_from_lims_runs` (drop gist on map analysis+type+TAT); `0077_process_assignment_container` (`eln_process_samples.container_id`)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)

## 1. Summary

P1 adds asked-for + analysis param defs. P2 adds routing_map + work_orders. P3 is column-use only. P4 stores apply output on the SOP job. P5 uses existing parser tables.

RLS: asked_for and work_orders follow sample → project (same pattern as tests). routing_map is config (admin / config:edit); FORCE RLS with admin or config:edit policy.

## 2. Delta

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `analysis_param_defs` | Catalog of **method params** per analysis (assay). Example keys: [working note](../../decision-logs/2026-08-28-analysis-param-defs.md) (not seed). | `id`, `analysis_id` FK, `key` text, `data_type` text (`number` \| `int` \| `text` \| `bool`), `unit` text null (display; not `results.unit_id`), `required` bool, `source_list_id` uuid null (list-backed enum), `allowed_values` jsonb null (inline enum sketch when no list), `sort_order` int, audit |
| `asked_for` | Requested analysis on a sample. `params` = values for that analysis’s defs (order layer). | `id`, `sample_id` FK, `analysis_id` FK, `tat_days` int not null check > 0, `params` jsonb not null default `{}`, `status` text not null, `routed_work_order_id` uuid null, audit |
| `routing_map` | P2: analysis × TAT range → ordered route | `id`, `analysis_id` FK, `tat_range` int4range not null, `process_definition_ids` uuid[] not null, `active` bool, audit. No admin-authored sample type. Optional display copy is derived from array position 1 / its first Experiment-LimsRun and refreshed on change |
| `work_orders` | P2: backlog item | `id`, `asked_for_id` FK unique, `sample_id` FK, `analysis_id` FK, ordered `process_definition_ids` uuid[] not null snapshot, `status` text not null |
| `eln_process_definition_step_accepted_sample_types` | P2 L2 / **OQ-WO-4:** accepted sample types per **step** (experiment **and** LimsRun). Not on analysis. Qubit = a LimsRun step. | `step_id` FK `eln_process_definition_steps` ON DELETE CASCADE, `sample_type_id` FK `list_entries`, unique `(step_id, sample_type_id)` |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| `sop_parse_jobs` (name as in code) | ADD `process_definition_id` uuid null FK | P4 |
| `eln_processes` | ADD `work_order_id` uuid null FK; ADD `work_order_route_position` int null | Each later start creates one process instance for one ordered definition. Unique `(work_order_id, work_order_route_position)`; no process-of-processes minted at Route |
| `eln_process_samples` | ADD `container_id` UUID NOT NULL FK `containers` (`0077`) | Process assignment is Contents (sample in a container). Unique `(process_id, container_id)`; active unique `(process_id, sample_id)` WHERE status <> removed |
| `eln_process_definition_steps` | P2: `experiment_template_id` **nullable**; ADD `analysis_id` uuid null FK `analyses` | Pulled from A8 so a **Qubit LimsRun** step does not need a fake ExperimentTemplate. CHECK: `eln_experiment` ⇒ template NOT NULL; `lims_run` ⇒ `analysis_id` NOT NULL. |
| `results` | none | P3 uses `reported_result`, `qualifiers` (UUID FK), `raw_result`. Fitted IC50 etc. live here, **not** in param JSON. |
| `tests` | **P2:** ADD `asked_for_params jsonb not null default '{}'` | **A5 / L3 / SC5.** Frozen copy of `asked_for.params` at **LimsRun start**. P1 does not write this column. |

Do **not** add `results.unit_id`. Do **not** add asked-for columns on `samples`. Param display units are `analysis_param_defs.unit`.

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| `uq_analysis_param_defs_key` | unique `(analysis_id, key)` | A2 |
| `uq_asked_for_open` | unique `(sample_id, analysis_id)` WHERE status <> 'cancelled' | RQ-AF-4 |
| `asked_for_status_chk` | status in (`requested`,`routed`,`cancelled`) | |
| `work_orders_status_chk` | status in (`queued`,`in_progress`,`completed`,`cancelled`) | |
| `routing_map_overlap_chk` | Service-side: refuse save (**409**) when `tat_range &&`, first-step allow-lists intersect, **and** LIMS Run analysis sets intersect | Extract-first vs Qubit-first for the same TAT is legal; two methods sharing extract types are legal; gist-on-TAT-alone is too coarse |
| `routing_map_handoff_chk` | Service-side: refuse save (**422**) when process *x* emerging types are not ⊆ process *x+1* first-step types | Emerging = aliquot/pool dest on *x* last Experiment/LIMS Run if set; else last-step accepted types. Dest mint remains Hold |
| `routing_map_defs_chk` | non-empty ordered `process_definition_ids`; every UUID resolves; reject duplicate positions | ordered route, not one definition or an unordered bag |
| `work_order_route_instance_uq` | unique (`work_order_id`, `work_order_route_position`) where work_order_id not null | one instance per route position |
| `uq_step_accepted_sample_type` | unique `(step_id, sample_type_id)` | OQ-WO-4 |
| `eln_process_definition_steps` kind check | `eln_experiment` ⇒ `experiment_template_id` NOT NULL; `lims_run` ⇒ `analysis_id` NOT NULL | Qubit as LimsRun |
| indexes | `asked_for(sample_id)`, `asked_for(status)`, `work_orders(status)`, `work_orders(sample_id)` | lists |
| extension | P2: `CREATE EXTENSION IF NOT EXISTS btree_gist` optional for TAT candidate lookup | Do **not** gist-exclude on analysis+TAT alone |

### 2.4 Enums / types

No Postgres ENUM. Text + check. Status lists may also seed `list_entries` if the app pattern prefers lists; if so, still constrain in DB.

### 2.5 RLS

| Table | Policy sketch |
|-------|----------------|
| `asked_for` | USING/WITH CHECK via sample.project access (mirror `tests`) |
| `work_orders` | same |
| `analysis_param_defs` | read: authenticated; write: config:edit / admin |
| `routing_map` | read: authenticated lab roles; write: config:edit / admin |
| `eln_process_definition_step_accepted_sample_types` | same as process definitions (config write; lab read) |

FORCE ROW LEVEL SECURITY on asked_for, work_orders, analysis_param_defs, routing_map, and the step-accepted-types table.

**P2 route/type lock:** map create has no sample-type picker. Match analysis + TAT, then current type against each candidate row’s first process / first ordered Experiment-LimsRun allow-list. Zero acceptable rows → 422; two saved rows that both accept this current type → 409; exactly one snapshots ordered `process_definition_ids`. Never silently use `first()`. Map save **409**s only when the same analysis, overlapping TAT, **and** overlapping first-step allow-lists all hold. Extract-first and Qubit-first for the same TAT are legal. Map save/Route do not AND later processes or steps. Start instantiates array position 1 only; each later start advances one position and gates current type then. Empty allow-list fails closed. Dest-type Hold remains unchanged.

## 3. Seed

P1: no asked-for rows. **Do not seed** the working-note example catalog (`EX_hERG`, `EX_ELISA`, …). When seed is allowed later: bind `EX_CTG` / `EX_NCI60` only to existing `NBIO-CMPD-001` / A549 (PR 49). Do not invent Qubit/blood IDs.

P2: **no** invented sample-type IDs. A Qubit-first process derives a DNA allow-list and refuses blood at Route; a later Qubit step is gated only when started. Dest type remains out.

## 4. Out of schema this cycle

Projects rename; intake profiles; lots; `status_history`; parser table redesign (already shipped).
