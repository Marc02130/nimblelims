# Calculations S8: proposing and activating a calculation configuration

Calculations slice S8 lets the configuring agent propose a calculation configuration, and lets an Admin activate it after reviewing it. It covers CALC-REQ-47, 34, 35, 45, and 46. It runs nothing. The stage runner and the first write of a calculated value are slice S9. Nothing in S8 writes to a result table.

Migrations: `backend/db/migrations/versions/0125_analysis_version_no_change.py` (revises `0124_calculation_configuration`) and `0126_calculation_activation.py` (revises 0125). Review document and diff: `backend/app/services/calculation_review.py`. Token, activation, and test cases: `backend/app/services/calculation_activation.py`. Canonical JSON: `backend/app/services/jcs.py`. Routes: `backend/app/routers/calculation_config.py`. Dialog: `frontend/src/components/analyses/CalculationActivationDialog.tsx`. UAT: [UAT_Scripts/uat-calculations-s8.md](../UAT_Scripts/uat-calculations-s8.md). Builder and storage: [calculation-configuration-s7.md](calculation-configuration-s7.md).

Limits are not part of the calculations work (future issue #259). S8 reads no limit table. A stage that reads a limit is marked in the review so the Admin sees it.

Only the eleven catalog functions are called validated catalog functions. Nothing else is labelled that way. The validation state below is a record of test counts, not a gate.

## Terms

- A **calculated value** is what a stage outputs. It is not a result.
- A calculated value becomes a **result** only when the experiment is published (slice S13).
- The configuration's `result` pointer (`{stage, output}`) names which stage output will be published as the analyte's result. Choosing it writes nothing.

## What the agent can do

- The agent saves a configuration as a draft: `PUT /v1/analyses/{analysis_id}/analytes/{analyte_id}/calculation-config`. It goes through the same builder rules as a person. A draft is never active.
- The agent records a test case for the draft: `POST .../calculation-config/test-cases`.
- The agent cannot add or change a catalog function. It cannot delete a configuration or run one. There is no run-R endpoint.
- The agent cannot reach the review, the token, the activation, or the activation list. The configuring-agent allow-list leaves them out, and the services refuse a call made inside an agent run (HTTP 403 `agent_context_refused`). The agent has no way to obtain or send a confirm token.
- A test case the agent records always has `expected_source` `system_output`. If it asks for `independent`, the answer is `agent_expected_source`.

The agent is allowed these two routes only when the confirming user has the `config:edit` permission.

## Test cases

`POST /v1/analyses/{analysis_id}/analytes/{analyte_id}/calculation-config/test-cases`, body `{name, inputs, expected, expected_source}`:

- A test case belongs to one configuration version. A new version starts with none.
- `expected_source` is `independent` (the expected value came from outside the system) or `system_output` (it was copied from what the system calculated). A person must say which. It is `expected_source_required` if missing.
- Inputs and expected values are JSON objects. A decimal is a string. A float is refused (`test_case_number_invalid`).
- A name is unique in a version (`test_case_name_exists`). An active configuration takes no new test case (`calculation_config_active`).
- Test cases cannot be edited or deleted. A test case has no run in S8. Running one is slice S9, so every case reads "Not run" until then.

`GET .../test-cases?version=N` lists them.

## The review document (CALC-REQ-45)

`GET .../calculation-config/activation-review` (Admin only) returns `{document, review_hash}`. The dialog renders only from the document. It holds:

- the analysis, the analyte, the configuration name, version, and calculation order;
- the calculator lock hash and the catalog function versions the configuration uses;
- the validation state, and the test cases with the summary text, for example "3 test cases, 2 passed, 1 from system output, no dry run";
- a notice, "No test cases recorded", when there are none, and a confirm label "Activate with no test cases recorded" in that case;
- the dry run (done or not, when, and the input);
- the diff from the previous version;
- the plain-language description of each stage and of the result pointer;
- the formula text of every saved and ad hoc formula stage;
- the four declarations of every stage (outcome and verdict, flag, missing limit flag, gates and precedence place), and whether it reads a limit.

The document has no timestamp of its own, no countdown, and no identity of the reader, so two builds of the same configuration give the same hash. `GET .../activation-review/export` returns the same canonical bytes, with the hash in the `X-Review-Hash` header.

### Validation state (OQ-CALC-12, decided provisionally)

| Value | When |
|-------|------|
| `no_test_cases` | No test case is recorded for this version. |
| `tests_none_passed` | Cases are recorded and none passed on the current calculator lock. |
| `tests_some_passed` | Some passed. |
| `tests_all_passed` | All passed. |

"Passed" counts only the latest outcome of a case on the current calculator lock. A pass on another lock does not count. The state is recorded with the activation. It never blocks one.

### The diff

The diff compares this version with configuration version N-1 as it stands in the analysis version history. It lists, per stage, each change in a binding, an on-fail declaration, a function version, formula text, a saved formula's name, version, and text, added and removed stages, the calculation order, the name, and the result pointer. Formula text is shown in full, before and after. For a first version it says "no previous version". If version N-1 is not in the history it says so.

## Activating (CALC-REQ-34, 35)

1. `POST .../calculation-config/activation-token` with `{review_hash}` (Admin only). The hash must be the one the review returned now. If the configuration changed since, the answer is `review_changed`. The response is `{confirm_token, review_hash, expires_in_seconds: 300}`. The token is shown once.
2. `POST .../calculation-config/activate` with `{confirm_token}` and nothing else. Any other field, including a password or a reason, is refused (`unknown_field`). Self-activation is allowed.

A token is:

- random, with only its SHA-256 stored;
- single use, consumed in the activation transaction (a failed activation rolls back and leaves it unconsumed);
- bound to the user, the proposal (analysis and analyte), the configuration version, the review hash, and the sign-in (`jti`);
- valid for 300 seconds on the database clock, accepted at 300 and refused at 301.

Refusals: `confirm_token_required`, `confirm_token_invalid`, `confirm_token_wrong_user`, `confirm_token_wrong_proposal`, `confirm_token_wrong_session`, `confirm_token_version_changed`, `confirm_token_review_changed`, `confirm_token_used`, `confirm_token_expired`, `already_active`, `configuration_missing`, `configuration_not_draft`. The review is rebuilt at activation and must hash to the bound value.

A Lab Manager and every non-Admin role is refused. Anyone with the Admin role is a lab admin for formulas.

### The activation record

Each activation writes one row in `calculation_activations`: the Admin, the time, the configuration name and version, the function versions, the lock hash, the validation state, the review document, and its hash. `GET .../activations` lists them. The application role can insert a row only as the signed-in Admin, and cannot update or delete one (`calculation_activation_append_only`).

## The dialog

An Admin sees a calculator icon on a draft row in Admin, Analyses, Analyte rules. It opens the review. The confirm button carries the label from the document. The dialog asks for the token for the hash it shows, then activates. On a refusal it shows the message and stays open. A non-Admin does not see the icon.

## Analysis versions no longer rise for a save with no change (migration 0125)

The deferred trigger now compares the new snapshot with the latest `analysis_versions` snapshot, ignoring `version`, `created_at`, `created_by`, `modified_at`, and `modified_by`. When they match there is no new version and no new snapshot. A reorder of analytes, a change of a configuration, and the removal of an analyte are real changes. A transaction that changes something and changes it back is no change. Several real changes in one transaction are one version.

## Provisional choices

- The Spec does not define a proposal id. S8 uses the analysis and analyte of the draft configuration. Any Admin may activate any proposal. The proposer is not stored.
- OQ-CALC-12 (the validation state values) and OQ-CALC-17 (no password re-entry) are applied as above and are provisional until the open-questions log records them.
- Test cases are stored per configuration version. Where results and dry runs come from is slice S9, so S8 has tables for them and no writer.
- Issuing a new token does not cancel an earlier token that is still within its 300 seconds.
