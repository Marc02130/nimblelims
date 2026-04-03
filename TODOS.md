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

### ~~Configurable run lifecycle — CRO use case~~ COMPLETED (dose-response branch, 2026-04-02)

**Customer context:** Virtually every early-stage biotech startup uses CROs (Contract Research Organizations). Companies like Nimbus Therapeutics operate entirely through CROs. Option A (two built-in lifecycles) was shipped.

**Standard lifecycle:** `draft → running → complete → published | failed | canceled`

**CRO lifecycle:** `draft → ordered → running → results_received → complete → published | failed | canceled`

`canceled` is a terminal state reachable from any non-terminal state in both lifecycles.

**Shipped in migration 0044 + dose-response branch:**
- `experiment_run_status` ENUM extended: `ordered`, `results_received`, `canceled` added (AUTOCOMMIT pattern — `COMMIT` before `ALTER TYPE`, then `BEGIN` to resume)
- `experiment_runs.canceled_at` — timestamp set when run is canceled
- `experiment_templates.lifecycle_type` — `'standard'` (default) or `'cro'`
- `backend/models/flexible_experiment.py` — `VALID_TRANSITIONS` (standard), `VALID_TRANSITIONS_CRO`, `LIFECYCLE_TRANSITIONS` registry
- `backend/app/services/experiment_run_service.py` — `_lifecycle_transitions(run)` reads lifecycle_type from template; `order_run()`, `mark_results_received()`, `cancel_run()` added; import gate allows `running` OR `results_received`
- `backend/app/routers/experiment_runs.py` — `PATCH /{run_id}/order`, `/results-received`, `/cancel`
- `frontend/src/pages/ExperimentRunDetail.tsx` — dynamic action buttons conditional on status + lifecycle_type; Cancel Run shown for all non-terminal states
- `frontend/src/pages/RunsManagement.tsx` — STATUS_COLORS and STATUS_LABELS for all 8 statuses
- `frontend/src/services/apiService.ts` — `orderExperimentRun`, `markResultsReceived`, `cancelExperimentRun`

**Remaining:** Add `lifecycle_type` selector to the ExperimentTemplate editor UI so users can set CRO vs standard on a template (currently defaults to standard; must be set directly in DB or via API).

### ExperimentProcess / ProcessStep — not surfaced in UI

`experiment_processes` and `process_steps` tables exist (migration 0040) and are the right model for tracking sub-process execution within a Run (e.g., "Sample Prep → queued", "Plate Reading → in_process"). Neither is wired into the Run Detail UI — the tab only shows Overview, Data, and Dose Response. Building the process/step UI would enable real-time checklist tracking within a run.

### Experiment linking is a linked list, not a DAG

Experiments are chained via `ExperimentDetail` rows (`detail_type = "experiment_link"`), not a parent FK or adjacency table. Lineage traversal requires sequential lookups. There is no enforced ordering, no gate preventing Experiment 3 from starting before Experiment 2 completes, and no automated data promotion between steps. A scientist must wire the chain and promote values manually. A proper process graph (adjacency table with status gates) would be needed for strict pipeline enforcement.

---

---

## Experiment Run — What is implemented (as of dose-response branch, 2026-04-02)

This section is a retrospective reference. It documents what is fully shipped.

### Data model

| Table | Key columns |
|-------|-------------|
| `experiment_templates` | `id`, `name`, `lifecycle_type` (standard\|cro), `template_definition` JSONB, `active` |
| `experiment_runs` | `id`, `name`, `experiment_template_id`, `status` (ENUM), `lifecycle_type`, `started_at`, `completed_at`, `published_at`, `canceled_at` |
| `experiment_data` | `id`, `run_id`, `well_position`, `sample_id`, `row_data` JSONB — one row per imported instrument row |
| `template_well_definitions` | `id`, `template_id`, `well_position`, `qc_type`, `concentration`, `compound_id` |
| `dose_response_results` | `id`, `run_id`, `compound_id`, curve parameters, fit quality, `approved_at`, `rejected_at` |
| `experiment_processes` | `id`, `run_id` — sub-process tracking within a run (not yet wired to UI) |
| `process_steps` | `id`, `process_id`, step name, status — step-level checklist (not yet wired to UI) |

### Status state machine

**Standard:** `draft → running → complete → published | failed | canceled`

**CRO:** `draft → ordered → running → results_received → complete → published | failed | canceled`

`canceled` is terminal and reachable from any non-terminal state in both lifecycles.

### API surface (`/v1/experiment-runs`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List runs (paginated, filter by status) |
| POST | `/` | Create run from template |
| GET | `/{run_id}` | Get run detail |
| PATCH | `/{run_id}/order` | CRO: draft → ordered |
| PATCH | `/{run_id}/start` | Start run (ordered→running or draft→running) |
| PATCH | `/{run_id}/results-received` | CRO: running → results_received |
| PATCH | `/{run_id}/review` | running or results_received → complete |
| PATCH | `/{run_id}/complete` | alias for review |
| PATCH | `/{run_id}/cancel` | Any non-terminal → canceled |
| POST | `/{run_id}/import` | Import instrument CSV (allowed in running or results_received) |
| GET | `/{run_id}/data` | List imported data rows (paginated) |
| GET | `/{run_id}/worklist` | Export robot worklist CSV |
| POST | `/{run_id}/dose-response/fit` | Trigger curve fitting (R service) |
| GET | `/{run_id}/dose-response/results` | List dose response results |
| PATCH | `/{run_id}/dose-response/results/{result_id}/approve` | Approve curve |
| PATCH | `/{run_id}/dose-response/results/{result_id}/reject` | Reject curve |
| POST | `/{run_id}/dose-response/batch-approve` | Batch approve all curves |

### Frontend pages

- **RunsManagement** (`/runs`) — paginated list, filter by status, name search, "New Run" dialog
- **ExperimentRunDetail** (`/runs/:runId`) — three tabs: Overview, Data, Dose Response
  - Dynamic action buttons driven by `status` + `lifecycle_type`
  - Dose Response tab: Curve Grid (SVG thumbnails), per-curve approve/reject, batch approve, fit status

### Key implementation files

| File | Purpose |
|------|---------|
| `backend/models/flexible_experiment.py` | ORM models + state machine dicts |
| `backend/app/services/experiment_run_service.py` | All lifecycle transitions + data import |
| `backend/app/routers/experiment_runs.py` | API router |
| `backend/app/schemas/flexible_experiment.py` | Pydantic schemas |
| `backend/app/services/dose_response_fit.py` | Curve fitting orchestration |
| `backend/services/r_calculator_client.py` | HTTP client for R Plumber service |
| `frontend/src/pages/ExperimentRunDetail.tsx` | Run detail page + action buttons |
| `frontend/src/pages/RunsManagement.tsx` | Run list page |
| `frontend/src/pages/DoseResponse/DoseResponseTab.tsx` | Dose response tab |
| `frontend/src/services/apiService.ts` | All API calls |

### Known gaps / deferred

- `experiment_processes` and `process_steps` tables exist but are not wired to any UI
- No workflow engine actions for ExperimentRun (see Workflow Engine section below)
- `lifecycle_type` on ExperimentTemplate has no UI selector — must be set via API/admin
- Dose response end-to-end not validated with real instrument data (see separate TODO)

---

## Workflow Engine — What is implemented (as of 2026-04-02)

This section is a retrospective reference for the ELN workflow orchestration layer.

### Concept

A `WorkflowTemplate` defines a named sequence of actions stored as JSONB steps. When executed, the engine runs each step in a single database transaction, threading a `context` dict (carrying `experiment_id`, `execution_id`, etc.) across steps. A `WorkflowInstance` record captures the runtime state and context after completion.

### API surface

| Method | Path | Requires |
|--------|------|----------|
| GET | `/admin/workflow-templates` | config:edit |
| POST | `/admin/workflow-templates` | config:edit |
| GET | `/admin/workflow-templates/{id}` | config:edit |
| PATCH | `/admin/workflow-templates/{id}` | config:edit |
| DELETE | `/admin/workflow-templates/{id}` | config:edit (soft delete) |
| POST | `/workflows/execute/{template_id}` | workflow:execute |

### Implemented actions (fully functional)

| Action | What it does |
|--------|-------------|
| `create_experiment` | Creates an Experiment; sets `context["experiment_id"]` |
| `create_experiment_from_template` | Creates an Experiment from an ExperimentTemplate; sets `context["experiment_id"]` |
| `link_sample_to_experiment` | Links a sample to the experiment in context; sets `context["execution_id"]` |
| `add_experiment_detail_step` | Adds a detail row (free-form step) to the experiment in context |
| `link_experiments` | Links two experiments via `ExperimentDetail(detail_type="experiment_link")` |
| `update_experiment_status` | Updates the `status_id` FK on an experiment |

### Stub actions (defined in VALID_WORKFLOW_ACTIONS but no-op bodies)

`update_status`, `validate_custom`, `create_qc`, `assign_tests`, `create_batch`, `enter_results`, `send_notification`, `accession_sample`, `link_container`, `review_result`

These are recognized as valid action names (no 400 error) but execute `pass` — they are placeholders for future implementation.

### Key implementation files

| File | Purpose |
|------|---------|
| `backend/models/workflow.py` | WorkflowTemplate + WorkflowInstance ORM models |
| `backend/app/routers/workflows.py` | Admin CRUD + execute endpoint + `_run_action()` dispatcher |
| `backend/app/schemas/workflow.py` | Pydantic schemas + `VALID_WORKFLOW_ACTIONS` list |

### Architectural gap — no ExperimentRun actions

The workflow engine has zero actions for System 2 (ExperimentRun / instrument-driven assays). A scientist running an NGS pipeline that includes a plate-reader QC step cannot include that Run inside a Workflow. The two systems are separate silos.

**Missing workflow actions needed to bridge the gap:**

```python
create_experiment_run     # create ExperimentRun from template_id; store run_id in context
import_run_data           # attach + parse instrument file for run in context
await_run_complete        # block next step until run reaches 'complete'
promote_run_results       # write DoseResponseResult back to Test/Result pattern
```

This is the primary architectural gap for a future milestone — not a blocker for current CRO or dose-response work.

---

## Dose Response — Run 3 deferred items (from /autoplan 2026-04-02)

### Async fit queue
Current curve fitting is synchronous — the HTTP request blocks until R returns (up to 60s). For large runs (>500 compounds) or concurrent users, this will hit request timeouts and exhaust the DB connection pool. The right fix is a background task queue (Celery + Redis, or pg-based like pgqueue). The `fit_in_progress` flag and the reset endpoint (`POST /fit/reset`) are already in place as stepping stones. Deferred until concurrent user load or timeout complaints from real data.

### Advisory lock for true fit mutex
~~`SELECT FOR UPDATE` on the `ExperimentRun` row reduces the race window for double-fit, but does not eliminate it.~~ **CLOSED — not a real bug.** `SELECT FOR UPDATE` + committed `fit_in_progress=True` is a correct mutex. Request B sees `True` after Request A commits and returns 409. No advisory lock needed. Reviewed 2026-04-02.

### Backend integration tests (22 cases)
**DONE (2026-04-02).** 22 integration tests written in `backend/tests/test_dose_response.py`. Coverage: status gates, fit_in_progress mutex, R failure cleanup, control validation (3 cases), normalization math (2 cases), refit supersession (2 cases), review endpoints (2 cases), batch review (2 cases), exclusion CRUD (3 cases), get_summary (2 cases), mixed units. All 22 pass. Test infrastructure (testcontainers PostgreSQL, `db_session`, `TestClient`) was already in `conftest.py`.

### lifecycle_type selector in ExperimentTemplate editor UI
**DONE (2026-04-02).** `ExperimentTemplatesManagement.tsx` now has a lifecycle_type dropdown (Standard / CRO) in the create/edit form and a column in the DataGrid list view. `apiService.ts` updated to include `lifecycle_type` in create/update payloads. Backend schema already exposed `lifecycle_type` — frontend-only change.

### CSV export of IC50 results
Scientists want to bulk-export `(compound_id, IC50, hill_slope, r_squared, review_status)` from a run to CSV. The `GET /results` endpoint has all the data; it just needs a `?format=csv` query param and a streaming response. Deferred until Curve Curator workflow is validated with real data.

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
