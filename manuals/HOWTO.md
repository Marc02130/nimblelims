# How to run the lab path

**Receive ≠ order ≠ work.** Three separate motions, not one chain:

- **Receive** (`/receive`) — the bench loop. Commit a tube, stay on the form, scan the next tube. That is the whole happy path.
- **Requested analysis** (`/asked-for`) — a **later look-up** of what a client or study asked for. Not a step in the receive motion, not the click after a commit.
- **Work** — later, unnumbered. Route is a planner (queued work order). **Start instantiates the first process only**; later processes need later starts. Route/Start does **not** start the whole chain and does not mint a process-of-processes. A request is not work.

This is a how-to, not a PRD. Marc keeps it current as features ship.

**Honest status**

| Step | Status |
|------|--------|
| Receive (`/receive`) | Shipped on `main` |
| Requested analysis (`/asked-for`) — later look-up, off the bench path | Shipped on `main` (P1 lake) |
| Later Route / work order (planner, not after receive) | Surfaces on this P2 branch. Live product SHA **`1572071`**. Signed AC-P2-9..11 history: `9342439`. Deiter Contents click on product `4671ba8` / assignment commit `02fe95f` (`0077`) is signed history: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass**. Leadership Confirmed that click; Wilhelmina folded C2 Fail into sketch `a3741d1` and requirements `60a9447`. C1/C2 are **not** unsigned. Docs Confirm `84d2810` is not a new execute or the click SHA. Live AC-P2-C2 on `1572071` is **unsigned** until Tobias (dest-follow in the execute txn, emptied-source **422**, same-sample dest container — in code, not QA-clicked; do not teach dest-follow as shipped). Freeze skip **OPEN**. **OQ-WO-6 stays OPEN**. **No overall P2 Pass**. Hold product merge. |
| Process / Experiment / LimsRun | Execute substrate shipped. Process assignment = the **tube in hand**; Deiter C1 **Pass** on `02fe95f` stays history. Deiter C2 **Fail** on `02fe95f` is signed history (Leadership restamp): dest not on the process; emptied-source **201**; later Start rode the emptied parent; **PATCH is not a path**. Live C2 lock on `1572071` is same-type dest-follow only: same dest type = **same sample, additional container**; `_follow_destination_in_process` follows that path; emptied-source assign **422**; later Start follows that dest container. **Unsigned** until Tobias. Different dest type = **new derivative sample** in a new container (`parent_sample_id`). The parent **Sample row** stays as history with its original type and parent-type work; its process assignment does not stay. For both grains, execute writes the destination sample + destination container pair to `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction. Dest mint Hold is lifted only for type-changing execute. Deiter Hold **Pass** on `02fe95f` remains Start-extract Blood / **0 DNA** history. Freeze skip is **OPEN**. Later-step type-gate **Met** on `9342439`. Do not claim freeze closed |
| Results | Classic type-a-number on a Test; persist lock is a later packet. WO-7 whole-run publish-refuse is **Tobias-signed Pass** on `8cfa2a9` (carol **422** `test_missing`) and remains history on `b005cfe`. Overall P2 Pass remains unsigned |

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

**The lake accepts nonsense on purpose.** Qubit-on-blood may sit in it. Empty Route **422** “No routing-map row accepts this analysis, TAT, and sample type” is **Tobias-signed Pass** on `8cfa2a9`. Later-step type-gate at start (current tube) is **Met** on `9342439` (qPCR-on-blood / still-Blood **422** `route_sample_type`; not dest-type E2E). The lake and routing-map save do not run a chain-wide check.

Params: intent only. P1 sends `{}` OOB — do not type assay params here, and do not enter them in P1 UAT. The WO-7 lock is that params freeze at the **first LimsRun start** (P2), never on receive or asked-for. That freeze is **in code on `8cfa2a9`**; it is **not** QA-verified. Setup (`config:edit`) may `GET/PUT /analyses/{id}/param-defs`; empty catalog is the OOB path.

| Case | HTTP |
|------|------|
| Duplicate open `(sample, analysis)` | **409** (full rollback) |
| No project access / client write / hidden sample | **403** (not 404) |
| Discarded sample / inactive analysis / TAT &lt; 1 | **422** |
| Receive with non-empty `analysis_ids` | **422** (receive freeze) |

---

## Later planner: Route / work order

**This is a later work-planning action, not the next click after Receive or after saving asked-for.** Receive still ends on `/receive`. Recording requested analysis still ends on `/asked-for` without minting work. Route stays unnumbered: it is not §3 after receive.

**Punch:** Route does **not** start the chain. Start does **not** start the chain. Route snapshots the ordered list and mints **zero Tests**. **First Start instantiates `chain[0]` only.** Later Start following the dest container is the **lock on `1572071`**, **unsigned** until Tobias — not a shipped Pass.

Empty Route 0→**422** is **Tobias-signed Pass** on `8cfa2a9`. Signed AC-P2-9..11 history is `9342439`. Deiter clicked the `0077` Contents slices on product `4671ba8` / assignment commit `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — that click is signed history. Live product SHA **`1572071`**: AC-P2-C2 **unsigned** until Tobias. Docs Confirm `84d2810` is not a new execute and not the click SHA. Round 2 **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter; R2-1…R2-4). A route **may have multiple LimsRun analyses**; asked-for ELISA matches extract→Qubit→ELISA because ELISA is **in** the chain. Freeze skip **OPEN**. **OQ-WO-6 stays OPEN** (earlier LimsRun must not reuse the asked-for `analysis_id`; do not teach extract-as-special). Parser at import, not process authoring. Do not write overall P2 Pass. Hold product merge.

**Leadership honesty locks (Rolf / Deiter / Hans / Heidi / Günter).** The dest-type split is **Leadership Confirmed**: same type = same Sample + additional container; different type = new derivative Sample + new container with `parent_sample_id`. The `1572071` `container_id` retarget is same-type C2 only. Type-changing execute mints and joins the destination pair and marks the inbound assignment `removed`; Route / Start / map-save mint zero daughters. C2 and extract-hold UAT 1.7 remain two clicks. Tobias-signed AC-P2-9..11 Pass stays history; the Dest-type mint Hold on `9342439` is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. Freeze skip OPEN. **OQ-WO-6 stays OPEN** (Leadership Confirm R2-3). Route stays `test:assign`. Overall P2 unsigned. Not IC50.

1. **Freeze skip:** `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until then `{}` is **ambiguous**. Do **not** teach skip-on-frozen-`{}`.
2. **OQ-WO-6 (earlier LimsRun `analysis_id`):** Extract is **not** a special assay. Type gates catch blood-on-Qubit. Blood→DNA is a new derivative sample in a new container (`parent_sample_id`); the parent Sample row stays as lineage and keeps its original type, while the destination sample + container pair continues on the process. Any **earlier** LimsRun that reuses the asked-for panel analysis mints/freezes that Test on the parent sample. Earlier LimsRun = own analysis, or experiment-only.
3. **Start:** First Start instantiates `chain[0]` only and assigns the receive **container-with-sample**. Later Start following dest is the lock on **`1572071`** (in code; not QA-clicked). Deiter’s C2 **Fail** on `02fe95f` is signed history. Do **not** teach dest-follow as shipped. Do **not** write C2 Pass.
4. **Route:** snapshots the ordered list, **zero Tests**.

**Setup:** an administrator configures **Routing map** at `/admin/routing-map`. Each row is TAT plus an ordered `process_definition[]`. There is **no admin-picked analysis or sample type**. A route **may list several LimsRun analyses**. Assignment: first process’s first Experiment/LimsRun allow-list **and** the asked-for analysis **contained** in that chain. Parser is **not** on the map or the process step — chosen at import (instrument XOR CRO). Map save does **not** AND inbound type across later processes. It **does** 422 when the type emerging from process *x* is not accepted by process *x+1* (authoring, not a runnable extract→Qubit).

Map save returns **409** when another active row has an **overlapping TAT range**, an **overlapping first-step allow-list**, **and** overlapping LIMS Run analyses. Extract-first and Qubit-first for the same TAT are legal at save when types or analyses differ. Overlapping TAT alone is not a 409.

**Route when work planning happens:**

1. Open the previously saved `requested` row on `/asked-for`.
2. Choose its row **Route** action, or select requested rows and choose **Route selected**. This is Route, not Start. Permission is `test:assign` plus project access, not `experiment:manage`.
3. P2 finds rows whose TAT matches, then keeps **any** route whose **first process’s first ordered Experiment/LimsRun** accepts the sample’s current type **and** whose chain **contains** a LimsRun for the asked-for analysis (the route may have other analyses too). **Tobias-signed Pass on `8cfa2a9`:** zero acceptable rows returns **422** and mints nothing. Route two-accept **409** is **unsigned** that SHA. Never silently call `first()`.
4. Exactly one acceptable row creates one queued `work_order`, **snapshots the ordered list**, changes asked-for to `routed`, and still creates **zero Tests**. Minting that queue record is planning; **work has not started**.
5. Open Experiments → **Work Orders** (`/work-orders`) and choose **Start process**. **First Start instantiates `chain[0]` only**. It does not mint a process-of-processes. Start process / LimsRun start remain `experiment:manage`; publish is `experiment:publish`.
6. Complete that process, then use **Later Start** only where the product has a valid continuing assignment. Process assignment is the **tube in hand** — a **container-with-sample** (Contents), not a naked sample. Assign with **no** vessel → **422** `process_container_required`; assign a sample sitting in **two** vessels with no `container_id` pick → **422** as well; receive-tube assign → **201**. Deiter’s C1 click **Pass** on `02fe95f` verifies those outcomes (history, not restamped). Deiter’s C2 **Fail** on `02fe95f` is signed history. Live C2 on **`1572071`** is same-type dest-follow only: same dest type = **same sample, additional container**; emptied-source assign **422**; later Start follows that dest container. **Unsigned** until Tobias. Different dest type = **new derivative sample** in a new container (`parent_sample_id`). For either grain, execute puts the destination sample + destination container pair on `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction. The parent Sample row stays for type-changing lineage, but its inbound process assignment does not. **PATCH is not a path.** Do not teach dest-follow as shipped. Later-step type-gate remains **Met** on `9342439` (qPCR on still-Blood **422** when no mint had run).

**Same-type follow vs type-changing derivative.** Same dest type = **same sample, additional container**. Live C2 on **`1572071`** covers only this same-type path and remains unsigned. `_follow_destination_in_process` moves the same sample’s active process assignment to the additional container; it does not require `entry.process_step_id`. Different dest type = **new derivative sample** in a new container with `parent_sample_id`. The parent **Sample row** stays as lineage, keeps its original type, and retains work attributable to the parent type; it is not retargeted onto the destination tube. In both paths, the destination sample + destination container pair lands on `eln_process_samples` and the inbound source assignment becomes `removed` in the execute transaction. Dest mint Hold is lifted only for type-changing execute. Deiter’s C2 **Fail** and dest mint Hold **Pass** on `02fe95f` remain signed history; that Hold Pass records Start extract still Blood / **0 DNA**, not a ban on type-changing derivative mint. **PATCH is not a path.** Extract-hold UAT step **1.7 is OOB execute** with no Result stamp and must not imply DNA on the parent.

**A Test stays `(sample, analysis)`.** The container records **which vessel was measured**; a concentration write-through hits **that** container. The container on the process is not a second Test key.

**WO-7 first-start freeze is not closed. Freeze skip stays unsigned.** Tobias recorded a **new-Test write** of `asked_for_params` `{}` onto Test `99b692d3` (not SQL NULL, not a skipped classic row). That `{}` is **ambiguous** — first start cannot tell a classic default `{}` from a frozen `{}` (same JSON). Do **not** teach later-start no-overwrite of `{}` as a verified freeze skip. Do **not** teach skip-on-frozen-`{}`. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, skip-on-`{}` is not a freeze. `if test: continue` is **not** a freeze. **OQ-WO-6:** an earlier LimsRun must **not** share the asked-for `analysis_id` or WO-7 attaches/freezes the panel Test on the parent at that start. Extract is not special. Do not claim overall P2 Pass.

Qubit-first on blood is refused by Route before a work order is minted. If Qubit is later, its step start refuses while the sample’s current type is still blood. A **422** `route_sample_type` means current type is wrong for the assigned first step or the later step being started; it does **not** mean the sample is broken. Dest mint Hold **Pass** on the Deiter click (`02fe95f`) means Start extract still leaves the tube Blood with **0 DNA** daughters. It does not close `_execute_transfer`. Deiter C2 **Fail** on `02fe95f` is signed history. Live dest-follow on `1572071` is **unsigned**. Do **not** claim Start extract creates a DNA daughter or that dest-follow shipped.

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

The WO-7 lock puts Test selection/creation and the params freeze on the **first LimsRun start** for the asked-for analysis — **not** on receive, Route, or work-order Start. A new-Test **write** of `{}` onto `99b692d3` was observed; freeze skip stays **unsigned**. `if test: continue` is **not** a freeze. Classic `/tests` must leave `asked_for_params` **NULL**, or we need a **freeze marker**. Until one of those exists, `{}` is **ambiguous** (classic default and frozen `{}` are the same JSON) — not a verified freeze skip. Do **not** teach skip-on-frozen-`{}`. **OQ-WO-6:** an earlier LimsRun must not share the asked-for `analysis_id`. **Do not claim freeze closed.**

LimsRun **publish** can promote instrument rows onto Tests/Results. Two writers on the same Test → **409**. The other half of WO-7 — if any cohort sample lacks an active Test, publish returns **422** and refuses the **whole run**, writes no Results, invents no Test, and leaves the run `complete` — is **Tobias-signed Pass** on `8cfa2a9` (carol **422** `test_missing`) and remains history on `b005cfe`. Overall P2 Pass is unsigned. Historical `9c4f9da` / `b005cfe` stamps stay signed history.

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
- Do **not** put a sample-type or analysis picker on routing-map create. Display first-process first-step types and chain LIMS Run analyses as derived information.
- Do **not** 409 map save on overlapping TAT alone. 409 requires overlapping TAT, overlapping first-step allow-lists, **and** overlapping LIMS Run analyses. Extract-first and Qubit-first for the same TAT must save when types or analyses differ.
- Do **not** teach routing-map save or Route as ANDing one type across later processes or steps. Route gates only the first process’s first ordered Experiment/LimsRun; later starts gate current type. Later Start following dest container is the lock on **`1572071`**, **unsigned** until Tobias.
- Do **not** collapse ordered `process_definition[]` into one definition or an unordered bag. Start instantiates the first process only; later processes need later starts; the UI must preserve route order.
- Do **not** teach Route or Start as starting the whole chain.
- Do **not** treat zero or multiple acceptable routes as `first()`: empty Route → **422** is **Tobias-signed Pass** on `8cfa2a9`; two saved rows that both accept current type → **409** is **unsigned** this SHA.
- Do **not** treat first-start freeze skip as closed or verified. A write of `{}` onto a new Test is not a freeze-skip Pass. Classic `/tests` must leave `asked_for_params` NULL, or we need a freeze marker. Until then `{}` is ambiguous.
- Do **not** teach `_mint_tests_at_start` `if test: continue` as a freeze.
- Do **not** teach skip-on-frozen-`{}` as a freeze. Classic default `{}` and frozen `{}` are the **same JSON**; first start cannot tell them apart. Until classic `/tests` leaves `asked_for_params` **NULL** or a **freeze marker** exists, `{}` is **ambiguous** — not a verified freeze skip.
- Do **not** treat a classic `/tests` row with `asked_for_params` NULL or default `{}` as frozen. Classic `/tests` must leave it NULL, and the first LimsRun start must **write** the snapshot onto that Test.
- Do **not** hang the asked-for panel `analysis_id` on an **earlier** LimsRun (extract, library prep, …) — WO-7 would mint/freeze the Test on the parent sample. Type gates are a different control (blood-on-Qubit). Extract is not a special assay.
- Do **not** teach first Start minting later processes (Qubit/reporting) or their Tests as shipped. First Start instantiates `chain[0]` only. Later Start following dest (not the parent tube) is the lock on **`1572071`**, **unsigned** until Tobias.
- Do **not** teach Route as starting work. Route snapshots the ordered list, **zero Tests**.
- Do **not** claim freeze closed/verified on `8cfa2a9`. Signed AC-P2-9..11 history stays `9342439`; Leadership restamp notes are honesty, **not** a merge vote. Deiter clicked `0077` on `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. Live product SHA **`1572071`**. C1/C2 on `02fe95f` are **not** unsigned. Overall P2 stays unsigned.
- Do **not** teach later Start as following the parent/source tube after an equivalent aliquot, or as legal assign of a sample with no container.
- Do **not** teach later Start as following a dest **type**. The follow is by dest **container**.
- Do **not** conflate same-type follow with type-changing derivative mint. Same dest type = same sample, additional container. Different dest type = new derivative sample in a new container (`parent_sample_id`); only the parent Sample row stays for lineage. In both paths the destination pair continues on the process and the inbound source assignment is `removed`.
- Do **not** write C2 Pass. Deiter C2 **Fail** on `02fe95f` stands as signed history. C2 on `1572071` is **same-type dest-follow only** (`_follow_destination_in_process`; emptied-source assign **422**) — not QA-clicked, not shipped Pass. Type-changing execute must not retarget the parent’s `container_id`. **PATCH is not a path.**
- Do **not** teach PATCH as a dest-follows path.
- Do **not** treat C1/C2 as unsigned. Deiter clicked them; Leadership Confirmed that stamp. Do not invent a Tobias Pass.
- Do **not** silently pick a vessel when a sample sits in two containers. That is **422**, not `first()`.
- Do **not** score extract-hold **1.7** as AC-P2-C2. 1.7 is AC-P2-C3 (DNA daughter). C2 is same dest type only. Both unsigned until Tobias.
- Do **not** turn Deiter’s Start-extract Hold history into a ban on type-changing execute minting a derivative.
- Do **not** teach `routing_map.analysis_id` as a required create field. Derive first-step types and chain LimsRun analyses at read.
- Not IC50. Not a fake Route how-to.
