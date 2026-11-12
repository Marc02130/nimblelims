# NimbleLIMS calculations: implementation plan

A proposed PR sequence for the merged calculations Spec ([PR #253](https://github.com/Marc02130/nimblelims/pull/253)). Each slice is a proposed PR scope inside that Spec. No dates, no owners. Do not invent behavior, defaults, or scope the Spec left open.

**Status (2026-11-11, 7:16 PM ET):** Marc authorized a go to build on **S1 only** (pin the R service). Later slices stay closed until he says go. S1 uses the Spec's OQ-CALC-16 default timeouts (R 50 s, backend 60 s). Existing dose-response `POST /fit` calls are left unchanged in S1; whether CALC-REQ-4 / 4a refusal also applies to them is not stated in the Spec and is still with Marc.

Interactive copy: [NimbleLIMS calculations: implementation plan](https://cursor.com/canvas/store-66f86e31-b3c1-4f49-811e-d9b1eca5b78a/f3537fe2-0308-42da-addb-b8a509e16e59).

## Recommendation

The Spec fixes the first slice's order: (a) pin, (b) KATs, (c) generic catalog functions (CALC-REQ-1). Start with S1, pin the R service. S1 needs no answer to any no-default OQ.

After S1, S2 (KAT harness) can follow without new decisions, but its real cases need OQ-13 (who supplies independent expected values). S4's three ungated functions come next. Everything from S6 onward waits on Not-specified or Open questions listed per slice.

Status labels come from the Spec: of 58 CALC-REQ entries, 54 are Not built, 3 are Partly shipped (CALC-REQ-27, 31, 36, all only through dose-response or an existing reason), and CALC-REQ-41 is Removed and parked toward #258. None is tagged Shipped.

## Source of truth

| | |
|---|---|
| [PR #253](https://github.com/Marc02130/nimblelims/pull/253) | Merged 2026-11-11 7:00 PM ET |
| Merge commit on main | `8f65fdf1c8dc96c8e6ce9d99cc1bd0d5b1ece3b4` (parents `8e327c2`, `ced25c1`) |
| Spec on main | [`.docs/internal/specs/calculations/SPEC.md`](https://github.com/Marc02130/nimblelims/blob/main/.docs/internal/specs/calculations/SPEC.md), blob `7e01dcd70c7cb31f8c76f4086c63c13d55123ec2`, last changed in `ced25c1`, 706 lines |
| Spec base | Shipped reality surveyed at `8e327c2` |

## Slices at a glance

| # | Proposed PR scope | CALC-REQs | Must decide first | Depends on | Parked elsewhere | Gate |
|---|-------------------|-----------|-------------------|------------|------------------|------|
| S1 | Pin the R service: digest base image, renv.lock, /health lock hash, sandbox self-attestation | CALC-REQ-2, 3, 4, 4a (ordering: CALC-REQ-1) | None. OQ-16 has a Spec default (R 50 s, backend 60 s) to confirm. | None | #25, #258, #259 untouched | Confirm default |
| S2 | KAT harness on the pinned image, serialiser unit test, and the release check | CALC-REQ-5 (harness, log), 6 (citation per case), 7, 29, 33 | OQ-13 blocks the expected values of real KAT cases, not the harness. | S1 merged | #258 (KATs read no constant from a configuration) | Confirm / sources |
| S3 | R-side catalog functions: fit_4pl, inverse_4pl, fit_loglog_linear, inverse_loglog_linear | CALC-REQ-8, 9, 12, 17, 24, 37 (R/backend split, shortest round-trip, r_non_finite) | OQ-13 (KAT sources). | S1, S2 | None | Confirm / sources |
| S4 | Backend decimal functions with no open formula: apply_dilution, subtract, copy_raw, convert_units, plus the units seed | CALC-REQ-38, 51, 53, 39, 28 (seed `OD`, `s`, `1`), 37 | OQ-44 blocks convert_units only. | S2 | None | Confirm / sources |
| S5 | Backend decimal functions with open formula or treatment: replicate_mean_cv, spike_recovery, limit_compare | CALC-REQ-14, 18, 19, 37 (inclusive bounds), 22 (catalog lists exactly eleven) | OQ-5 (replicate_mean_cv), OQ-6 (spike_recovery), OQ-51 (limit_compare, part). | S2 | #258 (bounds are directly bound values), #259 (not acceptance ranges) | Gated on OQs |
| S6 | Run and result-entry data model: tests.lims_run_id, entry run id, dedicated result-entry columns, results.display_order and units | CALC-REQ-49, 54, 55, 28, 53 | OQ-34, OQ-45, OQ-36; Test-creation timing (#254). | None technically; recommended after phase A | #25, #254 | Gated on OQs |
| S7 | Calculation configuration on analysis_analytes and the no-code builder (direct binding, on-fail declarations, calculation order) | CALC-REQ-40, 23, 48, 22, 28, 50, 46 | OQ-48, OQ-35, OQ-46; analysis-version storage. | S3–S5, S6 | #258, #255 | Gated on OQs |
| S8 | Configuring-agent proposal and Admin activation (confirm token, review document, activation record) | CALC-REQ-47, 34, 35, 45, 46 | OQ-12; OQ-17 default to confirm. | S7 | Required validation gate, e-signatures, Part 11 (§5) | Gated on OQs |
| S9 | Stage runner, calculation attempt with provenance, first calculation write, and stop rules | CALC-REQ-25, 26, 30, 21, 48, 49, 53, 4a (timeout attempts), 37, 58 | OQ-46 (via S7); OQ-25 default; OQ-39 for one case. | S1, S4/S5, S6, S7, S8 | #25 | Gated on OQs |
| S10 | Same-run reference reads and server-derived run scope | CALC-REQ-50, 52 | OQ-40 (unnamed replicate vs average); OQ-41 not pre-decided. | S6, S9 | #256 | Gated on OQs |
| S11 | Configured threshold checks and qualified results (low and high cutoffs, directly bound bounds) | CALC-REQ-20, 57, 10, 11, 13, 15, 16 | OQ-51, OQ-49, OQ-4 (calibrator knockouts). | S5, S7, S9 | #258, #259 | Gated on OQs |
| S12 | Recompute, knockout, and reported override (two-transaction clear then set) | CALC-REQ-31, 27, 32, 54, 49 | #25 decision; qualifier-clear on re-calc; OQ-4. | S9, S10 | #25 | Gated on OQs |
| S13 | Publish copy, stopped-compute publish gate, unpublish with reason, replacement run | CALC-REQ-49, 55, 56, 36 | OQ-43, OQ-42, #254. | S6, S9, S12 | #254, #25 | Gated on OQs |
| S14 | End-to-end KATs on the ELISA and LAL reference fixtures (test fixtures only, never seeds) | CALC-REQ-42, 43, 44, 7, 1 | OQ-13; ELISA OQ-11; LAL OQ-3, 5, 7, 8, 9, 19, 49, 51; OQ-18 default. | S2–S5, S7, S9, S11 | #259 | Gated on OQs |

## Slice detail


### S1. Pin the R service: digest base image, renv.lock, /health lock hash, sandbox self-attestation

- **Phase:** A. Spec's first slice: (a) pin
- **Goal:** Make the R service reproducible and fail-closed before any catalog function or KAT exists (CALC-REQ-1: nothing from (b) merges before (a)).
- **CALC-REQs:** CALC-REQ-2, 3, 4, 4a (ordering: CALC-REQ-1)
- **Depends on:** None
- **Parked:** #25, #258, #259 untouched
- **Gate:** No no-default OQ blocks it. Confirm OQ-16 default.

**Builds on** (shipped at `8e327c2`, per Spec §1):

- Plumber service `lims-r-calculator`, internal network only, no host port; `docker-compose.yml` sets no environment on it (§1).
- `/health` reports only `status`, `drc_version`, `r_version` today.
- Backend fit client `FIT_TIMEOUT_SECONDS` = 60 s; shipped R bounds its profiled CI at 5 s.

**What lands:**

- `FROM <image>@sha256:<digest>`; packages only from a committed `renv.lock` via `renv::restore()`; no `install.packages(`.
- `/health` reports base, renv, tree, the §2 lock hash, `R_IMAGE_DIGEST`, and the `sandbox` object (uid, root_read_only, scratch_tmpfs, egress_blocked, cpu/memory/pids limited, forbidden_env_absent).
- Backend holds the expected lock hash recomputed from the commit and checks lock + sandbox at startup and on every calculation call; refuses and writes nothing on mismatch.
- Non-root, read-only root, tmpfs scratch, egress deny, CPU/memory/PID limits, per-request timeout in R and backend; `docker inspect` check in deploy and CI only; no Docker socket in backend.

**Acceptance that would prove it:**

- CALC-REQ-2 AC: no `FROM` without `@sha256:`; two builds of one commit report the same lock hash; recomputing §2 without a build gives that hash.
- CALC-REQ-3 AC: changing one package version in `renv.lock` changes the lock hash.
- CALC-REQ-4 AC: mismatched expected hash, or missing/ill-formed `R_IMAGE_DIGEST`, refuses the call, names the cause, writes nothing.
- CALC-REQ-4a AC: egress fails, write outside tmpfs fails, uid not 0, no forbidden env, `/health` sandbox all true; any false/missing field refuses the call.
- The 4a timeout ACs that say the attempt records `r_timeout` / `backend_timeout` can only be proven once the calculation attempt exists (S9).

**Must be decided before build:**

- OQ-CALC-16 (Open, Spec default applies until Marc confirms): R stops at 50 s, backend at 60 s. For the authorized S1 build, use this default.
- Not stated in the Spec (no default proposed): whether the CALC-REQ-4 / 4a refusal also applies to the shipped dose-response `POST /fit` calls, which CALC-REQ-24 keeps. S1 leaves those calls unchanged.

**Can stay open:** Every other OQ.

**Out of scope:** Catalog routes, KATs, attempts, any result write. Bringing `fit_compound` under catalog rules.

### S2. KAT harness on the pinned image, serialiser unit test, and the release check

- **Phase:** A. Spec's first slice: (b) KATs
- **Goal:** A KAT runner, run log, and release record so no catalog function version can be released without passing KATs on the release's lock hash.
- **CALC-REQs:** CALC-REQ-5 (harness, log), 6 (citation per case), 7, 29, 33
- **Depends on:** S1 merged
- **Parked:** #258 (KATs read no constant from a configuration)
- **Gate:** Harness has no gate. Real cases need OQ-13.

**Builds on:** `services/r-calculator/tests/test_fit.R`: host-run, not in `ci.yml`, 10% band on one synthetic set; the Spec says it does not meet CALC-REQ-5.

**What lands:**

- R-side KATs run against the built pinned image over HTTP; backend KATs run against backend decimal code with no R call.
- Run log: image digest, lock hash, function name and version, R or backend, observed / expected / tolerance per case, source citation per case.
- Serialiser unit test inside the pinned image (shortest round-trip string).
- Release record: calculation-scoped, additive, incremental (CALC-REQ-33); refused when a version has a failing or absent KAT run on that lock (CALC-REQ-7); released versions immutable (CALC-REQ-29).

**Acceptance:** CALC-REQ-7 AC: releasing a version with a failing or absent KAT run is refused. CALC-REQ-29 AC: editing a released version is refused; the same change as a new version succeeds. CALC-REQ-33 AC: a new version of one function leaves every other version unchanged. Serialiser test passes inside the image; a host-R run does not count.

**Must be decided:** OQ-CALC-13 (Open): who supplies independent expected values. Needed before any real function case lands (CALC-REQ-6).

**Can stay open:** OQ-11, OQ-3 and the other fixture OQs (fixtures are S14).

**Out of scope:** Reference fixtures (S14). Lab validation gate (§5).

### S3. R-side catalog functions: fit_4pl, inverse_4pl, fit_loglog_linear, inverse_loglog_linear

- **Phase:** A. Spec's first slice: (c) catalog
- **Goal:** The four R-side fits and inversions, one route each, with backend-side range checks and decimal handling.
- **CALC-REQs:** CALC-REQ-8, 9, 12, 17, 24, 37
- **Depends on:** S1, S2
- **Gate:** Needs OQ-13 for KAT sources.

**Builds on:** `fit_compound()` wraps `drc::drm` (`LL.4` etc.); an unknown model silently falls back to `LL.4`, a defect the new routes must not copy (CALC-REQ-24). `POST /fit` and `POST /svg/full` stay for dose-response.

**What lands:** One R route per function; no generic run-R route; unknown function or model refused with no fallback. Backend decides in-range vs out-of-range in decimal before any inversion call; out-of-range gives the qualified kind for that end (`<` or `>` with its limit), no R call. R outputs as shortest round-trip strings; NaN/Inf/NA stops with `r_non_finite`.

**Acceptance:** Each function's AC (e.g. three usable levels stop `curve_not_fitted`; non-positive log input stops `non_positive_log_input`) and its KATs pass on the lock (CALC-REQ-7). `/fit` and `/svg/full` still answer; unknown model name refused and does not run `LL.4`.

**Must be decided:** OQ-CALC-13 (KAT expected-value sources). If `fit_4pl` v1 needs a weighting choice, that is OQ-CALC-11 territory; CALC-REQ-8 names no weighting, so the slice must not pick one.

**Can stay open:** OQ-3 (LAL uses `fit_loglog_linear`): a fixture question, S14. OQ-18 (stage per dilution): fixture, S14.

**Out of scope:** Dose-response `fit_compound` into the catalog. Assay thresholds in any function.

### S4. Backend decimal functions with no open formula: apply_dilution, subtract, copy_raw, convert_units, plus the units seed

- **Phase:** A. Spec's first slice: (c) catalog
- **Goal:** Four backend-only functions in Python decimal (precision 50, ROUND_HALF_EVEN), no R call.
- **CALC-REQs:** CALC-REQ-38, 51, 53, 39, 28 (seed `OD`, `s`, `1`), 37
- **Depends on:** S2
- **Gate:** apply_dilution, subtract, copy_raw ready. convert_units waits on OQ-44.

**Builds on:** `units` table with `multiplier` `Numeric(20, 10)`; no RLS on `units`.

**What lands:** `apply_dilution`, `subtract`, `copy_raw` (output = input decimal string, no conversion). `convert_units` within one unit type from `units` multipliers; cross-type refused. Additive seed `OD` (absorbance), `s` (time), `1` (dimensionless), multiplier 1 each.

**Acceptance:** Each function's AC and KATs (tolerance 0 where exact in decimal); no backend KAT calls R. `copy_raw` AC: `0.026` writes `0.026` to both outputs.

**Must be decided:** OQ-CALC-44 (Open): whether the `units.multiplier` lookup must run under row-level security. Blocks `convert_units` only.

**Can stay open:** OQ-39 (`copy_raw` when file units differ from the pairing unit) is a run-time case, gated in S9, not the function.

**Out of scope:** Lab-added units such as `EU/kg` (labelled examples, not a seed).

### S5. Backend decimal functions with open formula or treatment: replicate_mean_cv, spike_recovery, limit_compare

- **Phase:** A. Spec's first slice: (c) catalog
- **Goal:** Finish the eleven-function catalog (CALC-REQ-22) once the formula questions are answered.
- **CALC-REQs:** CALC-REQ-14, 18, 19, 37 (inclusive bounds), 22
- **Depends on:** S2
- **Parked:** #258 (bounds are directly bound values), #259 (not acceptance ranges)
- **Gate:** Each function waits on its OQ.

**Builds on:** Nothing shipped computes these.

**What lands:** `replicate_mean_cv`: mean and %CV in decimal; fewer than two numeric replicates gives no %CV and a replicate-missing flag (CALC-REQ-14). `spike_recovery`: (spiked − unspiked) × 100 ÷ nominal spike, products first, one division last. `limit_compare`: at most / at least / within, all inclusive, optional absolute value; the at-most rules for qualified `<` L and range-end `>` U, with `limit_above_el` / `limit_below_el` as written in CALC-REQ-19.

**Acceptance:** CALC-REQ-37 AC: a value equal to a bound passes; rounding before a compare fails; recovery from decimal strings is exact. CALC-REQ-22 AC: the catalog lists exactly eleven entries after S3–S5; no `elisa_*` or `lal_*`; adding an entry through API/UI/DB/agent is refused.

**Must be decided:** OQ-CALC-5 (SD with n−1 or n) blocks `replicate_mean_cv`. OQ-CALC-6 (confirm the `spike_recovery` formula) blocks `spike_recovery`. OQ-CALC-51 (what a high-cutoff `>` is stored as and how `limit_compare` treats it) blocks those cases; the at-most cases CALC-REQ-19 already states can be built.

**Can stay open:** OQ-8 (missing single tube, split duplicate): the function emits the Spec's flag; lab handling stays open. OQ-7 (not-detected unspiked value): set by the configuration, S14.

**Out of scope:** Any assay number as a bound. Acceptance limits (#259, OQ-47).

### S6. Run and result-entry data model: tests.lims_run_id, entry run id, dedicated result-entry columns, results.display_order and units

- **Phase:** B. Data model and configuration
- **Goal:** The schema the calculation reads and writes, with calculated locked and raw rules enforced.
- **CALC-REQs:** CALC-REQ-49, 54, 55, 28, 53
- **Depends on:** None technically; recommended after phase A
- **Parked:** #25 (no value-history table here), #254 (statuses, Test creation)
- **Gate:** Not specified items block the schema.

**Builds on:** `results.raw_result` / `reported_result` / `calculated_result` String(255); `qualifiers` is a `list_entries` id; `uq_results_test_analyte_replicate`. `entries.experiment_id` NOT NULL, no `lims_run_id`; values in `entry_field_values`. `analysis_analytes` already has `display_order`, `high_value`, `low_value`, `significant_figures`. `results.modified_by` / `modified_at` only (`0002_audit_triggers.py`): not an audit trail.

**What lands:** `tests.lims_run_id` required; `results.lims_run_id` removed; run-less result writes removed; no `results.sample_id`. Entries gain a LIMS run id; experiment id XOR LIMS run id. Dedicated result-entry columns: raw, optional `raw_units`, final units, calculated, reported, qualifiers, knockout flag, `display_order`, plus `raw_origin`; `results` gains `display_order`. API and DB refuse a user write to calculated; uploaded raw refused; reported write before a calculation refused. Pairing-unit field on `analysis_analytes`, defaulting from `analytes.units_default`. One row per sample × analyte × replicate, including the average analyte; no count column.

**Acceptance:** CALC-REQ-49 AC rows that do not need a calculation: rows exist with calculated and reported null; XOR holds; user POST of calculated refused; upload-raw edit refused; typed-raw edit succeeds; result insert with no `tests.lims_run_id` refused; write to `results.lims_run_id` fails. CALC-REQ-55 AC: second official row for the same key on a Test fails; no `official_set_id` / `superseded_*` columns.

**Must be decided:** OQ-CALC-34 (how the dedicated columns land on the shipped Entry / `entry_field_values` shape, and the XOR constraint). OQ-CALC-45 (type, default, and source of `display_order` on the entry and on `results`). OQ-CALC-36 (who may write the pairing unit, and whether a configuring-agent run may). Not designed in the Spec: when the first run's Tests are created (create-equals-start vs shipped draft-then-start, #254). Also not stated: what happens to existing rows when `results.lims_run_id` is removed.

**Can stay open:** OQ-50: `tests.test_date`, `tests.review_date`, `results.entry_date` stay as they are; the Spec does not remove them. OQ-29 (parser mapping).

**Out of scope:** Audit tables or value history (#25). Status lifecycle (#254). Import on init (#256).

### S7. Calculation configuration on analysis_analytes and the no-code builder (direct binding, on-fail declarations, calculation order)

- **Phase:** B. Data model and configuration
- **Goal:** A named, versioned configuration per analysis-analyte pair, built only from catalog functions, with each stage's four on-fail declarations.
- **CALC-REQs:** CALC-REQ-40, 23, 48, 22 (builder offers only catalog), 28, 50, 46
- **Depends on:** S3–S5 (catalog), S6
- **Parked:** #258 (no constants picker; the 11 identifiers are not a menu), #255 (copy-and-edit UI)
- **Gate:** Storage and versioning questions block it.

**Builds on:** Free-text `analysis_analytes.calculation` column exists; the Spec says it is not a formula and not this configuration.

**What lands:** Pick catalog functions; bind each input to a same-run entry field, an upstream stage output, or a reference input; or bind a value directly (temporary until #258). Each stage declares on-fail outcome (`run_failed`, `dilution_invalid`, sample verdict, `flag`, or a stage-stop code), flag, gated stages, precedence place; undeclared stops `on_fail_undeclared`; `pass` refused at save. Calculation order on `analysis_analytes`, separate from `display_order`. No formula text field; no ELISA/LAL templates; a binding naming a unit of another type than the function's declared unit is refused.

**Acceptance:** CALC-REQ-23 AC: direct binding saves; a builder that refuses it fails; a hardcoded threshold in code fails; no constants picker. CALC-REQ-48 AC: missing declaration refused and named; two stages claiming place 1 refused; `fit_4pl` declaring `run_failed` for `curve_not_fitted` fails. CALC-REQ-40: an active version is immutable; changing it needs a new analysis version.

**Must be decided:** OQ-CALC-48 (how the configuration is held on the `analysis_analytes` row). OQ-CALC-35 (calculation-order column name, type, default, and what missing or cyclic order does). OQ-CALC-46 (how a direct binding is recorded on the attempt, versioned, and replaced when constants ship). Not stated in CALC-REQ-40: how the analysis version is stored (`analyses` has no version column) and whether it is the same integer as the configuration version.

**Can stay open:** OQ-33 (constants; the Spec labels it Not in this Spec). OQ-31 (versioning UI, #255).

**Out of scope:** Constants table (#258). Acceptance ranges (#259). Copy-and-edit UI (#255).

### S8. Configuring-agent proposal and Admin activation (confirm token, review document, activation record)

- **Phase:** B. Data model and configuration
- **Goal:** The agent writes inactive proposals; only an Admin activates, through the interactive confirm path.
- **CALC-REQs:** CALC-REQ-47, 34, 35, 45, 46
- **Depends on:** S7
- **Parked:** Required validation gate, e-signatures, Part 11 (§5)
- **Gate:** OQ-12 blocks the activation row.

**Builds on:** Configuring-agent allow-list refuses `/v1/lims-runs`; `create_access_token` sets `jti`. `POST /v1/sop-parse` drafts an experiment template only.

**What lands:** Agent creates inactive proposals through the builder contracts; cannot add or enable a function or activate. Single-use confirm token bound to the configuration version, the review-document SHA-256 (RFC 8785 JCS), and the login `jti`; valid for 300 s on the DB clock; consumed in the activation transaction. Activation record: Admin, time, configuration and function versions, lock hash, validation state, review document and hash; append-only; self-activation allowed. Review dialog shows test cases, system-output flags, dry run, diff, plain-language description, every stage's four declarations.

**Acceptance:** CALC-REQ-34 AC (300 s accepted, 301 s refused; agent replay refused; token for A refused for B). CALC-REQ-35 AC (Lab Manager refused; UPDATE/DELETE of activation row fail). CALC-REQ-46: nothing labelled validated except catalog functions.

**Must be decided:** OQ-CALC-12 (the closed list of validation-state values recorded at activation). OQ-CALC-17 (Open, Spec default no): password re-entry on top of the confirm token. Confirm or change.

**Can stay open:** The agent's SOP and instrument-data history store is a dependency on the configuring-agent Spec; this plan does not design it.

**Out of scope:** Parsers (OQ-20). A required validation gate (§5).

### S9. Stage runner, calculation attempt with provenance, first calculation write, and stop rules

- **Phase:** C. Runtime
- **Goal:** Run an active configuration on a result-entry row, record the attempt, and write calculated and reported, or clear them on a stop.
- **CALC-REQs:** CALC-REQ-25, 26, 30, 21, 48 (runtime), 49 (calculation write), 53, 4a (timeout attempts), 37, 58
- **Depends on:** S1, S4/S5 (functions used), S6, S7, S8
- **Parked:** #25 (attempt is provenance, not the audit trail)
- **Gate:** Inherits OQ-46; OQ-25 default to confirm.

**Builds on:** Dose-response refit rows with `fit_version` and `superseded_by` (curve store, not this attempt).

**What lands:** Attempt always exists once a call is accepted: status, stop codes, lock hash, built digest, configuration and function versions, reference rows and values, values used, knocked-out points, time. Stops clear calculated and reported on the row; dependent stages do not run; refusals before acceptance write no attempt. Calculation writes calculated and reported; `copy_raw` writes both; no configuration leaves both empty. Run summary pass / fail / stopped naming the check (CALC-REQ-21).

**Acceptance:** CALC-REQ-25 AC: each function's stop case shows dependents not run and both values cleared. CALC-REQ-30 AC: the attempt shows versions, lock hash, digest, values, knockouts; lock hash matches `/health`. CALC-REQ-49 AC: `copy_raw` writes `0.026` to both; first calculation stopping with `r_timeout` clears both.

**Must be decided:** OQ-CALC-25 (Open, Spec default): provenance on the attempt row, linked, not copied onto `results`. Confirm or change. OQ-CALC-46: recording a directly bound value on the attempt. OQ-CALC-39: copy_raw when file units differ from the pairing unit. Blocks that case only.

**Can stay open:** OQ-33: the attempt neither requires nor forbids storing an MVD or `dose_unknown` marker. OQ-50: non-numeric metadata typing; numeric metadata analytes can be read.

**Out of scope:** Recompute and knockout (S12). Publish (S13). Audit trail (#25).

### S10. Same-run reference reads and server-derived run scope

- **Phase:** C. Runtime
- **Goal:** A calculation reads only values already in the same LIMS run, from a run id the server derives from the Test.
- **CALC-REQs:** CALC-REQ-50, 52
- **Depends on:** S6, S9
- **Parked:** #256 (import on init)
- **Gate:** OQ-40 blocks one case; OQ-41 must not be pre-decided.

**Builds on:** RLS: `results_access`, `lims_run_data_access`, `entries_access`, `entry_field_values_access`; none checks a LIMS run id.

**What lands:** Derive the run from `tests.lims_run_id`; any other supplied id is `reference_missing`. Read by named entry and field; `reference_missing`, `reference_ambiguous`, `reference_stopped` each clear the row being calculated and are not `run_failed`. `lims_run_data.row_data`: one top-level key, decimal string, JSON number as exact text; N/A, empty, null, bool, object, array are `reference_missing`. Later analyte in calculation order reads an earlier analyte's calculated or reported value in the same run, including unpublished result entries.

**Acceptance:** CALC-REQ-50 AC (second match ambiguous; other run missing; `0.050` stays `0.050`; nested key not read). CALC-REQ-52 AC (different run id or header-only id stops `reference_missing`).

**Must be decided:** OQ-CALC-40 (which record is read when the binding does not name the replicate or the average row). OQ-CALC-41 (whether same-run scope is also a row-level policy). The slice must neither add nor rule out a policy until answered. Not stated: what a dependent read gets from a row left cleared by a failed re-calc set (Rolf nit 3). No row lock, computing status, or read-block is to be invented.

**Can stay open:** OQ-35 ordering details (gated in S7).

**Out of scope:** Experiment calculation and `experiment_details.content` (OQ-37). Live process-step reads.

### S11. Configured threshold checks and qualified results (low and high cutoffs, directly bound bounds)

- **Phase:** C. Runtime
- **Goal:** Configurations compare against directly bound values and store qualified results as results, not missing data.
- **CALC-REQs:** CALC-REQ-20, 57, 10, 11, 13, 15, 16
- **Depends on:** S5, S7, S9
- **Parked:** #258 (bounds bound directly), #259 (not acceptance ranges)
- **Gate:** High-cutoff and no-value cases wait on OQ-51 and OQ-49.

**Builds on:** Seed `analysis-endotoxin-001` exists; no endotoxin calculation.

**What lands:** Configuration declares each cutoff's type, high or low. Low cutoff stores `<` with its limit and is the only cutoff that determines a non-detect; high cutoff stores `>` with its limit. Kind names and labels come from the lab SOP; two kinds both shown `<` stay distinct. Result limit, maximum dilution (including when dose is unknown, from configuration), correlation and point count, paired input, %CV threshold: all directly bound, none hardcoded.

**Acceptance:** CALC-REQ-25/26/49 AC: a `<` result keeps calculated and reported and is not a stop or `reference_stopped`. A hardcoded threshold in code fails each of CALC-REQ-10, 11, 13, 16.

**Must be decided:** OQ-CALC-51 (what a high-cutoff `>` is stored as and how it compares). OQ-CALC-49 (what a no-value input produces). CALC-REQ-57's AC cannot be written until answered. OQ-CALC-4 (calibrator knockout against the minimum point count, CALC-REQ-13). The configuration field holding a dose-unknown bound (MVD) is not specified (OQ-33 area); it must come from configuration, not code.

**Can stay open:** OQ-33 recording of the MVD on the attempt. OQ-10 (onset cutoff: Not in this Spec; directly bound).

**Out of scope:** Acceptance limits (#259, OQ-1, OQ-2, OQ-47).

### S12. Recompute, knockout, and reported override (two-transaction clear then set)

- **Phase:** C. Runtime
- **Goal:** Explicit before-publish recompute that clears, then sets calculated and reported together, with knockout as its own per-value flag.
- **CALC-REQs:** CALC-REQ-31, 27, 32, 54, 49
- **Depends on:** S9, S10
- **Parked:** #25 (clear and write are audited; details there)
- **Gate:** Audit dependency and qualifier-clear are unanswered.

**Builds on:** CALC-REQ-31 and 27 are Partly shipped only for dose-response: refit writes `fit_version + 1` with `superseded_by`; `lims_run_data_exclusions` records `excluded_by` / `excluded_at` and stays the dose-response store, not reused.

**What lands:** Recompute writes a new attempt linked to the replaced one, with who, when, why; earlier attempt kept. Transaction 1 clears calculated and reported. Transaction 2 sets the new calculated and reported together; on success reported equals the new calculated, even over a tech override. If transaction 2 fails, the row stays cleared. A cleared row is unpublished and is not read as an official result; same-run reads under CALC-REQ-50 still stand. Knockout: per-value flag beside qualifiers, who, when, clearable; setting or clearing triggers a recompute; knocked-out row keeps raw and still publishes. Average row: mean of what remains; one shared fail for a missed agreement-window or remaining-count check (directly bound values); nothing remaining gives `missing_input` and no mean. Refused while the run is published.

**Acceptance:** CALC-REQ-31 AC: recompute from `0.040` after override `0.030` leaves both `0.040`; published run refuses it. CALC-REQ-27 AC and CALC-REQ-54 AC as written. Spec cleanup Marc can ask for (Rolf): a set-transaction failure leaves calculated and reported both null; no state has one set and the other null.

**Must be decided:** #25 is deferred. The requirement says the clear and the write are audited. Marc decides whether this slice waits for #25 or merges with that audit criterion explicitly not yet met. This plan designs no audit record. Whether a re-calc clear also clears `<` / `>` qualifiers is unanswered (CALC-REQ-31 and OQ-28 say only the shared-fail rule does not clear them). The clear transaction cannot be finished until Marc answers. OQ-CALC-4: who may knock out a calibrator, and on what basis.

**Can stay open:** The knockout storage table is unnamed in the Spec (not `result_knockouts`); choosing a name is an implementation detail inside the Spec.

**Out of scope:** Audit table design (#25). Post-publish recompute (refused by the Spec).

### S13. Publish copy, stopped-compute publish gate, unpublish with reason, replacement run

- **Phase:** D. Publish
- **Goal:** Official results only come from publish, which copies the result entry and runs no calculation.
- **CALC-REQs:** CALC-REQ-49 (publish), 55, 56, 36
- **Depends on:** S6, S9, S12
- **Parked:** #254 (statuses), #25 (publish-copy audit, OQ-42)
- **Gate:** OQ-43, OQ-42, and #254 block it.

**Builds on:** `PATCH /v1/lims-runs/{id}/complete` writes `raw_result` only (`apply_plan`); `created_by` / `entered_by` = publisher. No unpublish route. `lims_runs.replaces_run_id` exists but is not this design. CALC-REQ-36 Partly shipped (existing dose-response reason).

**What lands:** Publish copies raw, raw units, final units, calculated, reported, qualifiers, knockout, `display_order`; all or nothing; non-knockout raw-only rows refused, including for a manager. Unpublish requires a reason; sets status unpublished; keeps `published_at`; no `unpublished_at`; published run locked otherwise. Replacement run: create equals start, new Tests, nothing copied, owner is the person who unpublished; delete refused; cancel distinct from failed.

**Acceptance:** CALC-REQ-49 publish AC rows. CALC-REQ-55 AC (two generations are two Tests). CALC-REQ-56 AC (no reason refused; lab tech publish refused).

**Must be decided:** OQ-CALC-43 (allowed values and format of the unpublish reason). OQ-CALC-42 (whether new publish/unpublish routes refuse a configuring-agent context, and whether the publish copy is audited). #254: the valid final Test status is unnamed, and create-equals-start collides with shipped draft-then-start.

**Can stay open:** OQ-30 (statuses, Not in this Spec).

**Out of scope:** Status lifecycle design (#254). Experiment publish of official results.

### S14. End-to-end KATs on the ELISA and LAL reference fixtures (test fixtures only, never seeds)

- **Phase:** E. Reference fixtures
- **Goal:** Exercise the framework end to end on two labelled example configurations bound in fixture configuration, not in code.
- **CALC-REQs:** CALC-REQ-42, 43, 44, 7 (re-run on new lock), 1 (no seed path)
- **Depends on:** S2–S5, S7, S9, S11
- **Parked:** #259 (kit QC ranges are acceptance ranges)
- **Gate:** Each fixture case waits on its OQ.

**Builds on:** IL-6 Gen5 fixture (synthetic, no unit on `Conc/Dil`); no ELISA plate math; no endotoxin calculation.

**What lands:** Fixture configurations pinning only function versions with passing KATs; every number in them is a labelled example value bound in the fixture. Run log names fixture name and version, pinned versions, lock hash, digest.

**Acceptance:** CALC-REQ-44 AC; CALC-REQ-1 AC (no migration, seed, startup path, or proposal inserts either configuration).

**Must be decided:** OQ-CALC-13: independent expected values. ELISA: OQ-CALC-11 (blank handling, weighting, repeat policy, number after `<` / `>`). LAL: OQ-CALC-3, 5, 7, 8, 9, 19, 49 (no onset: `>` with the limit vs no value), 51. OQ-18 has a Spec default (one stage per dilution) to confirm.

**Can stay open:** OQ-33: the fixture neither requires nor forbids storing an MVD.

**Out of scope:** Shipping either configuration as a built-in, template, seed, or proposal (OQ-24, Decided).

## OQ gates

Spec status as written in §4 at blob `7e01dcd`. No OQ is given a default here beyond what the Spec itself already states.

| OQ-CALC | Spec status | Plan effect | Bucket |
|---------|-------------|-------------|--------|
| OQ-1, OQ-2 | Not in this Spec | Acceptance limits; parked toward #259. | Decided or not in Spec |
| OQ-3 | Open | S14 LAL fit choice. | Blocks a slice |
| OQ-4 | Open | S11 and S12 calibrator knockout cases. | Blocks a slice |
| OQ-5 | Open | S5 replicate_mean_cv; S14 LAL. | Blocks a slice |
| OQ-6 | Open | S5 spike_recovery. | Blocks a slice |
| OQ-7 | Open, narrowed | S14 LAL not-detected unspiked case. | Blocks a slice |
| OQ-8 | Open | S14 LAL split-duplicate case; S5 emits the Spec's flag only. | Blocks a slice |
| OQ-9 | Open | S14 LAL reported dilution. | Blocks a slice |
| OQ-10 | Not in this Spec | Onset cutoff is a directly bound value. | Decided or not in Spec |
| OQ-11 | Open, narrowed | S14 ELISA; S3 only if fit_4pl needs weighting. | Blocks a slice |
| OQ-12 | Open | S8 activation record. | Blocks a slice |
| OQ-13 | Open | Real KAT cases in S2–S5, S14. | Blocks a slice |
| OQ-14, 15 | Decided | Admin-only activation; self-activation allowed. | Decided or not in Spec |
| OQ-16 | Open, Spec default | S1 timeouts 50 s / 60 s. | Spec default to confirm |
| OQ-17 | Open, Spec default | S8 no password re-entry. | Spec default to confirm |
| OQ-18 | Open, Spec default | S14 one LAL inversion stage per dilution. | Spec default to confirm |
| OQ-19 | Open | S14 LAL repeat policy after non_positive_log_input. | Blocks a slice |
| OQ-20 to 24 | Decided | Configuring agent proposes; fixtures are not shipped. | Decided or not in Spec |
| OQ-25 | Open, Spec default | S9 provenance on the attempt row. | Spec default to confirm |
| OQ-26, 27, 28 | Decided | Write, publish copy, stop clears both. | Decided or not in Spec |
| OQ-29 | Open | Parser-mapping fix; outside every slice. | Stays open |
| OQ-30, 31, 32 | Not in this Spec | #254, #255, #256. | Decided or not in Spec |
| OQ-33 | Not in this Spec | Constants (#258); MVD store on attempt neither required nor forbidden. | Stays open |
| OQ-34 | Not specified | S6 entry columns and XOR. | Blocks a slice |
| OQ-35 | Open | S7 calculation-order column. | Blocks a slice |
| OQ-36 | Not specified | S6 pairing-unit writer. | Blocks a slice |
| OQ-37 | Out of this Spec | Experiment calculation. | Decided or not in Spec |
| OQ-38 | Decided | Result and run model locks. | Decided or not in Spec |
| OQ-39 | Open | S9 copy_raw with differing file units. | Blocks a slice |
| OQ-40 | Open | S10 unnamed replicate vs average read. | Blocks a slice |
| OQ-41 | Open | S10 must not add or rule out an RLS policy. | Stays open |
| OQ-42 | Open | S13 agent refusal and publish-copy audit. | Blocks a slice |
| OQ-43 | Open | S13 unpublish reason. | Blocks a slice |
| OQ-44 | Open | S4 convert_units. | Blocks a slice |
| OQ-45 | Not specified | S6 display_order. | Blocks a slice |
| OQ-46 | Open | S7 and S9 direct-binding record. | Blocks a slice |
| OQ-47 | Open | Acceptance limits, #259; outside every slice. | Stays open |
| OQ-48 | Open | S7 configuration storage. | Blocks a slice |
| OQ-49 | Open | S11 no-value input; S14 LAL no onset. | Blocks a slice |
| OQ-50 | Open | Non-numeric metadata typing; existing date columns stay. | Stays open |
| OQ-51 | Open | S5 limit_compare part; S11; S14. | Blocks a slice |

## Spec nits (not work items)

- L465, L619, L621: the older "clears calculated and reported, then writes the new values" sentence repeats the two-transaction sentence. Cosmetic.
- CALC-REQ-31 AC (L470) does not test a failed set. Rolf's suggested AC, a cleanup Marc can ask for before S12: "a set-transaction failure leaves calculated and reported both null; no state has one set and the other null."
- "A value past a high cutoff is stored `>` with its limit" is repeated as boilerplate in 12 places, including the end of L465. Cosmetic.
- L329 (LAL example) says no onset stores `>` with the limit while OQ-49 is open; CALC-REQ-57's AC is not testable until OQ-49 is answered. This one does gate S11 and S14.
- Header L3/L5 still reads Working draft, no Confirm; §6 shows Rolf's Confirm and Marc's Approve as pending, and row 1 is dated 2026-11-10.
- `limit_above_el` / `limit_below_el` keep their v1 spelling; OQ-33 is labelled Not in this Spec while reviews treat it as open; OQ-36 is Not specified; the recovery range has no OQ number; "#257 closed, absorbed into #258" repeats many times.

## Not in this plan / parked

- [#25](https://github.com/Marc02130/nimblelims/issues/25) audit trail (open, deferred until Marc opens the system-wide auditing branch). Slices only point to it: the clear and the write are audited, details are #25. Marc's six-field minimum (table, field modified, old value, new value, modified by, timestamp) stays pending with Marc; #25 has old/new/who/when (and why) but not table or field modified. #25 is not edited.
- [#258](https://github.com/Marc02130/nimblelims/issues/258) constants table. Direct binding stays allowed until it exists. The eleven identifiers are an example of that future table, not a builder menu.
- [#259](https://github.com/Marc02130/nimblelims/issues/259) acceptance ranges by QC type and analysis-analyte (OQ-1, OQ-2, OQ-47).
- #254 statuses, #255 analysis/analyte versioning UI, #256 select and import on init.
- Reviewed-by: wanted, no GitHub issue yet, form not submitted. No slice designs it.
- Review and test dates as audit fields, not analytes: pending with Marc. The Spec keeps `tests.test_date`, `tests.review_date`, `results.entry_date` and leaves their future to OQ-50; `technician_id` does not appear in the Spec.
- CALC-REQ-58 as its own cross-Spec issue: Marc's call; no issue opened.
- Whether a re-calc clears `<` / `>` qualifiers: unanswered; gates S12.
- Experiments writing official results, experiment calculation, single-test reset; parsers; qPCR; a validation gate, e-signatures, Part 11 (§5).

## Where the Spec differs from the brief used to write this plan

- OQ-CALC-33 is labelled Not in this Spec (L590, L626), not Open with no default. The MVD configuration field is still unspecified, so S11 treats it as open.
- No requirement is tagged Shipped; only CALC-REQ-27, 31, 36 are Partly shipped.
- The merged Spec does not record Rolf's Confirm at `ced25c1`: §6 still shows Confirm and Approve pending.
- The Spec's scope lists the ELISA and LAL fixtures with the first slice, but their end-to-end KATs need the stage runner, so this plan places them at S14.
- CALC-REQ-31 requires the clear and the write to be audited while #25 is deferred; the plan surfaces that as a decision for Marc rather than designing an audit record.
- #25's MVP also lists why (reason) beside old/new/who/when.
