# How to run the lab path

Short operator path: receive → **requested analysis** → route (later) → Process / Experiment / LimsRun → results.

This is a how-to, not a PRD. Marc keeps it current as features ship.

**Honest status**

| Step | Status |
|------|--------|
| Receive (`/receive`) | Shipped on `main` |
| Requested analysis (`/asked-for`) | P1 lake on `feat/asked-for-p1` (PR 81) until that merges |
| Route / work order | **Not this slice** |
| Process / Experiment / LimsRun | Execute substrate shipped; P1 does **not** start it |
| Results | Classic type-a-number on a Test; persist lock is a later packet |

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

1. Set sticky **sample type**, **project**, and **1×1 container type** (required; pick existing — no auto-create). Session-sticky; they stay after each commit.
2. Scan or type the **primary barcode**. Optionally **Add** more barcodes for the **same** sample (more tubes, not aliquots).
3. Optional temperature and client sample ID.
4. **Receive**. Toast. Barcodes clear. Focus returns to primary. **Stay on the form.**

**One transaction:** Sample + first vessel (and any additional vessels) + Contents. Lab sample ID comes from the name template — **no sample-ID field**. Tube barcode is `containers.name`. Status is **Available for Testing**.

**Live form (match the UI):** matrix is **not** on receive (`samples.matrix` stays unset). Container type **is** on the form: active **1×1** only (`rows=1` and `columns=1`); plates are hidden and the API refuses them (**400**). Same type for every vessel on the commit.

**Do not send `analysis_ids`.** The UI never offers an analysis picker. Omit the field or send `[]`. Non-empty → **422** before any write. Zero Tests. Zero Results.

Duplicate barcode → **409**, full rollback, stay on receive.

Client / no `sample:create` → no Receive nav or **403**.

---

## 3. Requested analysis (asked-for lake, P1)

After receive, record **requested analysis**. That is the asked-for lake.

**Copy lock:** say **requested analysis**. Do **not** say asked-for assigns a Test or starts work.

**UI (when P1 is on the build):** Sample Mgmt → **Asked-for** (`/asked-for`), immediately after Receive. Also a section on sample detail.  
**API:** `POST /v1/asked-for` · `GET /v1/asked-for` · `POST /v1/asked-for/{id}/cancel`.

1. Receive first (identity + vessels). Sample is Available for Testing. Tests count is 0.
2. Open Asked-for → **Record requested analysis**.
3. Pick sample(s), pick an active analysis, TAT ≥ 1 (days). Save. Stay on `/asked-for`.

One action may cover a set of samples (same analysis + TAT). The API still writes one row per sample. Status is `requested`. Cancel while `requested` is allowed; then you may record the same analysis again. Duplicate open `(sample, analysis)` → **409**.

**Does not** create a Test. **Does not** start a process, Experiment, or LimsRun. Receive freeze stays: non-empty `analysis_ids` on receive is still **422**. No Start / Execute / Route on this screen.

Client write → **403**. Hidden / other-project sample → **403** (not 404).

Params: P1 may send `{}`. Assay params freeze at **LimsRun start** when that packet exists — **not** on receive.

---

## 4. Route / work order

**Not this slice.** Not shipped. Do not look for a Route CTA.

Later packet: tech hits Route; a routing map (`analysis` × `sample_type` × TAT) may mint a `work_order`. That work_order feeds Process / Experiment / LimsRun. Test row at **LimsRun start** (WO-7), not at receive, not on asked-for, not on work_order save.

---

## 5. Process / Experiment / LimsRun

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

## 6. Results

Classic path: **Results** (`/results`) — type a number on an existing Test (batch grid). Unit from `analytes.units_default` when that lock is enforced; missing unit is a later persist-packet **422**, not a receive rule.

Params freeze at **LimsRun start** when the work-order packet exists — **not** on receive.

LimsRun **publish** can promote instrument rows onto Tests/Results. Two writers on the same Test → **409**. Publish must not invent a Test if WO-7 is in force.

UAT (classic): [`UAT_Scripts/uat-results-entry-review.md`](../UAT_Scripts/uat-results-entry-review.md). Persist lock (P3) is specified on the spine packet, not shipped as that slice.

---

## 7. What not to do

- Do **not** mint a Test at intake. Do **not** send non-empty `analysis_ids` on receive.
- Do **not** hop off `/receive` after a successful scan — stay on the form.
- Do **not** treat requested analysis as “assign test” or “start work.”
- Do **not** invent a second workflow engine. Work_order (later) feeds the Process / Experiment / LimsRun that already exist.
- Do **not** put analysis param defs on receive.
- Not IC50. Not a fake Route how-to.
