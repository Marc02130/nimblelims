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
| Later Route / work order (planner, not after receive) | Surfaces on this P2 branch. Dest-follow execute SHA **`1572071`**. UAT numbering SHA **`570bbc0`** (docs/uat split + pytest, **not** a new execute). Signed AC-P2-9..11 history: `9342439`. Deiter Contents click on product `4671ba8` / assignment commit `02fe95f` (`0077`) is signed history: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass**. Leadership Confirmed that click; Wilhelmina folded C2 Fail into sketch `a3741d1` and requirements `60a9447`. C1/C2 are **not** unsigned. Docs Confirm `84d2810` is not a new execute or the click SHA. Tobias QA **Pass** on **`bf51b19`**: C1/C2/C3 dest-follow, cardinality 1, freeze skip NULL, Route two-accept **409**, seq-1 (two WOs; dest-cohort **1.2 / OQ-WO-7 not scored**). Execute joints remain **`1572071`**. `570bbc0` is Lab Ops numbering, not the click SHA. **OQ-WO-6 extract CLOSED** for the common path (not a forever ban). **Marc lock 2026-09-01:** care about the asked-for only; Extracted DNA = DNA tube (zero LimsRuns legal); sequencing ask = extract is route machinery. **No overall P2 Pass**. P2 on `main` (`5040f2d`). **OQ-WO-7 Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`): Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** not recoded. Closeout **1.4 / OQ-WO-8** pending Leadership Confirm. Stack down. |
| Process / Experiment / LimsRun | Execute substrate shipped. Process assignment = the **tube in hand**; Deiter C1 **Pass** on `02fe95f` stays history. Deiter C2 **Fail** on `02fe95f` is signed history (Leadership restamp): dest not on the process; emptied-source **201**; later Start rode the emptied parent; **PATCH is not a path**. C2 execute lock on `1572071` (numbered on `570bbc0`) is same-type dest-follow only: same dest type = **same sample, additional container**; `_follow_destination_in_process` follows that path; inbound assignment `removed` even if leftover volume remains; later Start follows that dest container. Amount 0 on the inbound tube is an edge (**422**), not the AC. Tobias QA **Pass** on **`bf51b19`**. **C3** numbered on `570bbc0`; execute **`1572071`** is the different-dest-type click, Tobias **Pass** on `bf51b19`: **new derivative sample** in a new container (`parent_sample_id`). The parent **Sample row** stays as history with its original type and parent-type work; its process assignment does not stay. For both grains, execute writes the destination sample + destination container pair to `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction. Dest mint Hold is lifted only for type-changing execute. Deiter Hold **Pass** on `02fe95f` remains Start-extract Blood / **0 DNA** history. Freeze skip NULL is **Tobias Pass** on `bf51b19` (classic NULL; first start wrote snapshot; later start left it). `{}` on `99b692d3` stays `8cfa2a9` history. Later-step type-gate **Met** on `9342439`. Overall P2 unsigned |
| Results | Classic type-a-number on a Test; persist lock is a later packet. WO-7 whole-run publish-refuse is **Tobias-signed Pass** on `8cfa2a9` (carol **422** `test_missing`) and remains history on `b005cfe`. Overall P2 Pass remains unsigned |

**Current Quantified DNA lock — Leadership Confirm 2026-09-02:** Quantified DNA is data. Reuse the existing **Qubit** catalog analysis on exactly one named asked-for LimsRun slot; Test `(DNA, Qubit)` is the ask. Do not create a Quantified DNA analysis. Extract stays experiment with no `analysis_id` or boolean Result. Zero LimsRuns → **422**. WGS/WES/ELISA keep Qubit as process QC. Route must match the named asked-for slot, not any route that merely contains Qubit. Old tube-only / zero-LimsRun 1.4 is struck. Overall P2 remains unsigned.

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
2. Scan or type the **primary barcode**. Optionally **Add** more barcodes for the **same** sample (more tubes, not aliquots). **Marc lock:** that second blood tube **may** carry its **own asked-for and own route** (equivalent aliquot / extra container on the same Sample). **Leadership Confirm:** two blood tubes → two process assignments (`container_id`); ELISA route and WGS/extract stay apart. Do not teach both tubes as one asked-for.
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

**Punch:** Route does **not** start the chain. Start does **not** start the chain. Route snapshots the ordered list and mints **zero Tests** and **zero** dest samples/containers. **First Start instantiates `chain[0]` only.** Dest exists only after aliquot/pool execute. Receive still mints identity + first vessel — that is **not** dest mint. Later Start following the dest container is the **lock on `1572071`**, **unsigned** until Tobias (C2/C3 numbered on `570bbc0`) — not a shipped Pass.

Empty Route 0→**422** is **Tobias-signed Pass** on `8cfa2a9`. Signed AC-P2-9..11 history is `9342439`. Deiter clicked the `0077` Contents slices on product `4671ba8` / assignment commit `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — that click is signed history. UAT numbering SHA **`570bbc0`** (docs/uat split + pytest, **not** a new execute); dest-follow execute txn **`1572071`**: AC-P2-C2 and AC-P2-C3 **Tobias Pass** on **`bf51b19`**. Docs Confirm `84d2810` is not a new execute and not the click SHA. Round 2 **Leadership Confirm** (Rolf/Deiter/Hans/Heidi/Günter; R2-1…R2-4). **Care about the asked-for only.** A route **may have multiple LimsRun analyses**. When the ask **is** an assay, that assay appears on **exactly one** LimsRun (ELISA, NGS, Qubit-as-asked-for, sequencing, …). **Quantified DNA ask (1.4 / OQ-WO-8, pending Leadership Confirm):** Qubit is the asked-for LimsRun; other QC supporting; do **not** code extract-only zero LimsRuns. Extract is typically an **experiment** (equipment) on a process — do **not** forever-ban extract-as-LimsRun. Qubit / Nanodrop are **supporting LimsRuns** in the same route as whatever the asked-for assay is (other `analysis_id`s, own Tests, own params freeze). Map-save / Route **422** if an **assay** asked-for analysis appears 0 or 2+ times among LimsRuns. **No route branching this phase:** WGS asked-for on blood owns WGS params; C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up (own params). Freeze skip NULL **Pass** on `bf51b19`. **OQ-WO-6 for extract CLOSED** (common path; extract does not wear the panel `analysis_id`). Parser at import, not process authoring. Do not write overall P2 Pass. P2 on `main` (`5040f2d`). **OQ-WO-7 Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). After C3, the DNA WGS Test freezes `{library_kit: TruSeq}` from the blood WO asked-for, **not** `{}`. Leftover **`9f86d14`** not recoded. Closeout **1.4 / OQ-WO-8** pending Leadership Confirm. Stack down.

**Leadership Confirm (2026-09-02) — closeout 1.4 / OQ-WO-8 Closed.** Quantified DNA uses existing **Qubit** as exactly one named asked-for LimsRun slot. Nanodrop/other QC has its own analysis and Test. Extract has no analysis or boolean Result. **422** on zero LimsRuns is right. WGS/WES/ELISA keep Qubit as process QC. [Living Confirm](../.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md). Not IC50.

**Leadership Confirm (2026-09-01, Rolf / Deiter / Hans / Heidi / Günter).** (1) **ELISA is not on DNA** (wrong matrix). Do **not** hang ELISA on the DNA dest after C3. (2) The **same blood Sample, second tube (Contents)** may carry its **own asked-for and route**. Two blood tubes → **two process assignments** (`container_id`). ELISA route and WGS/extract route stay apart. (3) Do **not** teach “extract can never be a LimsRun” as a forever ban. Hans’s punch: do not hang asked-for assay `analysis_id` on extract (panel Test would freeze on blood). **Extracted DNA asked-for can have Qubit/Nanodrop.** Extract-as-instrument LimsRun is later. **OQ-WO-6 still:** asked-for `analysis_id` once on the assay LimsRun, not extract. **OQ-WO-7 Closed**: WGS params on the DNA Test from the WO after C3 (`{library_kit: …}`, not `{}`, not Qubit params). **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`): Test **`55f9cad9`** `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** not recoded. Merged with this OPEN (`5040f2d`) is history. Closeout **1.4** stays OPEN. Science: Brief → code → UAT with Pass/Fail and not-a-Fail → stamp → merge. Asked-for-only lock, extract-as-process common path, supporting QC same-route, freeze skip Pass on `bf51b19` stand. Not IC50. Do not rewrite `bf51b19` / `8cfa2a9` / `9342439` / P1 / `02fe95f` / Deiter `570bbc0` Lab Ops Met.

**Leadership honesty locks (Rolf / Deiter / Hans / Heidi / Günter).** The dest-type split is **Leadership Confirmed**: same type = same Sample + additional container; different type = new derivative Sample + new container with `parent_sample_id`. The `container_id` retarget shipped on `1572071` is same-type C2 only. Type-changing execute mints and joins the destination pair and marks the inbound assignment `removed`. **Leadership Confirm of mint-only-at-execute:** dest sample/container exists only after aliquot/pool **execute**. Route / Start / map-save / asked-for mint **zero** daughters. Plan dest type is catalog intent, **not** a Sample. Receive still mints identity + first vessel — that is **not** dest mint. A tech must **not** scan DNA before extract execute. Do **not** teach dest existing at Route / Start / map-save. C2 and C3 / extract-hold UAT 1.7 remain two execute clicks (numbered on `570bbc0`; execute `1572071`); Tobias **Pass** on **`bf51b19`**. `570bbc0` does **not** inherit `1572071` C2 Pass or Fail. After execute, the process-sample is **only** that execute-minted dest (Günter). Tobias-signed AC-P2-9..11 Pass stays history; the Dest-type mint Hold on `9342439` is Start-extract still Blood / **0 DNA** history, not a live ban on type-changing execute. Freeze skip NULL **Pass** on `bf51b19`. **OQ-WO-6 extract CLOSED** (Leadership Confirm 2026-08-31; R2-3 “stays Open” is history). Route stays `test:assign`. Overall P2 unsigned. Not IC50.

1. **Freeze skip:** **Tobias Pass** on `bf51b19`. Classic `/tests` leaves **NULL**. First LimsRun start **writes** the snapshot. Later start does **not** overwrite. Frozen `{}` is locked empty. `{}` on `99b692d3` stays `8cfa2a9` history of a new-Test write. Do **not** teach skip-on-`{}` on the old NOT NULL default.
2. **OQ-WO-6 / OQ-WO-8:** Extract is an **experiment** with no `analysis_id` or boolean Result. Quantified DNA is not a tube-only SKU: use existing Qubit in the named asked-for LimsRun slot, producing Test `(DNA, Qubit)`. Zero LimsRuns is **422**. Nanodrop/other QC uses its own analysis/Test. For WGS/WES/ELISA, Qubit is process QC, not the asked-for slot. Blood→DNA remains a derivative sample (`parent_sample_id`). OQ-WO-7 is Closed and unchanged: same-analysis WO asked-for, else parent lineage, else `{}`.
3. **Start:** First Start instantiates `chain[0]` only and assigns the receive **container-with-sample**. Later Start following dest is the lock on **`1572071`** (C2/C3 numbered on `570bbc0`; Tobias **Pass** on `bf51b19`). Deiter’s C2 **Fail** on `02fe95f` is signed history.
4. **Route:** snapshots the ordered list, **zero Tests**, **zero** dest samples/containers. Dest type on a later aliquot/pool plan is catalog intent, **not** a Sample. Receive still mints identity + first vessel — that is **not** dest mint.
5. **Scan:** a tech must **not** scan DNA before extract execute. There is no DNA tube until execute.

**Setup:** an administrator configures **Routing map** at `/admin/routing-map`. Each row is TAT plus an ordered `process_definition[]` and names one LimsRun in that route as the **asked-for slot**. This is a slot choice, not a free-form catalog-analysis or sample-type picker. A route may list several LimsRun analyses. Assignment compares the asked-for analysis to the named slot; do not match any chain that merely contains Qubit. Missing slot or zero LimsRuns → **422**. Parser remains chosen at import.

Map save returns **409** when another active row has an **overlapping TAT range**, an **overlapping first-step allow-list**, **and** overlapping LIMS Run analyses. Extract-first and Qubit-first for the same TAT are legal at save when types or analyses differ. Overlapping TAT alone is not a 409.

**Route when work planning happens:**

1. Open the previously saved `requested` row on `/asked-for`.
2. Choose its row **Route** action, or select requested rows and choose **Route selected**. This is Route, not Start. Permission is `test:assign` plus project access, not `experiment:manage`.
3. P2 finds rows whose TAT and first-step type match, then requires `asked.analysis_id == named_slot.analysis_id`. A supporting Qubit in a WGS map does not make that map eligible for Quantified DNA. Zero acceptable rows returns **422**; two acceptable rows return **409**. Never silently call `first()`.
4. Exactly one acceptable row creates one queued `work_order`, **snapshots the ordered list**, changes asked-for to `routed`, and still creates **zero Tests**. Minting that queue record is planning; **work has not started**.
5. Open Experiments → **Work Orders** (`/work-orders`) and choose **Start process**. **First Start instantiates `chain[0]` only**. It does not mint a process-of-processes. Start process / LimsRun start remain `experiment:manage`; publish is `experiment:publish`.
6. Complete that process, then use **Later Start** only where the product has a valid continuing assignment. Process assignment is the **tube in hand** — a **container-with-sample** (Contents), not a naked sample. **Separate containers = separate assignments** when both are in play; do **not** collapse two tubes of the same Sample into one process-sample row. Assign with **no** vessel → **422** `process_container_required`; assign a sample sitting in **two** vessels with no `container_id` pick → **422** as well; receive-tube assign → **201**. Deiter’s C1 click **Pass** on `02fe95f` verifies those outcomes (history, not restamped). Deiter’s C2 **Fail** on `02fe95f` is signed history. Unsigned C2 numbered on **`570bbc0`**; execute **`1572071`** is same-type dest-follow only: same dest type = **same sample, additional container**; inbound assignment `removed` even if leftover volume remains; later Start follows that dest container. Amount 0 is an edge (**422**), not the AC. **Unsigned** until Tobias. Unsigned **C3** numbered on `570bbc0`; execute **`1572071`** is the different-dest-type click, also **unsigned**: **new derivative sample** in a new container (`parent_sample_id`). For either grain, execute puts the destination sample + destination container pair on `eln_process_samples` and marks the inbound source assignment `removed` in the same transaction. The parent Sample row stays for type-changing lineage, but its inbound process assignment does not. **PATCH is not a path.** Do not teach dest-follow as shipped. Later-step type-gate remains **Met** on `9342439` (qPCR on still-Blood **422** when no mint had run).

**Same-type follow vs type-changing derivative.** Same dest type = **same sample, additional container**. Unsigned C2 numbered on **`570bbc0`**; execute **`1572071`** covers only this same-type path and remains unsigned. `_follow_destination_in_process` moves the same sample’s active process assignment to the additional container; it does not require `entry.process_step_id`. Different dest type = **new derivative sample** in a new container with `parent_sample_id`. The parent **Sample row** stays as lineage, keeps its original type, and retains work attributable to the parent type; it is not retargeted onto the destination tube. In both paths, the destination sample + destination container pair lands on `eln_process_samples` and the inbound source assignment becomes `removed` in the execute transaction. Dest mint Hold is lifted only for type-changing execute. Deiter’s C2 **Fail** and dest mint Hold **Pass** on `02fe95f` remain signed history; that Hold Pass records Start extract still Blood / **0 DNA**, not a ban on type-changing derivative mint. **PATCH is not a path.** Extract-hold UAT step **1.7 is the AC-P2-C3 click** and is **unsigned** on `570bbc0`; it must not imply DNA on the parent.

**A Test stays `(sample, analysis)`.** The container records **which vessel was measured**; a concentration write-through hits **that** container. The container on the process is not a second Test key.

**WO-7 first-start freeze skip NULL is Tobias Pass on `bf51b19`.** Classic `/tests` leaves `asked_for_params` **NULL**. First LimsRun start writes the snapshot; later start does not overwrite. **OQ-WO-7 Closed** on `80f054b`; do not recode its same-analysis WO / parent-lineage / `{}` lookup. **OQ-WO-8 Closed:** Quantified DNA uses the existing Qubit analysis on the named asked-for slot; zero LimsRuns is not legal. Overall P2 remains unsigned.

Qubit-first on blood is refused by Route before a work order is minted. If Qubit is later, its step start refuses while the sample’s current type is still blood. A **422** `route_sample_type` means current type is wrong for the assigned first step or the later step being started; it does **not** mean the sample is broken. Dest mint Hold **Pass** on the Deiter click (`02fe95f`) means Start extract still leaves the tube Blood with **0 DNA** daughters. It does not close `_execute_transfer`. Deiter C2 **Fail** on `02fe95f` is signed history. Dest-follow execute on `1572071` is **unsigned** (C2/C3 numbered on `570bbc0`). Do **not** claim Start extract creates a DNA daughter or that dest-follow shipped.

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

The WO-7 lock puts Test selection/creation and params freeze on the **first LimsRun start** for the asked-for analysis — not receive, Route, or work-order Start. Freeze skip NULL is Tobias Pass on `bf51b19`. **OQ-WO-7 Closed** on `80f054b`; its lookup is unchanged. **OQ-WO-8 Closed:** existing Qubit is the named asked-for slot for Quantified DNA. Do not claim overall P2 Pass.

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
- Do **not** teach routing-map save or Route as ANDing one type across later processes or steps. Route gates only the first process’s first ordered Experiment/LimsRun; later starts gate current type. Later Start following dest container is the lock on **`1572071`**, **unsigned** until Tobias (C2/C3 numbered on `570bbc0`).
- Do **not** collapse ordered `process_definition[]` into one definition or an unordered bag. Start instantiates the first process only; later processes need later starts; the UI must preserve route order.
- Do **not** teach Route or Start as starting the whole chain.
- Do **not** treat zero or multiple acceptable routes as `first()`: empty Route → **422** is **Tobias-signed Pass** on `8cfa2a9`; two saved rows that both accept current type → **409** is **unsigned** this SHA.
- Do **not** recode OQ-WO-7 or rewrite its signed Pass on `80f054b`. The lookup remains same-analysis WO asked-for, else parent lineage, else `{}`.
- Do **not** teach `_mint_tests_at_start` `if test: continue` as a freeze.
- Do **not** teach skip-on-frozen-`{}` as a freeze on the old classic default. Classic `/tests` on `bf51b19` leaves `asked_for_params` **NULL**.
- Do **not** treat a classic `/tests` row with `asked_for_params` NULL as frozen. The first LimsRun start must **write** the snapshot onto that Test.
- Do **not** give extract an `analysis_id` or boolean Result. For Quantified DNA, reuse existing Qubit as the named asked-for slot; no second catalog analysis and no zero-LimsRun route. For WGS/WES/ELISA, Qubit remains process QC.
- Do **not** teach dest auto-joining a second WO or copy WGS params onto WES. **No route branching this phase.** Route blood for WGS (owns WGS params); C3 DNA then C2 aliquot into WGS; WES is a new asked-for on the DNA tube, which is then aliquoted or used up.
- Do **not** teach first Start minting later processes (Qubit/reporting) or their Tests as shipped. First Start instantiates `chain[0]` only. Later Start following dest (not the parent tube) is the lock on **`1572071`**, **unsigned** until Tobias (C2/C3 numbered on `570bbc0`).
- Do **not** teach Route as starting work. Route snapshots the ordered list, **zero Tests**.
- Do **not** claim freeze closed/verified on `8cfa2a9`. Signed AC-P2-9..11 history stays `9342439`; Leadership restamp notes are honesty, **not** a merge vote. Deiter clicked `0077` on `4671ba8` / `02fe95f`: C1 **Pass**, C2 **Fail**, dest mint Hold **Pass** — signed history. Dest-follow execute SHA **`1572071`**. UAT numbering SHA **`570bbc0`** (docs/uat split + pytest, **not** a new execute). C1/C2 on `02fe95f` are **not** unsigned. Overall P2 stays unsigned.
- Do **not** teach later Start as following the parent/source tube after an equivalent aliquot, or as legal assign of a sample with no container.
- Do **not** teach later Start as following a dest **type**. The follow is by dest **container**.
- Do **not** conflate same-type follow with type-changing derivative mint. Same dest type = same sample, additional container. Different dest type = new derivative sample in a new container (`parent_sample_id`); only the parent Sample row stays for lineage. In both paths the destination pair continues on the process and the inbound source assignment is `removed`.
- Do **not** scan DNA before extract execute. Plan dest type is catalog intent, not a Sample. There is no DNA tube until aliquot/pool execute.
- Do **not** teach dest existing at Route / Start / map-save / asked-for. Receive still mints identity + first vessel — that is **not** dest mint. Dest type on the plan is catalog intent until execute. Dest exists only after aliquot/pool execute.
- Do **not** write C2 or C3 Pass. Deiter C2 **Fail** on `02fe95f` stands as signed history. `570bbc0` does **not** inherit `1572071` C2 Pass or Fail. C2 execute on `1572071` is extra container, same sample (`_follow_destination_in_process`; leftover inbound volume is not a Fail) and C3 is the different-dest-type click — numbered on `570bbc0`, neither is QA-clicked, neither is a shipped Pass. **Fail C3 if dest tube is on the blood sample.** Do **not** teach `570bbc0` as a product execute SHA. Type-changing execute must not retarget the parent’s `container_id`. **PATCH is not a path.**
- Do **not** teach PATCH as a dest-follows path.
- Do **not** treat C1/C2 as unsigned. Deiter clicked them; Leadership Confirmed that stamp. Do not invent a Tobias Pass.
- Do **not** silently pick a vessel when a sample sits in two containers. That is **422**, not `first()`.
- Do **not** score extract-hold **1.7** as AC-P2-C2. 1.7 is AC-P2-C3 (DNA daughter). C2 is same dest type only. Both unsigned until Tobias.
- Do **not** turn Deiter’s Start-extract Hold history into a ban on type-changing execute minting a derivative.
- Do **not** teach `routing_map.analysis_id` as a required create field. Derive first-step types and chain LimsRun analyses at read.
- Not IC50. Not a fake Route how-to.
