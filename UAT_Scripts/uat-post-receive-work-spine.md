# UAT: Post-receive work spine — P1 asked-for

**Stem:** `post-receive-work-spine`  
**Phase:** P1 asked-for lake (P2–P5 **not** in this stamp)  
**SoT:** `.docs/review/requirements/post-receive-work-spine.md` RQ-AF-* · [asked-for.md](../manuals/asked-for.md) · [HOWTO.md](../manuals/HOWTO.md)  
**UI:** `/asked-for` (Sample Mgmt → **Asked-for**) + sample-detail Asked-for section. A **later look-up**, not the after-receive click and not a Start queue  
**API:** `POST /api/v1/asked-for` · `GET /api/v1/asked-for` · `POST /api/v1/asked-for/{id}/cancel`  
**Env:** local docker compose (`lims-*`); http://localhost:3000 + :8000. Compose **down** after the run. Not IC50. P1 lake only.  
**Build / commit:** `c649245` (`c6492455200fa69c2093865615f82ada23b8d2b1`, 2026-08-28)  
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

## P2 — Route / work_orders / WO-7 (stamp on `3b56cfb`)

**Result of this stamp:** **P2 not Pass**. Hold merge. Do **not** collapse with P1 (`c649245` / PR **#81**) or receive CORE (`uat-atomic-receive.md`). Not IC50. Do **not** seed blood→Qubit.

**Phase:** P2 Route / work_orders / WO-7 Test-at-LimsRun-start  
**UI:** `/asked-for` Route · `/admin/routing-map` · `/work-orders` · process definition accepted sample types  
**API:** `POST /v1/asked-for/{id}/route` · `/v1/routing-map` · `POST /v1/lims-runs` · LimsRun start  
**Env:** local docker compose (`lims-*`); http://localhost:3000 + :8000. Compose **down** after the run. Not IC50.  
**Build / commit:** `3b56cfb` (`3b56cfb8f2a111b278c3d8b4c546bf6e5bf9116c`, `feat/work-order-p2`, 2026-08-28 ET / 2026-08-29 UTC)  
**Executor:** Tobias. Click: `alice-tech` three motions (receive stay-on-form, asked-for later look-up, Route). Admin used only for routing-map / process-definition setup.  
**Date:** 2026-08-28 ET  
**Dest-type Hold** unchanged. Receive freeze unchanged.

**Motions (not ACs)** — three separate motions; do not run as one chain from receive.

1. **Receive (precondition).** `alice-tech` `/receive` barcode `NBIO-P2-0001` → sample name `mAb-2301 PK Study-05` (`e382ebb5-3b7e-443c-a01f-6ef1e6abd095`). Sticky Plasma / mAb-2301 PK Study / Cryovial. Stayed on `/receive`. Zero Tests. Then left to Dashboard, **not** asked-for. Receive freeze: `POST /samples/receive` with `analysis_ids` → **422**.
2. **Asked-for later look-up.** ELISA TAT **2** on Study-05. Status `requested`. 0 Tests, 0 `work_orders`. Copy: requested analysis, no Start / Execute. Route CTA present (per-row + **ROUTE SELECTED**). Save did **not** mint a work_order.

Admin is not a tube-tech actor for these motions. Admin is setup only (routing-map / process definition).

### AC-P2-1 — Empty map stays requested

**Result:** **Pass** (click, `alice-tech`, 2026-08-28 ET, `3b56cfb`)

**Steps**
1. Asked-for `requested`. No routing-map row for that analysis × type × TAT.
2. Route.

**Expect**
- 200 `no_route`. Status still `requested`. Zero work_orders. Zero Tests.

**Verified holds:**
- `POST /v1/asked-for/{id}/route` → **200** `{no_route: true, work_order: null}`.
- UI banner: “1 with no routing-map match (stayed requested)”.
- Status still `requested`. WOs **0**. Tests **0**.

### AC-P2-2 — Type gate 422

**Result:** **Pass** (API, 2026-08-28 ET, `3b56cfb`). UI map save blocked — leftover config **observation**, not extract-hold, not a tube-tech fail.

**Steps**
1. LimsRun (or experiment) step with empty accepted types, or types that do not include the sample’s current type.
2. Save routing map **or** Route.
3. **Expect:** **422** `route_sample_type`. Blood → Extract → Qubit still refuses if the Qubit step does not accept blood. This run did **not** seed blood→Qubit; type gate used DNA vs Plasma on an ELISA LimsRun.

**Verified holds (API):**
- Admin LimsRun definition `ELISA LimsRun P2 type-gate` with accepted type **DNA** (not Plasma).
- `POST /v1/routing-map` ELISA × Plasma TAT 1–7 → **422** `{code: route_sample_type, message: "Sample type is not accepted on every step in the chain"}`.
- Reads as **wrong type**, not a dead sample.

**Observation (leftover config, not extract-hold):** `/admin/routing-map` errors `List 'sample_type' not found` (page asks `sample_type`; receive uses `sample_types`). Dropdowns empty. Map save was not exercised as a lab-tech click; type gate is API Pass.

### AC-P2-3 — TAT overlap 409

**Result:** **Pass** (API, 2026-08-28 ET, `3b56cfb`)

**Steps**
1. Two active map rows, same analysis + sample type, overlapping TAT ranges.
2. **Expect:** second save **409**.

**Verified holds:**
- Accepted types set to Plasma. Map TAT 1–7 → **201**.
- Overlap TAT 5–10 same analysis + type → **409** `Overlapping TAT range for this analysis and sample type`.

### AC-P2-4 — Route mints work_order

**Result:** **Fail** (`alice-tech` bench, 2026-08-28 ET, `3b56cfb`). Do **not** mark Pass. Lab tech cannot complete Route. Hold merge.

**Steps**
1. Map row matches. Every step accepts the sample type.
2. Route.
3. **Expect:** asked-for `routed`, `work_orders` queued, still zero Tests. Cancel asked-for → **422**.

**Fail bar:** `alice-tech` Route on matching asked-for → **422** `route_sample_type` / `Process definition has no steps`. `alice-tech` GET definition → **404**. Admin GET sees **1** `lims_run` step.

**Root:** **visibility**. Alice cannot see the admin-created definition/steps (definition / steps RLS: `is_admin()` or same-client `created_by`; admin `client_id` `00000000-...-0001`; alice samples are another client). The bench actor cannot see the steps the map points at. Do **not** treat the 422 wording as the bug, and do **not** recommend changing the 422 text as the fix.

**Admin Route after alice failed — mint bar only, not a Pass:**
- Admin Route → **200**, asked-for `routed`, WO `7a23e690-…` queued, Tests still **0**. That is the **mint** bar (Route mints WO, still zero Tests). It does **not** make AC-P2-4 Pass. The AC is lab-tech Route.
- Cancel routed → **422** `Cannot cancel a routed asked-for`.
- If `/work-orders` looks Start-able, that is still a **fail note**, not a Pass. Copy observed: “Tests are still minted later, at LimsRun start.”

Fail stands.

### AC-P2-5 — WO-7 Test at LimsRun start

**Result:** **not Pass** (2026-08-28 ET, `3b56cfb`). Unsigned / unverified. Do **not** write “Pass (mint)”.

**Steps**
1. Start a LimsRun with the routed sample in the cohort.
2. **Expect:** Test minted; `asked_for_params` frozen. Publish without that Test → **422**. Not minted on Route.

**Observed (not a Pass):**
- After Route: **0** Tests.
- `alice-tech` `POST /v1/lims-runs` + PATCH start with sample in cohort → Test minted `mAb-2301 PK Study-05_ELISA (Human IgG)`.
- `asked_for_params` `{}`.
- Tests page 3 → **4**. Not present after Route.

**Why this AC is not Pass:** Publish was **unclickable**. PATCH `…/complete` → **403** `Permission 'experiment:publish' required`. Seed catalog has `experiment:manage` only. Exact **422** `Test missing; Tests are created at LimsRun start (WO-7)` was **not** HTTP-hit. Unsigned / unverified until a tech can publish and that WO-7 **422** is hit.

---

## Sign-off

**P1 Pass** — Tobias, 2026-08-28, `c649245` — AC-P1-1..4.

Click: `/receive` then `/asked-for` as `alice-tech`. API: AC-P1-3/4. Local compose; down after the run. Not IC50. P1 lake only.

Do **not** read this as P2–P5 Pass. Do **not** collapse this stamp with Atomic Receive **CORE** Pass (`uat-atomic-receive.md`). P1 is on `main` (PR **#81**).

**P2 not Pass** — Tobias, 2026-08-28 ET, `3b56cfb` — AC-P2-1 Pass, AC-P2-2 Pass (API), AC-P2-3 Pass (API), AC-P2-4 **Fail** (alice), AC-P2-5 **not Pass** (publish unclickable).

Click: `alice-tech` three motions (receive stay-on-form, asked-for later look-up, Route). Admin used only for routing-map / process-definition setup. Local compose; down after the run. Not IC50.

Hold merge. Do **not** collapse with P1 or receive CORE. Not IC50. Leftover config (observation, not extract-hold): `/admin/routing-map` list name `sample_type` vs receive `sample_types`.
