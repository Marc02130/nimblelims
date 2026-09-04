# UAT: Post-receive work spine — P1 Pass history / P2 signed not Pass

**Stem:** `post-receive-work-spine`  
**Phase:** P1 asked-for lake (**Pass history**) + P2 Route / work_orders / WO-7 (**QA signed, not Pass**)

**SoT:** `.docs/review/requirements/post-receive-work-spine.md` RQ-AF-* · [asked-for.md](../manuals/asked-for.md) · [HOWTO.md](../manuals/HOWTO.md)  
**P1 UI:** `/asked-for` (Sample Mgmt → **Asked-for**) + sample-detail Asked-for section. A **later look-up**, not the after-receive click and not a Start queue

**P1 API:** `POST /api/v1/asked-for` · `GET /api/v1/asked-for` · `POST /api/v1/asked-for/{id}/cancel`

**P1 env:** local docker compose (`lims-*`); http://localhost:3000 + :8000. Compose **down** after the run. Not IC50. P1 lake only.

**P1 build / commit:** `c649245` (`c6492455200fa69c2093865615f82ada23b8d2b1`, 2026-08-28)

**Executor:** Tobias (`alice-tech`: `/receive` as the precondition — stayed on the form — then `/asked-for` as a separate motion) + API AC-P1-3/4  
**Date:** 2026-08-28  
**Do not use** retired `uat-sample-accessioning.md`. Receive freeze: non-empty `analysis_ids` still **422**.

P1 records **requested analysis + TAT**. It does **not** assign a Test, mint a Test row, attach analytes, or start work; the save is not scientific assignment. Copy: “Asked-for” / “requested analysis”. No Start / Execute.

**Receive ≠ order ≠ work.** Receive’s happy path is **stay on `/receive`** for the next tube (CORE stamp: `uat-atomic-receive.md`). The lake is a later look-up. Do not run these ACs as one motion from receive.

**The lake accepts scientifically wrong pairings on purpose** — a Qubit-on-blood request may sit in it. Refusal belongs to **routing** (P2 `route_sample_type` **422**), not to P1. Do not exercise that here and do not invent Qubit/blood testdata.

**Out of this stamp:** Route, work_orders, WO-7 Test-at-LimsRun-start, `analysis_param_defs` on receive, results persist, SOP Apply, parser dry-run UX, Qubit/blood path.

**This stamp:** **P1 Pass** on `c649245` — AC-P1-1..4. Merged to `main` (PR **#81**, `af5b388`). Do **not** write P2–P5 Pass. Do **not** collapse with receive CORE stamps (`uat-atomic-receive.md`).

**Merge note (2026-08-28):** PR **#81** was merged to `main` (`af5b388`) after this stamp was signed. The hold sentences in this file record the stamp’s condition as written; they are history, not a live instruction.

---

## Fixtures

| Need | Seed |
|------|--------|
| Actor | `lab-tech` / `alice-tech` with `test:assign` + sample/project access |
| Client | `client` / `david-cro` — cannot POST asked-for |
| Receive | One Available-for-Testing sample via `/receive` (ELISA-ready; **no** analyses on receive) |
| Analysis | Existing ELISA (Human IgG) from 0058. Do **not** invent Qubit/blood IDs |

**This run:** receive barcode `NBIO-AF-P1-0001` → sample name `mAb-2301 PK Study-04`. Sticky Plasma / mAb-2301 PK Study / Cryovial. Hidden-sample API used `CAR-T-Batch-001`.

---

## AC-P1-1 — Asked-for save mints zero Tests (lake AC)

**Result:** **Pass** (click, 2026-08-28, `c649245`)

**What is measured:** zero Tests **after the asked-for save**. This is a **lake** AC, not a receive CORE AC, and **not one hop from receive**. Receive is a **precondition**, executed and stamped separately in `uat-atomic-receive.md`; its own happy path is **stay on `/receive`** for the next tube. Asked-for is a **later look-up** — a separate motion, not the after-receive click and not a Start queue.

**Precondition (already true before this AC starts)**
- A sample exists from an earlier `/receive` commit (empty analyses; UI never sends `analysis_ids`). Status **Available for Testing**. Tests count for that sample is 0. The tech has left the receive loop; nothing on the bench is waiting on asked-for.

**Steps (asked-for only)**
1. Log in as lab-tech. Open `/asked-for` (Sample Mgmt → **Asked-for**) as its own task, not as a continuation of receive.
2. **Record requested analysis** → multi-select the already-received sample. Pick ELISA. TAT ≥ 1 (default from analysis TAT is fine).
3. Do **not** enter assay params. P1 sends `{}`; params freeze at **LimsRun start** (P2 / WO-7), not here and not on receive.
4. Save. Stay on `/asked-for`.

**Expect (after the save)**
- Row `status=requested`, carrying **requested analysis + TAT** only. Copy is “requested analysis”, never “assign test” / “start work”.
- `COUNT(tests)` for that sample is still **0** — **this is the pass**. Save assigns no Test, attaches no analytes, and does not make type-a-number legal. Zero Results, Processes, Experiments, LimsRuns, work_orders.
- No Start / Execute / Route CTA. Sample stays **Available for Testing**.
- Sample detail shows the asked-for row under **Asked-for**.
- No redirect back into receive, and no prompt to leave `/receive` for this screen.

**Verified holds (Tobias click, `alice-tech`):**
- Sidebar Sample Mgmt lists **Receive** then **Asked-for** (observed nav order only — not an instruction to go there after a commit, and not a work queue).
- `/receive`: no analysis/asked-for picker, no lab Sample ID, no aliquot dialog. Received `NBIO-AF-P1-0001`; stayed on `/receive`; barcode cleared; sticky Plasma / mAb-2301 PK Study / Cryovial.
- `/asked-for` copy: “After receive, record what was asked for. This does not assign a test or start work.” CTA **RECORD REQUESTED ANALYSIS**. Modal: “Record a requested analysis. This does not assign a test or start work.” No Start / Execute anywhere.
- Recorded ELISA (Human IgG) on `mAb-2301 PK Study-04` (the receive of `NBIO-AF-P1-0001`). Grid shows requested row; after cancel+resave: one requested + one cancelled (1–2 of 2).
- Tests Management still 3 seed tests only (not minted for the new receive). No `work_orders` table.

**Observations (not fails):**
- Sample picker by raw barcode `NBIO-AF-P1-0001` showed “No options”; recording used the sample name.
- Page copy leads with “After receive, record what was asked for.” It is correct that no Test is assigned, but the lead-in reads as the next motion after a commit. Copy owner’s call, not a P1 result: the lake is a later look-up, and receive ends on `/receive`.

## AC-P1-2 — Duplicate 409

**Result:** **Pass** (click, 2026-08-28, `c649245`)

**Steps**
1. Repeat AC-P1-1 save for the same sample + ELISA while the first row is still `requested`.

**Expect**
- **409**. No second open row. Cancel the first, then re-save → **201**.

**Verified holds:** second save same sample+ELISA while requested → banner “An open asked-for already exists for this sample and analysis” (**409**). Cancel first, resave → new requested row.

## AC-P1-3 — Cross-project 403

**Result:** **Pass** (API, 2026-08-28, `c649245`)

**Steps**
1. As lab-tech, POST `/api/v1/asked-for` with a sample_id from a project the user cannot access (or a hidden sample).

**Expect**
- **403** with project-permission wording, **not 404**.
- Client role POST → **403** even if the role were granted `test:assign`.

**Verified holds:**
- `alice-tech` POST `/v1/asked-for` on hidden `CAR-T-Batch-001` → **403** “Access denied: insufficient project permissions” (not 404).
- `david-cro` POST on alice sample → **403** “Client role cannot record asked-for” (seed still has `test:assign`).

## AC-P1-4 — Receive freeze (regression)

**Result:** **Pass** (API, 2026-08-28, `c649245`)

**Steps**
1. `POST /api/samples/receive` with non-empty `analysis_ids`.

**Expect**
- **422** `analysis_ids must be empty`. Zero samples/tests created. Params / param-defs are not on this call.

**Verified holds:** `POST /samples/receive` with non-empty `analysis_ids` → **422** “analysis_ids must be empty for Atomic Receive CORE”. No refuse barcode row.

---

## Out of scope this stamp (P1)

Route, work_orders, LimsRun Test mint (WO-7), param defs on receive, results persist, SOP Apply rewrite, parser dry-run UX, Qubit/blood path. P1 remains **Pass**. P2 cases below are a **new** stamp; do not rewrite P1 results.

---

## Historical P2 record — `3b56cfb` (QA signed, not Pass)

This entire `3b56cfb` block is retained as history of that SHA, like the P1 merge note above. Its outcomes and observations are not the live AC-P2 stamp for the current product branch.

**Result:** **not Pass** (QA signed, Tobias, 2026-08-29, `feat/work-order-p2` @ `3b56cfb`). Do **not** report P2 Pass. Hold merge.

**Branch / build under test:** `feat/work-order-p2` at `3b56cfb` (`3b56cfb8f2a111b278c3d8b4c546bf6e5bf9116c`)

**UI:** `/asked-for` Route · `/admin/routing-map` · `/work-orders` · `/experiments/processes/{id}` · `/runs/{id}`

**API:** `POST /v1/asked-for` · `POST /v1/asked-for/{id}/route` · `POST /v1/asked-for/route` · `GET/POST /v1/routing-map` · `GET /v1/work-orders` · `POST /v1/work-orders/{id}/start` · `PATCH /v1/lims-runs/{id}/start` · `PATCH /v1/lims-runs/{id}/complete`

**Copy locks:** Receive ≠ order ≠ work. Receive stays on `/receive`. Asked-for save is a later look-up and mints no work order. Route is another later action. Params freeze at LimsRun start. Not IC50.

**Do not** seed blood→Qubit solely for this run; use configured sample types to prove the same fail-closed gate. Dest-type Hold and Receive freeze remain unchanged.

### AC-P2-1 — Route is a later action, never after-receive

**Result:** **Pass** (click, 2026-08-29, `3b56cfb`, Tobias)

1. As lab-tech, receive a sample on `/receive`.
2. Confirm the successful receive stays on `/receive`, clears the barcode, and is ready for the next tube. Do not follow the receive commit directly to Asked-for.
3. In a separate later task, open `/asked-for`, save a requested analysis, and end that task on `/asked-for`.
4. Later still, return to the requested row and choose **Route** (or select requested rows and choose **Route selected**).

**Expect**
- Receive offers no analysis or Route action and does not navigate to `/asked-for`.
- Asked-for is a later look-up, not the after-receive click and not a Start queue.
- Save does not auto-route. Only the explicit later Route call evaluates the routing map.

**Verified holds:** receive stayed on `/receive`; asked-for save stayed on `/asked-for` without auto-route; Route was a later explicit action.

### AC-P2-2 — Asked-for save mints no work_order

**Result:** **Pass** (API, 2026-08-29, `3b56cfb`, Tobias)

1. Record `COUNT(work_orders)` and `COUNT(tests)` for a received sample before saving requested analysis.
2. `POST /v1/asked-for` with an active analysis, TAT ≥ 1, and valid `params` (empty `{}` is acceptable).
3. Recount before invoking either Route endpoint.

**Expect**
- The new row is `requested`.
- `COUNT(work_orders)` and `COUNT(tests)` are unchanged. No Process, Experiment, or LimsRun is created.
- Saving valid params records intent only; it does not freeze them.

**Verified holds (API):** `POST /v1/asked-for` left `COUNT(work_orders)` and `COUNT(tests)` unchanged. Routing-map UI on `/admin/routing-map` was blocked (`sample_type` vs `sample_types`) and was not used for this AC.

### AC-P2-3 — work_order feeds the existing Process / Experiment / LimsRun engine

**Result:** **Pass** (API, 2026-08-29, `3b56cfb`, Tobias)

1. Configure a process definition with typed `eln_experiment` and/or `lims_run` steps. Give every step an accepted-sample-type set that includes the sample’s current type.
2. At `/admin/routing-map`, create a matching analysis × sample type × TAT row for that definition.
3. Explicitly Route the previously saved requested row.
4. Open Experiments → **Work Orders** (`/work-orders`) and choose **Start process**.
5. Follow the returned/opened process at `/experiments/processes/{process_id}` and start its typed step through the existing process UI.

**Expect**
- Route creates one queued `work_order`, sets asked-for to `routed`, and still creates zero Tests.
- Work-order start sets it `in_progress`, creates one linked ELN process from the first snapshot definition, and stores the linkage in `eln_processes.work_order_id` / returned `process_id`.
- Experiment and LimsRun steps execute in the existing Process/Experiment/LimsRun surfaces. There is no second work-order execution home.
- Cancel of the routed asked-for row returns **422**.

**Verified holds (API):** explicit Route minted a queued `work_order`; work-order start instantiated the existing ELN process (`eln_processes.work_order_id` / returned `process_id`). Routing-map UI on `/admin/routing-map` was blocked (`sample_type` vs `sample_types`); map/setup for this AC used API.

**Lab Ops note:** Admin Route that queues a work order is the **mint bar** only. It is **not** a P2 Pass.

### AC-P2-4 — WO-7 Test and params freeze at LimsRun start

**Result:** **Fail** (alice, 2026-08-29, `3b56cfb`, Tobias) — **visibility**: alice cannot see the process definition. Not a copy issue. Do not treat as Pass.

1. For a routed asked-for row, set a valid asked-for param (for example a configured text param) before starting the run.
2. Create or open the typed LimsRun from the linked process, select the routed sample cohort, and `PATCH /v1/lims-runs/{id}/start`.
3. Verify the active Test for `(sample_id, analysis_id)` and its `asked_for_params`.
4. With run data present, remove or deactivate that Test in the QA fixture before publish, move the run to `complete`, and call `PATCH /v1/lims-runs/{id}/complete`.

**Expect**
- Route and work-order start mint no Test.
- LimsRun start creates the Test when missing or attaches the existing active Test, then snapshots the asked-for params into `tests.asked_for_params`.
- The saved Test snapshot matches the params present at start; neither asked-for save nor Route copied them into a Test earlier.
- Publish with the required Test missing returns **422** and does not invent a Test or publish Results.

**Verified holds:** alice could not complete the LimsRun start / freeze path because she **cannot see the definition** (def/steps RLS). Fail is visibility, not copy. Publish 422 is not claimed here.

### AC-P2-5 — Type gate fails closed; empty map mints nothing

**Result:** **not Pass** (2026-08-29, `3b56cfb`, Tobias). Do **not** fold this AC as Pass. Publish was **unclickable**. Do not write “mint Pass / publish 422 unverified” as a Pass.

1. For a `requested` row, ensure no map matches its analysis × current sample type × TAT; choose Route.
2. Confirm **200** `no_route`, then configure a candidate process step with an empty accepted-type set and try to save the map.
3. Configure the step with only a different accepted type and retry map save.
4. After creating a valid map, remove the current sample type from a mapped step and Route another matching requested row.

**Expect**
- Empty map: status remains `requested`; zero work orders and zero Tests are minted.
- Empty or incompatible accepted-type sets fail map save and Route with **422** `detail.code = route_sample_type`.
- Every step in every mapped process definition must accept the current sample type. A Qubit step that does not accept blood therefore cannot route a blood sample.

**Verified holds:** empty-map mint is **not** recorded as Pass. Publish was **unclickable**, so missing-Test **422** was not exercised. Admin Route queued-WO remains the mint bar, not a Pass for this AC.

### Supplemental P2 regression — overlapping TAT ranges

**Result:** **not separately signed** (covered only as API setup for AC-P2-2/3 where applicable; do not treat as Pass)

1. Create two active routing-map rows for the same analysis and sample type with overlapping inclusive TAT ranges.
2. **Expect:** the second save returns **409** and no overlapping row is created.

---

## Historical sign-off — through `3b56cfb`

**P1 Pass** — Tobias, 2026-08-28, `c649245` — AC-P1-1..4.

Click: `/receive` then `/asked-for` as `alice-tech`. API: AC-P1-3/4. Local compose; down after the run. Not IC50. P1 lake only.

**P2 signed, not Pass** — Tobias, 2026-08-29, `feat/work-order-p2` @ `3b56cfb` — AC-P2-1 Pass; AC-P2-2/3 Pass (API; routing-map UI blocked on `sample_type` vs `sample_types`); AC-P2-4 Fail for alice (**visibility**: cannot see the def); AC-P2-5 **not Pass** (publish unclickable; do not fold mint/unverified-422 as Pass). Admin Route queued WO is the mint bar, not a Pass. Not IC50.

Do **not** read this as P2–P5 Pass. Do **not** collapse this stamp with Atomic Receive **CORE** Pass (`uat-atomic-receive.md`). P1 is on `main` (PR **#81**) and is **not** rewritten. The P2 statements in this historical block apply only to `3b56cfb`.

---

## Live AC-P2 stamp — `9c4f9da` (QA signed, not Pass)

**Result:** **not Pass** (QA signed, Tobias, 2026-08-29, `feat/work-order-p2` @ `9c4f9da`). Do **not** report P2 Pass. Hold merge.

**Branch / build under test:** `feat/work-order-p2` at `9c4f9da` (`9c4f9da61965c7bfd01692622102dc18e332dd39`)
**Executor:** Tobias
**Env:** local docker compose (`lims-*`); compose **down** after the run. Not IC50.

**History boundary:** Do not copy outcomes or observations from `3b56cfb` into this live stamp. That block remains history of that earlier SHA only.

**Copy locks:** Receive ≠ order ≠ work. Receive stays on `/receive`. Asked-for is an unnumbered later look-up. Route is a later planner. Minting a queued `work_order` is not work begun; **Start process** is the later action. A **422** `route_sample_type` means the analysis/sample-type pairing is wrong for a mapped step, not that the sample is broken. Test creation/attachment and params freeze at LimsRun start. The WO-7 lock is that publish refuses the whole run if any required Test is missing; that refuse is **not** verified as shipped on this SHA. Not IC50.

### AC-P2-1 — Route is a later planner, never after-receive

**Result:** **Pass** (click, 2026-08-29, `9c4f9da`, Tobias)

1. As lab-tech, receive a sample on `/receive`.
2. Confirm the successful receive stays on `/receive`, clears the barcode, and is ready for the next tube.
3. In a separate later task, open `/asked-for`, save requested analysis + TAT, and confirm that task ends on `/asked-for`.
4. Later still, return to the `requested` row and choose **Route** or **Route selected**.

**Expect**
- Receive offers no analysis or Route action and does not navigate to `/asked-for`.
- Asked-for is a later look-up, not the next numbered receive step and not a Start queue.
- Save does not auto-route. Only the later explicit Route action evaluates the routing map.

**Verified holds (alice):** receive stay-on-form; asked-for later; Route later. Empty-map Route banner “1 with no routing-map match (stayed requested)”; **200** `no_route`.

### AC-P2-2 — Asked-for save mints no work_order

**Result:** **Pass** (2026-08-29, `9c4f9da`, Tobias)

1. Record `COUNT(work_orders)` and `COUNT(tests)` for an already-received sample.
2. `POST /v1/asked-for` with an active analysis, TAT ≥ 1, and valid `params` (`{}` is acceptable).
3. Recount before invoking either Route endpoint.

**Expect**
- The new row is `requested`.
- `COUNT(work_orders)` and `COUNT(tests)` are unchanged. No Process, Experiment, or LimsRun is created.
- Params remain intent only; they are not frozen.

**Verified holds:** Study-06 asked-for save stayed `requested`; work orders **1 leftover only**; **0** tests on `bd68189f`.

### AC-P2-3 — queued mint is planning; Start process begins the process

**Result:** **Pass** (2026-08-29, `9c4f9da`, Tobias)

1. Use an existing process definition whose typed steps all accept the sample’s current type.
2. At `/admin/routing-map`, create a matching analysis × sample type × TAT row.
3. Explicitly Route the requested row.
4. Inspect `/work-orders` before choosing **Start process**.
5. Choose **Start process**, then follow the linked process at `/experiments/processes/{process_id}`.

**Expect**
- Route creates one queued `work_order`, changes asked-for to `routed`, and creates zero Tests.
- The queued mint is a planning record; work has not started and no process instance exists yet.
- **Start process** sets the work order `in_progress`, creates one linked ELN process from the first snapshot definition, and returns/stores its `process_id`.
- Experiment and LimsRun steps continue in the existing Process / Experiment / LimsRun surfaces.

**Verified holds (alice):** Route minted queued work order `ad87f804` with **0** Tests. **Start process** opened process `714014b2`.

**Observation only (not a Fail):** `/experiments/processes/{id}` is a blank page (`tid.slice`). Do not treat that observation as a Fail.

### AC-P2-4 — WO-7 freezes Test + params at LimsRun start; publish is all-or-nothing

**Result:** **Fail** (2026-08-29, `9c4f9da`, Tobias). The fail is publish succeeding without a Test. **Do not fold the mint as a Pass.** Do not claim whole-run publish-refuse as verified on this SHA.

1. For a routed row, save a valid asked-for param before starting the run.
2. From the linked process, create or open the typed LimsRun, select the routed sample cohort, and `PATCH /v1/lims-runs/{id}/start`.
3. Verify the active Test for `(sample_id, analysis_id)` and its `asked_for_params`.
4. With publishable run data present, remove or deactivate one required Test in the QA fixture, move the run to `complete`, and call `PATCH /v1/lims-runs/{id}/complete`.
5. Verify the run and every candidate Result after the response.

**Expect**
- Route and work-order start create no Test.
- LimsRun start creates the missing active Test or attaches the existing one and freezes the then-current asked-for params into `tests.asked_for_params`.
- The Test and params snapshot are fixed at run start, not receive, asked-for save, Route, or work-order start.
- Missing any required Test returns **422**. Publish creates no Test, refuses the whole run, leaves the run unpublished, and writes no partial Results.

**Verified holds:** LimsRun start did mint Test `6a8a1626`. After that Test was deleted, carol `PATCH /v1/lims-runs/ee5277b4/complete` returned **200 published** at 22:32 ET, **not 422**. The run published with **0** Tests and **0** data rows. Do **not** fold the mint as a Pass. The fail is publish succeeding without a Test.

### AC-P2-5 — type gate means wrong pairing, not broken sample

**Result:** **Pass** (2026-08-29, `9c4f9da`, Tobias)

1. For a `requested` row, confirm an empty routing map returns **200** `no_route` and mints nothing.
2. Using existing configured sample types, try to save a map whose candidate definition has an empty accepted-type set.
3. Configure a candidate step to accept only a different sample type and retry map save.
4. After creating a valid map, remove the current sample type from a mapped step and Route another matching requested row.

**Expect**
- Empty map leaves the row `requested` and creates zero work orders and zero Tests.
- Empty or incompatible accepted-type sets fail map save and Route with **422** `detail.code = route_sample_type`.
- The error identifies a wrong analysis/sample-type pairing for a mapped step. It does not mark or imply that the sample is broken.
- Every step in every mapped process definition must accept the current sample type.

**Verified holds:** **422** `route_sample_type` “Sample type is not accepted on every step in the chain”; UI “…accept that sample type.” TAT overlap **409**.

### Supplemental P2 regression — overlapping TAT ranges

**Result:** **Pass** (2026-08-29, `9c4f9da`, Tobias; covered with AC-P2-5)

1. Create two active routing-map rows for the same analysis and sample type with overlapping inclusive TAT ranges.
2. Expect the second save to return **409** and create no overlapping row.

**Verified holds:** TAT overlap **409**.

---

## Live sign-off

**P2 signed, not Pass** — Tobias, 2026-08-29, `feat/work-order-p2` @ `9c4f9da` — AC-P2-1 Pass; AC-P2-2 Pass; AC-P2-3 Pass (blank process page `tid.slice` is observation only, not a Fail); AC-P2-4 **Fail** (publish **200 published** with 0 Tests after Test delete; do not fold mint as Pass; whole-run refuse **not** verified); AC-P2-5 Pass (`route_sample_type` 422; TAT overlap 409). Local compose; down after the run. Not IC50.

P1 remains the historical **Pass** on `c649245`; this live P2 section does not alter it. The `3b56cfb` block remains history only. Hold merge of `feat/work-order-p2`.

---

The preceding `9c4f9da` section is retained verbatim as signed history, including its original “Live” heading and Results. It is not the current stamp. Do not rewrite or transfer those observations to another SHA.

## Live AC-P2 stamp — `b005cfe` (per-AC signed; overall P2 unsigned / not Pass)

**Branch / build tested:** `feat/work-order-p2` at `b005cfe` (`b005cfe4596ca64baf5c674d372536e27560cf69`)

**QA signature:** Tobias — signed per-AC results below. **Overall P2 Pass remains unsigned and is not claimed.**

**Executor / environment / date:** Tobias · local docker compose (`lims-*`) · 2026-08-29 · compose down after run
**Merge:** hold product merge of `feat/work-order-p2`. Not IC50.

This block records Tobias’s `b005cfe` results. It does not rewrite or transfer outcomes from `9c4f9da`, `3b56cfb`, or P1.

**Copy and permission locks:** Receive ends on `/receive`. Asked-for is a separate later look-up. Route is an unnumbered later planner requiring `test:assign` plus project access; it does not require `experiment:manage`. Client and inaccessible-project Route writes return **403**, not 404. **Start process** and LimsRun start require `experiment:manage`; publish requires `experiment:publish`.

**WO-7 maturity, stated so QA does not read a lock as shipped behavior:** the two halves differ on this SHA.

| WO-7 half | State on `b005cfe` |
|-----------|--------------------|
| Whole-run publish refuse when a cohort Test is missing | **Publish-refuse Pass signed by Tobias** in AC-P2-4; first-start freeze not scored |
| First-start freeze of `tests.asked_for_params` | **Lock, still OPEN and not scored.** `{}` was recorded; `_mint_tests_at_start` still has no already-frozen guard |

Empty `{}` is a freeze, not a hole to refill on a later start. AC-P2-4 records the freeze as the target lock; an overwrite observed on this SHA is the expected open gap, not a surprise.

### AC-P2-1 — Route remains a separate later planner

**Result:** **Pass** (alice click, Tobias signed, 2026-08-29, `b005cfe`)

1. As a lab user with `sample:create`, receive a sample on `/receive`.
2. Confirm the successful receive stays on `/receive`, clears the barcode, and is ready for the next tube.
3. In a separate later task, record requested analysis + TAT on `/asked-for`; confirm save stays on `/asked-for` and does not auto-route.
4. Later, choose **Route** or **Route selected** on a `requested` row.

**Expect**
- Receive has no analysis or Route action.
- Asked-for is not a numbered post-receive step or Start queue.
- Only the explicit later Route action evaluates the routing map.

**Verified holds:** alice received and stayed on `/receive`; asked-for was a separate later motion; Route was later again.

### AC-P2-2 — Asked-for save mints no work order or Test

**Result:** **Pass** (Tobias signed, 2026-08-29, `b005cfe`)

1. Record work-order and Test counts for Study-01.
2. Save requested analysis + TAT on `/asked-for`.
3. Recount before Route.

**Expect**
- The row stays `requested`.
- Work-order and Test counts remain zero.

**Verified holds:** Study-01 asked-for save left the row `requested` with **0 work orders** and **0 Tests**.

### AC-P2-3 — queued work order feeds the existing execution engine

**Result:** **Pass** (alice click, Tobias signed, 2026-08-29, `b005cfe`)

1. Use the admin-created ELISA LimsRun definition from the signed run. Do not invent seed IDs.
2. Use the admin-created matching routing map from that run and explicitly Route the requested row.
3. Inspect `/work-orders` before choosing **Start process**.
4. Start the work order, follow the linked process, and open its typed Experiment/LimsRun step.

**Expect**
- Route creates one queued `work_order`, changes asked-for to `routed`, and creates zero Tests.
- The queued record is planning only; **Start process** begins execution and requires `experiment:manage`.
- Route and process views make process/step order apparent; steps are not presented as an unordered bag.
- Process detail renders even when a step has a null template id; no `tid.slice` blank page.

**Verified holds:** alice used Route + Start on the admin-created ELISA LimsRun P2 type-gate definition. Route minted one queued work order and **0 Tests**; Start opened process `b47db5ee`; process detail rendered without a `tid.slice` crash.

### AC-P2-4 — WO-7 first-start freeze and whole-run refusal

**Result:** **Publish-refuse Pass** (carol API + UI, Tobias signed, 2026-08-29, `b005cfe`). **First-start freeze remains OPEN and was not scored. Do not fold this into overall P2 Pass.**

1. For a routed row, save a valid asked-for param before starting its typed LimsRun.
2. Select the routed cohort and call `PATCH /v1/lims-runs/{id}/start` for the first start.
3. Inspect the active Test for each `(sample_id, analysis_id)` and its `asked_for_params`.
4. Change the source asked-for params after first start, and clear the `routed` asked-for row for one cohort sample. Then reach `_mint_tests_at_start` a second time for the same `(sample, analysis)`: exercise any supported repeated-start path on the run, and also start a second run over the same cohort and analysis (the path that commits against the existing active Test).
5. Re-read `tests.asked_for_params` and record what that later start did to the first-start snapshot, including whether the cleared row left `{}` behind.
6. Add publishable run data, remove or deactivate one cohort Test in the QA fixture, and move the run to `complete`.
7. Call publish with `PATCH /v1/lims-runs/{id}/complete`, then inspect run status, Tests, and every candidate Result.

**Expect (publish refuse — in code on this SHA)**
- Receive, asked-for save, Route, and work-order start create no Test.
- First LimsRun start creates or attaches one active Test per cohort sample and freezes the then-current params into `tests.asked_for_params`.
- With any cohort Test missing, publish returns **422**, not **200 published**.
- The whole run is refused: it stays `complete`, no Test is invented, and no Results are written, including for cohort samples whose Tests still exist.

**Target lock (first-start freeze — OPEN on this SHA, do not score as a regression)**
- Intended: a later start neither replaces the Test nor rewrites the first-start `asked_for_params` snapshot, and never overwrites a snapshot with `{}`.
- Actual on `b005cfe`: steps 4–5 are expected to show the later start rewriting `asked_for_params`, because `_mint_tests_at_start` carries no already-frozen guard. Record the observed values; that gap is the open lock, not a product-code change for this docs fold.

**Verified holds (publish-refuse half):** after Test `40ac357f` was deleted, carol `PATCH /complete` returned **422** `test_missing`: “Test missing; Tests are created at LimsRun start (WO-7). Publish refuses the whole run.” The UI showed the same banner. Status stayed **Complete**, Published stayed **—**, and no Test was reminted.

**Recorded but not scored (first-start freeze):** `asked_for_params` was `{}`. This is the known OPEN overwrite gap, not a Pass and not evidence that first-start freeze is closed.

### AC-P2-5 — chain-AND map-save history on `b005cfe`

**Result:** **Pass** (Tobias signed, 2026-08-29, `b005cfe`). This Pass is **history of the chain-AND** (map save 422’d because the type was not accepted on every step). Do **not** re-score it. Do **not** teach that map-save 422 as the live authoring rule.

**Verified holds on `b005cfe`:** click-save returned **422** `route_sample_type` with “Sample type is not accepted on every step in the chain”; overlapping TAT was refused.

**Live ordered-route expect (not scored on this SHA; not this Result)**

1. Confirm map create has analysis, TAT, and sortable ordered `process_definition[]`, with no sample-type picker.
2. Confirm the form displays the first process and its first ordered Experiment/LimsRun allow-list. Change process order or first-step acceptance and verify derived display refreshes.
3. Save an extract-first route with a later Qubit process/step; confirm map save does not chain-AND later processes or steps.
4. Save extract-first and Qubit-first rows for the **same analysis and overlapping TAT**. Confirm map save succeeds because first-step allow-lists do not overlap.
5. Save a second extract-first row whose first-step allow-list overlaps the first extract-first row and whose TAT overlaps. Confirm **409**.
6. Route with zero acceptable rows (no analysis + TAT candidate or no candidate whose first process/step accepts current type).
7. Using a fixture with two saved rows that both accept current type, Route again.
8. Route with exactly one acceptable row and inspect the work-order snapshot order.
9. Choose Start; inspect created process instances. Complete the first process, then invoke the later start.
10. Attempt a later process/step start with an empty or incompatible allow-list.

**Expect**
- Map row = analysis + TAT + ordered `process_definition[]`. UI preserves order. Allowed types are derived from the first process / first step, not admin-authored.
- Map save **409**s only when the same analysis, overlapping TAT, **and** overlapping first-step allow-lists all hold. Extract-first vs Qubit-first for the same TAT is legal.
- Zero acceptable rows returns **422** and mints no work order. A first-step type refusal uses `route_sample_type`.
- Two saved rows that both accept this sample’s current type return **409**; no silent `first()`.
- Exactly one row snapshots the full ordered route.
- Start instantiates the first process only. Later processes require later starts in route order; Route does not mint a process-of-processes.
- Map save/Route do not AND later-process or later-step allow-lists.
- Each later process/step start checks current type; empty or incompatible fails with **422** then.
- Dest-type Hold remains out; do not claim an earlier step changed type unless the product did so.

---

## Live `b005cfe` per-AC sign-off

**Signed by Tobias, 2026-08-29; local docker compose, compose down.**

AC-P2-1 **Pass** · AC-P2-2 **Pass** · AC-P2-3 **Pass** · AC-P2-4 **publish-refuse Pass**; first-start freeze **OPEN, not scored** · AC-P2-5 **Pass as chain-AND history**.

**Overall P2 remains unsigned.** Do not write overall P2 Pass, signed Pass, or merge-ready. Hold product merge. Not IC50.

---

The preceding `b005cfe` section is retained verbatim as signed history, including its original “Live” heading and Results. It is not the current stamp. Do not rewrite or transfer those observations to another SHA. AC-P2-5 Pass on `b005cfe` is **chain-AND history only**.

## Live AC-P2 stamp — `8cfa2a9` (per-AC signed; overall P2 unsigned / not Pass)

**Branch / build tested:** `feat/work-order-p2` at `8cfa2a9` (`8cfa2a9be646630f5d4edba0ac64e47069312bfa`)

**QA signature:** Tobias — signed per-AC results below. **Overall P2 Pass remains unsigned and is not claimed.** Do **not** write overall P2 Pass.

**Executor / environment / date:** Tobias · local docker compose (`lims-*`) · 2026-08-30 · compose **down** after run
**Merge:** hold product merge of `feat/work-order-p2`. Not IC50.

This block records Tobias’s `8cfa2a9` click. It does **not** rewrite or transfer outcomes from `b005cfe`, `9c4f9da`, `3b56cfb`, or P1. AC-P2-5 Pass on `b005cfe` stays **chain-AND history only** and is **not** carried here.

**Copy and permission locks:** Receive ends on `/receive`. Asked-for is a separate later look-up. Route is an **unnumbered** later planner requiring `test:assign` plus project access; it does not require `experiment:manage`. Client and inaccessible-project Route writes return **403**, not 404. **Start process** and LimsRun start require `experiment:manage`; publish requires `experiment:publish`. **Start instantiates `chain[0]` only.** Dest-type Hold out.

**Hans freeze punch (still open — live freeze skip unsigned, not Pass):** Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, `{}` is **ambiguous** — first start cannot tell a classic default `{}` from a frozen `{}` (same JSON). Do **not** teach skip-on-frozen-`{}`. `{}` is **not** a verified freeze skip. `if test: continue` is **not** a freeze. Extract LimsRun must **not** share the asked-for `analysis_id`.

| Slice on `8cfa2a9` | Tobias |
|--------------------|--------|
| Receive stay-on-form | **Pass** |
| Asked-for save 0 work orders | **Pass** |
| Empty Route **422** `No routing-map row accepts this analysis, TAT, and sample type` | **Pass** |
| alice Route+Start **first process only** (ELISA first LimsRun, 1 step, no Qubit/qPCR Tests) | **Pass** |
| Freeze **wrote** `asked_for_params` `{}` onto **new** Test `99b692d3` (not SQL NULL, not a skipped classic row) | Observed write. **Not** a verified freeze skip — `{}` is ambiguous. |
| Classic `/tests` skip / skip-on-frozen-`{}` | **OPEN, unsigned, not Pass.** Do not fold later-start no-overwrite of `{}` as Pass. |
| carol publish **422** `test_missing`; run stayed complete unpublished | **Pass** |
| Routing-map UI **click-save** (not API-only): no sample-type picker; ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved (no AND 422); second ELISA overlap **409** | **Pass** (do not re-score) |
| Later-step type-gate at start (current tube) | **unsigned** — not click-run this SHA. Not Pass. |
| Route two-accept **409** | **unsigned** — not claimed this SHA |
| Overall P2 | **unsigned / not Pass** |

### AC-P2-1 — Route remains a separate later planner

**Result:** **Pass** (receive stay-on-form, Tobias signed, 2026-08-30, `8cfa2a9`)

1. As a lab user with `sample:create`, receive a sample on `/receive`.
2. Confirm the successful receive stays on `/receive`, clears the barcode, and is ready for the next tube.
3. In a separate later task, record requested analysis + TAT on `/asked-for`; confirm save stays on `/asked-for` and does not auto-route.
4. Later, choose **Route** or **Route selected** on a `requested` row.

**Expect**
- Receive has no analysis or Route action.
- Asked-for is not a numbered post-receive step or Start queue.
- Only the explicit later Route action evaluates the routing map.

**Verified holds:** receive stay-on-form **Pass**. Route stays an unnumbered later planner.

### AC-P2-2 — Asked-for save mints no work order or Test

**Result:** **Pass** (asked-for save 0 WO, Tobias signed, 2026-08-30, `8cfa2a9`)

1. Record work-order and Test counts for the project.
2. Save requested analysis + TAT on `/asked-for`.
3. Recount before Route.

**Expect**
- The row stays `requested`.
- Work-order and Test counts remain zero.

**Verified holds:** asked-for save left **0 work orders**.

### AC-P2-3 — queued work order feeds the existing execution engine

**Result:** **Pass** (alice Route+Start **first process only**, Tobias signed, 2026-08-30, `8cfa2a9`)

1. Admin-create an extract-then-later-process definition/map (ordered chain). Do not invent seed IDs.
2. Explicitly Route a requested row that the first process’s first Experiment/LimsRun accepts.
3. Inspect `/work-orders` before choosing **Start process**.
4. Start the work order, follow the linked process, and open its typed Experiment/LimsRun step.

**Expect**
- Route creates one queued `work_order`, **snapshots the ordered list**, changes asked-for to `routed`, and creates **zero Tests**.
- The queued record is planning only; **Start process** begins execution and requires `experiment:manage`.
- **First Start instantiates `chain[0]` only.** If first Start also mints later processes (Qubit/reporting) or their Tests, that is a punch — record it; do not teach as shipped.
- **Later Start** = next pending process, on the sample that exists then. Dest-type Hold is out.
- Process detail renders even when a step has a null template id; no `tid.slice` blank page.

**Verified holds:** alice Route+Start instantiated **first process only** — ELISA first LimsRun, **1 step**, **no Qubit/qPCR Tests**. Route remains unnumbered. Do not teach whole-chain-at-Start.

### AC-P2-4 — WO-7 first-start freeze and whole-run refusal

**Result:** **Publish-refuse Pass** (carol **422** `test_missing`, run stayed complete unpublished). Freeze skip remains **unsigned / not Pass**. Tobias signed publish-refuse, 2026-08-30, `8cfa2a9`. Do **not** fold freeze skip or overall P2 as Pass. Do **not** claim freeze closed.

1. For a routed row, save a valid asked-for param before starting its typed LimsRun.
2. Select the routed cohort and call `PATCH /v1/lims-runs/{id}/start` for the first start.
3. Inspect the active Test for each `(sample_id, analysis_id)` and its `asked_for_params`.
4. Change the source asked-for params after first start, and clear the `routed` asked-for row for one cohort sample (QA fixture; cancel-while-routed remains 422). Then reach `_mint_tests_at_start` a second time for the same `(sample, analysis)`: start a second run over the same cohort and analysis (the path that finds the existing active Test).
5. Re-read `tests.asked_for_params`.
6. Add publishable run data, remove or deactivate one cohort Test in the QA fixture, and move the run to `complete`.
7. Call publish with `PATCH /v1/lims-runs/{id}/complete`, then inspect run status, Tests, and every candidate Result.

**Expect**
- Receive, asked-for save, Route, and work-order start create no Test. Route snapshots the ordered list, **zero Tests**.
- First LimsRun start of the **asked-for** analysis **writes** `asked_for_params` onto a **new** Test.
- Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, `{}` is **ambiguous** — first start cannot tell a classic default `{}` from a frozen `{}` (same JSON). Do **not** teach skip-on-frozen-`{}`. `{}` is **not** a verified freeze skip.
- `if test: continue` is **not** a freeze. Extract LimsRun must **not** share the asked-for `analysis_id`.
- With any cohort Test missing, publish returns **422**, not **200 published**.
- The whole run is refused: it stays `complete`, no Test is invented, and no Results are written, including for cohort samples whose Tests still exist.

**Verified holds (new-Test write, not a freeze-skip Pass):** first start **wrote** `asked_for_params` `{}` onto **new** Test `99b692d3` (not SQL NULL, not a skipped classic row). That `{}` is still **ambiguous**. Do **not** score later-start no-overwrite of `{}` as a verified freeze skip.

**Not scored / still open (Hans):** freeze skip stays **unsigned**. Classic `/tests` must leave `asked_for_params` **NULL**, or a freeze marker must land. Until then skip-on-`{}` / skip-on-frozen-`{}` is not a freeze.

**Verified holds (publish-refuse):** carol publish returned **422** `test_missing`. Run stayed **complete** unpublished.

### AC-P2-5 — ordered route; first-process first-step types

**Result:** **Pass** for routing-map UI **click-save** (not API-only) / ELISA TAT 1–7 saved / Blood extract + later DNA qPCR chain saved (no AND 422) / second ELISA overlap **409** / empty Route **422**. **Later-step type-gate at start (current tube) unsigned** — not click-run this SHA; not Pass. Route two-accept **409** unsigned this SHA. Do **not** score or carry `b005cfe` chain-AND map-save 422. Tobias signed, 2026-08-30, `8cfa2a9`. **Do not re-score.**

1. Confirm map create has analysis, TAT, and sortable ordered `process_definition[]`, with no sample-type picker.
2. Confirm the form displays the first process and its first ordered Experiment/LimsRun allow-list. Change process order or first-step acceptance and verify derived display refreshes.
3. Save an extract-first route with a later Qubit process/step; confirm map save does not chain-AND later processes or steps.
4. Save extract-first and Qubit-first rows for the **same analysis and overlapping TAT**. Confirm map save succeeds because first-step allow-lists do not overlap.
5. Save a second extract-first row whose first-step allow-list overlaps the first extract-first row and whose TAT overlaps. Confirm **409**.
6. Route with zero acceptable rows (no analysis + TAT candidate, or no candidate whose first process/step accepts current type). Confirm **422** and no work order.
7. Using a fixture with two saved rows that both accept current type (e.g. change a Qubit-first first-step list so it also accepts the extract-first type), Route again. Confirm **409**; no silent `first()`.
8. Route with exactly one acceptable row and inspect the work-order snapshot order.
9. Choose Start; inspect created process instances. Complete or leave the first process, then invoke the later start. Confirm the second process instance and `work_order_route_position`.
10. Attempt a later process/step start with an empty or incompatible allow-list (sample still the inbound type; dest-type Hold is unchanged). Confirm **422** `route_sample_type`.

**Expect**
- Map row = analysis + TAT + ordered `process_definition[]`. UI preserves order. Allowed types are derived from the first process / first step, not admin-authored.
- Map save **409**s only when the same analysis, overlapping TAT, **and** overlapping first-step allow-lists all hold. Extract-first vs Qubit-first for the same TAT is legal. Blood extract + later DNA qPCR chain map-save is **click-save 201**, not AND.
- Zero acceptable rows returns **422** and mints no work order.
- Two saved rows that both accept this sample’s current type return **409**; no silent `first()`. **Unsigned this SHA** unless clicked.
- Exactly one row **snapshots the ordered list** and mints **zero Tests**.
- **First Start instantiates `chain[0]` only.** Scored on AC-P2-3 (ELISA first LimsRun, 1 step, no Qubit/qPCR Tests).
- **Later Start** = next pending process, on the sample that exists then. Route does not mint a process-of-processes.
- Map save/Route do not AND later-process or later-step allow-lists.
- Each later process/step start checks current type; empty or incompatible fails with **422** then. **This later-step type-gate was not click-run this SHA — leave unsigned, not Pass.**
- Dest-type Hold remains out; do not claim an earlier step changed type unless the product did so.

**Verified holds (click-save in the UI, not API-only — do not re-score):** `/admin/routing-map` has **no sample-type picker**. ELISA TAT **1–7** saved. Blood extract + later DNA qPCR chain saved (**no AND 422**). Second ELISA overlap **409**. Copy reads “First process is sample-type dependent. Later processes are not.” Empty Route **422** “No routing-map row accepts this analysis, TAT, and sample type”.

**Unsigned this SHA:** later-step type-gate at start (current tube). Route two-accept **409**.

---

## Live `8cfa2a9` per-AC sign-off

**Signed by Tobias, 2026-08-30; local docker compose, compose down.**

AC-P2-1 **Pass** (receive stay-on-form) · AC-P2-2 **Pass** (asked-for save 0 WO) · AC-P2-3 **Pass** (alice Route+Start first process only) · AC-P2-4 **publish-refuse Pass**; freeze skip **unsigned / not Pass** (`{}` on `99b692d3` is ambiguous) · AC-P2-5 **Pass** for routing-map **UI click-save** (ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved, no AND 422; second ELISA overlap 409) / empty Route 422; later-step type-gate **unsigned**. Do not re-score.

**Addendum (same stamp, do not re-score):** Routing-map Pass on `8cfa2a9` was **click-save in the UI**, not API-only: no sample-type picker; ELISA TAT 1–7 saved; Blood extract + later DNA qPCR chain saved (no AND 422); second ELISA overlap **409**. Later-step type-gate still **unsigned**. Everything else in this stamp stands.

**Overall P2 remains unsigned.** Do not write overall P2 Pass, signed Pass, or merge-ready. Hans: `{}` is ambiguous until classic `/tests` leaves NULL or a freeze marker exists. Hold product merge. Not IC50.

---

The preceding `8cfa2a9` section is retained verbatim as signed history (first Start `chain[0]`, empty Route 422, publish-refuse, routing-map UI click-save). It is not the current live stamp. Do not rewrite or transfer those observations to another SHA.

## Live AC-P2 stamp — `9342439` (AC-P2-9..11 Pass signed; overall P2 unsigned / not Pass)

**Not Pass overall.** Do **not** rewrite or transfer outcomes from `8cfa2a9`, `b005cfe`, `9c4f9da`, `3b56cfb`, or P1. AC-P2-5 Pass on `8cfa2a9` remains **analysis+TAT map / UI click-save** history. This block records Tobias’s `9342439` click.

**Branch / build tested:** `feat/work-order-p2` at `9342439` (`93424396ce3d02f01a8a8388abda39ae6ebf8010`). Docs merge `50c1f24` does not change the click SHA.

**QA signature:** Tobias — signed AC-P2-9..11 Pass below. **Overall P2 Pass remains unsigned and is not claimed.** Do **not** write overall P2 Pass.

**Executor / environment / date:** Tobias · local docker compose (`lims-*`) · 2026-08-30 · compose **down** after run
**Merge:** hold product merge of `feat/work-order-p2`. Not IC50.

**Leadership send:** [`.docs/discussions/2026-08-30-p2-route-lock.md`](../.docs/discussions/2026-08-30-p2-route-lock.md) — Round 1 **Leadership Confirmed**. Round 2 **Leadership Confirm** (R2-1…R2-4) landed 2026-08-30 (Rolf, Deiter, Hans, Heidi, Günter). **OQ-WO-6 stays OPEN** (Leadership Confirm that it stays Open). OQ-WO-4 / OQ-TAT-1 / OQ-WO-5 **Leadership Confirm** (round 1). Deiter / Hans / Heidi / Günter **confirmed Tobias’s `9342439` restamp** (honesty, **not** a merge vote). Not a merge stamp.

**Product under test (Leadership-confirmed lock; AC-P2-9..11 Pass; not overall P2 Pass):**
- Map row = TAT + ordered `process_definition[]`. **No** admin analysis picker and **no** admin sample-type picker.
- Create-route UI **displays** each selected process’s allowed sample types, LIMS Run analyses, and emerging types.
- Route assigns when (1) current sample type is on the **first process’s first** Experiment/LimsRun allow-list **and** (2) the asked-for analysis matches a **LimsRun somewhere in the route**.
- Zero acceptable → **422**. Two saved rows that both accept this type **and** this analysis → **409**. Never silent `first()`.
- Map save **409** only when overlapping TAT **and** overlapping first-step allow-lists **and** overlapping LimsRun analyses. Extract-first vs Qubit-first for the same TAT is legal. Two extract routes, same TAT and inbound types, **different** assays are legal.
- Map save **422** when the type emerging from process *x* is not accepted by process *x+1*. Emerging = aliquot/pool `default_dest_sample_type` on the last Experiment/LimsRun of *x* if set; else last-step accepted types. Dest-type mint remains Hold.

**Still OPEN, not this restamp:** Hans freeze skip (`{}` vs NULL). Classic `/tests` must leave `asked_for_params` NULL or we need a freeze marker. Extract LimsRun must **not** share asked-for `analysis_id` — analysis-in-chain does **not** close that; extract must not be ELISA or it freezes the panel Test at process 1. Route two-accept **409** unsigned that SHA (`8cfa2a9`). Dest-type mint **Hold**. Overall P2 unsigned.

| Slice on this SHA | Tobias |
|-------------------|--------|
| Create-route display: types + LimsRun analyses + emerging (no analysis/type picker) | **Pass** |
| Route: analysis on a **later** LimsRun in the chain | **Pass** |
| Route: asked-for analysis **not** in the chain → **422** | **Pass** |
| Map save: same first-step types, different LimsRun analyses, same TAT → **201** | **unsigned** — not claimed this click |
| Map save: dest DNA → next process accepts DNA → **201** | **Pass** |
| Map save: dest DNA → next process plasma-only → **422** | **Pass** |
| Map save: extract plasma (no dest) → qPCR DNA-only → **422** | **Pass** |
| Later-step type-gate (qPCR start on still-Blood / current type) — **not dest-type E2E** | **Pass** (Tobias). Leadership **Met**. |
| Dest-type mint / blood→DNA daughter | **out (Hold)** — after Start first extract, tube still Blood, **0 DNA daughters** |
| Freeze skip (`{}` vs NULL) | **OPEN** (not this restamp) |
| Extract LimsRun must not share asked-for `analysis_id` (extract must not be ELISA) | **OPEN** (not this restamp) |
| Overall P2 | **unsigned / not Pass** |

### AC-P2-9 — analyses come from LimsRuns in the chain

**Result:** **Pass** (Tobias signed, 2026-08-30, `9342439`)

1. Open `/admin/routing-map`. Confirm there is **no** analysis picker and **no** sample-type picker.
2. Build TAT + ordered processes: extract first (no asked-for analysis on its LimsRun), then a later process whose LimsRun is the asked-for analysis (e.g. ELISA or qPCR).
3. Save. Confirm **201** (not 422 for missing map analysis).
4. Record asked-for for that later-process analysis + overlapping TAT on a sample whose current type is on extract’s **first** Experiment/LimsRun allow-list.
5. Route.
6. Repeat with an asked-for analysis that appears on **no** LimsRun in the saved chain. Confirm **422**, no work order.

**Expect**
- Map row has no analysis field. Analyses are derived from LimsRun steps in the ordered processes.
- Route succeeds when current type is on first-process first-step **and** the asked-for analysis is a LimsRun somewhere in the chain.
- Route **422** when the analysis is not in the chain, even if TAT and first-step type match.
- Do **not** score `8cfa2a9` “map row = analysis + TAT” here. That SHA stays signed history.

**Verified holds:** **no** analysis/type picker; extract (Identity/Plasma) then ELISA click-save **201**; alice (`test:assign`) Route ELISA **200**; qPCR not in chain Route **422**, stayed `requested`, no WO.

### AC-P2-10 — create-route displays types, analyses, emerging

**Result:** **Pass** (Tobias signed, 2026-08-30, `9342439`)

1. Open `/admin/routing-map` create.
2. Add two processes. For each selected process, record that the UI shows: ordered steps, allowed sample types, LimsRun analyses, and emerging types.
3. Confirm the add-process list itself shows types and analyses (so the admin is not picking blind).
4. Reorder processes. Confirm display refreshes (first-process types follow the new first process; emerging of *x* vs accept of *x+1* updates).
5. Confirm Save stays disabled when first-process first-step types are empty, when the chain has no LimsRun analysis, or when a displayed handoff is incompatible.

**Expect**
- Display is derived, not admin-authored.
- No type picker. No analysis picker.

**Verified holds:** create-route derived (steps, types, LimsRun analyses, emerging); add-process list shows types+analyses; reorder refreshes; Save disabled on empty first-step types / no LimsRun analysis / incompatible handoff.

### AC-P2-11 — process *x* → *x+1* emerging-type handoff

**Result:** **Pass** for map-save (Tobias signed, 2026-08-30, `9342439`). Dest-type mint remains **Hold**. Do **not** fold dest-type mint or blood→DNA E2E as Pass.

1. Author extract whose last Experiment/LimsRun has an aliquot/pool dest of DNA, then Qubit/qPCR whose first step accepts DNA. Save. Confirm **201**.
2. Same extract dest DNA, next process first-step plasma-only. Save. Confirm **422**.
3. Extract with **no** dest (emerging = last-step accepted types, e.g. plasma) then Qubit DNA-only. Save. Confirm **422**.
4. Confirm execute still does **not** mint a DNA daughter (dest-type Hold). A 201 map save is catalog intent, not “the tube became DNA.”

**Expect**
- Handoff 422 is map-save, not Route chain-AND of inbound type.
- Dest-type mint remains Hold. Do not claim blood→DNA→Qubit E2E.

**Verified holds (map-save only):** dest-DNA extract → qPCR DNA **201**; dest-DNA → plasma-only **422**; no-dest Plasma → qPCR DNA **422**. Dest-type mint **Hold** — after Start first extract, tube still Blood, **0 DNA daughters**. Not blood→DNA E2E.

### Later-step type-gate (this SHA; not dest-type E2E)

**Result:** **Pass** (Tobias signed, 2026-08-30, `9342439`). Later qPCR start on still-Blood tube **422** `route_sample_type` (wrong type, sample not dead). This is **not** dest-type E2E. Leadership: later-step type-gate is **Met** on this SHA.

---

## Live `9342439` per-AC sign-off

**Signed AC-P2-9..11 Pass** — Tobias, 2026-08-30, local compose (down after). Product SHA `9342439`. Docs merge `50c1f24` does not change the click SHA. Round 2 **Leadership Confirm** landed (R2-1…R2-4; Rolf/Deiter/Hans/Heidi/Günter); OQ-WO-6 stays OPEN. AC-P2-9..11 Pass Results unchanged.

AC-P2-9 **Pass** (no analysis/type picker; extract Identity/Plasma then ELISA click-save **201**; alice Route ELISA **200**; qPCR not in chain Route **422**, stayed requested, no WO) · AC-P2-10 **Pass** (create-route derived; add-process types+analyses; reorder refreshes; Save disabled on empty first-step types / no LimsRun analysis / incompatible handoff) · AC-P2-11 **Pass** (map-save only: dest-DNA → qPCR DNA **201**; dest-DNA → plasma-only **422**; no-dest Plasma → qPCR DNA **422**) · dest-type mint **Hold** (tube still Blood, **0 DNA daughters**) · later-step type-gate **Pass** (later qPCR start on still-Blood **422** `route_sample_type`; not dest-type E2E).

**Leadership notes (Deiter / Hans / Heidi / Günter) — restamp honesty, not a merge vote.** Confirmed Tobias’s `9342439` click.

- Later-step type-gate is **Met** on `9342439`: qPCR-on-blood / still-Blood start **422** `route_sample_type` (current type vs that step; sample not dead). This is **not** dest-type E2E.
- AC-P2-11 / handoff Pass is **map-save only**. Dest mint **Hold** on this SHA is Start extract still Blood / 0 DNA — **history**, not a live ban on type-changing aliquot/pool execute.
- Freeze skip (`{}` vs NULL) stays **OPEN**.
- Extract sharing asked-for `analysis_id` stays **OPEN**.
- Route stays `test:assign`.
- No overall P2 Pass.

**Still OPEN — not this restamp:** freeze skip (`{}` vs NULL). Classic `/tests` must leave `asked_for_params` NULL or we need a freeze marker. **OQ-WO-6:** an earlier LimsRun must **not** share asked-for `analysis_id` (analysis-in-chain does not close that). Extract is **not** a special assay; type gates catch blood-on-Qubit.

**Honesty (not a Result rewrite):** Dest-type mint Hold on `9342439` is history of Start extract (tube still Blood, **0 DNA**), not a live ban on type-changing aliquot/pool execute.

**Overall P2 remains unsigned.** Do not write overall P2 Pass, signed Pass, or merge-ready. Hold product merge. Not IC50.

---

## Addendum (docs honesty after `9342439` — do not re-score)

Marc 2026-08-30. Does **not** rewrite Tobias Results above. Not Pass. Send: [`.docs/discussions/2026-08-30-p2-route-lock.md`](../.docs/discussions/2026-08-30-p2-route-lock.md) Round 2. **Leadership Confirm** of R2-1…R2-4 (2026-08-30; Rolf/Deiter/Hans/Heidi/Günter); OQ-WO-6 stays OPEN.

- Available routes for an asked-for assay = **any** map whose chain **contains** that LimsRun analysis. A route **may have multiple analyses**.
- Extract is not a special sample/assay. Blood→DNA is a **derivative**: a new Sample in a new container with `parent_sample_id`, while the parent Sample stays Blood. Tube→plate aliquot is equivalent (same Sample, extra container). Library is a new sample. Type gates on process steps catch blood-on-Qubit. The `9342439` Dest-type mint Hold above is Start-extract still Blood / **0 DNA** **history**, not a live ban on type-changing aliquot/pool execute — this bullet does not re-score that Result.
- The OPEN `analysis_id` punch is **OQ-WO-6**: any **earlier** LimsRun that reuses the asked-for analysis mints/freezes the panel Test on the parent. Extract is only usually process 1.
- Parser is chosen at **import**, not on the process.

---

## Live Deiter click — process assignment is a sample in a container (`0077`)

**Not Pass overall.** Do **not** transfer or rewrite `9342439` / `8cfa2a9` / P1 Results. Deiter clicked the Contents grain on product SHA **`4671ba8`** / assignment commit **`02fe95f`** (migration **`0077`** in that commit) on 2026-08-30. Docs Confirm SHA **`84d2810`** is not a new execute and is not the click SHA. This is a **Deiter (Lab Ops) click**, not a Tobias QA Pass and not a merge stamp. OQ-WO-6 and freeze skip stay **OPEN**.

| Slice | Deiter |
|-------|--------|
| C1 no-vessel / two-vessel 422 + receive-tube 201 | **Pass** |
| C2 equivalent aliquot dest-follows / source-removed / later Start dest container | **Fail** — execute mints dest; does not join dest or remove source; emptied-source assign 201 mix-up; PATCH is not a path |
| Dest mint Hold (Start extract still Blood, 0 DNA) | **Pass** |
| Overall P2 | **unsigned / not Pass** |

### AC-P2-C1 — assign is the tube in hand

**Result:** **Pass** (Deiter click, 2026-08-30, `4671ba8` / `02fe95f`).

1. Create a process definition instance.
2. Try to assign a sample that has **no** Contents. Confirm **422** `process_container_required`, lab-readable, and nothing assigned.
3. Take a sample sitting in **two** containers and assign it without a `container_id` pick. Confirm **422** and that the app did **not** silently pick a vessel.
4. Receive a tube (one container). Assign that sample by id. Confirm **201** and that `container_id` is the receive tube.

**Verified holds:** no-vessel assign **422**; two-vessel assign with no pick **422**; receive-tube assign **201**.

### AC-P2-C2 — equivalent aliquot: same sample, new container

**Result:** **Fail** (Deiter, 2026-08-30, `4671ba8` / `02fe95f`).

1. Start a work order (or process) with the receive tube assigned.
2. Execute an **equivalent aliquot** — the **same sample** moved into a **new container**.
3. Check whether the dest assignment joins the process.
4. Check whether the emptied inbound source assignment becomes `removed`.
5. Later Start of the next process in the route; check whether it carries the dest container rather than the original tube.

**Verified holds:** execute **mints dest**; it does **not** join dest or remove source; emptied-source assign returns **201 mix-up**; **PATCH is not a path**.

**Leadership Confirm of this Fail** (Rolf / Hans / Heidi / Günter, 2026-08-30) — Deiter remains the click. Wilhelmina folded the C2 Fail into sketch **`a3741d1`** and requirements **`60a9447`**. Do **not** treat C1/C2 as unsigned. Do **not** invent a Tobias Pass. Grok Build owns dest-join / source-remove.

- **Hans:** dest not on the process; emptied source still assignable (201) is the mix-up. Later Start would still follow the parent tube; results would not be attributable to the dest vessel.
- **Heidi / Mathilda / Wilhelmina:** Execute never writes the same-sample dest container onto `eln_process_samples`; join/release no-op without `entry.process_step_id`, so later Start via `_continuing_assignments` rides the emptied parent. Emptied-source assign **201** is leftover Contents at amount 0 (`_contents_for_sample` does not require remaining volume) — it must **422**, not dest-follow. Follow has to land in the **execute txn**: retarget `container_id`, or remove source then insert the dest pair. PATCH of `eln_process_samples` is not a path. Dest mint Hold is a different punch: a new Sample with `dest_sample_type` is not this fix. Equivalent aliquot is same sample, new container. Coding stays Grok Build.
- **Günter:** Emptied-source assign 201 is a leftover process-join — the wrong tube stays on the instance. Dest never lands on `eln_process_samples`. Dest mint Hold is a different punch.
- **Rolf:** QA restamps that Fail on `02fe95f` — do not treat C1/C2 as unsigned.

Do **not** teach dest-follows as shipped. Do **not** teach PATCH as the dest-follows path. The expected equivalent-aliquot behavior remains same sample, new container, with no new identity or `sample_type` rewrite, but this click did not verify that behavior.

### Dest mint Hold — distinct from AC-P2-C2

**Result:** **Pass** (Deiter, 2026-08-30, `4671ba8` / `02fe95f`).

**Verified holds:** Start extract still leaves the tube **Blood**, with **0 DNA** daughters.

This Hold Pass does not close `_execute_transfer` dest mint. AC-P2-C2 records that execute still mints dest and does not join dest or remove source. Do not fold the C2 Fail into the dest-mint Hold Pass.

Extract-hold UAT step **1.7** stays **OOB execute** with no Result stamp. It must not imply DNA on the parent: different dest type mints a **new derivative sample** in a new container with `parent_sample_id`; the parent stays. Test identity stays `(sample, analysis)` — the container is **which vessel was measured**, and a concentration write-through hits that container. Route stays `test:assign`. Sequencing data still not in NimbleLIMS.

---

The preceding Deiter click (`4671ba8` / `02fe95f`) is retained verbatim as signed history, including its original “Live” heading and Results (C1 **Pass**, C2 **Fail**, dest mint Hold **Pass**). It is not the current live stamp. Do not rewrite or transfer those observations to another SHA.

## Preceding dest-follow stamp — `570bbc0` Deiter Lab Ops Met

**Not Pass overall.** Deiter’s execute click on **`570bbc0`** (`570bbc01ff50fdac2d529448ceb95683c535401f`) is **Met for Lab Ops identity only**: same-type plate, DNA new Sample, and Later Start following the destination. It is not Tobias QA Pass. Execute joints stay **`1572071`**. Do **not** rewrite Deiter `02fe95f`, Tobias `9342439` / `8cfa2a9`, or P1. PATCH is not a path. Tobias QA restamp of C1/C2/C3 is the **live stamp `bf51b19`** below. **OQ-WO-6 extract CLOSED.** Hold merge. Not IC50.

**Leadership Confirm (2026-08-31):** extract is experiment / equipment execute on a process (not a LimsRun **today**; may be a LimsRun later if equipment is an instrument). Assay asked-fors have exactly one asked-for LimsRun. **If asked-for is Extracted DNA:** DNA tube only — no sequencing, **no other LimsRuns**. **Rolf/Marc:** After extract on an **assay** asked-for, Qubit / Nanodrop / other QC instruments are **supporting LimsRuns** that quantify DNA (own Tests). **Process QC is not an asked-for.** **No route branching:** WGS asked-for on blood owns WGS params (extract → seq); C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up (own params). **OQ-WO-6 extract CLOSED.** Not Pass.

| Slice | Deiter Lab Ops on `570bbc0` | Tobias QA on `bf51b19` |
|-------|-------------------------------|-------------------------|
| AC-P2-C1 assignment identity | **Met** | **Pass** (live stamp below) |
| AC-P2-C2 same-type dest-follow | **Met** | **Pass** (live stamp below) |
| AC-P2-C3 type-changing dest-follow | **Met** | **Pass** (live stamp below) |
| Overall P2 | **not Pass** | **unsigned / not Pass** |

**Leadership Confirm** (Rolf / Deiter / Hans / Heidi / Günter): two grains at execute — C2 same-type destination; C3 derivative destination. Dest exists only after aliquot/pool execute; Route / Start / map-save / asked-for mint zero daughters; receive identity + first vessel is not dest mint. C2 leftover inbound volume is whatever was not transferred — emptying is not required.

`9342439` Dest-type mint Hold stays Start-extract still Blood / **0 DNA** history — **not** a live ban on type-changing execute.

### AC-P2-C2 — same dest type (tube → plate)

**Lab Ops Result:** **Met** (Deiter execute click on `570bbc0`; Lab Ops identity only, not Tobias QA Pass).

**Tobias QA Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Execute joints remain **`1572071`**. Do **not** rewrite Deiter Met. Do **not** score Blood→DNA here — that is AC-P2-C3. Stack down after.

**Setup (numbered)**
1. Receive one tube. Receive does **not** weigh it and often leaves Contents `amount` **NULL**.
2. Asked-for. Route a two-process map whose first process has an Aliquot / pool plan experiment. First Start. Confirm the receive tube is on process 1 and the plan dest type is **Same as parent.** (blank).
3. **Before execute, set a tracked source amount (and units) so the transfer can run.** Receive does not weigh. For fixture setup, use `PATCH /containers/{container_id}/contents/{sample_id}` with `amount` (`sample:update`; this is Contents setup, not an `eln_process_samples` PATCH). If execute returns **400** `source_amount_null`, set the tracked amount and retry; that response is a fixture gap, not dest-follow Fail. Do **not** require the amount to empty the tube.

**Steps**
1. Execute Aliquot — by volume (or by target amount). Transfer **some** of the source into a **new container**. Do **not** require the source tube to go to amount 0. Leftover on the inbound tube is whatever was not transferred.
2. Confirm **no new Sample row**: dest `sample_id` is the receive sample. Dest `container_id` is not the receive tube. Sample type is unchanged.
3. Confirm process 1’s **active** assignment is that dest container (same sample). The inbound-tube assignment is **`removed`** even if that tube still has leftover volume.
4. Later Start the next process. Confirm it carries the **dest container**, not the original tube.

**Expect:** steps 1–4 are the fair click: same `sample_id`, new `container_id`, destination on the process, inbound assignment `removed` even with leftover volume, and Later Start follows the destination. **Fail C2** if execute creates a new Sample, the destination is not on the process, or Later Start follows the parent tube. Leftover volume on the inbound tube is **not** a Fail.

**Edge (not C2 core):** If the transfer **does** leave amount 0 on the inbound tube, assigning that container is **422** `process_container_required`. If leftover remains, that tube is still a vessel with Contents; it is just not the process assignment.

**Observations (not fails):**
- **No dest at Route or Start.** Dest does not exist until execute. Route / map-save / asked-for mint **zero** daughters. Process 1 carrying only the receive tube before step 1 is correct. Do **not** treat no dest at Route or Start as dest-follow Fail.
- **A DNA execute is AC-P2-C3**, not a C2 Fail. Score type-changing dest there; do not fold Blood→DNA into C2.
- **400 `source_amount_null`** is the Setup fixture gap above, not dest-follow Fail. Do **not** treat execute 400 `source_amount_null` as dest-follow Fail.
- **Leftover inbound volume** is whatever was not transferred. Emptying is not required.

### AC-P2-C3 — different dest type (Blood → DNA)

**Lab Ops Result:** **Met** (Deiter execute click on `570bbc0`; Lab Ops identity only, not Tobias QA Pass).

**Tobias QA Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Execute joints remain **`1572071`**. Do **not** rewrite Deiter Met. Do **not** fold into C2. Same click as extract-hold UAT **1.7**. Stack down after.

**Setup (numbered)**
1. Use the prepared tracked-amount fixture from C2; 400 `source_amount_null` is setup, not dest-follow Fail.
2. Set a catalog destination on the plan (e.g. Blood × aliquot → DNA). First Start still leaves the parent **Blood**.

**Steps**
1. Execute aliquot with dest type **DNA** (not Same as parent).
2. Confirm a **new Sample** in a **new container**, `parent_sample_id` = the receive sample. Dest type is DNA. The parent Sample is still Blood; it is not retargeted onto the DNA tube.
3. Confirm process 1’s **only active** assignment is dest sample + dest container. The inbound source assignment is **`removed`**.
4. Later Start the next process. Confirm it carries the **DNA dest pair**, not the Blood tube.

**Expect:** steps 1–4 are the fair click: new Sample + new container, parent still Blood, destination pair is the only active assignment, and Later Start follows DNA. **Fail C3** if the destination tube lands on the Blood Sample, the parent `container_id` is retargeted, the destination is not on the process, or Later Start follows Blood.

**Observations (not fails):**
- **Parent still Blood at Start extract.** Start is not execute and dest does not exist yet. The `9342439` dest-type mint Hold (still Blood / 0 DNA) is history, not a live ban on type-changing execute.
- **No dest at Route or Start.** Route / map-save / asked-for mint **zero** daughters; the plan dest type is catalog intent, **not** a Sample. Do **not** treat no dest at Route or Start as dest-follow Fail.
- **400 `source_amount_null`** is the C2 Setup fixture gap (receive amount often NULL), not dest-follow Fail.

Route / Start / map-save / asked-for still mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint. Dest exists only after execute. That is not this click.

Deiter C2 **Fail** on `02fe95f` stays history. `9342439` untouched. Deiter’s `570bbc0` execute is Lab Ops **Met**. Tobias QA of C1/C2/C3 is **Pass** on **`bf51b19`** (live stamp below). **OQ-WO-6 extract CLOSED.** Overall P2 remains **unsigned / not Pass**. Hold merge. Not IC50.

---

The preceding dest-follow stamp (`570bbc0` Lab Ops Met; C2/C3 numbered) is retained as Lab Ops history. Tobias QA Results for those numbered ACs, plus cardinality / freeze skip / sequential asked-fors, are the live stamp below.

## Live AC-P2 stamp — `bf51b19` (per-AC Pass; overall P2 unsigned / not Pass)

**Not Pass overall.** Do **not** rewrite `8cfa2a9`, `9342439`, Deiter `02fe95f`, or P1. Do **not** rewrite Deiter Met on `570bbc0`.

**Branch / build tested:** `feat/work-order-p2` at `bf51b19` (`bf51b192b417663f677b80be6d8b9afd790cb78a`). Alembic **`0078`**. Execute joints remain **`1572071`**. UAT numbering SHA `570bbc0` is **not** this click SHA.

**QA signature:** Tobias — signed per-AC results below. **Overall P2 Pass remains unsigned and is not claimed.** Freeze skip NULL is **Pass** on this SHA. **Merge hold is closeout 1.2 dest-cohort lookup** after C3 (asked-for by dest `sample_id` → `{}`), not freeze skip. Hold product merge. Stack **down** after. Not IC50.

**Standing UAT rule (Leadership Confirm 2026-09-01, Rolf/Deiter/Hans/Heidi/Günter):** after **two** UAT attempts on the same issue, the **next** run needs a written “what we are testing and why” **before** the click — fixtures, Pass/Fail, and what is **not** a Fail. Do **not** rewrite signed Results on this stamp to satisfy that rule.

**Executor / environment / date:** Tobias · local docker compose (`lims-*`) · 2026-08-31 · compose **down** after run

| AC | Tobias |
|----|--------|
| AC-P2-C1 assignment identity | **Pass** |
| AC-P2-C2 same-type dest-follow | **Pass** |
| AC-P2-C3 type-changing dest-follow | **Pass** |
| AC-P2-card-1 two ELISA LimsRuns map-save **422** | **Pass** |
| AC-P2-card-2 extract process + Qubit + ELISA map-save **201** | **Pass** |
| AC-P2-card-3 Route asked-for count 0 or 2+ **422** | **Pass** |
| AC-P2-qc-1 Qubit supporting LimsRun, own Test | **Pass** |
| AC-P2-4 freeze skip NULL | **Pass** — classic `/tests` **NULL**; first start wrote `{cell_line: A549}`; later start left it |
| AC-P2-5 addendum Route two-accept **409** | **Pass** |
| AC-P2-seq-1 sequential asked-fors (two WOs) | **Pass** — dest-cohort params (closeout **1.2**) **not scored** |
| Overall P2 | **unsigned / not Pass** |

**Do not re-score** empty Route 422 / map overlap 409 / first Start `chain[0]` / publish-refuse / AC-P2-9..11. Those stay signed history. `{}` on `99b692d3` stays `8cfa2a9` history of a **new** Test write, not this freeze-skip Pass.

### AC-P2-card-1 — map-save two ELISA LimsRuns

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Stack down after.

**Setup**
1. Admin `/admin/routing-map`. No analysis or sample-type picker.
2. Author **one** process whose chain has **two LimsRun steps** with the **same** analysis (e.g. two ELISA). First step has accepted types. Extract is **not** this AC.

**Steps**
1. Save the map.

**Expect:** **422** `route_sample_type`. Message: a LIMS Run analysis may appear only once; two LimsRuns with the same analysis are refused. No row saved. That is **not** QC.

**Fail** if save is **201**.

### AC-P2-card-2 — extract process + Qubit + ELISA

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Stack down after.

**Setup**
1. Process 1 = **extract** as an Experiment (aliquot/pool plan). **No** `analysis_id` on extract. Dest type DNA (or same-as-parent if the next process accepts inbound).
2. Process 2 = Qubit **LimsRun** (other analysis).
3. Process 3 = ELISA **LimsRun** (the asked-for assay).
4. Handoff types accept: extract emerging type is accepted by Qubit first step; Qubit emerging is accepted by ELISA first step.

**Steps**
1. Save TAT + that ordered chain.

**Expect:** **201**. Asked-for ELISA appears **once**. Qubit is a supporting LimsRun. Extract is a process and is not counted.

**Fail** if 422 because extract “has no analysis,” or because Qubit is treated as a second ELISA.

### AC-P2-card-3 — Route 422 when asked-for count is 0 or 2+

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Stack down after. Do **not** re-score empty Route Pass on `8cfa2a9`.

Do **not** re-score empty Route Pass on `8cfa2a9`.

**Steps**
1. Asked-for ELISA on a received tube. Route against a map whose LimsRuns do **not** include ELISA (e.g. Qubit-only). Confirm **422**, row stays `requested`, **0** work orders.
2. (Legacy / QA fixture only.) A map whose chain has **two** ELISA LimsRuns — map-save now refuses this, so insert is a fixture if needed. Route ELISA. Confirm **422**, stays `requested`, **0** work orders.

**Expect:** for an **assay** asked-for (this AC: ELISA), the asked-for analysis must appear on **exactly one** LimsRun. 0 or 2+ → **422**. Never silent `first()`. **Not this AC / closeout 1.4:** Extracted DNA asked-for may have **zero** LimsRuns (DNA tube only) — do not Fail that ask type here.

### AC-P2-qc-1 — supporting Qubit in the same route

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Stack down after.

**Setup:** Use the AC-P2-card-2 map (extract process + Qubit LimsRun + ELISA LimsRun). Route a blood (or inbound-type) tube as **ELISA** asked-for.

**Steps**
1. Route. Confirm one WO, ELISA asked-for, snapshot includes extract → Qubit → ELISA.
2. Start extract (process). Do **not** expect an ELISA Test at extract start.
3. Later Start Qubit LimsRun and start that run. Confirm a Test `(sample, Qubit)` — **own** Test, not the ELISA Test.
4. Later Start ELISA LimsRun and start that run. Confirm a Test `(sample, ELISA)` with asked-for params freeze. ELISA still appears **once**.

**Expect:** Qubit is not a second asked-for. Do **not** put Qubit/Nanodrop on extract. Do **not** fold Qubit into the ELISA `analysis_id`.

**Fail** if extract start writes the ELISA Test, or if Qubit start writes ELISA params onto `(sample, ELISA)`.

### AC-P2-4 — freeze skip NULL (live restamp)

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Classic `/tests` **NULL**; first start wrote `{cell_line: A549}`; later start left it. Do **not** transfer `8cfa2a9` (`{}` on `99b692d3`) as this Result. That write is history of a **new** Test, not classic skip. Stack down after.

**Requires `0078`.** If classic `/tests` still stores `{}`, rebuild the backend and stop — that is setup, not a skip Pass.

**Steps**
1. Receive. Asked-for with a real param (e.g. `cell_line`). Route a one-assay LimsRun map.
2. **Before** LimsRun start, classic `POST /tests/` for that `(sample, analysis)`. Inspect `asked_for_params`.
3. `PATCH /v1/lims-runs/{id}/start` for the asked-for analysis. Re-read `asked_for_params`.
4. Change the asked-for params. Start a **second** LimsRun over the same cohort and analysis. Re-read `asked_for_params`.

**Expect**
- Step 2: classic row is **NULL** (not `{}`).
- Step 3: first start **writes** the asked-for snapshot onto that Test (does not mint a second Test).
- Step 4: later start does **not** overwrite. Frozen `{}` (a prior first-start empty write) also must not overwrite — that is locked empty, not classic NULL.

**Fail** if classic stores `{}`, if first start skips the NULL row, or if later start overwrites.

**Not this AC:** publish-refuse (`test_missing` 422) — already Tobias-signed Pass on `8cfa2a9`.

### AC-P2-5 addendum — Route two-accept 409

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`). Do **not** re-score AC-P2-5 click-save Pass on `8cfa2a9`. This is only step 7 of that AC. Stack down after.

**Steps**
1. Two saved maps that both accept this sample’s current type **and** this asked-for analysis (e.g. widen a Qubit-first first-step list so it also accepts the extract-first type, same assay in both chains).
2. Route.

**Expect:** **409**. No silent `first()`. No work order. Asked-for stays `requested`. No picker this phase.

### AC-P2-seq-1 — sequential asked-fors (WGS then WES)

**Result:** **Pass** (Tobias, 2026-08-31, `bf51b19`) — two WOs. Dest-cohort params (closeout **1.2**) **not scored**. **No route branching.** Dest does **not** auto-join a second WO. Stack down after.

**Setup**
1. WGS route: **blood** inbound. Process 1 = extract (Experiment, dest DNA). Process 2 = WGS sequencing LimsRun (exactly one asked-for LimsRun). WGS asked-for **owns WGS params**.
2. WES route: **DNA** inbound. Post-extract → WES sequencing LimsRun. **No** extract on this route.

**Steps**
1. Route blood as WGS. C3 execute mints the DNA tube. A **C2 aliquot** of that DNA continues the **WGS** WO (same asked-for, WGS params).
2. Record a **new asked-for on the DNA tube** for WES (own params). Route WES. That DNA tube is then **aliquoted or used up** on the WES WO.
3. Confirm **two** asked-fors, **two** param snapshots, **two** WOs. Dest from WGS extract does **not** appear on the WES WO until WES Route/Start.

**Expect:** Do **not** copy WGS params onto WES. Do **not** teach one WO splitting to two assays.

**Not this AC:** WGS params freeze onto a Test whose cohort sample is the **DNA dest** (WO-7 still looks up asked-for by cohort `sample_id` — closeout **1.2**, not coded). **Not scored** on this stamp. Do Fail seq-1 if dest auto-joins WES or WES is not a new asked-for on the DNA tube.

---

## Live `bf51b19` per-AC sign-off

**Signed by Tobias, 2026-08-31; local docker compose, compose down.**

AC-P2-C1 **Pass** · AC-P2-C2 **Pass** · AC-P2-C3 **Pass** · AC-P2-card-1 **Pass** · AC-P2-card-2 **Pass** · AC-P2-card-3 **Pass** · AC-P2-qc-1 **Pass** · AC-P2-4 freeze skip NULL **Pass** (classic NULL; first start `{cell_line: A549}`; later start left it) · AC-P2-5 addendum Route two-accept **409** **Pass** · AC-P2-seq-1 **Pass** (two WOs; dest-cohort 1.2 not scored).

**Overall P2 remains unsigned / not Pass.** Do not write overall P2 Pass, signed Pass, or merge-ready. Stack down. Not IC50.

---

## Science — OQ-WO-7 OPEN on the merge — 2026-09-01

**Not a restamp of Tobias Results above.** Does **not** rewrite `bf51b19` per-AC Pass, `8cfa2a9`, `9342439`, P1, Deiter `02fe95f`, or Deiter Lab Ops Met on `570bbc0`. Not IC50.

**Science:** Per-AC on `bf51b19` **Pass**. **Overall P2 stayed unsigned.** We merged (`5040f2d`) with **OQ-WO-7 OPEN** (WGS params on the DNA Test from the WO after C3). Seq-1 on this stamp did **not** score dest-cohort params. Clarifying the issue made the product better. Leftover **`9f86d14`** on product SHA **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`) **is** the OQ-WO-7 Grok Build work (pytest for this AC in that same commit). **Do not recode.** Remaining work is **Tobias**, not a new design. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. Do **not** invent Tobias Pass. Do **not** pretend `5040f2d` was held for it. Not IC50.

---

## AC-P2-OQ-WO-7 — WGS params on the DNA Test from the WO after C3

**Living AC** (not a restamp of `bf51b19`). Does **not** rewrite Tobias Results on `bf51b19`, `8cfa2a9`, `9342439`, P1, Deiter `02fe95f`, or Deiter Lab Ops Met on `570bbc0`. Not IC50.

**Result:** **Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `(DNA, WGS)` has `asked_for_params` **`{library_kit: TruSeq}`** from blood work order **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`). **Was not recoded.** **OQ-WO-7 Closed.** Closeout **1.4** stays later (Extracted DNA zero assay LimsRuns) — still **OPEN**. Overall P2 remains **unsigned**. Does **not** rewrite `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f`. Not IC50.

**Product SHA:** **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`). Leftover **`9f86d14`** on that SHA **is** the OQ-WO-7 Grok Build work. **Do not recode.** Pytest for Hans **AC-P2-OQ-WO-7** landed in `9f86d14`.

**CEO Accept (Rolf, 2026-09-01):** Accept of this written what/why **before Tobias**. That Accept’s “Grok Build codes first” is **done** (`9f86d14` on `80f054b`).

**OQ:** [OQ-WO-7](../.docs/review/open-questions/post-receive-work-spine.md) is **Closed.** Closeout **1.4** is a different OPEN if still listed. Overall P2 remains **unsigned**.

**Lookup already on `80f054b`:** (1) WO asked-for **only if** `asked.analysis_id == run.analysis_id` so Qubit/Nanodrop do not steal WGS `{library_kit: TruSeq}`; (2) else walk `parent_sample_id` for a routed asked-for of that analysis; (3) else `{}`; (4) freeze skip: write onto NULL; do not overwrite an already-frozen payload including locked empty `{}`.

**What / why:** After C3, WGS LimsRun starts on DNA; asked-for WGS with params still on blood. Lookup by dest `sample_id` only used to freeze `{}` on Test `(DNA, WGS)`. Freeze from the work order’s asked-for. Not Qubit. Not extract=LimsRun. Not dest-follow.

**Fixture:** Receive blood → asked-for WGS with real param (e.g. `library_kit: TruSeq`) → Route extract (dest DNA) → optional Qubit → one WGS LimsRun → C3 execute → Later Start WGS on DNA.

**Pass:** Test `(DNA, WGS)` has `{library_kit: TruSeq}` from the blood WO asked-for.

**Fail:** `{}` / missing kit; WGS Test on blood; assay hung on extract.

**Not a Fail:** no dest at Route/Start; `source_amount_null`; Qubit empty supporting freeze; 1.4; ELISA on a second blood tube.

**Out of this AC / do not fold as this work:** dest-follow, extract-as-LimsRun, freeze skip, cardinality, Route 409, closeout 1.4.

## Docs-only CEO Confirm addendum — Quantified DNA / OQ-WO-8 (1–6 stands; stayed OPEN on this fold) — 2026-09-02

**Not a UAT Result.** Does **not** rewrite any Result / Pass block above (`bf51b19`, OQ-WO-7 Pass on `80f054b`, `9342439`, P1, `02fe95f`). No product code. Not IC50.

**CEO Confirm 1–6 (Rolf)** plus Qubit-reuse punch. Wear existing **Qubit**. Do **not** mint a second catalog analysis named Quantified DNA. Old 1.4 (zero LimsRuns) **struck**. **422 on 0 LimsRuns is right** for this SKU. Extract stays experiment. WGS/ELISA: Qubit stays process QC. Tube-only DNA later SKU. Quantified DNA is an assay ask (data); Test `(DNA, Qubit)` is the ask.

**Named asked-for LimsRun slot** (Heidi/Günter: Route must name the asked-for LimsRun slot, not any-chain-contains-Qubit) was a **punch pending Leadership Confirm** on this fold. It is **not** part of 1–6. **1–6 stands.** **Superseded** by the Full Leadership Confirm addendum below.

**OQ-WO-8 stayed OPEN** on this CEO Confirm fold until Deiter / Hans / Heidi / Günter stamped.

Send: [`.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md`](../.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md).

## Docs-only Full Leadership Confirm addendum — OQ-WO-8 Closed (named asked-for LimsRun slot) — 2026-09-02

**Not a UAT Result.** Does **not** rewrite any Result / Pass block above (`bf51b19`, OQ-WO-7 Pass on `80f054b`, `9342439`, P1, `02fe95f`) or the CEO Confirm 1–6 addendum. No product code. Not IC50.

**Full Leadership Confirm** (Rolf / Deiter / Hans / Heidi / Günter). **OQ-WO-8 Closed.** Named asked-for LimsRun slot is no longer pending. **CEO Confirm 1–6 stands.**

Map / Route **names the asked-for LimsRun slot**. Eligibility is `asked.analysis_id` vs **that slot**, not “any chain that contains Qubit.” A WGS map with Qubit as process QC must **not** steal a Quantified DNA ask (409 / wrong join). Same OQ-WO-7 lookup after C3; **do not recode.** Product code may start after this fold is on `main`.

Send: [`.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md`](../.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md).

---

## AC-P2-OQ-WO-8 — named asked-for LimsRun slot and manual route assignment

**Brief date:** 2026-09-03
**Authority:** Full Leadership Confirm (Rolf / Deiter / Hans / Heidi / Günter)
**Product under test:** `feat/p2-named-slot` at **`6244bf6`** (`6244bf6e742c4ed0f046ff8770e2b8c112446fb3`) · Alembic **`0079`**
**Result:** **Pass** (Tobias, 2026-09-03, `6244bf6`). This per-AC Result is distinct from the overall QA Result below.

This addendum does not rewrite any signed Result above, including `bf51b19`, `80f054b`, `9342439`, P1, `02fe95f`, or Deiter Lab Ops Met on `570bbc0`. OQ-WO-8 Closed history from PR 119 remains Closed. OQ-WO-7 remains Closed and is not recoded.

**Supporting context for this click SHA:** Heidi Architecture **Accept** and Günter CSO **Accept** `6244bf6`; Deiter Lab Ops supplied the Pass/Fail boundary. This is not a Hans Science Accept.

### What and why

Route compares `asked.analysis_id` with the map’s persisted, author-named asked-for LimsRun slot at `routing_map.asked_for_step_id`. Chain containment is insufficient because WGS may include Qubit as process QC; that WGS map must not accept a Quantified DNA ask.

### Fixture

1. Use the existing Qubit catalog analysis for Quantified DNA; do not create a second Quantified DNA analysis.
2. Author map A for Quantified DNA with Qubit as the named asked-for LimsRun slot.
3. Author map B for WGS where Qubit is only process QC and WGS is the named asked-for LimsRun slot.
4. Prepare a Quantified DNA asked-for row whose current sample type and TAT otherwise fit both maps.
5. Prepare two additional active maps whose named asked-for slot is Qubit and whose TAT and first-step type both accept that same asked-for row.

### Numbered execution

1. Route the Quantified DNA ask with only map A eligible by named slot.
2. Confirm map A mints one work order and that map B is excluded even though its chain contains Qubit.
3. Remove or deactivate all acceptable named-slot maps and Route again with a fresh Quantified DNA ask.
4. Confirm **422**, no work order, and asked-for remains `requested`.
5. Restore two or more acceptable Qubit-slot maps and Route a fresh Quantified DNA ask.
6. Confirm the UI shows a route picker with the acceptable candidates and mints no work order before selection.
7. Select one route and submit its `routing_map_id`.
8. Confirm exactly one work order is minted from the selected route and the asked-for becomes `routed`.

### Pass

- Quantified DNA routes to the named Qubit slot at `routing_map.asked_for_step_id`.
- WGS+Qubit-as-process-QC does not steal the ask.
- Zero acceptable maps returns 422 and mints nothing.
- Two or more acceptable maps return **409** `route_pick_required`; the picker mints only after the tech selects one.

### Fail

- Eligibility uses containment anywhere in the chain.
- The WGS map wins through a wrong join.
- Two or more candidates silently use `first()` or mint before selection.
- A second catalog analysis named Quantified DNA is required or created.

### Not a Fail

- OQ-WO-7 behavior after C3.
- Destination follow.
- Historical zero-LimsRun 1.4 copy.
- ELISA on a second tube.

### Result

**Pass** — Tobias, 2026-09-03, `feat/p2-named-slot` @ **`6244bf6`** (Alembic `0079`). One named Qubit slot minted; zero acceptable maps returned **422**; two or more returned **409** `route_pick_required` and minted only after selection; WGS+Qubit-as-process-QC did not steal Quantified DNA. Eligibility used `asked.analysis_id` against `routing_map.asked_for_step_id`, not containment.

---

## Tobias overall P2 Pass — QA

**Result:** **Pass** (Tobias QA, 2026-09-03, `6244bf6`).

This overall QA Result folds the per-AC Pass set on **`bf51b19`**, **AC-P2-OQ-WO-7 Pass** on **`80f054b`**, and **AC-P2-OQ-WO-8 Pass** on **`6244bf6`**. The historical Results remain on their original SHAs and are not rewritten.

**Leadership overall Pass remains unsigned / not Pass.** This Tobias QA Result is not a Leadership overall stamp and does not authorize inventing one.
