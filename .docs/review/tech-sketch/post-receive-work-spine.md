# Tech sketch: Post-receive work spine

**Date:** 2026-08-28  
**Stem:** `post-receive-work-spine`  
**Status:** Architecture / UI / Spec **Accept with conditions** on `feat/work-order-p2` @ `8cfa2a9`. **Hold product merge to main.** Live AC-P2 **unsigned**. Do **not** claim freeze closed/verified. Punch (3) **open**: first Start must not mint later processes or their Tests. Route snapshots ordered `process_definition[]`, zero Tests. First Start = process[0] / `chain[0]` only; later Start = next process, on the sample that exists then. **Hans freeze open:** `if test: continue` is not a freeze, and **skip-on-`{}` is not a freeze until classic `/tests` leaves `asked_for_params` NULL or a freeze marker lands** — classic default `{}` and frozen `{}` are the same JSON. Extract must not share asked-for `analysis_id`. P2-4 still `0074`. `b005cfe` signed history: publish-refuse Pass, freeze OPEN then, AC-P2-5 chain-AND. Not IC50.
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
5. Architecture / UI / Spec **Accept with conditions** on P2 @ `8cfa2a9`. Hold merge until UAT. Not IC50.
6. **Receive freeze:** non-empty `analysis_ids` still **422**.
7. **P2 ordered route (Leadership / Heidi / Günter, unsigned on `8cfa2a9`):** a route is analysis + TAT + **ordered** `process_definition[]`. Route snapshots the list, **zero Tests**. First Start = process[0] / `chain[0]` only. Later Start = next process, on the sample that exists then. Punch (3) is **first Start minting later processes or their Tests**, not the list itself. Do not teach that mint as shipped.
8. **WO-7 publish (Tobias-signed Pass @ `b005cfe`):** `_require_wo7_tests` 422s before promote if any cohort sample lacks an active Test. `plan.errors` also 422s. Status stays unpublished (complete). Do **not** fold first-start freeze into this Pass.
9. **Hans freeze (still open; unsigned on `8cfa2a9` — not closed, not verified):** `if test: continue` is **not** a freeze. **Skip-on-`{}` is not a freeze until classic `/tests` leaves `asked_for_params` NULL or a freeze marker lands** — classic default `{}` and frozen `{}` are the same JSON, so `{}` cannot prove a first-start snapshot. Until then, first LimsRun start must **write**. Skip only on a provable LimsRun-start snapshot.
10. **P2-4 visibility:** Route is `test:assign` and must **read** the mapped def/steps (catalog-visible, same client / logged-in, like `routing_map`). Do **not** put `experiment:manage` on Route. **`0074`:** `is_admin() OR has_experiment_access()` is **not** catalog-visible. Mutate stays `config:edit`. Instantiate stays. **Still open** on `8cfa2a9`.
11. **No sample-type picker (unsigned until QA):** derive first Exp/LimsRun allow-list. `assert_chain_accepts_sample_type` is gone. Route: 0 hits **422**, two that accept **409**, live check vs first step of process[0]. Never `first()`. Map-save 409 when TAT **and** first-step allow-lists overlap. Denorm `sample_type_id` is display/sync only. Empty first-step allow-list fails closed at **start**, not map-save.
12. **Extract `analysis_id` (still open):** Extract LimsRun must **not** share the asked-for `analysis_id` or it attaches/freezes the panel Test at extract start.

---

## 1. Problem (technical)

Receive writes Sample + Containers + Contents. Nothing records the request. Classic `POST /tests` mints a Test, which collides with WO-7 (Test at LimsRun start). Work_order / routing tables do not exist. SOP Apply writes templates only. Parser engine exists; setup UX is the gap.

## 2. Architecture

```
UI /asked-for ──▶ asked_for (P1)
                      │
                      ▼  explicit Route (P2)
          analysis + TAT + ordered process_definition[]
             │ 0: 422 │ 2 accept current type: 409
             ▼ exactly 1
            work_order (snapshot the list, zero Tests)
                 │
                 ▼ First Start = process[0] only
         existing /v1/eln-processes
                 │
                 ▼ Later Start = next process, on the sample that exists then
         LimsRun start → Test (WO-7) for that process only
                 │
                 ▼
         results persist (P3)  or  parser import (P5) → publish
```

SOP Apply (P4) writes **process definitions** that routing_map points at.

No new execute runtime. No second AuthZ. No second workflow engine. First Start must not mint later processes or their Tests.

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

`routing_map`: analysis + TAT + **ordered** `process_definition[]`. No sample-type picker; derive first Exp/LimsRun allow-list of process[0]. Save **409**s when the same analysis, overlapping TAT, **and** overlapping first-step allow-lists all hold.

**OQ-WO-1 Decided:** Tech hits **Route**. No auto-route on asked-for save. `POST /api/v1/asked-for/{id}/route` (batch the same call for a selected set). Then:

- Select analysis + TAT candidates; filter by current type against process[0]’s first Exp/LimsRun step allow-list
- Zero acceptable rows → 422; two saved rows that both accept this current type → 409; exactly one **snapshots the ordered list** and mints **zero Tests**
- Never silently use `first()`
- Denorm `sample_type_id` is display/sync only — Route uses the live first-step list
- Empty first-step allow-list fails closed at **start**, not map-save

`work_orders.process_definition_ids` snapshot at mint (**L4**), **zero Tests**. Ordered list is the lock. Punch (3): **first Start must not mint later processes or their Tests** — do not teach that mint as shipped.

Start: `ELNProcessService.instantiate_from_definition` on **process[0] / `chain[0]` only**. Later Start = next pending process, on the sample that exists then. Instantiate stays `experiment:manage`. Route stays `test:assign`. Later process/step starts type-gate current type vs **that** step only. Dest-type Hold out.

**L3 / A5 / SC5 / Hans:** `if test: continue` is **not** a freeze. At LimsRun start for the asked-for analysis, insert the Test if missing and **write** `asked_for.params` → `tests.asked_for_params`. Classic `/tests` must leave `asked_for_params` **NULL**; NULL or default `{}` is **not** frozen. **Skip-on-`{}` is not a freeze** — classic default `{}` and frozen `{}` are the same JSON, so `{}` cannot prove a LimsRun-start snapshot. Skip is honest only once classic `/tests` leaves NULL or a **freeze marker** lands. Extract must **not** share the asked-for `analysis_id` or it attaches/freezes the panel Test at extract start. P1 does **not** write that Test snapshot. Do not claim freeze closed/verified on `8cfa2a9`.

WO-7 publish @ `b005cfe` is Tobias-signed Pass: `_require_wo7_tests` + `plan.errors` 422 the whole run. Status stays complete / unpublished. Zero Results. First-start freeze is **unsigned on `8cfa2a9`** — not closed, not verified. Overall P2 Pass is unsigned.

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
| Route with zero acceptable rows | **422**, no WO |
| Route with two saved rows that both accept current type | **409**, no silent `first()` |
| Map save, same analysis + overlapping TAT + overlapping first-step allow-lists | **409** |
| Map save, same analysis + overlapping TAT, disjoint first-step allow-lists | Save succeeds (extract-first vs Qubit-first) |
| First Start mints later processes or their Tests | Bounce — punch (3). Snapshot is the list only |
| Later Start | Next pending process, on the sample that exists then |
| Later step start with current type outside that step’s accepted types | **422 `route_sample_type`**; sample is not broken |
| Publish without Test | **422** the whole run (`_require_wo7_tests` / `plan.errors` @ `b005cfe`). Stay unpublished. Zero Results. Publish-refuse Pass is history. Freeze in code on `8cfa2a9`, unsigned until QA. |
| Invisible process def (`0074` `has_experiment_access`) | Catalog-visible **read**. Route stays `test:assign`. Not `experiment:manage` on Route. |
| Empty accepted set at step start | **422 `route_sample_type`** |
| Classic `/tests` default `{}` | Not a freeze — LimsRun start must still snapshot. Classic `/tests` must leave `asked_for_params` NULL |
| Skip-on-`{}` treated as a freeze | Bounce — classic default `{}` and frozen `{}` are the same JSON. Honest only after classic NULL or a freeze marker |
| Extract LimsRun shares asked-for `analysis_id` | Bounce |
| Parser AI on import | Impossible (no call site) |
| Receive non-empty `analysis_ids` | **422** (freeze) |

## 9. Delivery

| PR | Scope |
|----|--------|
| 1 | P1 tables + API + `/asked-for` UI + pytest + UAT script. **Hold merge until UAT.** |
| 2 | P2 routing + work_order + ordered `process_definition[]` + LimsRun WO-7. Architecture / UI / Spec Accept with conditions @ `8cfa2a9`. Live AC-P2 **unsigned**. **Hold product merge to main.** Punch (3) open: first Start must not mint later processes or Tests. Still open: Hans freeze (skip-on-`{}` is not a freeze), extract `analysis_id`, P2-4 `0074`. Freeze / Route 422/409 in code, not QA-clicked. |
| 3 | P3 persist lock + results UAT fold (**closed**) |
| 4 | P4 SOP Apply → process def (**closed**) |
| 5 | P5 parser setup UX (**closed** this cycle) |

Coding stays Grok Build. One phase per PR. Receive code freeze except bugs. Not IC50.
