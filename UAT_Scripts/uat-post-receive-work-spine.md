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

## Live AC-P2 stamp — `9c4f9da` (unsigned)

**Branch / build to test:** `feat/work-order-p2` at `9c4f9da` (`9c4f9da61965c7bfd01692622102dc18e332dd39`)  
**QA signature:** _Unsigned. QA must execute and sign this exact SHA._  
**Merge gate:** Hold merge of the product branch until QA signs this SHA.  
**History boundary:** Do not copy outcomes or observations from `3b56cfb` into this live stamp. In particular, the prior alice visibility, `sample_type` versus `sample_types`, and unclickable-publish observations describe only that earlier SHA.

**Product context to verify, not re-implement:** process definitions are visible to lab technicians as lab catalog; Routing map uses `sample_types`; Lists accepts the singular alias; Administrator and Lab Manager have seeded `experiment:publish`.

**Copy locks:** Receive ≠ order ≠ work. Receive stays on `/receive`. Asked-for is an unnumbered later look-up. Route is a later planner. Minting a queued `work_order` is not work begun; **Start process** is the later action. A **422** `route_sample_type` means the analysis/sample-type pairing is wrong for a mapped step, not that the sample is broken. Test creation/attachment and params freeze at LimsRun start. Publish refuses the whole run if any required Test is missing. Not IC50.

### AC-P2-1 — Route is a later planner, never after-receive

1. As lab-tech, receive a sample on `/receive`.
2. Confirm the successful receive stays on `/receive`, clears the barcode, and is ready for the next tube.
3. In a separate later task, open `/asked-for`, save requested analysis + TAT, and confirm that task ends on `/asked-for`.
4. Later still, return to the `requested` row and choose **Route** or **Route selected**.

**Expect**
- Receive offers no analysis or Route action and does not navigate to `/asked-for`.
- Asked-for is a later look-up, not the next numbered receive step and not a Start queue.
- Save does not auto-route. Only the later explicit Route action evaluates the routing map.

### AC-P2-2 — Asked-for save mints no work_order

1. Record `COUNT(work_orders)` and `COUNT(tests)` for an already-received sample.
2. `POST /v1/asked-for` with an active analysis, TAT ≥ 1, and valid `params` (`{}` is acceptable).
3. Recount before invoking either Route endpoint.

**Expect**
- The new row is `requested`.
- `COUNT(work_orders)` and `COUNT(tests)` are unchanged. No Process, Experiment, or LimsRun is created.
- Params remain intent only; they are not frozen.

### AC-P2-3 — queued mint is planning; Start process begins the process

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

### AC-P2-4 — WO-7 freezes Test + params at LimsRun start; publish is all-or-nothing

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

### AC-P2-5 — type gate means wrong pairing, not broken sample

1. For a `requested` row, confirm an empty routing map returns **200** `no_route` and mints nothing.
2. Using existing configured sample types, try to save a map whose candidate definition has an empty accepted-type set.
3. Configure a candidate step to accept only a different sample type and retry map save.
4. After creating a valid map, remove the current sample type from a mapped step and Route another matching requested row.

**Expect**
- Empty map leaves the row `requested` and creates zero work orders and zero Tests.
- Empty or incompatible accepted-type sets fail map save and Route with **422** `detail.code = route_sample_type`.
- The error identifies a wrong analysis/sample-type pairing for a mapped step. It does not mark or imply that the sample is broken.
- Every step in every mapped process definition must accept the current sample type.

### Supplemental P2 regression — overlapping TAT ranges

1. Create two active routing-map rows for the same analysis and sample type with overlapping inclusive TAT ranges.
2. Expect the second save to return **409** and create no overlapping row.

---

## Live sign-off

**AC-P2 on `9c4f9da`:** _Unsigned — QA executor, date, environment, and evidence to be added only after this exact SHA is exercised._

P1 remains the historical **Pass** on `c649245`; this live P2 section does not alter it. Hold merge of `feat/work-order-p2`.
