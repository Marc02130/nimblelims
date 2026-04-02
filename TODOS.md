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
