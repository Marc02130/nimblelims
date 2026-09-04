# Tech sketch: Post-receive work spine

**Date:** 2026-08-28  
**Stem:** `post-receive-work-spine`  
**Status:** Architecture / UI / Spec **C2 Fail** on `02fe95f` is signed history (Deiter click C1 **Pass**, dest mint Hold **Pass**); do not rewrite it. On live SHA **`570bbc0`**, Deiter’s C1/C2/C3 execute click is **Met for Lab Ops identity only**: same-type plate, DNA new Sample, and Later Start following the destination. It is not Tobias QA Pass. Dest-follow execute joints remain **`1572071`** and have no Tobias Result; Tobias’s QA restamp remains unsigned until Results land on the same numbered ACs. **Leadership Confirmed** (Rolf / Deiter / Hans / Heidi / Günter): C2 is same sample + additional container; C3 is new derivative Sample + container with `parent_sample_id`, while parent stays Blood. No destination at Route/Start/map-save is intended. Receive often leaves Contents amount NULL; set a tracked amount so execute can transfer, and treat 400 `source_amount_null` as fixture setup. Emptying is not required. DNA scored as C2 is the wrong AC. `9342439` Hold is Start-extract Blood / 0 DNA history, not a ban on C3. P2 on `main` (`5040f2d`). **OQ-WO-7 Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Freeze skip NULL **Pass** on `bf51b19`. Route two-accept 409 **Pass** on `bf51b19`. **OQ-WO-6 for extract CLOSED** (Leadership Confirm 2026-08-31). Closeout **1.4 / OQ-WO-8** is **Closed** (**Full Leadership Confirm**; Quantified DNA; Qubit is the asked-for LimsRun; named asked-for LimsRun slot, not contains-Qubit). No overall P2 Pass. Not IC50.  
**Leadership Confirm (2026-08-31, Rolf / Deiter / Hans / Heidi / Günter):** extract is a **process** (not a LimsRun; no asked-for `analysis_id`); exactly **one** LimsRun in the route has the asked-for `analysis_id` (assay step); extract (process) and Qubit (supporting LimsRun) may sit in the chain; map-save / Route **422** if asked-for count among LimsRuns is 0 or 2+; two ELISA LimsRuns refused. Hans’s 1-count-on-extract freeze punch is closed. Keep: one asked-for per process instance; **no route branching** — WGS asked-for on blood owns WGS params (extract → seq); C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up (own params); freeze skip OPEN. Do not rewrite `9342439`. Tobias C2/C3 unsigned. Hold merge. Not IC50.
**Leadership Confirm (Rolf, Marc, 2026-08-31):** Qubit / Nanodrop / etc. are supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …). Sequencing is an example, not the only case. Other `analysis_id`s, own Tests, own params freeze. Asked-for analysis appears **once**, on the assay LimsRun. Extract stays a process. Do not invent a second asked-for for QC. Do not put Nanodrop on extract.
**Full Leadership Confirm #2 (2026-09-03, Rolf / Deiter / Hans / Heidi / Günter):** Keep no route branching and asked-for only (PR 111). WGS on blood owns WGS params; C3 DNA and a C2 aliquot continue WGS; WES is a new asked-for on the DNA tube. Seq-1 Pass is not this Confirm. The zero-LimsRun Extracted DNA clause is struck. OQ-WO-8 remains Closed history from PR 119; named-slot product code and the 2+ route picker remain outstanding. This Confirm is not overall P2 Pass and does not recode OQ-WO-7.
**Leadership Confirm (2026-09-01, Rolf / Deiter / Hans / Heidi / Günter):** **ELISA is not on DNA** (wrong matrix) — do not hang ELISA on the DNA dest after C3. Same blood Sample **second tube (Contents)** may carry its **own asked-for and route**; two blood tubes → two process assignments (`container_id`); ELISA route and WGS/extract stay apart. Do **not** teach “extract can never be a LimsRun” as a forever ban (Hans: do not hang asked-for assay `analysis_id` on extract). **Extracted DNA asked-for can have Qubit/Nanodrop**; extract-as-instrument LimsRun is later. **OQ-WO-6 still:** asked-for `analysis_id` once on the assay LimsRun, not extract. **OQ-WO-7 stays OPEN:** blood WGS → C3 DNA → WGS start freezes `{library_kit: …}`, not `{}` / not Qubit params. Standing UAT rule: after two attempts on the same issue, next click needs written “what we are testing and why.” Not IC50. Do not rewrite `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f` / Deiter `570bbc0` Lab Ops Met.
**Science (2026-09-01):** Per-AC on `bf51b19` Pass. Overall P2 stayed unsigned. Merged (`5040f2d`) with **OQ-WO-7 OPEN**. Leftover **`9f86d14`** on **`80f054b` is** the Grok Build work. **Do not recode.** Remaining work is **Tobias**. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. Do not invent Tobias Pass. Not IC50.
**CEO Accept (Rolf, 2026-09-01):** Accept Hans’s written what/why as **AC-P2-OQ-WO-7** before Tobias. “Grok Build codes first” is **done** (`9f86d14` on `80f054b`). Remaining work is **Tobias**. Result unsigned. OQ-WO-7 stays **OPEN / AC unsigned** until Tobias stamps. Do not rewrite `bf51b19`. Not IC50.
**Tobias Result (2026-09-01):** **AC-P2-OQ-WO-7 Pass** on `80f054b`. Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** (WO asked-for same `analysis_id`, else parent lineage, else `{}`) **was not recoded.** **OQ-WO-7 Closed.** Overall P2 unsigned. Older OPEN walls above are history — do not restamp. Do not rewrite `bf51b19`. Not IC50.
**CEO Confirm 1–6 (Rolf, 2026-09-02) — closeout 1.4 / OQ-WO-8 (1–6 stands):** Quantified DNA is an assay ask (data); Qubit is the asked-for LimsRun (exactly one). Wear existing Qubit `analysis_id`; do **not** mint a second catalog analysis named Quantified DNA. Test `(DNA, Qubit)` is the ask. Other QC may sit (own analysis_id / Test). Extract stays experiment; no boolean Result. Old 1.4 (zero LimsRuns) **struck**. **422 on 0 LimsRuns is right.** WGS/WES/ELISA: Qubit stays process QC. Tube-only DNA later SKU. Named asked-for LimsRun slot was a punch pending Leadership Confirm on that fold (not part of 1–6).
**Full Leadership Confirm (2026-09-02, Rolf / Deiter / Hans / Heidi / Günter) — OQ-WO-8 Closed:** Named-slot is no longer pending. Map / Route **names the asked-for LimsRun slot**. Eligibility is `asked.analysis_id` vs **that slot**, not “any chain that contains Qubit.” A WGS map with Qubit as process QC must **not** steal a Quantified DNA ask (409 / wrong join). Same OQ-WO-7 lookup after C3; **do not recode.** No product code in this fold. Product code may start after this fold is on `main`. Not IC50. Send: [2026-09-01-p2-closeout-1-4-quantified-dna](../../discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md).
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
7. **P2 ordered route (AC-P2-9..11 Pass on `9342439`; prior signed on `8cfa2a9`):** Route snapshots the ordered list, **zero Tests**. First Start = process[0] / `chain[0]` only — **Tobias-signed Pass**. Empty Route **422** Pass. Later-step type-gate **Met** on `9342439`. Deiter `0077` click at `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. On live `570bbc0`, Deiter C1/C2/C3 execute is **Lab Ops Met**, not QA Pass; joints remain `1572071`. Tobias QA restamp has no execute Result yet.
8. **WO-7 publish (Tobias-signed Pass @ `8cfa2a9` and history @ `b005cfe`):** `_require_wo7_tests` 422s before promote if any cohort sample lacks an active Test. Status stays unpublished (complete). Do **not** fold first-start freeze into this Pass.
9. **Hans freeze (classic skip still OPEN / unsigned on `8cfa2a9`):** Freeze is **per Test** `(sample, analysis)`. First LimsRun start writes `asked_for_params`. Later start does **not** overwrite — including frozen `{}`. NULL = not frozen yet. `{}` after first start = locked empty. `if test: continue` is **not** a freeze. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Do **not** close freeze skip. Do **not** teach skip-on-`{}` as shipped. **OQ-WO-6 for extract is CLOSED** (Leadership Confirm 2026-08-31) — freeze skip stays OPEN separately.
10. **P2-4 visibility:** Route is `test:assign` and must **read** the mapped def/steps. Do **not** put `experiment:manage` on Route. **`0074` still open** on `8cfa2a9`. Mutate stays `config:edit`.
11. **No sample-type picker (Tobias-signed Pass on `8cfa2a9` — UI click-save):** ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved (no AND 422); second ELISA overlap **409**. Empty Route **422** Pass. Two-accept **409** unsigned that SHA.
12. **OQ-WO-6 extract punch CLOSED — Leadership Confirm (2026-08-31, Rolf/Deiter/Hans/Heidi/Günter):** Extract is a **process** (experiment / aliquot-pool execute; derivative dest), not a LimsRun. No asked-for `analysis_id` on extract. Cardinality 1 cannot land on extract. Extract cannot wear ELISA. Hans’s 1-count-on-extract freeze punch is **closed**. Strike “extract LimsRun must not share asked-for `analysis_id`.” Exactly **one** LimsRun in the route has the asked-for `analysis_id` — that LimsRun is the **assay step**. Extract (process) and Qubit (supporting LimsRun, own Test) may sit in the chain. Qubit / Nanodrop are supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …; own params freeze). Map-save / Route **422** if asked-for analysis appears 0 or 2+ times among LimsRuns. Two ELISA LimsRuns refused. Type gates catch blood-on-Qubit. Supporting QC = other LimsRun analyses, own Tests — not a second asked-for on the same process. Round 2 R2-3 “stays Open” is history. Freeze skip stays OPEN. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md).
13. **After `8cfa2a9` (Round 1 Leadership Confirm; Round 2 Leadership Confirm R2-1…R2-4):** no map analysis picker. A route **may have multiple analyses**. Asked-for → any chain that **contains** that LimsRun analysis. Map 409 = TAT ∩ first-step types ∩ analysis **sets**. Map 422 handoff is **map-save only**. Dest mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. Parser at import. Send: [2026-08-30-p2-route-lock](../../discussions/2026-08-30-p2-route-lock.md).
14. **C2 Fail on `02fe95f` (Deiter click; Leadership Confirm) — signed history:** C1 **Pass**. C2 **Fail** — C1/C2 **not** unsigned. Execute minted dest (`_execute_transfer` always inserts a new Sample) and never wrote the same-sample dest container onto `eln_process_samples`. `_join_minted_destination` and `_release_source_from_process` both **no-op** unless `entry.process_step_id` is set. Later Start via `_continuing_assignments` then rode that emptied parent. Emptied-source assign **201** is leftover Contents at amount 0 / leftover process-join — **not** dest-follow. **PATCH is not a path.** Dest mint Hold **Pass** is a different punch (still Blood, **0 DNA**; a new Sample with `dest_sample_type` is **not** this C2 fix). Hold merge. Not IC50.
15. **Leadership Confirm — two grains at execute (Rolf / Deiter / Hans / Heidi / Günter):** C2 same dest type = same sample, additional container, destination active, inbound assignment `removed` even with leftover volume, Later Start follows destination. Emptying is not required; amount 0 **422** is an edge, not the AC. C3 DNA = new derivative Sample + container (`parent_sample_id`), parent stays Blood, destination pair only active, Later Start follows DNA. No destination at Route/Start/map-save is intended, not a dest-follow failure. DNA scored as C2 is the wrong AC. Receive often leaves Contents amount NULL; set a tracked amount so execute can transfer. 400 `source_amount_null` is fixture setup, not dest-follow Fail. Deiter’s `570bbc0` C1/C2/C3 execute is **Lab Ops Met**, not Tobias QA Pass. Execute joints remain `1572071`; Tobias restamps the same numbered ACs and has no Result yet. Hold history is not a ban on C3.
16. **Marc lock (2026-08-31) kept; OQ-WO-6 extract overwritten by Leadership Confirm; “join many WOs” overwritten by sequential asked-fors:** One asked-for per process instance. Supporting QC = other analyses, own Tests (Qubit is a supporting LimsRun). **No route branching this phase.** Route **blood** for WGS (extraction → sequencing); that asked-for **owns WGS params**. C3 execute mints DNA. A **C2 aliquot** of that DNA continues the WGS WO. **WES is a new asked-for on the DNA tube** (owns WES params); that tube is then **aliquoted or used up**. Two asked-fors, two param snapshots, two WOs. Do not teach dest auto-joining a second WO. Do not copy WGS params onto WES. Freeze per Test: first start writes; later start does not overwrite including frozen `{}`; skip-on-`{}` OPEN. **OQ-WO-6 for extract CLOSED.** Click SHA C2/C3 remains `570bbc0`. `9342439` / `02fe95f` untouched. Tobias C2/C3 unsigned. Hold merge. Not IC50.

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
                    (joints `1572071`; Deiter `570bbc0` Lab Ops Met;
                     Tobias QA restamp unsigned;
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

`routing_map`: TAT + ordered `process_definition_ids` + a persisted **named asked-for LimsRun slot**. No sample-type picker. Prefer a FK from `routing_map` to the selected `eln_process_definition_steps` LimsRun. If the implementation instead persists `routing_map.analysis_id`, it must be the author-named ask and must stop deriving from `analyses[0]`. Map-save validates that the named slot belongs to the route and that its analysis appears exactly once among route LimsRuns; 0 or 2+ → **422**.

**OQ-WO-1 Decided:** Tech hits **Route**. No auto-route on asked-for save. `POST /api/v1/asked-for/{id}/route` (batch the same call for a selected set). Then:

- Select TAT candidates; keep a row when current type is on the first process / first ordered Experiment-LimsRun list **and** `asked.analysis_id` equals the persisted named slot’s `analysis_id`. Do not use chain containment. Qubit may be process QC on WGS without making that WGS map eligible for a Quantified DNA ask.
- Zero acceptable rows → 422; exactly one snapshots its ordered `process_definition[]` and mints **zero Tests**; 2+ returns route candidates for manual assignment and mints nothing until the tech posts one chosen `routing_map_id`.
- Never silently use `first()`
- Denorm `sample_type_id` is display/sync only — Route uses the live first-step list
- Prefer deriving first-process types, chain LIMS Run analyses, and emerging types on read
- Map save/Route do not AND inbound sample types across later processes or steps. Map save **422**s when the type emerging from process *x* is not accepted by process *x+1* (aliquot/pool dest on *x* last Experiment/LIMS Run if set; else last-step accepted types). That dest type is **catalog intent** until execute. Route / Start / map-save / asked-for mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint. Dest exists only after aliquot/pool execute. Dest-type mint Hold on `9342439` / `02fe95f` is Start-extract still Blood / **0 DNA** history; Hold lifts for type-changing aliquot/pool execute only.

`work_orders.process_definition_ids` snapshot at mint (**L4**), **zero Tests**. Ordered list is the lock. Punch (3): **first Start must not mint later processes or their Tests** — do not teach that mint as shipped.

Start: `ELNProcessService.instantiate_from_definition` on **process[0] / `chain[0]` only**. Assignment is a Contents pair: `container_id` NOT NULL (`0077`). Deiter C1 **Pass** and C2 **Fail** on `02fe95f` are signed history. On `570bbc0`, Deiter’s C1/C2/C3 execute click is **Lab Ops Met**, not Tobias QA Pass; Tobias restamp remains unsigned. C2 on joints `1572071` is same-type only: `_follow_destination_in_process` follows the same sample into its additional container; inbound assignment `removed` even with leftover volume; Later Start follows that destination. Emptying is not required; amount 0 **422** is an edge. C3 on `1572071` mints a new derivative Sample with `parent_sample_id` in a new container; parent stays Blood, its inbound assignment is removed, and Later Start follows DNA. In either path, only the destination pair remains active after execute. Receive amount often starts NULL, so numbered fixture setup sets a tracked amount so execute can transfer; 400 `source_amount_null` is not dest-follow Fail. **PATCH of `eln_process_samples` is not a path.**

**Dest mint Hold history (Deiter Pass, distinct from C2):** on `02fe95f`, Start extract remained Blood / 0 DNA. That signed Result is not a ban on type-changing execute. The Hold is lifted only for type-changing execute, which inserts a new derivative Sample with `parent_sample_id`; the parent Sample row stays for lineage while the destination pair replaces the inbound source assignment on the process. C2 remains same-type dest-follow only.

**L3 / A5 / SC5 / Hans:** Freeze is **per Test** `(sample, analysis)`. First LimsRun start writes `asked_for.params` → `tests.asked_for_params`. Later start does **not** overwrite — including frozen `{}`. NULL = not frozen yet. `{}` after first start = locked empty. `if test: continue` is **not** a freeze. Classic `/tests` default `{}` makes skip-on-`{}` **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Do **not** close freeze skip. Do **not** teach skip-on-`{}` as shipped. **OQ-WO-6 for extract CLOSED** (Leadership Confirm): extract is a process, not a LimsRun; exactly one asked-for LimsRun is the assay step. P1 does **not** write that Test snapshot. Freeze skip stays unsigned.

A process instance is bound to **one** asked-for row. Qubit / Nanodrop / etc. are supporting LimsRuns in the **same route as whatever the asked-for assay is** (ELISA, NGS, Qubit-as-asked-for, sequencing, …) — other `analysis_id`s, own Tests, own params freeze — not a second asked-for, not on extract. Extract is a **process** and has no asked-for `analysis_id`. Type-changing execute mints the DNA Sample **once**. **No route branching:** C2 aliquot of that DNA continues WGS; **WES is a new asked-for on the DNA tube**, which is then **aliquoted or used up**. Do not teach dest auto-joining a second WO.

### 4.1 Heidi architecture file map — named-slot build (not implemented in this fold)

**Hole today:** `_acceptable_maps` in `backend/app/services/routing_service.py` retains a map when `_asked_for_lims_run_count(chain, analysis_id) == 1`. That is containment anywhere in the chain, so WGS with Qubit as process QC can steal a Quantified DNA ask.

**Build shape:**

- Persist the author-named slot on `routing_map`; prefer the specific assay `eln_process_definition_steps` LimsRun FK, with author-named `routing_map.analysis_id` as the fallback design.
- Keep map-save 422 when the named slot analysis occurs 0 or 2+ times among route LimsRuns.
- Match Route eligibility to the named slot’s `analysis_id`.
- Return 0/1/2+ outcomes explicitly. For 2+, expose candidates and accept a chosen `routing_map_id`; do not silently select the first row.

**Touch in the product slice:**

- `backend/app/services/routing_service.py`: `create_map`, update, `_acceptable_maps`, and chosen-map assignment.
- `backend/models/work_order.py` plus Alembic only if a new persisted column/FK is selected.
- Routing schemas and the `work_orders` router.
- `frontend/src/pages/admin/RoutingMapManagement.tsx`: map author names the asked-for slot.
- `frontend/src/pages/AskedFor.tsx` and the API service: show the 2+ picker; one candidate remains one-click Route; post the chosen `routing_map_id`.
- `backend/tests/test_work_order_p2.py` and the matching UI test.

**Do not touch:** `lims_run_service` OQ-WO-7 lookup, destination follow, freeze skip, cardinality beyond named-slot validation, a second Quantified DNA analysis, or extract-as-LimsRun.

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
| Route with two or more named-slot-matching rows | Return candidates; require manual assignment by chosen `routing_map_id`; mint nothing before selection |
| Map save, same analysis + overlapping TAT + overlapping first-step allow-lists | **409** |
| Map save, same analysis + overlapping TAT, disjoint first-step allow-lists | Save succeeds (extract-first vs Qubit-first) |
| First Start mints later processes or their Tests | Bounce — punch (3). Snapshot is the list only |
| Assign omit container / 0 vessels / 2+ without a pick | **422** `process_container_required`, lab-readable. C1 **Pass**. |
| Emptied-source assign (Contents amount 0) | **422** on `1572071`; Deiter `570bbc0` Lab Ops Met, Tobias QA restamp unsigned; leftover 201 is C2 Fail history |
| Execute does not join dest / remove inbound in the same txn | **C2 Fail history** on `02fe95f`. On `570bbc0`, follow in execute txn is Lab Ops Met; Tobias restamp unsigned. PATCH is not a path |
| Join / release no-op without `entry.process_step_id` | Bounce on `02fe95f`. Live follow on joints `1572071` does not require `entry.process_step_id`; Deiter Lab Ops Met, Tobias restamp unsigned |
| Later Start follows inbound parent / emptied source | Bounce — destination follow is Deiter `570bbc0` Lab Ops Met; Tobias QA restamp unsigned |
| Type-changing execute | Mint new derivative Sample + new container with `parent_sample_id`; preserve the parent Sample row and original type; put the destination pair on the process and mark the inbound source assignment `removed`. Dest mint Hold lifted only for this path |
| Later Start | Target is next process on destination container (`1572071` joints): Deiter `570bbc0` Lab Ops Met; Tobias QA restamp unsigned. C2 **Fail** on `02fe95f` stays signed history |
| Later step start with current type outside that step’s accepted types | **422 `route_sample_type`**; sample is not broken. **Unsigned on `8cfa2a9`** — not click-run |
| Publish without Test | **422** the whole run (`_require_wo7_tests` / `plan.errors`). Stay unpublished. Zero Results. Publish-refuse **Pass** on `8cfa2a9` and history on `b005cfe`. Freeze skip unsigned: `{}` on `99b692d3` is ambiguous, not a skip Pass. |
| Invisible process def (`0074` `has_experiment_access`) | Catalog-visible **read**. Route stays `test:assign`. Not `experiment:manage` on Route. |
| Empty accepted set at step start | **422 `route_sample_type`** |
| Classic `/tests` default `{}` | Not a freeze — skip-on-`{}` stays OPEN. NULL = not frozen yet. First start must still write. |
| Later start overwrites frozen `asked_for_params` (including `{}`) | Bounce — freeze is write-once per Test. Skip-on-`{}` is still not shipped. |
| Skip-on-`{}` treated as a freeze | Bounce — classic default `{}` makes skip-on-`{}` **not** a freeze. OPEN until classic NULL or a freeze marker |
| Named slot analysis appears 0 or 2+ times among route LimsRuns | **422** map-save. Two ELISA LimsRuns refused. Extract is not a LimsRun and is not counted |
| Eligibility checks chain containment instead of named slot | Bounce. WGS+Qubit-as-QC must not accept a Quantified DNA ask |
| Teaching extract as a LimsRun / extract wearing ELISA (OQ-WO-6 extract) | Bounce — **CLOSED**. Extract is a process; no asked-for `analysis_id`. Hans 1-count-on-extract freeze is closed |
| One process instance carrying two asked-for assays | Bounce — one asked-for per process instance |
| QC folded into asked-for `analysis_id` / extract-as-LimsRun | Bounce — Qubit = supporting LimsRun, own Test; extract is a process |
| Extract-every-WO / dest auto-joining a second WO / route branching | Bounce — no branching this phase. WGS asked-for on blood owns WGS params; C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up |
| Parser AI on import | Impossible (no call site) |
| Receive non-empty `analysis_ids` | **422** (freeze) |

## 9. Delivery

| PR | Scope |
|----|--------|
| 1 | P1 tables + API + `/asked-for` UI + pytest + UAT script. **Hold merge until UAT.** |
| 2 | P2 routing + work_order + ordered `process_definition[]` + LimsRun WO-7 + 0077 assignment. Signed AC-P2-9..11 `9342439`. Deiter click at `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** (signed history). On live `570bbc0`, Deiter C1/C2/C3 execute is **Lab Ops Met**, not QA Pass; execute joints remain `1572071`. Tobias restamp has no Results yet. Overall P2 **unsigned / not Pass**. **Hold product merge to main.** Freeze skip, Route two-accept 409, and P2-4 `0074` remain open. **OQ-WO-6 extract CLOSED** (Leadership Confirm). Keep: one asked-for per process; QC own Tests; **no route branching** (WGS params on WGS; WES is a new asked-for on the DNA tube, then aliquoted or used up). |
| 3 | P3 persist lock + results UAT fold (**closed**) |
| 4 | P4 SOP Apply → process def (**closed**) |
| 5 | P5 parser setup UX (**closed** this cycle) |

Coding stays Grok Build. One phase per PR. Receive code freeze except bugs. Not IC50.
