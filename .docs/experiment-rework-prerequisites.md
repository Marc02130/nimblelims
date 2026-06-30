# Experiment / Experiment Runs Rework — Prerequisites & Issues Checklist

**Date:** 2026-06-29  
**Context:** On the `dose-response` branch. The system has two largely parallel experiment tracking mechanisms that share only `experiment_templates`:
- **ELN Experiments** (`experiments`, `experiment_details`, `experiment_sample_executions`)
- **Flexible Experiment Runs** (`experiment_runs`, `experiment_data`, dose-response results, parsers, worklists, processes)

This document captures issues, inconsistencies, gaps, and bugs that should be reviewed, fixed, or explicitly decided **before or as the first phase of any significant rework** of these areas.

---

## Top-Level Checklist (start here)

- [x] Fix the one failing test in flexible experiments (pagination response shape) — **done**
- [x] Standardize error handling in experiment-related frontend pages (eliminate raw `.detail` access that crashes on Pydantic V2 errors) — **done** (ExperimentsManagement, ExperimentRunDetail, ExperimentTemplatesManagement now use `apiErrorMsg`)
- [ ] Decide and document the target data model shape (one model? parent/child? "Run is an execution of Experiment"?)
- [ ] Decide name uniqueness rule (global unique via BaseModel vs per-client service enforcement) and plan any constraint migration
- [ ] Decide status modeling strategy (converge on enum? keep list_entry for ELN? hybrid?)
- [ ] Decide client scoping approach (explicit `client_id` columns + RLS vs. pure `created_by` RLS functions) for unified tables
- [ ] Audit and fix (or accept) the dose-response fit concurrency issues (fit_in_progress + refit versioning)
- [ ] Add or document missing ownership assertions in exclude/unexclude endpoints (beyond RLS query visibility)
- [ ] Decide whether to add `active` / soft-delete consistency for runs or remove it from the ELN side
- [ ] Plan how (or if) ELN `Experiment` and `ExperimentRun` will be linked (new FK? junction? promotion path?)
- [ ] Add workflow engine actions for runs (`create_experiment_run`, `import_run_data`, `promote_run_results`, etc.) — or explicitly defer
- [ ] Wire (or explicitly remove) the existing `experiment_processes` / `process_steps` feature into the Run detail UI
- [ ] Enforce (or document) rules for using templates with `lifecycle_type`, `active=false`, mandatory_review, etc.
- [ ] Align test data expectations and add regression tests for the new unified model
- [ ] Clean deprecation warnings (`HTTP_422_UNPROCESSABLE_ENTITY`, `utcnow()`) in experiment paths

---

## 1. Concrete Bugs & Broken Tests

| Issue | Location | Severity | Notes |
|-------|----------|----------|-------|
| `test_get_data_rows_after_import` expects old non-paginated response | `backend/tests/test_flexible_experiment.py:346` (`assert len(data) == 1; data[0]...`) | High (blocks clean CI) | Pagination was added; one test site was missed. Other import test uses `data["rows"]` correctly. |
| Raw `.detail` error handling (Pydantic V2 crash risk) | `ExperimentsManagement.tsx` (multiple), `ExperimentRunDetail.tsx` (2 sites) | Medium-High | `RunsManagement.tsx` already uses the safe `apiErrorMsg` helper. |

**Action:** Fix the test + port safe error helper to the remaining experiment pages before major changes.

---

## 2. Data Model & Schema Inconsistencies (Biggest Rework Risk)

### Inheritance & Core Columns
- `Experiment` / `ExperimentTemplate` extend `BaseModel` (provides `id`, global `unique=True` on `name`, `active`, full audit).
- `ExperimentRun` / `ExperimentData` / parsers etc. extend raw `Base` (no global name unique, no `active`).
- `DoseResponseResult`, `ExperimentDataExclusion`, `TemplateWellDefinition` have explicit `client_id` + FK.
- Core experiment tables (`experiment_runs`, `experiments`, `experiment_templates`, ...) have **no** `client_id` column; isolation is only via RLS policies on `created_by`.

### Status
- ELN: `status_id` FK to `list_entries`.
- Runs: `ExperimentRunStatus` enum (8 values) + multiple timestamp columns (`started_at`, `completed_at`, `published_at`, `canceled_at`).
- CRO vs standard lifecycles are encoded only on the Run side via `lifecycle_type` on the shared template.

### Name Uniqueness
- Experiments: enforced at DB level (global).
- Runs: deliberately **not** globally unique; service layer does per-client check via `created_by → user.client_id`.

### Soft Delete / Active
- ELN uses `active`.
- Runs have no `active` flag; terminal states are the only way to "retire" a run.

**Implication:** Any unification will require a deliberate choice + migration for at least name constraints, status, active, and client scoping columns.

---

## 3. RLS / Multi-Tenancy Asymmetries

- 0041 + 0042 + 0045 migrations added `FORCE ROW LEVEL SECURITY` + client-scoped policies for all experiment-related tables.
- Dose-response tables use explicit `client_id` (easier direct filtering + ownership checks).
- Core tables rely on `has_experiment_access()` SECURITY DEFINER function + subquery on `created_by`.
- `exclude_data_point` / `unexclude_data_point` in `dose_response.py` load rows by raw ID + join but do **not** add an explicit `client_id` or `created_by` filter in the Python query (TODO item from adversarial review).
- ListEntry QC type lookups in dose-response fit cross tenants unless RLS protects `list_entries` (needs confirmation in rework).

**Recommendation:** Before unifying tables, pick one ownership pattern and apply it consistently (or keep the split and document why).

---

## 4. Missing or Incomplete Integration Points

### Workflow Engine
- Full actions exist for ELN side: `create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `update_experiment_status`.
- **Zero actions** for the Run side (explicit gap called out in `TODOS.md`).
- Required for "instrument steps inside a larger workflow" use case.

### Linking Experiments ↔ Runs
- No FK, no junction table, no `experiment_id` on `experiment_runs`.
- The "Runs" tab inside `ExperimentsManagement.tsx` just does a broad list of runs (comment: "Experiment runs are not yet filterable by experiment_id in the API").
- `GET /experiment-runs` supports `?template_id=`, but nothing higher-level tying a Run to an ELN Experiment instance.

### Sub-process Tracking
- `experiment_processes` + `process_steps` tables + full API (CRUD + start/complete/fail/notes) exist (migration 0040).
- **Not surfaced** in `ExperimentRunDetail.tsx` (only Overview / Data / Dose Response tabs).

---

## 5. Template Sharing Issues

- One `ExperimentTemplate` row powers two very different execution models.
- `template_definition` is free-form `JSONB` in the experiment service; strict `TemplateDefinition` Pydantic model is only used on SOP parse + apply path.
- You can create an `ExperimentRun` from a template where `active=false`.
- `lifecycle_type` on the template only affects Runs (ELN Experiments still use list_entry status).
- Mandatory review / sign-off flow only applies to the flexible engine path.

---

## 6. Frontend / UX Fragmentation

- Sidebar groups `/experiments`, `/experiments/templates`, and `/runs` under one "Experiments" accordion (intentional).
- `MainLayout` titles and route handling treat them as related but separate.
- `ExperimentRunDetail` action buttons are status + lifecycle_type driven (good).
- The embedded Runs list in the ELN detail page is acknowledged as temporary.

**During rework:** decide whether Runs become a sub-view of Experiments (or vice versa) or remain sibling top-level concepts.

---

## 7. Correctness & Concurrency (Dose-Response on Runs)

From code + `TODOS.md` adversarial review notes (some still relevant):

- `fit_in_progress` mutex: `SELECT ... FOR UPDATE` is used, but check-then-set + long-running work + separate commits still leaves a theoretical window. Second caller may see stale `False`.
- Concurrent refits can both read `fit_version = N` and both write `N+1`, producing orphaned result rows. No `FOR UPDATE` on the "find prior" query and no unique constraint on `(run_id, sample_id, fit_version, superseded_by)`.
- Full SVG endpoint recomputes normalization instead of using stored values from the `DoseResponseResult`.
- Exclusions are visible in some SVG renders.
- R service response is not fully schema-validated before DB write.

These live on the Run + dose-response path. A rework that touches fitting or data import should address them.

---

## 8. Other Technical Debt / Polish

- Multiple deprecation warnings in experiment paths (`HTTP_422_UNPROCESSABLE_ENTITY`, `datetime.utcnow()` in security + workflow code).
- Hamilton-specific worklist export is documented as deferred (lower priority).
- Cross-experiment IC50/trend analysis, PDF reports, pre-fit validation endpoint, async fit queue are deferred.
- `ExperimentDetail` lineage is a linked-list of `detail_type = "experiment_link"` rows (not a DAG with ordering/gates).
- Some SQLAlchemy relationship overlap warnings appear during test mapper configuration (not experiment-specific but noisy).

---

## 9. Documentation & Process Items

- Update `TODOS.md` to reference this document once created.
- Ensure any rework PR updates `.docs/experiment-planning.md`, `README.md` (features section), `api_endpoints.md`, and UAT scripts.
- Add or expand tests for the chosen unified model (the current 22 dose-response + flexible experiment tests are a good base; one is currently broken).
- Consider adding RLS isolation tests that cover the new linking if introduced.

---

## Recommended Phasing Before/During Rework

1. **Stabilize (do these first)**
   - Fix the failing pagination test.
   - Port safe error handling to all experiment frontend pages.
   - Clean the most glaring deprecation warnings in touched files.

2. **Make Decisions (document in a short ADR or update to this file)**
   - Unified model shape + relationship between ELN Experiment and Run.
   - Name uniqueness, status, active, client scoping.
   - Whether workflow actions for runs are in scope for the same milestone.

3. **Foundation Work (can be done in parallel with or right after decisions)**
   - Add missing workflow actions (if in scope).
   - Add proper ownership checks or client_id assertions where currently relying only on RLS.
   - Address the fit concurrency items (or accept with comments).
   - Decide fate of process/step tracking (wire it or remove the dead API surface).

4. **The Actual Model + UI Rework**
   - Schema changes + data migration.
   - Service / router consolidation or clear layering.
   - Update navigation, linking, and detail pages.
   - Add/update tests and RLS tests.

5. **Polish & Docs**
   - Fix remaining warnings.
   - Update all planning docs, README, API docs.
   - Run full UAT scripts for experiment flows.

---

## Files Most Likely to Change in Any Rework

**Backend models:** `models/experiment.py`, `models/flexible_experiment.py`, `models/experiment_process.py`, `models/dose_response.py`, `models/template_well.py`

**Services/Routers:** `app/services/experiment*`, `app/routers/experiments.py`, `experiment_runs.py`, `dose_response.py`, `workflows.py`

**Repositories:** `app/repositories/experiment_repository.py`, `flexible_experiment_repository.py`

**Frontend:** `pages/ExperimentsManagement.tsx`, `ExperimentRunDetail.tsx`, `RunsManagement.tsx`, `ExperimentTemplatesManagement.tsx`, `Sidebar.tsx`, `App.tsx`, `apiService.ts`

**Tests:** `tests/test_flexible_experiment.py`, `test_dose_response.py`, `test_experiment_process.py`, `test_rls_experiment_isolation.py`

**Docs:** `TODOS.md`, `.docs/experiment-planning.md`, `README.md`, `.docs/api_endpoints.md`

---

## References

- `TODOS.md` (especially "Architecture: Two Systems, One Gap", dose-response deferred items, concurrency review)
- `.docs/experiment-planning.md`
- Migrations 0036, 0039, 0040–0045 (RLS, CRO, dose-response)
- `backend/app/schemas/workflow.py` (VALID_WORKFLOW_ACTIONS)
- Adversarial review notes embedded in `TODOS.md` (2026-04-03)

---

**Next step:** Review this checklist with stakeholders, mark items as "fix before", "during", or "accept and document", then start the rework with a clear plan.

If any of the above items are actually already resolved on a newer branch or local changes, update this document immediately.