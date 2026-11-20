# UAT: calculations S6, run and result-entry data model

**Scope:** CALC-REQ-49, 54, 55, 28, and 53, the schema a calculation reads and writes, plus the CALC-REQ-27 knock-in record. Migration `0123_result_entry_data_model`. No catalog function, no configuration, no binder, no attempt, and no screen. Nothing computes a value in S6. S7 is not in this pass.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** none new, because S6 adds no catalog function. The S4 `copy_raw` KATs run again and their outputs are stored on a result entry unchanged. See [manuals/calculation-data-model-s6.md](../manuals/calculation-data-model-s6.md).

**Limits:** not part of the calculations work. No limits table, migration, or LOQ / `<LOQ` reporting is built or tested here.

## Setup

1. Check out `calculations` at the S6 commit.
2. Install `backend/requirements.txt` into a Python 3.12 environment. These tests need Docker (testcontainers Postgres).

## Backend suite

3. `cd backend && python -m pytest -q tests/test_calculation_result_entry_s6.py tests/test_calculation_result_entry_s6_db.py` passes.
4. `cd backend && python -m pytest -q tests/test_result_promotion.py tests/test_results.py tests/test_dose_response.py tests/test_work_order_p2.py tests/test_elisa_224_followups.py tests/test_configuring_agent_catalog_seed.py tests/test_append_only_revokes.py tests/test_instant_timestamptz.py` still passes.
5. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py tests/test_calculation_kat_s2.py tests/test_calculation_release_s2.py tests/test_calculation_catalog_r_s3.py tests/test_calculation_catalog_decimal_s4.py tests/test_calculation_catalog_s5.py` still passes. `test_0122_sits_under_the_single_alembic_head` now finds head `0123_result_entry_data_model` directly on top of 0122.

## Schema (CALC-REQ-49, 55)

6. `test_0123_schema_shape`:
   - `tests.lims_run_id` exists and `results.lims_run_id` does not.
   - `results` has `display_order`, `raw_units`, `final_units_id`, `knocked_out` (not null), `knocked_out_by`, and `knocked_out_at`, and no `official_set_id` or `superseded_*` column.
   - `entries.experiment_id` is nullable and `entries.lims_run_id` exists.
   - `result_entries` has every dedicated column and no count column. `analysis_analytes` has `pairing_unit_id` and no `replicates` column.
   - RLS is on and forced for `result_entries`.
7. `test_entries_belong_to_exactly_one_parent`: an entry with both an experiment and a run, or with neither, is refused by `ck_entries_experiment_xor_lims_run`. A run id on an entry type other than `experiment_data` / `experiment_sample_data` is refused.
8. `test_result_guards_for_the_app_role`, as `lims_app`:
   - A result insert, or a value change, on a Test with no run is refused with `result_test_has_no_run`. Retiring a legacy run-less result (`active = false`, values unchanged) is allowed.
   - A calculated value on insert or update is `calculated_locked`. With `lims.calculation_write = 'on'`, the same update is allowed.
   - A second row for the same Test, analyte, and replicate fails on `uq_results_test_analyte_replicate`.
   - A write to `results.lims_run_id` fails.
   - Moving a Test that already has a run to another run, or back to null, is `test_run_immutable`. Giving a run-less Test a run is allowed.
9. `test_result_entry_guards_for_the_app_role`:
   - A row on an entry that is not the run's `experiment_sample_data` entry, or on a Test from another run, is `result_entry_scope`.
   - Calculated on insert, or reported before calculated, is refused.
   - The calculation path cannot change raw (`calculation_changes_raw`).

## Start creates the run's Test and rows (CALC-REQ-49, 54)

10. `test_start_puts_test_on_run_and_creates_one_row_per_analyte`:
    - Start gives the sample one Test on the run, and the run one `Results` entry (`experiment_sample_data`, no experiment).
    - One row per analyte has calculated, reported, raw, and origin null and is not knocked out.
    - The rows are in display order (arsenic 1 before lead 2). Lead's final units are its pairing unit.
11. `test_rows_are_created_once`: calling `ensure_rows` again creates nothing.
12. `test_replicate_count_comes_from_the_caller_not_a_column`:
    - The model has no `replicates` attribute.
    - A count of 3 for lead adds replicates 2 and 3 once.
    - Counts `0`, `-1`, `true`, and `"2"` are HTTP 400 `invalid_input`.
13. An accessioned Test with no run and no results is claimed by start (`test_unclaimed_test_without_results_is_claimed`). A run-less Test that already has results is left alone, and a new Test is minted (`test_unclaimed_test_with_results_is_left_and_a_new_test_is_minted`).
14. `test_rerun_gets_its_own_test`: the original run and its rerun each have their own Test for the sample.
15. `tests/test_work_order_p2.py::TestWorkOrderP2::test_wo7_first_start_freeze`: each of three runs on the same sample and analysis has its own Test. All three keep the first start's `asked_for_params` (`cell_line` `A549`), after the asked-for changes to `HeLa` and after it is cancelled.
16. `test_list_pages`: `GET /v1/lims-runs/{id}/result-entries?page=2&size=1` returns total 2, page 2, size 1, pages 2, and one row. An unknown run is 404.

## Editing a result entry (CALC-REQ-53)

17. `test_typed_raw_is_stored_with_origin_and_units`: a typed raw value with units is stored with origin `typed`. Clearing raw clears its units and origin. `test_blank_raw_units_is_stored_as_null`.
18. `test_refusals_are_400_with_a_code`. Each of these is HTTP 400 with `{code, message}`:
    - `calculated_result` in the body: `calculated_locked`.
    - An unknown field, an empty body, a non-string value, or an over-long value: `invalid_input`.
    - `raw_units` without raw: `invalid_input`.
    - A null or blank `reported_result`: `invalid_input`.
    - Reported before calculated: `reported_before_calculation`.
19. `test_uploaded_raw_cannot_be_edited`: raw written by an upload is `raw_uploaded` on PATCH.
20. `test_reported_override_after_calculation_keeps_calculated`: after the calculation path writes calculated and reported, a user overwrite of reported is stored, and calculated is unchanged.
21. `test_published_run_refuses_edits` (`run_published`), `test_row_on_another_run_is_404`, and `test_list_needs_result_read` (403 without `result:read`).
22. `test_copy_raw_kats_pass_and_its_outputs_store_exactly`: the S4 `copy_raw` KATs pass at tolerance 0. Their calculated and reported strings are stored on a row exactly. `test_copy_raw_missing_input_leaves_outputs_empty`: a missing raw is a `missing_input` stop with empty outputs.

## Classic results API

23. `POST /results/` on a Test with a run returns that run as `lims_run_id`. `POST` or `PATCH` with `calculated_result` is HTTP 400 `calculated_locked`. A Test with no run is HTTP 400 `result_test_has_no_run`. The Test response carries `lims_run_id`.
24. `test_publish_writes_results_on_the_run_test`: publish writes onto the run's own Test.
25. `tests/test_elisa_224_followups.py::test_accepting_a_failed_run_keeps_entered_by`: accepting the rejected run's value writes it onto that run's Test, and `entered_by` stays the person who entered it.

## Pairing unit (CALC-REQ-28, OQ-CALC-36)

26. `test_pairing_unit_defaults_from_the_analyte`: a link inserted in SQL with no pairing unit takes `analytes.units_default`.
27. `TestAnalyteRules`:
    - A rule created without a unit takes the analyte default, and its response has no `replicates` field.
    - An explicit unit is kept. A link through `POST /analyses/{id}/analytes` is defaulted.
    - `PATCH` sets a unit. An unknown unit is HTTP 400, and `null` clears it.

## Knock-in audit (CALC-REQ-27)

28. `tests/test_dose_response.py::test_unexclude_data_point_records_the_clear`:
    - `DELETE /v1/lims-runs/data/{data_id}/exclude` returns the exclusion with `cleared_by` and `cleared_at` set, and the original `excluded_by`, `excluded_at`, and `reason`.
    - The point can be excluded again.
    - `GET /v1/lims-runs/data/{data_id}/exclusions` lists both knockouts, oldest first.
    - All three routes still need `experiment:manage`.
29. `test_knockout_record_is_kept_for_the_app_role`:
    - `lims_app` has no DELETE on `lims_run_data_exclusions`. With DELETE granted, the trigger still refuses it with `exclusion_record_kept`.
    - Changing a cleared row, or any field other than the one clear, is refused.
    - A second active exclusion on a point is refused.

## Migration round trip

30. `test_0123_backfills_and_splits_tests_by_run_then_downgrades`:
    - A Test with results from one run takes that run.
    - A Test with results from two runs, or with run results beside run-less results, is split into one Test per run. Run-less results stay on the original. No row is deleted.
    - Downgrade restores `results.lims_run_id` from the Test.
31. `test_0123_downgrade_drops_cleared_knockouts_and_run_entries`: downgrade deletes cleared exclusions and run-scoped entries, keeps the active exclusion, and restores `uq_experiment_data_exclusions_data_id`. The test then upgrades back to head.
32. `tests/test_configuring_agent_catalog_seed.py` passes. The Schema catalog lists `tests.lims_run_id` and the new `results` columns, and not `results.lims_run_id`.

## Unchanged

33. The S1 pin, the S2 harness, the S3 R routes, and the S4 and S5 functions are unchanged. `bash services/r-calculator/scripts/ci-pin.sh` still ends with `ci-pin ok`.

## Not in this pass

- No calculation run, binder, configuration, or attempt (S7, S9). No recompute on a typed correction.
- No replicate count field. The count is a configuration value (#258).
- No knockout API on result entries (S12). No qualifier edit through the result-entry PATCH.
- No result-entry fill from file import, and no publish copy from result entries to `results`.
- No limits, LOQ, or `<LOQ` work.
- No screen.
- No merge to `main`.
