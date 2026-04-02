# TODOS

## ~~Client-scoped RLS for experiment_templates and pre-0039 tables~~

**Completed:** experiment-template-isolation branch — migration 0042 applies client-scoped RLS + FORCE ROW LEVEL SECURITY to all four 0036 tables (`experiment_templates`, `experiments`, `experiment_details`, `experiment_sample_executions`). Decision: private by default (no cross-org sharing). Tests in `backend/tests/test_rls_experiment_isolation.py`.

---

## Hamilton-specific worklist format

**What:** Add Hamilton .csv worklist format output as an alternative to the generic CSV.

**Why:** Hamilton is the most common liquid handling robot at Series A biotech. Generic CSV works and maps to any robot, but scientists running Hamilton robots will want a native format that loads directly without a field-mapping step.

**Pros:** Reduces friction for the most common robot type at NimbleLIMS's target customer. Unlocks a demo talking point: "it generates a Hamilton worklist directly."

**Cons:** Hamilton format is validated against a specific robot model/firmware version. Needs a real Hamilton worklist to test against before shipping. Minor maintenance burden if Hamilton changes their format.

**Context:** Phase 2 of the NimbleLIMS flexible experiment engine adds robot worklist export as generic CSV (source_well, dest_well, volume). Hamilton format was deliberately deferred until the generic CSV path is validated with a real experiment end-to-end. See design doc: `~/.gstack/projects/garrytan-gstack/marcbreneiser-main-design-20260324-214055.md`.

**Depends on / blocked by:** Generic CSV worklist export (Phase 2) validated with a real experiment run.

---

## ~~Paginate GET /experiment-runs/{id}/data~~

**Completed:** v0.0.0 (2026-03-25) — commit `e97e93c` on branch `Paginate-Experiment-Runs`

`GET /experiment-runs/{id}/data` now accepts `page`/`size` query params and returns an `ExperimentDataListResponse` envelope (rows/total/page/size/pages). Worklist export path uses `list_all_for_run` (unbounded) — intentional.

---

## ~~Background task connection pool: release DB before API call~~

**Completed:** v0.0.0 (2026-03-25) — commit `56410e2` on branch `Paginate-Experiment-Runs`

`run_extraction_background` now uses two short-lived sessions: Session 1 marks the job as processing and closes, the Anthropic API call runs with no DB connection held, then Session 2 writes the result.

---

## Dose Response — Deferred items (from /autoplan 2026-04-02)

### Multi-plate normalization
Control averaging across multiple plates in a single run. Current design normalizes within a single run (one set of controls per run). Cross-plate normalization needed for large screens where controls are on a dedicated plate. Deferred to after dose-response v1 ships and is validated.

### PDF report generation
Export dose response results (curves + IC50 table) to PDF. The `POST /svg/full` endpoint on the R service is the hook — full-size SVG per compound. FastAPI needs a PDF assembly layer (e.g., WeasyPrint or ReportLab). Deferred — endpoint exists, implementation deferred.

### Parallel Plumber workers (future/callr)
R service is single-threaded by default. For multi-tenant SaaS with concurrent users on different runs, Plumber's `future`/`callr` async workers would let R handle multiple `/fit` requests simultaneously. The `fit_in_progress` boolean prevents per-run conflicts. Cross-run queuing at R is acceptable for v1. Deferred until concurrent user load requires it.

### ~~Relational concentration storage~~
**Completed (scope change 2026-04-02)**: User chose to add `template_well_definitions` table in migration 0043. Concentrations are now in a relational table from day 1.

### Cross-experiment IC50 comparison / trend analysis
Compare IC50 values for the same compound across multiple experiment runs. Requires concentration data to be queryable (see relational concentration storage above). Deferred until base dose response feature is validated with real data.

### Pre-fit validation endpoint
`GET /experiment-runs/{id}/dose-response/validate` — check that control wells are identified, concentrations are present, and template is configured before triggering a fit. Currently the validation happens inline at fit time (422 on failure). A separate validation endpoint allows the UI to show pre-flight checks before the "Fit Curves" button is clicked. Nice-to-have for v2.

---

## Architecture: Two Systems, One Gap (documented 2026-04-02)

This section captures architectural decisions and gaps identified during design review. Not a single feature — context for prioritization.

### The two systems

NimbleLIMS has two parallel experiment tracking systems that serve different workflows and are not connected to each other.

**System 1 — ELN (Experiments)**
The Electronic Lab Notebook. Designed for multi-step, multi-instrument workflows like NGS sample prep where a process chains together many experiments:

```
Blood received
  └── DNA Extraction    [Experiment]  → steps/entries, sample conditions
  └── QC                [Experiment]  → result written to Test/Result
  └── Normalization      [Experiment]  → processing_conditions per sample
  └── Library Prep       [Experiment]  → steps/entries
  └── Pooling            [Experiment]  → links to previous experiments
  └── Flowcell Loading   [Experiment]
  └── Sequencing data → analysis pipeline (out of scope)
```

Data lives in `ExperimentDetail` (free-form key/value rows, typed by `detail_type`) and `ExperimentSampleExecution` (sample↔experiment junction with role, conditions, replicate). Results can be manually promoted to the `Test/Result` pattern via `result_id`/`test_id` FKs on the execution record.

The Workflow engine (`WorkflowTemplate` + `WorkflowInstance`) orchestrates this system. A `WorkflowTemplate` defines a sequence of actions (JSONB steps) such as `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `assign_tests`, `enter_results`, `review_result`. Experiments are chained via `ExperimentDetail` rows with `detail_type = "experiment_link"` — lineage is a linked list of detail rows, not a parent FK.

**System 2 — Runs (Instrument-driven assays)**
Designed around the core NimbleLIMS value proposition: upload an SOP + instrument output file, Claude extracts the template (protocol steps, plate layout, result columns, instrument parser config, robot worklist config), and every subsequent run against that template imports instrument data validated against the parser. Dose-response curve fitting, Curve Curator review, and batch approval live here.

```
SOP + instrument file
  → Claude API (SopParseJob) → ExperimentTemplate + InstrumentParser + RobotWorklistConfig
  → Scientist creates ExperimentRun from template
  → Imports instrument CSV → ExperimentData rows (validated against parser_config)
  → Fit Curves → DoseResponseResult per compound
  → Curve Curator review → batch approve → publish
```

Data import requires an `InstrumentParser` on the template — there is no manual entry path. This is by design: Runs are for instrument-driven, repeatable assays, not manual observation.

### The gap: Workflow engine does not know about Runs

The Workflow engine (`workflows.py`) has actions for every operation in System 1 but **zero actions for System 2**. There is no `create_experiment_run`, no `import_run_data`, no `promote_run_results`. A scientist running an NGS pipeline that includes a plate-reader QC step (which produces an instrument file) has no way to include that Run inside a Workflow. The two systems are separate silos.

**Missing workflow actions needed to bridge the gap:**

```python
create_experiment_run     # create ExperimentRun from template_id; store run_id in context
import_run_data           # attach + parse instrument file for run in context
await_run_complete        # poll/gate: block next step until run reaches 'complete'
promote_run_results       # write ExperimentData/DoseResponseResult back to Test/Result pattern
```

Without these, the Workflow engine orchestrates the ELN side only. Instrument-driven steps must be done manually outside the workflow and results linked back by hand.

### Configurable run lifecycle — CONCRETE REQUIREMENT (CRO use case)

**Customer context:** Virtually every early-stage biotech startup uses CROs (Contract Research Organizations) — lab equipment is expensive and most startups have no lab of their own. Companies like Nimbus Therapeutics operate entirely through CROs. NimbleLIMS must support the CRO lifecycle as a first-class citizen alongside the standard in-house lifecycle.

**Standard (in-house) lifecycle:**
```
draft → running → complete → published | failed
```

**CRO lifecycle:**
```
draft → ordered → running → results_received → complete → published | failed
```

- `ordered` — experiment sent to CRO, awaiting confirmation they have started
- `running` — CRO has confirmed the experiment is in progress
- `results_received` — CRO has returned the instrument data file; ready to import
- Data import must be allowed in `results_received` state (not just `running`)

**Current state:** The lifecycle is hardcoded in two places that must change together:
1. `ExperimentRunStatus` Python enum (`models/flexible_experiment.py`) — 5 fixed values
2. `VALID_TRANSITIONS` dict — hardcoded state machine
3. DB column is a Postgres `ENUM` type — requires `ALTER TYPE` migration to add values
4. `import_data()` in `experiment_run_service.py` gates import on `status == running` only

**Implementation options:**

*Option A — Two built-in lifecycles (pragmatic, low risk):*
Add `ordered` and `results_received` to the Postgres ENUM and Python enum. Add a `lifecycle_type` field (`standard` | `cro`) to `ExperimentTemplate`. Service layer selects `VALID_TRANSITIONS` based on `lifecycle_type`. Import gating allows `running` OR `results_received`. UI shows appropriate transition button labels per lifecycle type ("Start Run" vs "Mark as Ordered" vs "Mark Results Received"). Covers the concrete requirement with minimal new surface area.

*Option B — JSONB lifecycle config (flexible, higher complexity):*
`lifecycle_config` JSONB on `ExperimentTemplate` defines allowed states and transitions per template. DB column changes from Postgres ENUM to `VARCHAR`. Service reads transitions at runtime. UI renders state machine dynamically from config. Fully arbitrary — supports any future lifecycle without code changes. Significantly more implementation work; config validation needed.

**Recommendation:** Ship Option A now to unblock CRO customers. Build Option B when a third lifecycle variant emerges that can't be covered by the two built-in types.

**Files to change (Option A):**
- `backend/db/migrations/versions/` — new migration: `ALTER TYPE experiment_run_status ADD VALUE 'ordered'; ALTER TYPE experiment_run_status ADD VALUE 'results_received';`
- `backend/models/flexible_experiment.py` — add enum values; add `VALID_TRANSITIONS_CRO`
- `backend/models/experiment.py` (ExperimentTemplate) — add `lifecycle_type` column
- `backend/app/services/experiment_run_service.py` — select transitions by lifecycle_type; update import gate
- `frontend/src/pages/ExperimentRunDetail.tsx` — dynamic action button labels
- `frontend/src/pages/RunsManagement.tsx` — status badge labels for new states

### ExperimentProcess / ProcessStep — not surfaced in UI

`experiment_processes` and `process_steps` tables exist (migration 0040) and are the right model for tracking sub-process execution within a Run (e.g., "Sample Prep → queued", "Plate Reading → in_process"). Neither is wired into the Run Detail UI — the tab only shows Overview, Data, and Dose Response. Building the process/step UI would enable real-time checklist tracking within a run.

### Experiment linking is a linked list, not a DAG

Experiments are chained via `ExperimentDetail` rows (`detail_type = "experiment_link"`), not a parent FK or adjacency table. Lineage traversal requires sequential lookups. There is no enforced ordering, no gate preventing Experiment 3 from starting before Experiment 2 completes, and no automated data promotion between steps. A scientist must wire the chain and promote values manually. A proper process graph (adjacency table with status gates) would be needed for strict pipeline enforcement.

---

## Dose Response — End-to-end flow needs test data (2026-04-02)

The full curve-fitting path (Fit Curves → SVG thumbnails → Curve Curator review → batch approve) was verified structurally during QA but not exercised with real data. To validate end-to-end:

1. Create samples with `qc_type` set (positive control, negative control)
2. Add `TemplateWellDefinition` rows to the template with concentration values
3. Import instrument data rows that include inhibition-relevant columns
4. Trigger Fit Curves → verify R calculator returns curve parameters
5. Verify SVG thumbnails render in Curve Grid
6. Approve/reject individual curves and batch-approve

Blocked on having a real or realistic synthetic instrument file that matches the parser config of an existing template.
