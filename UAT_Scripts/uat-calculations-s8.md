# UAT: calculations S8, proposing and activating a calculation configuration

**Scope:** CALC-REQ-47, 34, 35, 45, and 46. Migrations `0125_analysis_version_no_change` and `0126_calculation_activation`. The configuring agent saves an inactive proposal. An Admin reviews it and activates it with a single-use confirm token. The activation record is append-only. The analysis version does not rise for a save that changes nothing. Nothing runs a calculation in S8. The stage runner is S9, and nothing here writes to a result table.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** none new. S8 adds no catalog function. The S2 to S5 KATs run again unchanged. See [manuals/calculation-configuration-s8.md](../manuals/calculation-configuration-s8.md).

**Terms:** a stage output is a calculated value, not a result. It becomes a result only when the experiment is published (S13). The `result` pointer names which output will be published.

**Limits:** not part of the calculations work (future issue #259). S8 reads no limit table.

## Setup

1. Check out `calculations` at the S8 commit.
2. Install `backend/requirements.txt` into a Python 3.12 environment. The database tests need Docker (testcontainers Postgres).
3. For the dialog steps, run the stack (`sudo docker compose up -d --build`) and generate the seed passwords with `python backend/seed_dev_passwords.py --apply --secrets-out PATH`. Read the passwords from that file. Do not copy them anywhere else.

## Analysis version, no change (migration 0125)

4. `cd backend && python -m pytest -q tests/test_analysis_version_no_change_0125.py` passes:
   - `test_a_save_that_writes_the_same_values_keeps_the_version_and_adds_no_snapshot`: an UPDATE with identical values leaves the version and the snapshot count unchanged.
   - `test_a_save_that_changes_only_audit_columns_keeps_the_version`: changing only the modified time or the modified-by user is no change.
   - `test_a_real_change_bumps_once_and_a_repeat_of_it_does_not_bump_again`.
   - `test_a_change_that_is_undone_in_the_same_transaction_is_no_change`.
   - `test_a_reorder_is_a_real_change_and_bumps_once_per_transaction`: a reorder of `display_order` and of `calculation_order` bumps once.
   - `test_removing_an_analyte_row_is_a_real_change`, and `test_a_calculation_configuration_edit_is_a_real_change_and_the_same_edit_again_is_not`.
   - `test_a_no_change_save_as_the_app_role_keeps_the_version`.
   - `test_0125_downgrade_restores_the_0124_behaviour_and_upgrade_the_new_one`.

## Backend suite

5. `cd backend && python -m pytest -q tests/test_calculation_activation_s8.py tests/test_calculation_activation_s8_api.py tests/test_calculation_activation_s8_db.py` passes.
6. `cd backend && python -m pytest -q tests/test_calculation_config_s7.py tests/test_calculation_config_s7_api.py tests/test_calculation_config_s7_db.py tests/test_append_only_revokes.py tests/test_configuring_agent_catalog_seed.py` still passes. The head assertions find `0126_calculation_activation`.

## Review document (CALC-REQ-45)

7. API, `test_the_review_holds_every_item_the_spec_lists`: the document holds the test cases, the system-output flags, the dry run, the diff, the plain-language description, the formula text, and every stage's four declarations.
8. `test_two_builds_at_different_times_hash_the_same` and `test_the_document_has_no_render_time_nonce_countdown_or_identity`: the hash is stable.
9. `test_the_review_hash_is_the_sha256_of_the_jcs_encoding_and_the_export_is_the_same_bytes`: the hash is the SHA-256 of the RFC 8785 encoding. The export returns the same bytes and an `X-Review-Hash` header.
10. `test_the_review_is_for_admins_only`, `test_a_review_needs_a_draft_configuration`.
11. `test_a_second_version_shows_each_changed_binding_declaration_and_formula_text`, `test_a_changed_saved_formula_version_shows_both_texts`, `test_a_version_missing_from_the_history_is_said_so`, `test_the_review_lists_formula_text_for_a_first_version`: the diff shows formula text, before and after.
12. Canonical JSON, `test_the_rfc_8785_sorting_example_orders_names_by_utf16_code_units` and `test_the_rfc_8785_string_example`: the encoder gives the RFC 8785 vectors.

## Confirm token (CALC-REQ-34)

13. `test_a_token_is_issued_for_the_hash_shown_and_stored_only_hashed`: only the SHA-256 is stored.
14. `test_a_token_is_accepted_at_300_seconds_and_refused_at_301`.
15. `test_a_token_is_single_use`, and `test_a_failed_activation_rolls_back_so_the_token_stays_unconsumed`.
16. `test_a_token_for_proposal_a_is_refused_for_proposal_b`.
17. `test_a_token_from_one_sign_in_is_refused_in_another`, `test_a_token_issued_to_one_admin_is_refused_for_another`.
18. `test_a_token_is_bound_to_the_configuration_version`, `test_a_token_is_bound_to_the_review_hash`, `test_a_review_that_changed_after_it_was_shown_gets_no_token`, `test_a_token_for_a_hash_that_was_not_shown_is_refused`.
19. `test_activation_takes_the_token_and_nothing_else`: a `password` or `reason` field is `unknown_field`.
20. Agent replay and agent context:
    - `test_an_agent_context_cannot_review_get_a_token_or_activate_even_for_the_same_admin`: HTTP 403 `agent_context_refused`.
    - `test_an_agent_replay_of_a_spent_token_is_refused`.
    - `test_the_agent_cannot_reach_an_activation_route`, `test_no_activation_route_is_on_the_agent_allow_list`, `test_no_header_or_field_sets_the_agent_context`.

## Activation (CALC-REQ-35)

21. `test_an_admin_activates_and_the_record_holds_the_review_and_the_actor`: the row holds the Admin, the time, the configuration and function versions, the lock hash, the validation state, the document, and its hash.
22. `test_only_admins_get_a_token_or_activate`: a Lab Manager is refused.
23. DB, `test_update_and_delete_of_an_activation_row_are_refused_and_leave_it_unchanged`, `test_an_activation_row_is_written_only_by_the_signed_in_admin`, `test_a_forged_actor_leaves_no_row`.
24. DB, `test_the_activation_flag_moves_a_draft_to_active_and_the_version_bumps_once`, and `test_the_activation_service_runs_as_the_app_role_against_the_real_guards`.
25. `test_an_active_configuration_cannot_be_activated_again_or_edited`, `test_activation_needs_a_configuration`.
26. DB, `test_0126_schema_shape` and `test_0126_downgrade_removes_the_tables_and_upgrade_restores_them`.

## Validation state and test cases (OQ-CALC-12)

27. `test_activation_succeeds_whatever_the_test_counts`: the state is recorded and never blocks.
28. `test_three_cases_two_passing_one_from_system_output_and_no_dry_run`: the summary reads "3 test cases, 2 passed, 1 from system output, no dry run".
29. `test_a_pass_on_another_lock_hash_does_not_count`, `test_the_latest_outcome_on_the_lock_is_the_one_that_counts`.
30. `test_the_validation_state_is_a_closed_list_without_the_word_validated` (DB) and `test_validation_state_is_a_closed_list_derived_from_the_counts`.
31. `test_the_confirm_control_names_the_no_test_case_choice`: with no test cases the label is "Activate with no test cases recorded".
32. Agent test cases: `test_the_agents_test_case_is_flagged_as_system_output`, `test_a_person_can_say_a_system_output_case_is_system_output`, `test_a_test_case_needs_the_config_permission_and_a_draft`, `test_test_case_inputs_are_checked`.

## Agent proposal (CALC-REQ-47)

33. `test_the_agent_proposes_an_inactive_draft_through_the_builder`: the draft is saved and is `draft`.
34. `test_the_agent_cannot_add_a_function_to_the_catalog`, `test_the_agent_cannot_change_the_catalog`, `test_the_agent_cannot_delete_a_configuration_or_run_one`.
35. `test_the_agent_needs_the_confirming_users_config_permission`.

## Wording (CALC-REQ-46)

36. `test_the_s8_files_use_validated_only_for_catalog_functions`, `test_s8_code_does_not_call_a_stage_output_a_result`, `test_s8_code_writes_nothing_to_result_tables`, `test_the_s8_files_hold_no_parked_constant`.

## Dialog (manual)

37. Sign in as the Admin. Open Admin, Analyses, Analyte rules for an analysis. Save a draft configuration on an analyte through the API or the configuring agent. The row's Calculation column reads "draft, version 1" and a calculator icon shows.
38. Open the review. Confirm it shows the test case summary, the dry run line, the diff, the plain-language text, the formula text, and the declarations of every stage. With no test cases, the warning reads "No test cases recorded" and the button reads "Activate with no test cases recorded". Nothing on the page calls the configuration validated.
39. Select the button. The dialog says the configuration is active, and the row reads "active, version 1".
40. Sign in as a Lab Manager. The same row shows no calculator icon. `GET .../activation-review` returns HTTP 403.
41. `cd frontend && npm test -- --watchAll=false src/__tests__/CalculationActivationDialog.test.tsx` passes, and `npx tsc --noEmit` is clean.

## Notes for the reviewer

- The Spec has no definition of a proposal id. S8 uses the analysis and analyte. Any Admin may activate any proposal.
- OQ-CALC-12 and OQ-CALC-17 are applied provisionally, as in the manual.
- Test case results and dry runs have no writer until S9. Their tests insert rows with the maintenance connection.
