# TODOS

## Client-scoped RLS for experiment_templates and pre-0039 tables

**Priority:** P2

**What:** Extend client-scoped RLS (pattern from migration 0041) to `experiment_templates` and any other tables added before migration 0039 that still use role-only `has_experiment_access()` policies.

**Why:** Migration 0041 closes the isolation gap for the 5 tables from migration 0039 (`experiment_runs`, `experiment_data`, `instrument_parsers`, `robot_worklist_configs`, `sop_parse_jobs`). But `experiment_templates` (migration 0036) is still globally readable by any Lab Tech at any client org. A complete demo of data isolation requires `experiment_templates` to also be client-scoped.

**Pros:** Full data isolation for the experiment engine. Closes the partial-fix gap. Required for a credible "no, Client B cannot see Client A's data" demo claim.

**Cons:** Templates may be intentionally shared across orgs as "global templates" in a future product direction. Adding `created_by`-based scoping now would prevent that without a schema change. Decide the sharing model before implementing.

**Context:** Noted during adversarial review of migration 0041 (multi-tenancy branch). The design doc for 0041 explicitly deferred this. The pattern is identical to 0041 — add an Alembic migration that drops the role-only policy and creates `is_admin() OR (has_experiment_access() AND created_by IN (...))` with `FORCE ROW LEVEL SECURITY`.

**Depends on / blocked by:** Decision on whether `experiment_templates` will ever support cross-org sharing.

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
