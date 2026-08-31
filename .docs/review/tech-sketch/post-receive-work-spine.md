# Tech sketch: Post-receive work spine

**Date:** 2026-08-28  
**Stem:** `post-receive-work-spine`  
**Status:** Architecture / UI / Spec **C2 Fail** on `02fe95f` is signed history (Deiter click C1 **Pass**, dest mint Hold **Pass**). The dest-type split is **Leadership Confirmed** (Rolf / Deiter / Hans / Heidi / Günter). Live product SHA **`570bbc0`**: AC-P2-C2 is **same-type dest-follow only**, AC-P2-C3 is the different-dest-type click, and both remain **unsigned** until Tobias. `1572071` is the dest-follow execute-txn implementation SHA, not the live click SHA. Same dest type = same sample, additional container; `_follow_destination_in_process` may retarget `container_id` only on that path. Different dest type = new derivative Sample in a new container (`parent_sample_id`); the parent **Sample row** stays with its original type, Tests, and parent-type work. Type-changing execute mints and joins the destination pair on `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction; only that destination pair continues on the process. Route / Start / map-save mint zero daughters. Dest mint Hold is lifted only for type-changing execute. **Hold product merge.** Do not write C2 or C3 Pass, rewrite the parent `sample_type`, or retarget the parent Sample onto a type-changing destination. C2 and C3 / extract-hold UAT 1.7 remain two clicks. PATCH is not a path. OQ-WO-6 and freeze skip stay OPEN. Route stays `test:assign`. Signed AC-P2-9..11: `9342439`; its Dest-type mint Hold is Start-extract Blood / **0 DNA** history, not a live ban. Overall P2 unsigned. Not IC50.
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
7. **P2 ordered route (AC-P2-9..11 Pass on `9342439`; prior signed on `8cfa2a9`):** Route snapshots the ordered list, **zero Tests**. First Start = process[0] / `chain[0]` only — **Tobias-signed Pass**. Empty Route **422** Pass. Later-step type-gate **Met** on `9342439`. Deiter `0077` click at `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. Live dest-follow on `570bbc0` is **unsigned** until Tobias (implementation landed on `1572071`). Do not teach dest-follow as shipped.
8. **WO-7 publish (Tobias-signed Pass @ `8cfa2a9` and history @ `b005cfe`):** `_require_wo7_tests` 422s before promote if any cohort sample lacks an active Test. Status stays unpublished (complete). Do **not** fold first-start freeze into this Pass.
9. **Hans freeze (classic skip still OPEN / unsigned on `8cfa2a9`):** `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until then `{}` is **ambiguous**. Do **not** teach skip-on-frozen-`{}`. **OQ-WO-6:** earlier LimsRun must **not** share asked-for `analysis_id` (extract is not a special assay).
10. **P2-4 visibility:** Route is `test:assign` and must **read** the mapped def/steps. Do **not** put `experiment:manage` on Route. **`0074` still open** on `8cfa2a9`. Mutate stays `config:edit`.
11. **No sample-type picker (Tobias-signed Pass on `8cfa2a9` — UI click-save):** ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved (no AND 422); second ELISA overlap **409**. Empty Route **422** Pass. Two-accept **409** unsigned that SHA.
12. **Earlier LimsRun `analysis_id` (OQ-WO-6 stays OPEN — Leadership Confirm R2-3):** Earlier LimsRun must **not** share asked-for `analysis_id`. Do not teach extract-as-special-assay. Type gates catch blood-on-Qubit. Any earlier LimsRun that reuses the asked-for analysis freezes the panel Test on the parent.
13. **After `8cfa2a9` (Round 1 Leadership Confirm; Round 2 Leadership Confirm R2-1…R2-4):** no map analysis picker. A route **may have multiple analyses**. Asked-for → any chain that **contains** that LimsRun analysis. Map 409 = TAT ∩ first-step types ∩ analysis **sets**. Map 422 handoff is **map-save only**. Dest mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. Parser at import. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md).
14. **C2 Fail on `02fe95f` (Deiter click; Leadership Confirm) — signed history:** C1 **Pass**. C2 **Fail** — C1/C2 **not** unsigned. Execute minted dest (`_execute_transfer` always inserts a new Sample) and never wrote the same-sample dest container onto `eln_process_samples`. `_join_minted_destination` and `_release_source_from_process` both **no-op** unless `entry.process_step_id` is set. Later Start via `_continuing_assignments` then rode that emptied parent. Emptied-source assign **201** is leftover Contents at amount 0 / leftover process-join — **not** dest-follow. **PATCH is not a path.** Dest mint Hold **Pass** is a different punch (still Blood, **0 DNA**; a new Sample with `dest_sample_type` is **not** this C2 fix). Hold merge. Not IC50.
15. **Leadership Confirm — dest-type split; live `570bbc0` C2 and C3 remain unsigned until Tobias (`1572071` is the execute-txn implementation SHA):** same dest type = same sample, additional container; `_follow_destination_in_process` may retarget `container_id` only on that path. Emptied-source assign is **422** and later Start follows that dest container. Different dest type = new derivative Sample in a new container (`parent_sample_id`); only the parent Sample row stays, preserving its original type, Tests, and parent-type work. Type-changing execute mints and joins the destination pair and marks the inbound source assignment `removed` in the execute transaction; only the destination pair remains on this chain. Route / Start / map-save mint zero daughters. Dest mint Hold is lifted only for type-changing execute. C2 and C3 / extract-hold UAT 1.7 remain two clicks. Test identity stays `(sample, analysis)`. In code since `1572071`; not QA-clicked on `570bbc0`. Do not write C2 or C3 Pass or teach type-changing dest as parent `container_id` retarget.

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
                 ▼ Target Later Start = next process, dest container-with-sample
                    (lock on `570bbc0`, unsigned until Tobias;
                     C2 Fail history on `02fe95f`: dest not joined,
                     source not removed, emptied-source 201)
         LimsRun start → Test (WO-7) for that process only
                 │
                 ▼
         results persist (P3)  or  parser import (P5) → publish
```

SOP Apply (P4) writes **process definitions** that routing_map points at.

No new execute runtime. No second AuthZ. No second workflow engine. First Start must not mint later processes or their Tests. Dest mint (new DNA Sample) is **not** the P2 follow. PATCH of process samples is not a path.

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

`routing_map`: TAT + ordered `process_definition_ids`. No analysis or sample-type picker. Do **not** gist-exclude on analysis+TAT. Save **409**s when overlapping TAT, overlapping first-step allow-lists, **and** overlapping LIMS Run analyses in the chains all hold. (`8cfa2a9` UAT scored analysis+TAT map rows; that SHA remains signed history.)

**OQ-WO-1 Decided:** Tech hits **Route**. No auto-route on asked-for save. `POST /api/v1/asked-for/{id}/route` (batch the same call for a selected set). Then:

- Select TAT candidates; keep a row when current type is on the first process / first ordered Experiment-LimsRun list **and** the asked-for analysis is **among** the LimsRun analyses in that route (a route may have several)
- Zero acceptable rows → 422; two saved rows that both accept this type and this analysis → 409; exactly one snapshots its ordered `process_definition[]` and mints **zero Tests**
- Never silently use `first()`
- Denorm `sample_type_id` is display/sync only — Route uses the live first-step list
- Prefer deriving first-process types, chain LIMS Run analyses, and emerging types on read
- Map save/Route do not AND inbound sample types across later processes or steps. Map save **422**s when the type emerging from process *x* is not accepted by process *x+1* (aliquot/pool dest on *x* last Experiment/LIMS Run if set; else last-step accepted types). Route / Start / map-save mint **zero** daughters. Dest-type mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history; Hold lifts for type-changing aliquot/pool execute only.

`work_orders.process_definition_ids` snapshot at mint (**L4**), **zero Tests**. Ordered list is the lock. Punch (3): **first Start must not mint later processes or their Tests** — do not teach that mint as shipped.

Start: `ELNProcessService.instantiate_from_definition` on **process[0] / `chain[0]` only**. Assignment is a Contents pair: `container_id` NOT NULL (`0077`). Deiter C1 **Pass** and C2 **Fail** on `02fe95f` are signed history. Live C2 on **`570bbc0`** is same-type only: `_follow_destination_in_process` follows the same sample into its additional container; emptied-source assign **422**; later Start follows that dest container. Live **C3** on `570bbc0` is the different-dest-type click: execute mints a new derivative Sample with `parent_sample_id` in a new container. The parent Sample row stays with its original type; its inbound process assignment is `removed`. In either path, execute writes the destination Contents pair to `eln_process_samples` in the same transaction. **PATCH is not a path.** Instantiate stays `experiment:manage`. Route stays `test:assign`.

**Dest mint Hold history (Deiter Pass, distinct from C2):** on `02fe95f`, Start extract remained Blood / 0 DNA. That signed Result is not a ban on type-changing execute. The Hold is lifted only for type-changing execute, which inserts a new derivative Sample with `parent_sample_id`; the parent Sample row stays for lineage while the destination pair replaces the inbound source assignment on the process. C2 remains same-type dest-follow only.

**L3 / A5 / SC5 / Hans:** `if test: continue` is **not** a freeze. At LimsRun start for the asked-for analysis, insert the Test if missing and **write** `asked_for.params` → `tests.asked_for_params`. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, `{}` is **ambiguous**. Do **not** teach skip-on-frozen-`{}`. **OQ-WO-6:** any earlier LimsRun must **not** reuse the asked-for `analysis_id` (extract is not special; type gates are a different axis). P1 does **not** write that Test snapshot. Freeze skip stays unsigned.

WO-7 publish @ `8cfa2a9` is Tobias-signed Pass (carol **422** `test_missing`) and remains history @ `b005cfe`: `_require_wo7_tests` + `plan.errors` 422 the whole run. Status stays complete / unpublished. Zero Results. A write of `{}` onto `99b692d3` is not a freeze-skip Pass (`{}` is ambiguous). Freeze skip **unsigned**. Overall P2 Pass is unsigned.

## 5. P3 design

Single function `persist_typed_result(test, analyte, value)` used by UI results table and any manual LimsRun entry.

No `results.unit_id`. Typed token → `reported_result` as-is (no float roundtrip). `qualifiers` remains **UUID FK** (SC1); NULL if none. Missing `units_default` → 422 for numeric quantities (SC3). Text/boolean exempt.

## 6. P4 design

`SopParseApplyService`: map extracted steps → `eln_process_definition_steps`. Experiment steps keep `experiment_template_id` (create template as today, then attach). LimsRun steps store `analysis_id` if parsed.

**L5:** Apply writes a process definition. It does **not** stamp type-changing execute. No blood → DNA → Qubit UAT in this packet; that path remains OOB and unsigned here.

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
| Assign omit container / 0 vessels / 2+ without a pick | **422** `process_container_required`, lab-readable. C1 **Pass**. |
| Emptied-source assign (Contents amount 0) | **422** — lock on `570bbc0`, **unsigned**; leftover 201 is C2 Fail history |
| Execute does not join dest / remove inbound in the same txn | **C2 Fail history** on `02fe95f`. Live lock on `570bbc0`: follow in execute txn (implementation `1572071`); **unsigned**. PATCH is not a path |
| Join / release no-op without `entry.process_step_id` | Bounce on `02fe95f`. Live follow does not require `entry.process_step_id` (`570bbc0`, unsigned) |
| Later Start follows inbound parent / emptied source | Bounce — live lock on `570bbc0` is dest container, **unsigned** |
| Type-changing execute | Mint new derivative Sample + new container with `parent_sample_id`; preserve the parent Sample row and original type; put the destination pair on the process and mark the inbound source assignment `removed`. Dest mint Hold lifted only for this path |
| Later Start | Target is next process on dest container (lock on `570bbc0`, **unsigned**). C2 **Fail** on `02fe95f` is signed history |
| Later step start with current type outside that step’s accepted types | **422 `route_sample_type`**; sample is not broken. **Unsigned on `8cfa2a9`** — not click-run |
| Publish without Test | **422** the whole run (`_require_wo7_tests` / `plan.errors`). Stay unpublished. Zero Results. Publish-refuse **Pass** on `8cfa2a9` and history on `b005cfe`. Freeze skip unsigned: `{}` on `99b692d3` is ambiguous, not a skip Pass. |
| Invisible process def (`0074` `has_experiment_access`) | Catalog-visible **read**. Route stays `test:assign`. Not `experiment:manage` on Route. |
| Empty accepted set at step start | **422 `route_sample_type`** |
| Classic `/tests` default `{}` | Not a freeze — LimsRun start must still snapshot. Classic `/tests` must leave `asked_for_params` NULL |
| Skip-on-frozen-`{}` treated as a freeze | Bounce — classic default `{}` and frozen `{}` are the same JSON. `{}` is ambiguous until classic NULL or a freeze marker |
| Earlier LimsRun shares asked-for `analysis_id` (OQ-WO-6) | Bounce — extract is not a special assay |
| Parser AI on import | Impossible (no call site) |
| Receive non-empty `analysis_ids` | **422** (freeze) |

## 9. Delivery

| PR | Scope |
|----|--------|
| 1 | P1 tables + API + `/asked-for` UI + pytest + UAT script. **Hold merge until UAT.** |
| 2 | P2 routing + work_order + ordered `process_definition[]` + LimsRun WO-7 + 0077 assignment. Signed AC-P2-9..11 `9342439`. Deiter click at `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** (Start-extract Blood / 0 DNA history, not a live ban). Live SHA **`570bbc0`**: same-type dest-follow in code since `1572071`; AC-P2-C2 and AC-P2-C3 **unsigned**. Type-changing execute mints a derivative Sample with `parent_sample_id`; the parent Sample row stays and the inbound process assignment is `removed`. Overall P2 **unsigned / not Pass**. **Hold product merge to main.** Still open: Tobias C2 + C3 clicks, Hans freeze, **OQ-WO-6**, P2-4 `0074`. |
| 3 | P3 persist lock + results UAT fold (**closed**) |
| 4 | P4 SOP Apply → process def (**closed**) |
| 5 | P5 parser setup UX (**closed** this cycle) |

Coding stays Grok Build. One phase per PR. Receive code freeze except bugs. Not IC50.
