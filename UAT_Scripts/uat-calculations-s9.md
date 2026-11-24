# UAT: calculations S9, the stage runner and the first calculation write

**Scope:** CALC-REQ-25, 26, 30, 21, 48 (run time), 49 (the calculation write), 53, 4a (timeouts recorded on the attempt), 37, and 58. Migration `0127_calculation_attempts`. The stage runner runs an active configuration on a result-entry row. Each run records an append-only calculation attempt with its provenance. On success it writes calculated and reported. On a stop it clears both and runs no later stage. Test cases and dry runs run through the same runner, so the S8 activation review shows real outcomes. Nothing here writes to `results`.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** none new. S9 adds no catalog function. The S2 to S5 KATs run again unchanged. See [manuals/calculation-configuration-s9.md](../manuals/calculation-configuration-s9.md).

**Terms:** a stage output is a calculated value, not a result. It becomes a result only when the experiment is published (S13). The run summary (`pass`, `fail`, `stopped`) is not the Test status.

**Out of scope:** limits (#259), the constants table (#258), same-run multi-analyte reads beyond one reference row (S10), thresholds (S11), recalculation and knockout after a calculation (S12), publishing (S13), and the audit trail (#25).

## Setup

1. Check out `calculations` at the S9 commit.
2. Install `backend/requirements.txt` into a Python 3.12 environment. The database tests need Docker (testcontainers Postgres).
3. For the API steps against a running stack, run `sudo docker compose up -d --build` and generate the seed passwords with `python backend/seed_dev_passwords.py --apply --secrets-out PATH`. Read the passwords from that file. Do not copy them anywhere else. Set the lab timezone if the stack asks for it.

## Backend suite

4. `cd backend && python -m pytest -q tests/test_calculation_runner_s9.py tests/test_calculation_attempts_s9_api.py tests/test_calculation_attempts_s9_db.py` passes.
5. `cd backend && python -m pytest -q tests/test_calculation_activation_s8.py tests/test_calculation_activation_s8_api.py tests/test_calculation_activation_s8_db.py tests/test_calculation_config_s7_db.py tests/test_append_only_revokes.py tests/test_instant_timestamptz.py` still passes. The head assertions find `0127_calculation_attempts`.

## The first calculation write (CALC-REQ-49, 53)

6. `test_copy_raw_writes_0_026_to_calculated_and_reported_and_links_the_attempt`: a raw `0.026` with a `copy_raw` configuration gives calculated `0.026` and reported `0.026`. The row's `calculation_attempt_id` is the attempt. The attempt's lock hash equals the `/health` lock hash, and the digest is the built image digest.
7. `test_copy_raw_writes_the_raw_string_to_calculated_and_reported`, `test_copy_raw_keeps_trailing_zeros_and_never_converts`: the raw string is written unchanged.
8. `test_reported_can_be_overwritten_after_the_calculation_wrote_it`: a person changes the reported value. The calculated value and the link stay.
9. `test_a_formula_result_is_written_to_both`, `test_a_saved_formula_is_run_from_its_pinned_text`, `test_a_boolean_formula_is_written_as_true_or_false`.
10. `test_an_r_value_feeds_the_next_stage_and_is_written`, `test_fit_4pl_success_feeds_the_next_stage_and_calls_only_its_route`.

## Stops (CALC-REQ-25, 4a)

11. `test_a_first_calculation_that_stops_with_r_timeout_clears_both_and_is_200`: HTTP 200. The attempt is `stopped` with stop code `r_timeout` and the stop stage. Calculated and reported are both empty. The later stage is `not_reached`.
12. `test_a_backend_timeout_is_also_a_recorded_stop`, `test_a_timeout_is_a_stage_stop_recorded_on_the_attempt`.
13. Each stop code, with no later stage run:
    - `test_fit_4pl_curve_not_fitted_stops_and_dependents_do_not_run`
    - `test_r_non_finite_stops`, `test_inverse_4pl_r_non_finite_stops`
    - `test_fit_loglog_linear_non_positive_log_input_stops`, `test_inverse_loglog_linear_non_positive_endpoint_stops`
    - `test_convert_units_unit_not_found_stops`, `test_convert_units_across_unit_types_stops_with_the_type_mismatch_code`
    - `test_a_reference_that_cannot_be_read_stops`
    - `test_a_stage_with_no_on_fail_declaration_stops_on_fail_undeclared`, `test_an_unusable_declaration_fails_closed`
14. `test_a_formula_error_stops_with_its_excel_text_and_no_stop_code`: the attempt holds `#DIV/0!` in `formula_error`.
15. DB, `test_a_stopped_attempt_clears_both_values_on_the_row`, and `test_the_stop_and_summary_rules_are_checked_by_the_database`: the database refuses a stopped attempt that carries a value or no stop.

## Refusals before the call is accepted (CALC-REQ-25, HTTP 400, nothing recorded)

16. `test_a_draft_configuration_is_not_run` (`configuration_not_active`), `test_an_analyte_with_no_configuration_is_refused` (`configuration_missing`).
17. `test_a_lock_or_sandbox_refusal_writes_no_attempt`: each `/health` refusal (`lock_hash`, `lock_mismatch`, `missing_digest`, `ill_formed_digest`, `sandbox`) is HTTP 400 and writes no attempt.
18. `test_an_r_refusal_mid_run_that_is_not_a_timeout_writes_nothing`, `test_a_refusal_that_is_not_a_timeout_is_raised_and_nothing_is_recorded`.
19. `test_a_row_is_calculated_once_in_s9` (`already_calculated`), `test_a_knocked_out_row_is_not_calculated` (`row_knocked_out`), `test_a_published_run_is_not_calculated` (`run_published`).
20. `test_a_run_field_s9_cannot_read_is_refused_before_the_call` (`binding_not_readable`), `test_raw_units_that_differ_from_the_pairing_unit_are_refused_for_copy_raw` (`raw_units_differ`, OQ-CALC-39).
21. `test_an_unknown_catalog_function_is_refused_before_any_call`, `test_a_saved_formula_that_is_not_stored_is_refused`, `test_an_unreadable_configuration_is_refused`.
22. `test_calculating_needs_result_enter_not_configuration_rights`: a user with only `config:edit` gets HTTP 403. A user with `result:enter` calculates.

## Provenance (CALC-REQ-30)

23. The attempt in step 6 shows the configuration name and version, the analysis version, the function versions, the inputs read with their entry, record, field, value, and units, the values used, the knocked-out points, each stage's record, the user, and the time.
24. `test_direct_values_are_recorded_in_values_used` (OQ-CALC-46).
25. `test_a_knocked_out_replicate_is_left_out_of_the_mean_and_recorded`, `test_a_knocked_out_value_in_a_formula_is_na_and_is_recorded`, `test_every_replicate_knocked_out_is_missing_input_with_no_fabricated_mean` (CALC-REQ-26).
26. `test_the_outcome_is_json_safe`.

## On-fail at run time and the run summary (CALC-REQ-48, 21)

27. `test_a_failed_check_with_run_failed_names_the_check_in_the_summary`: the summary is `fail` and names the check.
28. `test_the_first_run_failed_by_precedence_is_named`, `test_flags_are_in_precedence_order_not_stage_order`.
29. `test_a_failed_check_gates_the_stages_it_names`, `test_a_passing_check_does_not_gate`.
30. `test_a_fail_verdict_at_the_pointer_writes_fail`, `test_a_missing_limit_raises_the_missing_limit_flag`.
31. `test_a_flag_raised_with_outputs_is_carried_not_failed`, `test_a_failure_that_is_not_a_stop_at_an_r_stage_is_a_flag`.
32. `test_a_dilution_below_one_is_dilution_invalid_and_gates`, `test_a_dilution_is_applied_in_decimal`.
33. `test_a_qualified_inverse_is_not_a_stop_and_its_dependents_are_skipped`: nothing is written and the attempt holds a `result_qualified` note.

## Units and references (OQ-CALC-39, CALC-REQ-58)

34. `test_convert_units_converts_the_raw_unit_to_the_pairing_unit`, `test_convert_units_with_no_raw_unit_reads_the_pairing_unit`, `test_convert_units_per_amount_divides`.
35. `test_a_reference_is_read_as_an_analyte_and_recorded`, and API `test_a_reference_to_an_analyte_on_the_same_test_is_read_and_recorded`: the attempt records the referenced row and its value.
36. `test_a_reference_not_calculated_yet_stops_reference_missing`, `test_a_reference_whose_calculation_stopped_stops_reference_stopped`.

## Test cases and dry runs (S8 review sees real outcomes)

37. `test_running_test_cases_records_outcomes_and_the_review_reads_them`: each case is `passed`, `failed`, or `not_run`. Outcomes are recorded with the lock hash and digest. The review's validation state and summary text change from "Not run" to the real counts.
38. `test_test_cases_check_stops_and_flags`, `test_all_test_cases_passing_reaches_all_passed` (`tests_all_passed`).
39. `test_a_gate_refusal_records_no_test_case_outcome`, `test_running_test_cases_needs_configuration_permission`, `test_a_manager_with_config_edit_may_run_test_cases`.
40. `test_a_dry_run_is_recorded_and_the_review_shows_it`: the review's dry run line reads done, with the time and the input.
41. `test_an_unreadable_dry_run_is_refused_and_records_nothing` (`dry_run_invalid`), `test_a_dry_run_on_an_analyte_with_no_configuration_is_refused`, `test_a_dry_run_of_a_reference_reads_the_inputs_references`.
42. `test_no_s9_route_is_on_the_agent_allow_list`: the configuring agent cannot calculate, run test cases, or dry run.

## Database (migration 0127)

43. `test_0127_schema_shape`: the attempts table, the link column, the new outcome columns, row-level security forced, the triggers, and the privileges (SELECT and INSERT only). The result-entry guard's owner is the attempts table's owner.
44. `test_an_attempt_is_recorded_for_the_signed_in_user_with_the_database_clock` (`calculation_attempt_actor`), `test_an_attempt_names_the_test_analyte_run_and_analysis_of_its_row` (`calculation_attempt_scope`).
45. `test_an_attempt_is_never_updated_or_deleted_by_the_application`: refused by privilege, and by the trigger even with the privilege handed back.
46. `test_the_row_links_only_an_attempt_of_that_row_with_its_values_on_the_calculation_path`: `calculation_attempt_locked` off the calculation path, `calculation_attempt_mismatch` for another row's attempt or other values.
47. `test_attempts_are_visible_only_with_their_result_entry`: a user of another client sees neither the row nor its attempt.
48. `test_the_application_records_test_case_results_and_dry_runs_only_as_itself` (in the S8 DB tests), `test_every_regrant_is_a_grant_in_a_later_migration`.
49. `test_0127_downgrade_removes_attempts_and_upgrade_restores_them`.
50. `test_calculate_row_runs_as_the_app_role_against_the_real_guards`: the service writes the attempt and the row as `lims_app` against the real triggers and row-level security.

## Wording

51. The four wording tests at the end of `tests/test_calculation_runner_s9.py` pass: the S9 files use the word only in "validated catalog functions", never call a stage output a result, write no official result, and hold no parked constant.

## API against a running stack (manual)

52. Sign in as the Admin. Save and activate a `copy_raw` configuration on an analyte (S7 and S8). Start a LIMS run for a sample with that analysis and type a raw value `0.026` on the analyte's row.
53. `POST /v1/lims-runs/{run_id}/result-entries/{row_id}/calculate`. The answer is HTTP 200. `result_entry.calculated_result` and `reported_result` are `0.026`. `attempt.status` is `completed` and `attempt.run_summary` is `pass`. `attempt.lock_hash` equals the `lock_hash` that the R calculator's `/health` reports.
54. Call it again. The answer is HTTP 400 `already_calculated` and `GET .../calculation-attempts` still lists one attempt.
55. Sign in as the Lab Technician. On a second row, calculate. It succeeds. Sign in as a user with only `config:edit`. The call is HTTP 403.
56. Stop the R calculator container and calculate a row whose configuration has an R stage. The answer is HTTP 400 and no attempt is listed.

## Notes for the reviewer

- OQ-CALC-25, 46, 39, and 40 are applied provisionally, as listed in the manual.
- A formula error stops with its Excel text and no stop code. `unit_type_mismatch` is a provisional spelling.
- There is no user interface for calculating a row in S9, and no release-state check of the calculator.
