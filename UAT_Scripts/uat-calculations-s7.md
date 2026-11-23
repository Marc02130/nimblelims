# UAT: calculations S7, calculation configuration and the no-code builder

**Scope:** CALC-REQ-40, 23, 48, 22, 28, 50, and 46. Migration `0124_calculation_configuration`. Analysis versions, configuration storage on `analysis_analytes`, the builder's rules, saved and ad hoc formulas, direct binding, on-fail declarations, and calculation order. Nothing runs a calculation in S7. The stage runner is S9, and proposing or activating a configuration is S8. Neither is in this pass.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** none new. S7 adds no catalog function. The formula engine has hand-computed expectations in `test_calculation_formula_s7.py`. The S2 to S5 KATs run again unchanged. See [manuals/calculation-configuration-s7.md](../manuals/calculation-configuration-s7.md).

**Limits:** not part of the calculations work (future issue #259). No limits table, LOQ, or acceptance range is built or tested here.

## Setup

1. Check out `calculations` at the S7 commit.
2. Install `backend/requirements.txt` into a Python 3.12 environment. The database tests need Docker (testcontainers Postgres).

## Backend suite

3. `cd backend && python -m pytest -q tests/test_calculation_formula_s7.py tests/test_calculation_config_s7.py tests/test_calculation_config_s7_api.py tests/test_calculation_config_s7_db.py` passes.
4. `cd backend && python -m pytest -q tests/test_calculation_result_entry_s6.py tests/test_calculation_result_entry_s6_db.py tests/test_append_only_revokes.py tests/test_configuring_agent_catalog_seed.py tests/test_explicit_patch.py tests/test_asked_for_p1.py tests/test_work_order_p2.py` still passes. `test_calculation_result_entry_s6_db.py` upgrades to its own target `0123_result_entry_data_model`, then to head.
5. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py tests/test_calculation_kat_s2.py tests/test_calculation_release_s2.py tests/test_calculation_catalog_r_s3.py tests/test_calculation_catalog_decimal_s4.py tests/test_calculation_catalog_s5.py` still passes. The head assertions find `0124_calculation_configuration`.

## Analysis version (CALC-REQ-40, OQ-CALC-31)

6. `test_a_new_analysis_is_version_1_with_a_snapshot_of_what_committed`: a new analysis is version 1 and has one `analysis_versions` row listing its analytes.
7. `test_each_committed_change_bumps_the_version_once_and_keeps_the_old_snapshot`:
   - Three statements in one transaction raise the version once, from 1 to 2.
   - The version 2 snapshot holds the configuration and the edited description. The version 1 snapshot is unchanged.
   - Its `created_by` is the user of the transaction, and empty when the session has no user.
   - Deleting the analyte row is version 4, with no analytes in the snapshot.
8. `test_a_rolled_back_change_does_not_bump_the_version`: a rolled-back transaction leaves version 1 and one snapshot.
9. `test_the_app_role_cannot_write_the_analysis_version`, as `lims_app`:
   - An insert with a version other than 1, and any update of `version`, is `analysis_version_locked`.
   - A normal edit of the analysis is allowed.
10. `test_a_change_made_as_the_app_role_bumps_the_version_the_app_cannot_write`: the database makes the increment and writes the snapshot even when the change comes from `lims_app`.
11. `test_the_app_role_cannot_write_versions_or_change_a_saved_formula`: `lims_app` can insert into `calculation_formulas`, and cannot update or delete it. It cannot insert, update, or delete `analysis_versions`.

## Schema (CALC-REQ-48, OQ-CALC-35 and 48)

12. `test_0124_schema_shape`: `analyses.version` is not null with default 1. The five configuration columns exist and are nullable. The check constraints, the unique partial order index, the case-insensitive unique name index, and the four triggers (two of them deferred) exist. `analysis_analytes.calculation`, the free-text column, is still there.
13. `test_configuration_columns_are_all_or_nothing_and_unique`:
    - Setting only the order, or only the name, is `ck_analysis_analytes_calc_config_complete`.
    - An order of 0 or less, a state other than `draft` or `active`, and a blank name are `ck_analysis_analytes_calc_config_values`.
    - The same order twice in one analysis is `uq_analysis_analytes_calculation_order`. The same name in another case is `uq_analysis_analytes_calculation_config_name`.
    - `display_order` may repeat.
14. `test_formula_rows_are_unique_by_name_and_version`: the same name and version is refused, whatever the case. Version 0, a blank text, and a text over 2000 characters are refused.
15. `test_0124_downgrade_removes_everything_and_upgrade_restores_it`: downgrade drops the columns, tables, and functions and leaves `analysis_analytes.calculation`. Upgrade brings the analysis back at version 1 with its snapshot.

## Active is immutable (CALC-REQ-40)

16. `test_activation_is_a_flag_the_app_cannot_set_by_writing`: writing `active` as `lims_app` is `calculation_activation_required`, on update and on insert. With `lims.calculation_activate = 'on'` it is allowed.
17. `test_an_active_configuration_is_immutable_for_the_app_role`: for an active row, a change to the body, name, version, or order, clearing the columns, setting `draft`, and a delete are all `calculation_config_active`. Setting `is_required` stays allowed.
18. `test_new_version_flag_allows_only_active_to_draft_with_the_same_content`: with `lims.calculation_new_version = 'on'`, active to draft with unchanged content is allowed. Active to draft with a changed body, or a changed order, is still refused. Once draft, the content can change.
19. `test_superusers_and_the_migrator_skip_the_guards`.
20. API, `test_an_active_configuration_is_refused_in_place_and_nothing_changes`: with the row active, a changed formula text, a changed binding, and a changed on-fail flag are each HTTP 400 `calculation_config_active`. The order change and the delete are also refused. The stored body is unchanged.
21. API, `test_changing_only_the_flag_a_stage_sets_is_refused_in_place_and_succeeds_as_a_new_version`:
    - The in-place flag change is refused.
    - `POST /v1/analyses/{id}/new-version` returns `drafted_analyte_ids` with the analyte, and the row is `draft`.
    - The same change now saves, and the configuration version is 2.
22. API, `test_new_version_needs_an_active_configuration`: HTTP 400 `no_active_configuration`. An unknown analysis is 404.
23. API, `test_the_analyte_routes_refuse_to_drop_an_active_configuration`: removing the analyte by `PUT /analyses/{id}/analytes`, `DELETE .../analytes/{id}`, or `DELETE .../analyte-rules/{id}` is HTTP 400 `calculation_config_active`. A `display_order` edit is still allowed.

## The catalog is closed (CALC-REQ-22)

24. `test_the_catalog_is_readable_and_has_eleven_entries`: `GET /v1/calculation-catalog` returns the eleven functions, with failure stops and required inputs.
25. `test_a_write_to_the_catalog_is_405_and_the_catalog_is_unchanged`: POST, PUT, PATCH, and DELETE are 405.
26. `test_the_builder_offers_only_catalog_functions`: a function name outside the catalog is `catalog_function_unknown`.
27. `test_no_route_serves_constants_or_runs_r`: no calculation route carries a constants or run-R path.

## Saving a configuration (CALC-REQ-23, 48, 50)

28. `test_admin_saves_a_draft_configuration_and_reads_it_back`: the saved body is returned as `draft`, version 1, with the order and the analysis version. `GET` returns the same body.
29. `test_the_free_text_calculation_column_is_not_the_configuration`: a value in `calculation` is not touched by a configuration save.
30. `test_saving_the_same_content_again_changes_nothing`: the configuration version stays 1, and rises to 2 when a binding changes.
31. `test_a_missing_declaration_is_refused_with_the_stage_named`: HTTP 400 `on_fail_declaration_missing`, with the `stage`. Nothing is stored.
32. `test_refusals_are_400_and_write_nothing`: `on_fail_pass_refused`, `precedence_place_conflict`, `direct_value_invalid` (a JSON number), `formula_range_not_supported`, `on_fail_stage_stop_required`, and `catalog_function_unknown` are each HTTP 400. Nothing is stored.
33. `test_a_direct_binding_saves_and_a_stop_is_not_a_refusal`: a direct decimal string is stored in the body.
34. `test_unknown_json_fields_are_refused`: an extra field in the body, a `constants` key in the configuration, and an extra field on the order patch are `unknown_field`.
35. See `test_calculation_config_s7.py` for the builder rules without a database:
    - The four on-fail outcomes. A verdict is required for `sample_verdict` only. A missing-limit flag is required for a limit stage only.
    - Each function's failure stops, and gates that name later stages.
    - Unit rules: one shared unit per group, dimensionless for `1`, a percentage for `%`, and an output unit that carries forward.
    - The scan that finds no use of the #258 constants identifiers, and the wording scan over the S7 code, manual, and this script, which allows that word only in the phrase for the catalog functions.

## Calculation order (OQ-CALC-35)

36. `test_calculation_order_is_required_positive_and_unique`: a missing order is `calculation_order_required`. 0, -1, 1.5, `"1"`, `true`, and `null` are `calculation_order_invalid`. A repeat in the same analysis is `calculation_order_duplicate`.
37. `test_a_later_analyte_reads_an_earlier_analytes_value_and_order_is_enforced`:
    - An analyte reads an earlier one through a `reference` binding.
    - The reader cannot take the same or a smaller order. The earlier analyte cannot move past its reader. A forward read is `calculation_order_violation`.
    - The earlier configuration cannot be deleted while it is read (`configuration_in_use`).
38. `test_patch_order_and_delete_a_draft`: the order patch raises the configuration version. A draft deletes cleanly, and the row's order and body are null afterward.
39. `test_display_order_and_calculation_order_are_separate`: `PATCH .../analyte-rules/{id}` with `display_order` does not change `calculation_order`. The analyte-rule response carries `calculation_order`, `calculation_config_name`, `calculation_config_version`, and `calculation_config_state`.
40. `test_a_configuration_name_is_unique_in_the_analysis`: `calculation_config_name_exists`, whatever the case.

## Formulas (CALC-REQ-23, OQ-CALC-52)

41. `test_only_an_admin_writes_a_formula_in_a_configuration`:
    - A user with `config:edit` who is not an Administrator gets HTTP 403 `formula_admin_only`, naming the stage, for a configuration with a formula stage.
    - The same user can save a catalog-only configuration, and can edit a binding in a configuration that holds an unchanged formula. A changed formula text is 403.
42. `test_only_an_admin_saves_or_tries_a_formula`: the formula save and the dry run are 403 for a non-Admin.
43. `test_admin_saves_a_formula_as_version_1_then_2_and_old_versions_stay`: the same text again is `formula_unchanged`. A different text is version 2, and version 1 still reads back. An unknown version is 404.
44. `test_a_saved_formula_is_pinned_by_a_configuration`: a later version of the formula does not change the pinned version. An unknown version is `saved_formula_unknown`.
45. `test_the_ad_hoc_formula_version_counts_edits_by_an_admin`.
46. `test_a_formula_outside_the_grammar_is_not_saved`: a range, an unknown function, an empty text, and a syntax error are each HTTP 400 with their code. An unknown field is refused.
47. `test_evaluate_round_half_even_and_excel_errors_return_200`:
    - `ROUND(2.5, 0)` is `2` and `ROUND(3.5, 0)` is `4`.
    - Division by zero is `#DIV/0!`, `SQRT(0-1)` is `#NUM!`, a non-numeric term is `#VALUE!`.
    - A null term, a knocked-out term, and a missing term are `#N/A`.
    - Every one is HTTP 200 with the error in the body, and nothing is stored.
48. `test_evaluate_stdev_divides_by_n_minus_1_and_stdev_p_by_n`: for 2, 4, 4, 4, 5, 5, 7, 9, `STDEV.P` is 2 and `STDEV` is 2.138089935...
49. In `test_calculation_formula_s7.py`: unary minus binds tighter than `^`, and `^` is left-associative. An error in one formula does not stop another. `IF` evaluates only the branch it takes. Decimal results are exact. A scan finds no use of `eval` or `exec`.

## Unchanged

50. The S1 pin, the S2 harness, the S3 R routes, and the S4 to S6 behaviour are unchanged. `bash services/r-calculator/scripts/ci-pin.sh` still ends with `ci-pin ok`.

## Not in this pass

- No calculation run, stage runner, attempt, or recompute (S9).
- No proposal, activation, or review by the configuring agent (S8). No route sets `lims.calculation_activate`.
- No limits table, LOQ, or acceptance range (#259).
- No generic "run R" endpoint.
- No screen.
- No merge to `main`.
