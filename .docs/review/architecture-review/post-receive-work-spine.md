# Architecture Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Schema changes:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md) — **present**; P1 tables OK; P2/P4 deltas incomplete vs L2/L3/L4 (A4–A6, A8, A10)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/post-receive-work-spine.md) (L1–L5; P1 OPEN; P2 CLOSED until L2–L4) · [Scientific CSO](../scientific-cso-review/post-receive-work-spine.md) (SC1–SC5)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
**Prior architecture review:** none for this stem

---

## Executive summary

The spine is the right system shape. Do not collapse layers. Do not add a third execute engine. P1 is implementable as a request lake on existing sample/project RLS + `test:assign`.

Schema-changes exists and lists the four new tables. That is enough to Accept the spine **only with the locks below**. Lab Ops L2–L4 are prose in the sketch; they are **not** columns yet. `tests: none` contradicts L3 / SC5. Type eligibility has no config object. Chain walk cannot be `work_orders.process_id` only. Publish still **ensure-creates Tests**.

**P1 OPEN** if A1–A3 land in the same PR. **P2 CLOSED** until schema-changes names A4–A7 (and A10). **P3** persist lock is column-use only after SC1–SC4 fold; no `results.unit_id`. **P4** needs step `analysis_id` (A8) before Apply can write a real LimsRun step. **P5** is admin UX on shipped parser tables.

**This stamp decides OQ-WO-3:** SoT is `eln_processes.work_order_id`. See A6.

---

## System shape

```
 /asked-for  ──► asked_for (requested)
                      │
                      │  P2: routing_map
                      │  key = analysis × sample_type × TAT range
                      │  type gate = step accepted sample types  (experiment AND lims_run; NOT analysis; NOT sample_type_transitions)
                      ▼
                 work_orders  (process_definition_ids[] snapshot)
                      │
                      ▼
         ELNProcessService.instantiate_from_definition  (existing)
                      │
                      │  complete process N → surface N+1 from snapshot
                      ▼
         LimsRun.start  →  INSERT Test if missing  (WO-7)
                      │     snapshot asked_for.params → tests.asked_for_params (freeze)
                      ▼
         persist_typed_result  |  parser import
                      │
                      ▼
         publish  →  422 if Test missing   (NO ensure_test)
```

SOP Apply (P4) writes **process definitions** that `routing_map` points at. Dest-type Hold is a different packet.

---

## Schema-changes vs sketch

| Claim | Sketch | Schema-changes | Verdict |
|-------|--------|----------------|---------|
| `analysis_param_defs` | P1 | New table | **Match.** Add unique `(analysis_id, key)` (A2). |
| `asked_for` | P1 | New table + `routed_work_order_id` | **Match.** Reverse FK is denorm; SoT is `work_orders.asked_for_id` (A6). |
| Partial unique open `(sample_id, analysis_id)` | Yes | `uq_asked_for_open` | **Match.** |
| P1 does not mint Tests / WO | Yes | No asked-for cols on `samples` | **Match.** |
| `routing_map` gist exclude | P2 | `int4range` + `EXCLUDE gist` | **Match.** Must `CREATE EXTENSION btree_gist` (A10). |
| Type eligibility | L2: config on LimsRun step and/or analysis; **not** `sample_type_transitions` | **Missing** | **Drift.** A4. |
| L3 params snapshot on Test at LimsRun start | Yes | `tests: none` / WO-7 timing only | **Drift.** A5. Sci CSO SC5. |
| L4 chain walk from WO snapshot | Yes | `process_definition_ids uuid[]`; FK “pick one” | **Under-specified.** A6 closes OQ-WO-3. |
| WO-7 mint at start; publish refuse | Yes | `tests: none` | Timing is app; **ensure-on-publish still in code** (A7). |
| P3 columns | persist lock | `results: none` | **Match** after SC1: do not change `qualifiers` type. No `results.unit_id`. |
| P4 Apply → process def | `process_definition_id` on job | ADD on `sop_parse_jobs` | **Partial.** Steps still require `experiment_template_id` NOT NULL; no `analysis_id` (A8). |
| Seed blood→Qubit | Forbidden | No default routing that claims it | **Match.** |

`sample_type_transitions` in code is an **aliquot/pool allowed-dest catalog** (`operation IN ('aliquot','pool')`). It is not proof execute minted DNA. Using it as a route gate would ship the dest-type lie. A4.

---

## What already exists (reuse, do not rebuild)

| Existing | Use |
|----------|-----|
| `POST /samples/receive` + 422 on non-empty `analysis_ids` | Frozen. P1 does not touch except regression tests. |
| `_create_tests_for_sample` (legacy accession / bulk) | **Do not call** from asked-for. |
| `tests_access` RLS via `samples.project_id` + FORCE (0064) | Mirror for `asked_for` / `work_orders`. |
| `require_project_for_receive` → **403** | Pattern for asked-for. Do **not** copy `require_accessible_sample` (404). |
| `require_test_assign` | P1 write AuthZ (OQ-AF-2). |
| `ELNProcessService.instantiate_from_definition` | P2 start. Existing `experiment:manage`. |
| `LimsRunService.start_run` | Cohort lock exists; **does not mint Tests today**. |
| `ResultPromotionService.ensure_test` | **Remove from publish** (A7). Landmine: `lims_run_service.py` “may create tests via ensure”; `plan_promotion` dry_run=False “ensure Test instances exist (used on publish)”. |
| `Test.custom_attributes` JSONB | Field Management. **Not** the params snapshot (A5). |
| `results.qualifiers` UUID → list_entries | Keep. SC1. Typed token → `reported_result`. |
| `sop_parse_jobs` Apply → ExperimentTemplate only | P4 must add process definition as success path. |
| `DataParsersManagement` / `InstrumentCatalogManagement` | P5 UX; no new import engine. |

---

## Nimble checklist

| Area | This packet |
|------|-------------|
| Entry kinds / write-back | N/A (not entries). |
| Cohort | Reuse `lims_runs.cohort` lock + process sample assign. No new cohort table. |
| Aliquot execute / dest type | Out. Extract-hold dest-type Hold unchanged (L5). |
| Multi-tenant / RLS | `asked_for` / `work_orders` via sample → project. Config tables admin/`config:edit`. FORCE RLS. Hidden sample → **403** (A1). |
| Migrations | P1: two tables. P2: routing + WO + type-eligibility + `tests.asked_for_params` + process FK. P4: job FK + step nullability. Rollback: DROP P1/P2 tables; drop added columns. |
| APIs | Spec paths OK. Auth: `test:assign` asked-for write; `config:edit` routing/param-defs/parsers; `experiment:manage` process start. Client: no write. |
| Failure modes | See below. |
| Tests | Named in Test expectations. |

---

## Conditions

| ID | Phase | Severity | Condition |
|----|-------|----------|-----------|
| **A1** | **P1** | Same-phase | **RLS-hidden sample/project → 403, never 404.** Mirror `atomic_receive_service.require_project_for_receive`. Do not reuse `sample_access.require_accessible_sample` (that helper 404s). Unknown UUID that does not exist **and** is not hidden may 404; cross-project miss is 403. Pytest: no project access → 403 (AC-P1-3). Client POST asked-for → 403. |
| **A2** | **P1** | Same-phase | **P1 migration is only `asked_for` + `analysis_param_defs`.** Unique `(analysis_id, key)` on param defs. `tat_days` check `> 0`. Partial unique `uq_asked_for_open`. Status check. FORCE RLS. Policy: USING/WITH CHECK via sample.project (mirror `tests_access`). Param-defs write: `config:edit` / admin. Rollback: DROP both tables. Do not create `routing_map` / `work_orders` in the P1 PR. |
| **A3** | **P1** | Same-phase | **Zero Tests, zero work_orders, zero processes on asked-for save.** Never call `_create_tests_for_sample` or any `_create_asked_for_tests`. Receive stays 422 on non-empty `analysis_ids`. Copy = L1. Multi-sample: one operator action; **one transaction** (`sample_ids[]` on POST or equivalent); unique 409 rolls back the batch — no partial rack. API may still persist one row per sample. |
| **A4** | **P2** | Blocks P2 | **Superseded in part (Leadership OQ-WO-4, 2026-08-28):** type eligibility is **not** `analysis_accepted_sample_types`. SoT: `eln_process_definition_step_accepted_sample_types (step_id, sample_type_id)` on **both** `eln_experiment` and `lims_run` steps. **Qubit is a LimsRun.** Empty set = fail closed on map save and on Route. Check: **current** sample type ∈ **every** step in the chain. Named error `route_sample_type` **422**. Do not read `sample_type_transitions`. Do not infer “an earlier extract will mint DNA.” Extract → Qubit keyed on blood **refuses**. No OOB blood→Qubit rows. Do not invent Qubit/blood testdata IDs. Still: CONFIG, not transitions. |
| **A5** | **P2** | Blocks P2 | **L3 params snapshot column.** Schema-changes `tests: none` is wrong. ADD `tests.asked_for_params jsonb not null default '{}'` (Sci CSO SC5). At **LimsRun start**, copy matching asked-for `params` (sample + run.analysis_id, status `routed`) and freeze. Do not merge into `tests.custom_attributes`. Later asked-for edits do not mutate a started Test. Empty defs → `{}` only. |
| **A6** | **P2** | Blocks P2 | **L4 WO snapshot is the work plan. OQ-WO-3 decided here.** SoT: ADD `eln_processes.work_order_id` uuid NULL FK (index). Every process instance in the chain points at the WO. `work_orders.process_id` if kept is **denorm of current only** — completing N and starting N+1 must not orphan N. `work_orders.asked_for_id` UNIQUE is the asked-for link; `asked_for.routed_work_order_id` is optional denorm set in the same txn (prefer drop reverse if insert-order bites). Start first definition via existing instantiate + process AuthZ. Completing process N **surfaces** start of N+1 from `process_definition_ids[i+1]` — no second routing hop, no first-only + route-next. Do not auto-instantiate N+1. `POST /work-orders/{id}/start` is first and next. Completed definition not in snapshot → 409. |
| **A7** | **P2** | Blocks P2 | **WO-7: mint Test at LimsRun start; no ensure-on-publish.** `start_run` inserts Test if no active `(sample_id, analysis_id)` (reuse classic Test if present). Publish: Test missing → **422**. **Delete** the ensure path: `ResultPromotionService.ensure_test` must not run from `plan_promotion` when `dry_run=False`. Promote may only attach results to an existing Test. Classic `POST /tests` remains (WO-4). |
| **A8** | **P2** (was P4) | Blocks P2 | **LimsRun steps need `analysis_id`.** Pulled into P2 because **Qubit is a LimsRun** (OQ-WO-4). ALTER `eln_process_definition_steps`: `experiment_template_id` nullable; ADD `analysis_id` uuid NULL FK `analyses`. CHECK: `eln_experiment` ⇒ template NOT NULL; `lims_run` ⇒ `analysis_id` NOT NULL. Same on instance steps if they snapshot the def. Apply never silent-activate remains L5/P4. No dest-type E2E in this packet. |
| **A9** | **P3** | Blocks P3 coding until SC fold | **Persist lock uses live columns.** Typed token → `reported_result`; `raw_result` may copy on the manual path; `qualifiers` stays UUID FK (NULL for a clean number). Do not migrate `qualifiers` to JSON. No `results.unit_id`. Missing numeric `units_default` → 422. Two writers → 409. Fold SC1–SC4 into RQ-RES-1 / AC-P3-1 / sketch before the P3 PR. Promote must not ensure-create Tests (A7). |
| **A10** | **P2 docs** | Before P2 PR | **Update schema-changes** with A4–A8 deltas, `CREATE EXTENSION IF NOT EXISTS btree_gist`, unique param-def key, rollback section, open-schema blockers (OQ-WO-3 closed by A6), and this review link. P1 PR may ship A2 without waiting for the P2 rows. |

---

## Failure modes

| Path | Failure | Handling | Test |
|------|---------|----------|------|
| Asked-for on hidden sample | Existence leak | **403** (A1) | pytest 403 |
| Duplicate open asked-for | Unique race | **409** | pytest 409 |
| Unknown / required param | Bad request | **422** | pytest 422 |
| Discarded sample | Not orderable | **422** | pytest |
| Multi-sample partial unique | Half rack | One txn; all-or-nothing 409 | pytest |
| Empty routing map | Fake work | 200, `work_order: null`, stay `requested` | pytest AC-P2-2 |
| TAT overlap on map save | Ambiguous route | **409** gist exclude | pytest |
| Qubit-on-blood / type miss | Assay on wrong matrix | **422 `route_sample_type`** | pytest AC-P2-3; assert no `sample_type_transitions` query |
| Empty accepted-types set | Unconfigured analysis | **422** fail closed | pytest |
| Publish without Test | WO-7 violation | **422**; no `ensure_test` | pytest; grep-guard optional |
| Two writers on Test | Classic vs promote | **409** | existing + P3 |
| Missing numeric `units_default` | Ununited number | **422**, no row | P3 |
| Chain start when N not in snapshot | Tamper / stale WO | **409** | P2 |
| Client writes asked-for / routing / parsers | AuthZ | **403** | pytest |
| Receive `analysis_ids` non-empty | CORE reopen | **422** | regression |

---

## Test expectations

Packet spine names (pytest, testcontainers, same style as `test_atomic_receive_phase1.py`):

**P1 — `backend/tests/test_asked_for.py`**

- Create asked-for → 201, `status=requested`, **tests count 0**, no work_orders
- Duplicate `(sample_id, analysis_id)` while open → 409
- Recreate after cancel → 201
- No project access → **403** (not 404)
- Missing `test:assign` → 403
- Client role POST → 403
- Unknown param key / missing required def → 422
- Empty defs: `params={}` OK; non-empty object → 422
- Discarded sample → 422
- Multi-sample one POST: N rows or all 409
- Receive non-empty `analysis_ids` still 422
- Asked-for does not call `_create_tests_for_sample`

**P2 — `backend/tests/test_work_orders.py`** (when P2 opens)

- Map match mints WO with ordered process ids; asked-for → `routed`
- Empty map: no WO
- Overlap save → 409
- Blood / unaccepted type → 422 `route_sample_type`; **no** `sample_type_transitions` in the route path
- LimsRun start inserts Test + freezes `asked_for_params`
- Publish with no Test → 422; `ensure_test` not invoked
- Complete process N → next definition from snapshot (no second route)

**P3** — persist_typed_result: `12.3` → `reported_result`; qualifiers NULL; missing units_default 422; no `unit_id` column

**P4** — Apply returns `process_definition_id`; template-only is not the success path; `active=false` until human save

**P5** — activate after dry-run pass; import path has no LLM call site

UAT script `UAT_Scripts/uat-post-receive-work-spine.md` at implement (P1 cases first). Do not use retired `uat-sample-accessioning.md`.

---

## NOT in scope

- Extract-hold dest type / blood → DNA daughter → Qubit E2E
- Inventing Qubit or whole-blood testdata IDs
- Intake-profile engine, wizard revival, analysis picker on `/receive`
- `projects` → orders rename; lots / registration (WO-5/6)
- Second execute engine; IC50 / dose-response
- `results.unit_id`; JSON `qualifiers`
- CMMS; user-uploaded executable parsers
- Hiding classic TestForm (WO-4 stays)

---

## Open questions (architecture)

| ID | This stamp |
|----|------------|
| **OQ-WO-3** | **Decided:** `eln_processes.work_order_id` is SoT (A6). |
| **OQ-WO-1** | Not blocking P1. Agree with Lab Ops: auto-route when a map row matches; else stay `requested`. Resolve before P2 UX. Explicit `POST .../route` remains for rows created while the map was empty. |
| **OQ-SOP-2** | Architecture default: yes, inactive parser draft; never bind to production runs. Security still Open — do not code the draft until Security stamps. |
| **OQ-RES-1** | Already **Decided** (Sci CSO). Architecture agrees (A9). |
| Watch | Open uniqueness is `(sample_id, analysis_id)` — two ELISA cell lines cannot coexist. Fine for P1 empty params. Revisit when required param defs ship. |

---

## Parallelization

Sequential by phase (one PR per phase). P5 may parallel P1 (OQ-IMP-1). P2 must not start until A4–A7 + A10 are in schema-changes.

Lane A: P1 asked-for. Lane B: P5 parser UX (no shared new tables). Merge. Then P2. Then P3 persist (may parallel P2 if Tests exist via classic or a later LimsRun). Then P4.

---

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (A1–A10) |
| **Date** | 2026-08-28 |
| **Schema-changes** | **Present** (P1 OK; update before P2/P4) |
| **P1** | **OPEN** — A1–A3 same-phase |
| **P2** | **CLOSED** until A4–A7 + A10 in schema-changes (L2 config SoT, L3 `tests.asked_for_params`, L4 chain FK, WO-7 no ensure-on-publish) |
| **P3** | Column-use only after SC1–SC4 fold (A9). No migration if columns stay as they are. |
| **P4** | Apply → process definition with A8 + L5. Dest-type Hold unchanged. |
| **P5** | **OPEN** (independent admin UX). |
| **Not licensed** | Dest-type execute · blood→DNA→Qubit E2E · Qubit/blood testdata IDs · minting Tests at asked-for or WO save · ensure-on-publish · type gate via `sample_type_transitions` |

```
ARCHITECTURE REVIEW: Accept with conditions
SCHEMA-CHANGES: present
IMPLEMENT GATE: OPEN (P1 only)
```
