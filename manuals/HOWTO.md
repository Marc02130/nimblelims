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
| Route / work order | **Not this slice** |
| Process / Experiment / LimsRun | Execute substrate shipped; P1 does **not** start it |
| Results | Classic type-a-number on a Test; persist lock is a later packet |
| Requested analysis (`/asked-for`) — later look-up, off the bench path | P1 lake on `feat/asked-for-p1` (PR 81) until that merges |

Local legacy handbooks (not on git): `.docs/manuals/` — `dev-setup.md`, `admin-setup.md`, `atomic-receive.md`, `processes.md`, `experiments.md`, `lims-runs.md`, `api-endpoints.md`, `navigation.md`.  
UAT: [`UAT_Scripts/uat-atomic-receive.md`](../UAT_Scripts/uat-atomic-receive.md) · P1 [`UAT_Scripts/uat-post-receive-work-spine.md`](../UAT_Scripts/uat-post-receive-work-spine.md) (on the asked-for branch).  
Stamps: [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../.docs/decision-logs/framework-stamps-2026-08-26.md) (WO-7: Test at LimsRun start, not at receive).

---

## 1. Start / login

Bring the stack up and log in. Do not duplicate setup here.

- Dev / compose: local `.docs/manuals/dev-setup.md` and root [`README.md`](../README.md) Quick Start.
- Admin password: local `.docs/manuals/admin-setup.md`.
- Frontend: http://localhost:3000 · API: http://localhost:8000 · docs: http://localhost:8000/docs.
- Lab path accounts: `admin` / `admin123` · `lab-tech` / `labtech123` · `alice-tech` / `alice123`. Change the default admin password.

Need `sample:create` for Receive. Need `test:assign` plus project access for requested analysis. Client role cannot receive and cannot write asked-for.

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

## 3. Route / work order

**Not this slice.** Not shipped. Do not look for a Route CTA.

Later packet: tech hits Route; a routing map (`analysis` × `sample_type` × TAT) may mint a `work_order`. That is also where the wrong pairing (e.g. Qubit on blood) is refused. That work_order feeds Process / Experiment / LimsRun. Test row at **LimsRun start** (WO-7), not at receive, not on asked-for, not on work_order save.

---

## 4. Process / Experiment / LimsRun

The execute substrate is already in the app. Requested analysis does **not** open it.

| Where | What |
|-------|------|
| **Experiments** → All Experiments (`/experiments`) | ELN experiment list/detail. `experiment:manage`. |
| **Experiments** → Experiment Templates (`/experiments/templates`) | Template authoring. Same permission. |
| **Experiments** → Processes (`/experiments/processes`) | ELN process **definitions** and **instances**. Assign samples (Samples list → **Assign to process**, or on the process). Start a step (Experiment or lazy LimsRun). |
| **Experiments** → Runs (`/runs`) | LIMS Runs: create/start/import/review/publish. Every run has an **analysis**. |

Deeper local handbooks: `.docs/manuals/processes.md`, `experiments.md`, `lims-runs.md`.

P1 does not instantiate a process from requested analysis. Classic `/tests` can still mint a Test for typing a number; that is **not** the request path.

---

## 5. Results

Classic path: **Results** (`/results`) — type a number on an existing Test (batch grid). Unit from `analytes.units_default` when that lock is enforced; missing unit is a later persist-packet **422**, not a receive rule.

Params freeze at **LimsRun start** when the work-order packet exists — **not** on receive.

LimsRun **publish** can promote instrument rows onto Tests/Results. Two writers on the same Test → **409**. Publish must not invent a Test if WO-7 is in force.

UAT (classic): [`UAT_Scripts/uat-results-entry-review.md`](../UAT_Scripts/uat-results-entry-review.md). Persist lock (P3) is specified on the spine packet, not shipped as that slice.

---

## Later look-up: requested analysis (asked-for lake, P1)

*Deliberately outside the numbered path. It is a look-up, not a step in the bench motion.*

**Not the next step after receive.** Asked-for is a **separate motion**, done whenever someone needs to see or record what was asked for — reading a client request, a study plan, a paper form. Nobody is waiting on the bench for it, and it is **not** a Start queue: a `requested` row has no Start / Execute / Route CTA and no work behind it.

**Copy lock:** say **requested analysis**. Do **not** say asked-for assigns a Test, orders work, or starts work.

**UI (when P1 is on the build):** Sample Mgmt → **Asked-for** (`/asked-for`). Also a section on sample detail, which is where a tech normally meets it.  
**API:** `POST /v1/asked-for` · `GET /v1/asked-for` · `POST /v1/asked-for/{id}/cancel`.

**What a row is:** **requested analysis + TAT**, against an already-received sample. That is all.

1. The sample must already be received (identity + vessels), Available for Testing, Tests count 0.
2. Open Asked-for → **Record requested analysis**.
3. Pick sample(s), pick an active analysis, TAT ≥ 1 (days). Save. Stay on `/asked-for`.

One action may cover a set of samples (same analysis + TAT). The API still writes one row per sample. Status is `requested`. Cancel while `requested` is allowed; then you may record the same analysis again. Duplicate open `(sample, analysis)` → **409**.

**Save is not scientific assignment.** A saved row does **not** assign a Test, does **not** attach analytes, and does **not** make type-a-number legal. It does **not** create a Test, Result, Process, Experiment, LimsRun, or work_order. Receive freeze stays: non-empty `analysis_ids` on receive is still **422**.

**The lake accepts nonsense on purpose.** Qubit-on-blood may sit in it. Scientific eligibility is refused **later**, at routing (`route_sample_type` **422**, P2) — not by the lake.

Client write → **403**. Hidden / other-project sample → **403** (not 404).

Params: intent only. P1 sends `{}` OOB — do not type assay params here, and do not enter them in P1 UAT. Params freeze at **LimsRun start** (P2 / WO-7), not on receive and not on asked-for.

---

## 6. What not to do

- Do **not** teach receive → asked-for as one motion. Receive ends on `/receive`.
- Do **not** hop off `/receive` after a successful scan — stay on the form for the next tube.
- Do **not** put Asked-for in front of the tech as the after-receive click or as a Start queue.
- Do **not** mint a Test at intake. Do **not** send non-empty `analysis_ids` on receive.
- Do **not** treat a saved requested analysis as “assign test,” “attach analytes,” or “start work.”
- Do **not** pick container type in the scan loop. Default tube, off the form (RQ-AR-8).
- Do **not** invent a second workflow engine. Work_order (later) feeds the Process / Experiment / LimsRun that already exist.
- Do **not** put analysis param defs on receive, and do **not** type params on asked-for.
- Not IC50. Not a fake Route how-to.
