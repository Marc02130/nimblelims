# Calculations S9: the stage runner and the first calculation write

Calculations slice S9 runs an active calculation configuration on a result-entry row, writes the calculated and reported values, and records a calculation attempt that holds the provenance of the calculation. It also runs a configuration's test cases and dry runs, so the S8 activation review shows real outcomes. It covers CALC-REQ-25, 26, 30, 21, 48 (run time), 49 (the calculation write), 53, 4a (timeouts recorded on the attempt), 37, and 58.

Migration: `backend/db/migrations/versions/0127_calculation_attempts.py` (revises `0126_calculation_activation`). Stage runner (pure, no database): `backend/app/services/calculation_runner.py`. Calculating a row and the attempt: `backend/app/services/calculation_attempt_service.py`. Test cases and dry runs: `backend/app/services/calculation_test_run_service.py`. Routes: `backend/app/routers/result_entries.py` and `backend/app/routers/calculation_config.py`. UAT: [UAT_Scripts/uat-calculations-s9.md](../UAT_Scripts/uat-calculations-s9.md). Earlier slices: [calculation-data-model-s6.md](calculation-data-model-s6.md), [calculation-configuration-s7.md](calculation-configuration-s7.md), [calculation-configuration-s8.md](calculation-configuration-s8.md).

Limits are not part of the calculations work (future issue #259), and neither is the constants table (#258). S9 reads no limit table and no constants table. A `limit_compare` stage reads its limit from its own bindings, as in S5.

Only the eleven catalog functions are called validated catalog functions. Nothing else in S9 is labelled that way.

## Terms

- A **calculated value** is what a stage outputs. S9 writes the configuration's chosen output to the row's `calculated_result` and `reported_result`. It is still a calculated value, not a result.
- A calculated value becomes a **result** only when the experiment is published (slice S13). S9 writes nothing to `results`.
- A **calculation attempt** is one run of the stage runner on one row. It is append-only.
- The **run summary** (`pass`, `fail`, or `stopped`) is the outcome of the attempt. It is not the Test status, and S9 does not change the Test status.

## Calculating a row

`POST /v1/lims-runs/{run_id}/result-entries/{row_id}/calculate`, with no body. It needs the `result:enter` permission. The `config:edit` permission alone is not enough. The response is `{attempt, result_entry}`. `GET .../result-entries/{row_id}/calculation-attempts` (permission `result:read`) lists the row's attempts, oldest first.

The call runs in three steps, so no database transaction is open while R runs.

1. **Read.** The row, its run, the analyte's active configuration, the units, the saved formulas, and the referenced rows on the same Test are read. The transaction is then released.
2. **Gate and run.** `/health` is read and the call is accepted or refused (CALC-REQ-4, 4a). Once it is accepted, the stage runner runs the stages in order. Every calculation is gated, even when no stage calls R.
3. **Write.** The row is locked. If anything read in step 1 changed, the answer is HTTP 409 `calculation_inputs_changed` and nothing is written. Otherwise the attempt is inserted and the row's calculated value, reported value, and `calculation_attempt_id` are written on the calculation path, in one transaction.

### Refused before the call is accepted (HTTP 400, no attempt)

A refusal writes nothing: no attempt and no change to the row (CALC-REQ-25).

| Code | When |
|------|------|
| `configuration_missing` | The analyte has no calculation configuration. |
| `configuration_not_active` | The configuration is a draft. A draft is never run on a row. |
| `configuration_unreadable` | The stored configuration cannot be read as S7 stores it. |
| `catalog_function_unknown` | A stage names a function or version outside the closed catalog. |
| `saved_formula_unknown` | A saved formula stage names a formula version that is not stored. |
| `binding_not_readable` | A `run_field` binding names something other than the row's own raw value (see below). |
| `raw_units_differ` | The row's raw units differ from the pairing unit and the raw value is not read by a `convert_units` stage (OQ-CALC-39). |
| `run_published` | The run is published. |
| `run_has_no_analysis` | The run has no analysis. |
| `row_knocked_out` | The row is knocked out. |
| `already_calculated` | The row already has a calculated value. Recalculation is slice S12. |
| `lock_hash`, `lock_mismatch`, `missing_digest`, `ill_formed_digest`, `sandbox` | The `/health` gate refused (CALC-REQ-4). |
| `r_service` and other R refusals | R refused a call mid-run for a reason that is not a timeout. Nothing is recorded. |

### Stopped (HTTP 200, attempt recorded)

A stage stop is an outcome, not a refusal. The attempt is recorded with status `stopped`, the stop code, and the stage that stopped. The row's calculated and reported values are both written empty, and no later stage runs (CALC-REQ-25).

| Stop | Raised by |
|------|-----------|
| `curve_not_fitted`, `r_non_finite`, `non_positive_log_input` | The four R functions (`fit_4pl`, `inverse_4pl`, `fit_loglog_linear`, `inverse_loglog_linear`). |
| `r_timeout`, `backend_timeout` | The R call or the backend call timed out (CALC-REQ-4a). |
| `unit_not_found`, `unit_type_mismatch` | `convert_units` cannot convert the value. |
| `reference_missing`, `reference_ambiguous`, `reference_stopped` | A reference input cannot be read (see below). |
| `on_fail_undeclared` | A stage has no usable on-fail declaration (CALC-REQ-48). |
| A formula error (`#DIV/0!`, `#VALUE!`, `#N/A`, `#NUM!`) | A lab-written formula stage. The attempt records the Excel text in `formula_error` and has no stop code. |

## How a stage ends

| Stage status | Meaning |
|--------------|---------|
| `ok` | The stage produced its outputs. |
| `flagged` | The stage produced outputs and its function raised a flag (`replicate_missing`, `mean_zero`). The flag is recorded and carried. The on-fail declaration is not applied. |
| `failed` | A check missed: no output with a flag (`missing_input`, `limit_above_el`, `inactive`, `response_at_asymptote`), a `missing_limit` with no verdict, a `fail` verdict, or an input the function refuses (`apply_dilution` below 1). The declared outcome applies at its precedence place, and the declared gates do not run. |
| `no_verdict` | `limit_compare` does not judge this qualified value (`unspecified`). Not a failure. |
| `qualified` | An inverse function answered `<` or `>`. Not a stop and not missing. A stage that reads its output does not run. |
| `stopped` | A stage stop or a formula error. |
| `gated`, `skipped`, `not_reached` | The stage did not run: a failed check named it in its gates, it reads an output that was not produced, or an earlier stage stopped. |

### On-fail declarations at run time (CALC-REQ-48)

Each stage's four declarations (outcome, flag, gates, precedence place) are read as S7 stored them. A declaration that is missing, incomplete, or says `pass` fails closed: the stage stops with `on_fail_undeclared`.

- When a stage fails, its declared flag is raised at its precedence place, and the stages it gates are marked `gated`.
- A stage on an R function declares a stage stop. If that stage fails without a stop (for example a flag), the failure is recorded as a flag.
- A `limit_compare` stage that finds no limit raises its `missing_limit_flag`.
- Flags are listed in precedence order (numeric places first, then stage order), not in the order the stages ran.

### Run summary (CALC-REQ-21)

- `stopped`: a stage stopped. `summary_check` names the stage, and `summary_code` holds the stop code or the formula error text.
- `fail`: a failed check declared `run_failed`. `summary_check` names the first such check by precedence, and `summary_code` is `run_failed`.
- `pass`: neither. `summary_check` and `summary_code` are empty.

The run summary is not the Test status. S9 does not change the Test status, its qualifiers, or `final_units`.

## What is written

- The configuration's `result` pointer (`{stage, output}`) names the stage output that is written. It is written to both `calculated_result` and `reported_result` as a decimal string, unchanged. A boolean formula output is written as `TRUE` or `FALSE`.
- `copy_raw` writes its two outputs: the raw string, unchanged and with its trailing zeros, to both columns (CALC-REQ-53). A raw `0.026` gives calculated `0.026` and reported `0.026`.
- A person may change the reported value afterwards, as in S6. The link to the attempt stays.
- When the pointed-at stage did not produce a value, both columns are written empty and the attempt records a `result_note`:
  - `{code: result_qualified, qualifier, end, message}` when the stage answered `<` or `>`. How a qualified value is reported is slice S11.
  - `{code: result_not_produced, message}` otherwise, for example when the stage was gated or failed.
- Fit parameters and other stage outputs stay in the attempt's `stages` record. They are not written to the row.

## The attempt (CALC-REQ-30)

Each attempt is one row in `calculation_attempts`. It holds:

- the row, Test, analyte, LIMS run, and analysis;
- the status (`completed` or `stopped`), the stop code, the stop stage and detail, or the formula error text;
- the run summary, the check that produced it, and its code;
- the R lock hash and the built image digest read from `/health` at the gate. The lock hash is the one `/health` reported, so the two match;
- the configuration name and version, and the analysis version;
- the version of every catalog function stage (`function_versions`) and every formula stage, with the formula text (`formula_versions`);
- every run field and reference read, with the entry, record, field, value, and units (`inputs_read`);
- every value used, including direct values (`values_used`, OQ-CALC-46);
- the knocked-out points left out (`knocked_out_points`);
- the flags, in precedence order;
- each stage's record: status, outputs, flags, whether R was called;
- the calculated and reported values written, and the result note;
- the user (`current_user_id()`) and the time (the database clock).

The row's `calculation_attempt_id` points at the attempt that last wrote it. Provenance lives on the attempt and is linked from the row. It is not copied onto row columns (OQ-CALC-25, the Spec default).

## What a row can read

- A `run_field` binding reads the row's own raw value only: entry type `experiment_sample_data`, field `raw_result`, no match field. Any other run field is `binding_not_readable`. Reading other fields is not in S9.
- A `reference` binding reads another analyte on the same Test (CALC-REQ-58: a metadata analyte is read the same way). It reads the referenced row's `calculated` or `reported` value, as the binding says. The referenced analyte must have an earlier calculation order (S7).
  - No row for that analyte on the Test, or a row with no value yet: `reference_missing`.
  - More than one row: `reference_ambiguous`. Which replicate or average a reference reads is OQ-CALC-40, so S9 fails closed.
  - The referenced row's latest attempt stopped: `reference_stopped`.
  - The referenced row is knocked out: it is read as a knocked-out value.
- A `direct` binding reads its value from the configuration and is recorded in `values_used`.

## Units (OQ-CALC-39)

- The row's raw value is in the row's `raw_units`. When they are empty, the value is taken to be in the analyte's pairing unit.
- When the raw units differ from the pairing unit, the raw value must be read by a `convert_units` stage. Otherwise the calculation is refused with `raw_units_differ`. S9 never converts silently.
- `convert_units` converts within a unit type from the value's unit to the pairing unit, or divides by an amount when `amount` is bound. Units of different types stop with `unit_type_mismatch`.

## Knocked-out points

A knocked-out value in a formula is `#N/A`. A knocked-out replicate is left out of `replicate_mean_cv`, and the attempt records it in `knocked_out_points`. When every replicate is knocked out, the stage fails with `missing_input` and no mean is made up. A knocked-out row is not calculated (`row_knocked_out`).

## Test cases

`POST /v1/analyses/{analysis_id}/analytes/{analyte_id}/calculation-config/test-cases/run`, with no body, runs every test case of the analyte's current configuration version, draft or active. It needs `config:edit` (or another configuration permission). It is gated on `/health` first. A gate refusal is HTTP 400 and records nothing. If the configuration changes while the cases run, the answer is HTTP 409 `configuration_changed` and nothing is recorded.

A test case's `inputs` is an object:

- Each key is a field name a `run_field` binding names (for a live row, `raw_result`). Its value is a decimal string, `null` (missing), a list of those, or `{"value": "...", "knocked_out": true}`.
- `references`: analyte id to `{"calculated": "...", "reported": "..."}`, or `{"stopped": true}`. An analyte not listed is `reference_missing`.
- `units`: field name to unit name. A field with no unit is in the pairing unit.

A test case's `expected` is an object with any of `calculated`, `reported`, `status`, `stop_code`, `formula_error`, `run_summary`, `summary_check`, and `flags` (a list of flag names), plus `tolerance`: an absolute decimal allowed between the calculated or reported value and the expected one. Decimals are compared as decimals, so `0.0260` matches `0.026`.

Each case ends in one of three states:

- `passed`: every expected key matched.
- `failed`: one did not. The response lists each check with the expected and the observed value.
- `not_run`: the inputs (`inputs_unreadable`) or the expected (`expected_unreadable`) cannot be read, including an empty expected or an unknown key. Nothing is recorded for it.

Each run case is recorded in `calculation_test_case_results` with the lock hash, `passed`, the built image digest, and the outcome (the checks and the full run). The S8 review counts the latest outcome of each case on the current lock hash. The response is `{total, run, passed, lock_hash, built_image_digest, live_refusal, cases}`. `live_refusal` says what a live row calculation would refuse for this configuration (for example `binding_not_readable`), because a test case can bind fields a row cannot yet supply.

## Dry runs

`POST .../calculation-config/dry-run` with the body `{"input": {...}}` runs the current configuration version once on the given input, which has the same shape as a test case's inputs. It needs a configuration permission and is gated first. It is recorded in `calculation_dry_runs` with the input, the outcome, the lock hash, the built image digest, and the user. The S8 review shows the latest dry run. A body that is not exactly `{"input": {...}}`, a float, or an input over 20000 characters is `dry_run_invalid`.

Neither a test case run nor a dry run writes a result-entry row.

## The configuring agent

None of the S9 routes is on the configuring-agent allow-list. The agent cannot calculate a row, run test cases, or make a dry run.

## Database (migration 0127)

- `calculation_attempts` is append-only for the application role: it has no UPDATE or DELETE privilege, and a trigger refuses both (`calculation_attempt_append_only`). An attempt is recorded only for the signed-in user (`calculation_attempt_actor`) and only with the Test, analyte, run, and analysis of its row (`calculation_attempt_scope`). The time is the database clock. Check constraints keep a stop and its cleared values together and require the summary to name its check unless it is `pass`.
- Row-level security on `calculation_attempts` follows the result entry the attempt belongs to.
- `result_entries.calculation_attempt_id` changes only on the calculation path, only to an attempt of that same row, and only together with that attempt's calculated and reported values (`calculation_attempt_mismatch`). Outside the calculation path it cannot change (`calculation_attempt_locked`).
- The application role gains INSERT on `calculation_test_case_results` and `calculation_dry_runs`. UPDATE and DELETE stay revoked, and a trigger refuses any other actor than the signed-in user (`calculation_run_record_actor`) and any update or delete (`calculation_run_record_append_only`).
- Downgrade to 0126 drops the attempts table and the link, restores the 0123 result-entry guard, and revokes the INSERT grants. Attempts and recorded outcomes are lost.

## Provisional choices and open questions

These follow the Spec defaults or fail closed. Each stays provisional until the open-questions log records it.

- OQ-CALC-25: provenance lives on the attempt, linked from the row (Spec default).
- OQ-CALC-46: direct values are recorded on the attempt in `values_used`, as well as in the versioned configuration.
- OQ-CALC-39: raw units that differ from the pairing unit need a `convert_units` stage. Otherwise the calculation is refused with `raw_units_differ`.
- OQ-CALC-40: a reference is read only when the Test has exactly one row for that analyte. Otherwise `reference_ambiguous`.
- A formula error stops the attempt with its Excel text and no stop code. The Spec does not give a stop code for it.
- `unit_type_mismatch` is the spelling of the cross-type unit stop. The Spec does not lock one.
- A flagged stage that still produced outputs is not a failure. Its declaration is not applied.
- A non-stop failure at an R stage, whose declaration must be a stop, is recorded as a flag.
- Replicates and points are identified by their position in the list.
- A row is calculated once in S9 (`already_calculated`). Recalculation and knockout after a calculation are slice S12.
- A live row reads only its own raw value (`binding_not_readable` for any other run field).
- An R refusal mid-run that is not a timeout records nothing (HTTP 400).
- Test cases and dry runs run on the current configuration version, draft or active.
- There is no release ledger, so S9 does not check the release state of the calculator before running.
- There is no user interface for calculating a row in S9. It is an API call.
