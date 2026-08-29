# Tech sketch: Post-receive work spine

**Date:** 2026-08-28  
**Stem:** `post-receive-work-spine`  
**Status:** P2 `b005cfe` has Tobias-signed per-AC results; publish-refuse Pass. **Overall P2 Pass remains unsigned** because first-start-wins is OPEN. Hold product merge. Marc/Rolf map-create lock supersedes the type picker / chain-AND design. Not IC50.
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Process:** [`.docs/review/development-process/README.md`](../development-process/README.md)

P1 is on `main`. P2 is on `feat/work-order-p2` (Accept with conditions). Do not code P3–P5 in the P2 PR. Coding stays Grok Build.

**Lab Ops 2026-08-28:** Accept with conditions. P1 implementable if **L1** is in the UI/copy. **P2 coding closed until L2–L4 are in this sketch** (folded below). **L5** binds P4 copy. Artifact: [lab-ops-review/post-receive-work-spine.md](../lab-ops-review/post-receive-work-spine.md).

**Room locks (2026-08-28):**

1. **P1 lake** = asked-for records **requested analysis + TAT + params**. Bounce Test / Result / Process / Experiment / LimsRun / work_order mint, second workflow engine, analysis picker on `/receive`, silent Order→work.
2. **Heidi:** `GET /asked-for` `list()` must **dual-belt `has_project_access`** (same as create), **not RLS-only**. `analysis_param_defs` RLS may be any logged-in user; mutate stays `config:edit` in the router. P1 must **not** write status `routed` (`routed` is P2). Type × analysis eligibility is **P2 (L2)**, not this PR.
3. **Params** on `asked_for` are **order capture**, not the Test snapshot. Freeze still happens at LimsRun start (WO-7 / P2). Bounce Start/Execute CTA, silent Order→work, analysis picker on `/receive`, README that equates asked-for with Test assign. Classic `/tests` type-a-number stays.
4. **Mathilda U1 / U2:** asked-for ≠ Test assign. Label params as order capture, not Test snapshot.
5. Architecture / UI / Spec **Accept with conditions** on P2. Hold product merge. Not IC50.
6. **Receive freeze:** non-empty `analysis_ids` still **422**.
7. **P2 one process (Heidi / Mathilda U1):** `routing_map` and `work_order` hold **one** process definition (typed Exp/LimsRun steps). Bounce process-of-processes, `uuid[]` chain, completing N starts N+1, `start` of `[0]` only. **Still open** on `b005cfe`.
8. **WO-7 publish (Tobias-signed Pass @ `b005cfe`):** `_require_wo7_tests` 422s before promote if any cohort sample lacks an active Test. Status stays unpublished (complete). Do **not** fold first-start freeze into this Pass; that half remains OPEN.
9. **Freeze:** first LimsRun start wins. `_mint_tests_at_start` must **not** overwrite `asked_for_params` on an existing Test. **Still open** on `b005cfe`.
10. **P2-4 visibility (QA Fail / Heidi belt):** Route is `test:assign` and must **read** mapped process/step metadata so the UI makes order apparent, displays derived allowed types for the first/only process and first ordered Experiment/LimsRun step, and runs the first-step Route gate. SOP def/step **read** is catalog-visible (same client / logged-in, like `routing_map`). Do **not** require `experiment:manage` on Route. Do **not** filter read by `created_by`. **`0074`:** dropping `created_by` is good; `is_admin() OR has_experiment_access()` is **not** catalog-visible. Mutate stays `config:edit`; instantiate stays. Route is **not** admin-only. **Still open** on `b005cfe`.
11. **Marc/Rolf map-create lock:** remove the sample-type picker from routing-map authoring. Match is analysis + TAT; type eligibility is derived from the selected first/only process and its first ordered Experiment/LimsRun step.

---

## 1. Problem (technical)

Receive writes Sample + Containers + Contents. Nothing records the request. Classic `POST /tests` mints a Test, which collides with WO-7 (Test at LimsRun start). Work_order / routing tables do not exist. SOP Apply writes templates only. Parser engine exists; setup UX is the gap.

## 2. Architecture

```
UI /asked-for ──▶ asked_for (P1)
                      │
                      ▼  (P2)
              routing_map match?
                 │ yes          │ no
                 ▼              ▼
            work_orders      stop (configure)
                 │
                 ▼
         existing /v1/eln-processes
                 │
                 ▼
         LimsRun start → Test (WO-7)
                 │
                 ▼
         results persist (P3)  or  parser import (P5) → publish
```

SOP Apply (P4) writes **process definitions** that routing_map points at.

No new execute runtime. No second AuthZ. No second workflow engine.

## 3. P1 design

### 3.1 Tables and param bind

Three layers (normative with [analysis-param-defs working note](../../decision-logs/2026-08-28-analysis-param-defs.md) — **example data, not seed**):

| Layer | Where | When |
|-------|--------|------|
| **Catalog** | `analysis_param_defs.analysis_id` | Admin associates keys to an **assay** (`config:edit`). `unit`, `data_type`, `required`, optional `source_list_id` / `allowed_values`. RLS may be any logged-in user; mutate stays `config:edit` in the router. Empty OOB seed is OK. |
| **Order (P1)** | `asked_for.params` jsonb | User fills values for that analysis on the request (**order capture**, not the Test snapshot). Validate keys vs defs. **No Test.** |
| **Execute (P2)** | `tests.asked_for_params` jsonb | **LimsRun start:** copy asked-for JSON and freeze. Not receive. Not publish. Not result fields. |

`asked_for` — request row. FK sample, analysis. `tat_days int`. `params jsonb`. `status` check constraint. P1 writes `requested` / `cancelled` only — **must not write `routed`**.

Fitted IC50 / Hill / CLint / fu / % remaining are **results**, not catalog keys.

Partial unique index: `(sample_id, analysis_id) WHERE status <> 'cancelled'`.

### 3.2 Service

`AskedForService.create`:

1. AuthZ `test:assign` + **dual-belt `has_project_access`** (403 if hidden) — not RLS-only
2. Sample.status should be Available for Testing (422 otherwise for v1 — do not order on discarded)
3. Validate analysis active
4. Validate params vs defs (`params` = **order capture**, not a Test snapshot; unknown key / missing `required` → 422). **OQ-AF-6:** `required` is boolean only, set on the analysis. No “required if …” engine.
5. Insert `requested` only — P1 must **not** write `routed`
6. **Do not** write `tests.asked_for_params`. **Do not** call `_create_tests` / `_create_asked_for_tests`. Bounce Test / Result / Process / Experiment / LimsRun / work_order mint. No silent Order→work. No second workflow engine.

`AskedForService.list` (`GET /asked-for`): must **dual-belt `has_project_access`** (same as create), **not RLS-only**. Filter every returned row by project access before respond.

`analysis_param_defs` RLS may be any logged-in user; mutate stays `config:edit` in the router.

P1 **does not** call routing (table may not exist yet). Type × analysis eligibility is **P2 (L2)**, not this PR.

**L1 (Lab Ops, same-phase P1):** Copy is “asked-for / requested analysis,” never assign/create test, start work, or order process. No Start/Execute CTA on `requested`. Multi-sample: one operator action (same analysis + TAT + params) writes one row per sample in the set **in one txn** (A3). Hidden sample → **403** (A1). **Client role cannot write** even with leftover `test:assign` (S2). No PATCH in P1 — cancel and recreate (BA4).

### 3.3 Frontend

`pages/AskedFor.tsx` + sample detail panel. Reuse analysis dropdown from Tests, **not** TestForm (TestForm creates Tests). Multi-select samples for one request (L1).

Sidebar Sample Mgmt: after Receive, add **Asked-for**.

No analysis picker on `/receive`. No Start/Execute CTA. Classic `/tests` type-a-number stays (WO-4). Asked-for ≠ Test assign.

### 3.4 Tests

Pytest: create, 409 dup, **403 dual-belt** (create **and** `list()` / `GET /asked-for` — `has_project_access`, not RLS-only), 422 params, receive still 422 on non-empty `analysis_ids`, asked-for leaves tests count 0, P1 never writes `routed`.

## 4. P2 design

`routing_map`: range-gist or exclusion constraint on `(analysis_id, tat_range)`. Postgres: `int4range` + `EXCLUDE USING gist`. No admin-authored `sample_type_id`.

**OQ-WO-1 Decided:** Tech hits **Route**. No auto-route on asked-for save. `POST /api/v1/asked-for/{id}/route` (batch the same call for a selected set). Then:

- Resolve the sample’s current type (not an admin map key)
- Select map row
- **Marc/Rolf superseding lock / OQ-WO-4:** map match is analysis + TAT. The admin does not select a sample type. The planner derives and displays allowed types for the selected first/only process and its first ordered `eln_experiment` or `lims_run` step; this may refresh or be stored when the process/step changes, but it is not authored. Route compares the sample’s **current** type with that first-step list only; empty or incompatible returns **422 `route_sample_type`** and mints nothing. Later steps may expect a transformed type and check current type only when started; empty fails closed then. Do **not** infer a transformation from `sample_type_transitions`. Dest-type Hold remains unchanged. Do not invent Qubit/blood testdata IDs.

`work_orders.process_definition_id` snapshot at mint (**L4**). **One** existing process definition (typed Exp/LimsRun steps). Bounce `uuid[]` chain, completing N starts N+1, process-of-processes.

Start: `ELNProcessService.instantiate_from_definition` on **that** definition; `work_orders.process_id`. Instantiate stays existing process AuthZ (`experiment:manage`). **P2-4 / Route:** `test:assign` — must **read** mapped def/steps to display their order and derived first-process / first-step allowed types, then compare current type with that first step. SOP def/step **read** is catalog-visible (same client / logged-in, like `routing_map`). Do **not** put `experiment:manage` on Route. Do **not** filter read by `created_by` or `has_experiment_access()`. Mutate stays `config:edit`. Later step starts run their own current-type gate.

**L3 / A5 / SC5:** At LimsRun start, insert Test if missing; copy `asked_for.params` → `tests.asked_for_params` and freeze. **First start wins** — do not overwrite `asked_for_params` on an existing Test. Column ships in the P2 migration. P1 does **not** write that Test snapshot. Shape: JSON object matching that analysis’s defs (see working-note §3 snapshots).

WO-7 publish @ `b005cfe` is Tobias-signed Pass: missing cohort Test returns 422, status stays complete / unpublished, and no Test is reminted. First-start params freeze remains OPEN and unscored; overall P2 Pass is unsigned.

## 5. P3 design

Single function `persist_typed_result(test, analyte, value)` used by UI results table and any manual LimsRun entry.

No `results.unit_id`. Typed token → `reported_result` as-is (no float roundtrip). `qualifiers` remains **UUID FK** (SC1); NULL if none. Missing `units_default` → 422 for numeric quantities (SC3). Text/boolean exempt.

## 6. P4 design

`SopParseApplyService`: map extracted steps → `eln_process_definition_steps`. Experiment steps keep `experiment_template_id` (create template as today, then attach). LimsRun steps store `analysis_id` if parsed.

**L5:** Apply writes a process definition. It does **not** close dest-type Hold. No blood → DNA → Qubit UAT in this packet.

Job row: `process_definition_id` nullable.

## 7. P5 design (interim)

No new import engine. **Do not build “admin authors parsers” as the product.** Authoring belongs to [ai-sop-north-star](ai-sop-north-star.md) (SOP + example files → MCP → `data_parsers` draft). P5 is dry-run + activate. Day-to-day import: no LLM.

## 8. Failure modes

| Case | Behavior |
|------|----------|
| Hidden sample (create or list) | **403** via dual-belt `has_project_access` (not RLS-only) |
| Cancelled asked-for re-create | Allowed (unique ignores cancelled) |
| Route with empty map | 200, no WO |
| Map overlap | 409 on map save |
| Map create offers sample type | Remove the field; derive first-process / first-step display |
| Route with current type outside first step’s accepted types | **422 `route_sample_type`**; no WO; sample is not broken |
| Later step start with current type outside that step’s accepted types | **422 `route_sample_type`**; sample is not broken |
| Publish without Test (deleted Test or empty plan / 0 data rows) | **422** the whole run (`_require_wo7_tests` / `plan.errors` @ `b005cfe`). Stay unpublished. Zero Results. Publish-refuse Pass; first-start freeze remains OPEN. |
| Invisible process def (alice vs `created_by` / `has_experiment_access`) | Catalog-visible **read** (same client / logged-in). `0074` is not enough. Route stays `test:assign`. Not `experiment:manage` on Route. Not `route_sample_type`. |
| Derived first-step types unavailable | Fail assignment closed; do not restore an admin type picker |
| Parser AI on import | Impossible (no call site) |
| Receive non-empty `analysis_ids` | **422** (freeze) |

## 9. Delivery

| PR | Scope |
|----|--------|
| 1 | P1 tables + API + `/asked-for` UI + pytest + UAT script. **Hold merge until UAT.** |
| 2 | P2 routing + work_order + route + LimsRun WO-7. Architecture / UI / Spec Accept with conditions. **Hold product merge.** Publish-refuse signed Pass on `b005cfe`; overall P2 remains unsigned/not Pass because first-start-wins is OPEN. Map-create lock: no sample-type picker; Route gates derived first-step types only. |
| 3 | P3 persist lock + results UAT fold (**closed**) |
| 4 | P4 SOP Apply → process def (**closed**) |
| 5 | P5 parser setup UX (**closed** this cycle) |

Coding stays Grok Build. One phase per PR. Receive code freeze except bugs. Not IC50.
