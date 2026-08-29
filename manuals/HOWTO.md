# How to run the lab path

**Receive ≠ order ≠ work.** Three separate motions, not one chain:

- **Receive** (`/receive`) — the bench loop. Commit a tube, stay on the form, scan the next tube. That is the whole happy path.
- **Requested analysis** (`/asked-for`) — a **later look-up** of what a client or study asked for. Not a step in the receive motion, not the click after a commit.
- **Work** (route → Process / Experiment / LimsRun → results) — later packets. A request is not work.

This is a how-to, not a PRD. Marc keeps it current as features ship.

**Honest status**

| Step | Status |
|------|--------|
| Receive (`/receive`) | Shipped on `main` |
| Requested analysis (`/asked-for`) — later look-up, off the bench path | Shipped on `main` (P1 lake) |
| Later Route / work order (planner, not after receive) | Shipped on this P2 branch (`/asked-for` Route, `/admin/routing-map`, `/work-orders`) |
| Process / Experiment / LimsRun | Execute substrate shipped; P1 does **not** start it. WO-7 **first-start freeze is the lock and still OPEN** on `b005cfe` — a later start overwrites `tests.asked_for_params` |
| Results | Classic type-a-number on a Test; persist lock is a later packet. WO-7 whole-run publish-refuse **is in code** on `b005cfe`; the live AC-P2 stamp is **unsigned** and makes no outcome claim |

Handbooks in this folder: [atomic-receive.md](atomic-receive.md), [asked-for.md](asked-for.md), [navigation.md](navigation.md), [api-endpoints.md](api-endpoints.md), [dev-setup.md](dev-setup.md), [admin-setup.md](admin-setup.md), [processes.md](processes.md), [experiments.md](experiments.md), [lims-runs.md](lims-runs.md). Index: [README.md](README.md).  
UAT: [`UAT_Scripts/uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md) · P1 [`UAT_Scripts/uat-post-receive-work-spine.md`](../UAT_Scripts/uat-post-receive-work-spine.md).  
Stamps: [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../.docs/decision-logs/framework-stamps-2026-08-26.md) (WO-7: Test at LimsRun start, not at receive).

---

## 1. Start / login

Bring the stack up and log in. Do not duplicate setup here.

- Dev / compose: [dev-setup.md](dev-setup.md) and root [`README.md`](../README.md) Quick Start.
- Admin password: [admin-setup.md](admin-setup.md).
- Frontend: http://localhost:3000 · API: http://localhost:8000 · docs: http://localhost:8000/docs.
- Lab path accounts: `admin` / `admin123` · `lab-tech` / `labtech123` · `alice-tech` / `alice123`. Change the default admin password.

Need `sample:create` for Receive. Need `test:assign` plus project access for requested analysis and the later Route action. Client role cannot receive, write asked-for, or Route; those writes return **403**, not 404. Route does **not** require `experiment:manage`.

---

## 2. Accession (receive)

**UI:** Sample Mgmt → **Receive** (`/receive`).  
**API:** `POST /samples/receive`.  
`/accessioning` redirects here. There is no wizard.

1. Set sticky **sample type** and **project**. Session-sticky; they stay after each commit.
2. Scan or type the **primary barcode**. Optionally **Add** more barcodes for the **same** sample (more tubes, not aliquots).
3. Optional temperature and client sample ID.
4. **Receive**. Toast. Barcodes clear. Focus returns to primary.

**Happy path = stay on `/receive` and scan the next tube.** The loop ends on the form. Nothing else is owed at the bench: the sample is **Available for Testing** and waits. Do not send the tech to Asked-for after a commit.

**One transaction:** Sample + first vessel (and any additional vessels) + Contents. Lab sample ID comes from the name template — **no sample-ID field**. Tube barcode is `containers.name`. Status is **Available for Testing**.

**Container type is not a receive decision.** RQ-AR-8 / Lab Ops **L3**: the lab **default tube** applies to **all** vessels on the call, **off the form** — no type picker in the scan loop. Plates are never receivable (non-1×1 → **400**). The current build still exposes a 1×1 container type on the form and still requires `container_type_id` on the API; that is CORE **drift** against RQ-AR-8, not the path this how-to teaches.

**Not on receive:** matrix (`samples.matrix` stays unset). No analysis picker, no requested analysis, no Route, no Test.

**Do not send `analysis_ids`.** The UI never offers an analysis picker. Omit the field or send `[]`. Non-empty → **422** before any write. Zero Tests. Zero Results.

Duplicate barcode → **409**, full rollback, stay on receive.

Client / no `sample:create` → no Receive nav or **403**.

---

## Later look-up: requested analysis (asked-for lake, P1)

*Deliberately outside the numbered path. It is a look-up, not a step in the bench motion.*

**Not the next step after receive.** Asked-for is a **separate motion**, done whenever someone needs to see or record what was asked for — reading a client request, a study plan, a paper form. Nobody is waiting on the bench for it, and it is **not** a Start queue. Saving a `requested` row creates no work. P2 exposes Route on that row for a distinct, later work-planning action.

**Copy lock:** say **requested analysis**. Do **not** say asked-for save assigns a Test, mints a work order, or starts work. Only the later explicit Route action can mint a work order.

**UI:** Sample Mgmt → **Asked-for** (`/asked-for`). Also a section on sample detail, which is where a tech normally meets it.  
**API:** `POST /v1/asked-for` · `GET /v1/asked-for` · `POST /v1/asked-for/{id}/cancel`.  
Handbook: [asked-for.md](asked-for.md).

**What a row is:** **requested analysis + TAT**, against an already-received sample. That is all.

1. The sample must already be received (identity + vessels), Available for Testing, Tests count 0.
2. Open Asked-for → **Record requested analysis**.
3. Pick sample(s), pick an active analysis, TAT ≥ 1 (days). Save. Stay on `/asked-for`.

One action may cover a set of samples (same analysis + TAT). The API still writes one row per sample. Status is `requested`. Cancel while `requested` is allowed; then you may record the same analysis again. Duplicate open `(sample, analysis)` → **409**.

**Save is not scientific assignment.** A saved row does **not** assign a Test, does **not** attach analytes, and does **not** make type-a-number legal. It does **not** create a Test, Result, Process, Experiment, LimsRun, or work_order. Receive freeze stays: non-empty `analysis_ids` on receive is still **422**.

**The lake accepts nonsense on purpose.** Qubit-on-blood may sit in it. Scientific eligibility is refused when a step starts with an incompatible current sample type (`route_sample_type` **422**, P2) — not by the lake or routing-map save.

Params: intent only. P1 sends `{}` OOB — do not type assay params here, and do not enter them in P1 UAT. The WO-7 lock is that params freeze at the **first LimsRun start** (P2), never on receive or asked-for. That first-start freeze is **still open** on `b005cfe`: see [Later planner](#later-planner-route--work-order). Setup (`config:edit`) may `GET/PUT /analyses/{id}/param-defs`; empty catalog is the OOB path.

| Case | HTTP |
|------|------|
| Duplicate open `(sample, analysis)` | **409** (full rollback) |
| No project access / client write / hidden sample | **403** (not 404) |
| Discarded sample / inactive analysis / TAT &lt; 1 | **422** |
| Receive with non-empty `analysis_ids` | **422** (receive freeze) |

---

## Later planner: Route / work order

**This is a later work-planning action, not the next click after Receive or after saving asked-for.** Receive still ends on `/receive`. Recording requested analysis still ends on `/asked-for` without minting work. Route stays unnumbered: it is not §3 after receive.

**Setup:** an administrator configures **Routing map** at `/admin/routing-map`. Each map row selects an analysis, intake/current sample type, TAT range, and one process definition. Saving a map does **not** compare that type with every step’s accepted types: later ordered steps may correctly expect a transformed type (for example, extract blood → Qubit DNA). The planner shows the first ordered Experiment or LimsRun step’s allowed types for information only. The Route UI must show the process’s step order; a process definition is an ordered workflow, not an unordered bag of steps.

**Route when work planning happens:**

1. Open the previously saved `requested` row on `/asked-for`.
2. Choose its row **Route** action, or select requested rows and choose **Route selected**. This is Route, not Start. Permission is `test:assign` plus project access, not `experiment:manage`.
3. P2 matches analysis × current sample type × TAT against the routing map. No match returns **200** `no_route`; the row stays `requested`, and nothing is minted.
4. A match creates one queued `work_order`, changes asked-for to `routed`, and still creates **zero Tests**. Minting that queue record is planning; **work has not started**.
5. Open Experiments → **Work Orders** (`/work-orders`) and choose **Start process**. P2 instantiates the first snapshot process definition, links it through `eln_processes.work_order_id`, and opens that process at `/experiments/processes/{id}`. Start process / LimsRun start remain `experiment:manage`; publish is `experiment:publish`.
6. Continue in order through that existing process’s typed Experiment and LimsRun steps. At each step start, the sample’s **current** type must be accepted by that step. A mismatch returns **422** `route_sample_type`; the sample is not broken. The WO-7 lock is that the **first** LimsRun start creates or attaches the Test and freezes the then-current `asked_for_params`; nothing freezes at receive, asked-for save, Route, or work-order start.

**WO-7 first-start freeze is OPEN on `b005cfe`. Do not teach it as shipped.** `_mint_tests_at_start` has no already-frozen guard: every start that reaches it assigns `tests.asked_for_params`, so a later start that finds the existing active Test for the same sample + analysis overwrites the first-start snapshot. When no `routed` asked-for row matches, that write is the empty `{}` over a real snapshot. **Empty `{}` is itself a freeze, not a hole to refill later** — that is the intended lock, not verified-closed behavior. Until the guard lands, treat params on a Test touched by a second start as unreliable.

Qubit-on-blood is refused when the Qubit step starts while the sample’s current type is still blood; it is not made valid by saving a request or routing map. A **422** `route_sample_type` means the sample’s current type is wrong for the step being started; it does **not** mean the sample is broken. A legitimate earlier transformation may make a later step eligible. Dest-type Hold is unchanged, so do not claim this branch already creates that transformed daughter.

---

## Later execution: Process / Experiment / LimsRun

The execute substrate is already in the app. Requested analysis does **not** open it.

| Where | What |
|-------|------|
| **Experiments** → All Experiments (`/experiments`) | ELN experiment list/detail. `experiment:manage`. |
| **Experiments** → Experiment Templates (`/experiments/templates`) | Template authoring. Same permission. |
| **Experiments** → Processes (`/experiments/processes`) | ELN process **definitions** and **instances**. Assign samples (Samples list → **Assign to process**, or on the process). Start a step (Experiment or lazy LimsRun). |
| **Experiments** → Runs (`/runs`) | LIMS Runs: create/start/import/review/publish. Every run has an **analysis**. |

Deeper handbooks: [processes.md](processes.md), [experiments.md](experiments.md), [lims-runs.md](lims-runs.md).

P1 does not instantiate a process from requested analysis. Classic `/tests` can still mint a Test for typing a number; that is **not** the request path.

---

## Later results

Classic path: **Results** (`/results`) — type a number on an existing Test (batch grid). Unit from `analytes.units_default` when that lock is enforced; missing unit is a later persist-packet **422**, not a receive rule.

The WO-7 lock puts Test selection/creation and the params freeze on the **first LimsRun start** when the work-order packet exists — **not** on receive. That freeze half of the lock is **still open**: later starts overwrite `tests.asked_for_params` (see [Later planner](#later-planner-route--work-order)).

LimsRun **publish** can promote instrument rows onto Tests/Results. Two writers on the same Test → **409**. The other half of WO-7 — if any cohort sample lacks an active Test, publish returns **422** and refuses the **whole run**, writes no Results, invents no Test, and leaves the run `complete` — **is in code** on `b005cfe`, unsigned until QA. Keep the two halves apart: **the publish refuse is implemented; the first-start freeze is not.** The historical `9c4f9da` run returned **200 published** with 0 Tests and stays signed not Pass.

UAT (classic): [`UAT_Scripts/uat-results-entry-review.md`](../UAT_Scripts/uat-results-entry-review.md). Persist lock (P3) is specified on the spine packet, not shipped as that slice.

---

## What not to do

- Do **not** teach receive → asked-for as one motion. Receive ends on `/receive`.
- Do **not** hop off `/receive` after a successful scan — stay on the form for the next tube.
- Do **not** put Asked-for in front of the tech as the after-receive click or as a Start queue.
- Do **not** mint a Test at intake. Do **not** send non-empty `analysis_ids` on receive.
- Do **not** treat a saved requested analysis as “assign test,” “attach analytes,” or “start work.”
- Do **not** pick container type in the scan loop. Default tube, off the form (RQ-AR-8).
- Do **not** invent a second workflow engine. Work_order (later) feeds the Process / Experiment / LimsRun that already exist.
- Do **not** put analysis param defs on receive, and do **not** type params on asked-for.
- Do **not** teach routing-map save as ANDing the intake type across every step’s allow-list. Display the first ordered step’s allowed types as information only; enforce current type when each step starts.
- Do **not** present a process definition as an unordered bag. Route must make the process and step order apparent.
- Do **not** write “later starts do not re-freeze params” as current behavior. That freeze is the WO-7 lock and is **open** on `b005cfe`.
- Do **not** treat empty `{}` as a hole to refill on a later start. `{}` is a freeze.
- Not IC50. Not a fake Route how-to.
