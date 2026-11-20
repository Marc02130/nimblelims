# Calculations S6: run and result-entry data model

Calculations slice S6 lands the schema that a calculation reads and writes. It covers CALC-REQ-49, 54, 55, 28, and 53, and the CALC-REQ-27 knock-in record. It adds no catalog function, no configuration, no binder, and no screen. Nothing in S6 computes a value. A calculation first writes in S7 and S9.

Migration: `backend/db/migrations/versions/0123_result_entry_data_model.py` (revises `0122_calculation_units_seed`). Service: `backend/app/services/result_entry_service.py`. Routes: `backend/app/routers/result_entries.py`. UAT: [UAT_Scripts/uat-calculations-s6.md](../UAT_Scripts/uat-calculations-s6.md).

Limits are not part of the calculations work. S6 adds no limits table, no limits migration, and no LOQ or `<LOQ` reporting.

## A Test belongs to one LIMS run

- `tests.lims_run_id` is the run a Test belongs to (FK to `lims_runs`, `ON DELETE RESTRICT`). Once set, it does not change (trigger `tests_guard_run_change`, error `test_run_immutable`). A new generation, such as a rerun, is a new Test.
- The column is nullable. Accessioning still creates Tests before any run exists, and the Spec does not design when Tests are created (#254). A result on a Test with no run is refused (trigger `results_guard_write`, error `result_test_has_no_run`). The one exception is retiring a legacy run-less result: setting `active` to false with its values unchanged.
- `results.lims_run_id` is removed. The run a result came from is `tests.lims_run_id`. `ResultResponse.lims_run_id` and `TestResponse.lims_run_id` still return it, read through the Test. A write that names `results.lims_run_id` fails, because the column is gone.
- Run start (`PATCH /v1/lims-runs/{id}/start`) gives each started sample a Test on the run, in this order:
  1. the Test already on this run,
  2. an accessioned Test with no run and no active results, which is claimed for this run,
  3. a new Test.
- A minted Test copies `asked_for_params` from the latest earlier Test for that sample and analysis, so the WO-7 first-start freeze holds across runs. With no earlier Test, it snapshots the asked-for params as before.
- Publish writes only onto the run's own Test. Accepting another run's value (`POST /v1/lims-runs/{id}/value-choices`) writes onto the picked run's Test and retires the value shown from the other run. `entered_by` stays the person who entered the value.

### Existing rows (upgrade)

- A Test whose results all came from one run takes that run.
- A Test with results from more than one run, or with run results beside run-less results, is split. Each run gets its own copy of the Test, and that run's results move onto it. Run-less results stay on the original Test. Nothing is deleted.
- Downgrade restores `results.lims_run_id` from `tests.lims_run_id`. Split Tests stay split.

## Run entries and result entries

- `entries.experiment_id` is nullable and `entries.lims_run_id` is new. `ck_entries_experiment_xor_lims_run` requires exactly one of the two, and allows a run id only on `experiment_data` and `experiment_sample_data` entries.
- At start, the run gets one `experiment_sample_data` entry named `Results` (`predefined_entry_key = lims_run_results`). Its records are `result_entries` rows.
- `result_entries` has one row per Test × analyte on the run's analysis × replicate (`uq_result_entries_test_analyte_replicate`). The average analyte is another analyte on the same analysis, so it is another row on the same Test (CALC-REQ-54).
- There is no replicate count column. Start creates replicate 1 for each active analyte. `ResultEntryService.ensure_rows(run, replicate_counts)` adds replicates 2 to N for the analytes the caller names. The count is a configuration value (CALC-REQ-15, parked toward #258), so the caller is the bound configuration once S7 lands.
- Columns:

| Column | Meaning |
|--------|---------|
| `raw_result`, `raw_units` | The raw value and its optional free-text units. `raw_units` needs a raw value. |
| `raw_origin` | `upload` or `typed`. Null exactly when raw is null. |
| `final_units_id` | Units of calculated and reported. Starts as the analysis analyte's pairing unit. |
| `calculated_result` | Written only by a calculation. |
| `reported_result` | Written by the calculation. A user may overwrite it once calculated has a value. |
| `qualifiers` | A `list_entries` id, as on `results`. |
| `knocked_out`, `knocked_out_by`, `knocked_out_at` | The knockout flag. Who and when are set only together with the flag. |
| `display_order` | Copied from `analysis_analytes.display_order` when the row is created. |

- `results` also gains `display_order`, `raw_units`, `final_units_id`, and the knockout flag, so publish (a later slice) can copy a row across unchanged.
- RLS on `result_entries` follows the parent entry, as `entry_field_values` does. `result_entries` is not a Configuring-agent catalog table.
- Every new FK to `users` is `ON DELETE RESTRICT`.

## Calculated is locked, raw follows its origin

The API refuses each of these with HTTP 400 and `{code, message}`. The database refuses the same write from the application role, so a code path that skips the API is still held.

| Write | Code |
|-------|------|
| Any user write of `calculated_result` (result entry PATCH, `POST /results/`, `PATCH /results/{id}`). Batch entry has no calculated field. | `calculated_locked` |
| An edit of raw that came from a file upload | `raw_uploaded` |
| A reported write while calculated is null | `reported_before_calculation` |
| A null or blank reported value | `invalid_input` |
| An unknown field, an empty body, a non-string value, or a value that is too long | `invalid_input` |
| `raw_units` without a raw value | `invalid_input` |
| Any edit on a published run | `run_published` |
| A classic result write on a Test with no run | `result_test_has_no_run` |

- Only server code that writes a calculation's outputs may write calculated. It sets the transaction-local setting `lims.calculation_write = 'on'` (`calculation_write()` in the service). No API route sets it. That path may not change raw (`calculation_changes_raw`).
- Typed raw may be edited and cleared. Clearing raw clears its units and its origin.
- A typed raw correction does not recompute in S6, because no calculation is configured until S7 and S9.
- Qualifiers are not editable through the result-entry PATCH.

## Routes

| Method and path | Permission | Notes |
|-----------------|-----------|-------|
| `GET /v1/lims-runs/{run_id}/result-entries` | `result:read` | `page`, `size` (at most 500). Ordered by sample name, display order (nulls last), analyte name, and replicate. 404 for an unknown run. |
| `PATCH /v1/lims-runs/{run_id}/result-entries/{row_id}` | `result:enter` | Body fields: `raw_result`, `raw_units`, `reported_result`. Client access is checked. 404 when the row is not on the run. |

## Pairing unit (CALC-REQ-28, OQ-CALC-36)

- `analysis_analytes.pairing_unit_id` holds the final units of calculated and reported for that analyte on that analysis.
- It defaults from `analytes.units_default` when the analyte is linked (trigger `analysis_analytes_default_pairing_unit`, and the analyses routes). Existing rows were backfilled.
- It is written with the analyte-rule permissions (`config:edit`, `test:configure`, or `analysis:manage`) through `POST` and `PATCH /analyses/{id}/analyte-rules`. An inactive or unknown unit is refused with HTTP 400. Sending `null` clears it.

## Knock-in audit (CALC-REQ-27)

- `DELETE /v1/lims-runs/data/{data_id}/exclude` no longer deletes the exclusion. It records `cleared_by` and `cleared_at` on the active row and returns it. `excluded_by`, `excluded_at`, and `reason` still show the original knockout. 404 when the point has no active exclusion.
- `GET /v1/lims-runs/data/{data_id}/exclusions` returns every knockout of the point, cleared or not, oldest first.
- Each point has at most one active exclusion (`uq_lims_run_data_exclusions_active`, where `cleared_at` is null). A point can be knocked out again after a clear.
- The permission is unchanged. All three routes need `experiment:manage`.
- `lims_app` has no DELETE on `lims_run_data_exclusions` (`db/append_only_tables.py`). Trigger `lims_run_data_exclusions_keep_record` refuses a delete, and any update except the one clear (`exclusion_record_kept`).
- The dose-response fit and the plate SVG read only active exclusions.
- Downgrade deletes cleared exclusions, because the old schema recorded a clear by deleting the row.

## Marc's decisions and S6

The decisions on `#N/A` for a missing or blank input, the missing-value error for a knocked-out result named in a formula, Excel error text on a formula error, and 4PL/5PL parameter names (A bottom, B top, C slope, D inflection) with optional `1/y` and `1/y²` weights belong to the formula and fit slices (S7 and S9). S6 stores no formula or fit field, so none of them changes this schema.
