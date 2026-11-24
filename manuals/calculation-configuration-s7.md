# Calculations S7: calculation configuration and the no-code builder

Calculations slice S7 stores how a value is calculated on `analysis_analytes`, and gives the builder its rules. It covers CALC-REQ-40, 23, 48, 22, 28, 50, and 46. It runs nothing. A calculation first runs in slice S9 (the stage runner). Proposing and activating a configuration is slice S8, and nothing in S7 sets a configuration to `active`.

Migration: `backend/db/migrations/versions/0124_calculation_configuration.py` (revises `0123_result_entry_data_model`). Builder rules: `backend/app/services/calculation_config.py`. Formula language: `backend/app/services/calculation_formula.py`. Storage and routes: `backend/app/services/calculation_config_service.py` and `backend/app/routers/calculation_config.py`. UAT: [UAT_Scripts/uat-calculations-s7.md](../UAT_Scripts/uat-calculations-s7.md).

Limits are not part of the calculations work (future issue #259). S7 adds no limits table, no LOQ, and no acceptance ranges. `limit_compare` takes its limit as a binding, the same as any other input.

Only the eleven catalog functions are called validated catalog functions. A formula an admin writes is not in that group.

## Analyses are versioned (CALC-REQ-40, OQ-CALC-31)

- `analyses.version` is an integer, 1 at creation. Any committed change to the analysis, to one of its `analysis_analytes` rows, or to a calculation configuration raises it by one, once per transaction.
- A save that changes nothing does not raise the version (migration 0125, slice S8). The trigger compares the new snapshot with the latest snapshot and ignores `version` and the audit columns. See [calculation-configuration-s8.md](calculation-configuration-s8.md).
- A database trigger makes the change, not the application. The application role cannot write `version` (`analysis_version_locked`). Three edits in one transaction are one version.
- `analysis_versions` keeps one snapshot per version: the analysis row and its analyte rows as they were when the transaction committed. It is how a past version, with its configuration, stays readable. The application role can read it and cannot write it.
- Existing analyses were backfilled at version 1 with a snapshot.
- A calculation attempt will record the analysis version (S9). No separate copy of formula text is stored with the attempt. The snapshot is the record.
- Reads: `GET /v1/analyses/{id}/versions` and `GET /v1/analyses/{id}/versions/{version}`. `AnalysisResponse.version` carries the current version.

## Where a configuration lives (OQ-CALC-48)

A configuration is five columns on the `analysis_analytes` row, so it is per analyte per analysis:

| Column | Meaning |
|--------|---------|
| `calculation_order` | A positive integer, unique inside the analysis. Separate from `display_order`. |
| `calculation_config_name` | The configuration's name, unique inside the analysis (case-insensitive). |
| `calculation_config_version` | Starts at 1. Rises only when the content changes. |
| `calculation_config` | The body as JSON: stages, bindings, on-fail declarations, and the result pointer. |
| `calculation_config_state` | `draft` or `active`. |

- The five are all null, or all set (`ck_analysis_analytes_calc_config_complete`). A configured row cannot have a missing order.
- The free-text `analysis_analytes.calculation` column is not the configuration. The routes never read or write it for this purpose.
- Saved formulas are in `calculation_formulas`, pinned by name and version. A row is never updated or deleted by the application role. A changed formula is a new version.

## Active is immutable (CALC-REQ-40)

- A trigger refuses a change to the configuration columns of an `active` row, and a delete of it, from the application role (`calculation_config_active`). The API refuses it first with HTTP 400 and the same code.
- The analyses routes that would drop an active configuration are also refused with `calculation_config_active`: `PUT /analyses/{id}/analytes` without the analyte, `DELETE /analyses/{id}/analytes/{analyte_id}`, and `DELETE /analyses/{id}/analyte-rules/{analyte_id}`. Other analyte-rule edits (such as `display_order`) stay possible.
- `POST /v1/analyses/{id}/new-version` (no body) is the only way back. It sets the transaction-local `lims.calculation_new_version = 'on'` and returns each active configuration on the analysis to `draft`, with its content unchanged. The response lists `drafted_analyte_ids`. HTTP 400 `no_active_configuration` when none is active.
- A configuration becomes `active` only with `lims.calculation_activate = 'on'`. No route sets it in S7. Activation is S8. Until then a new-version call leaves the analysis with drafts only.

## Routes

New routes are under `/v1`. Config writes need one of `config:edit`, `test:configure`, or `analysis:manage`. Formula writes and the formula dry run need the Administrator role.

| Method and path | Notes |
|-----------------|-------|
| `GET /v1/calculation-catalog` | The eleven catalog functions with inputs, outputs, and declared failure stops. Read-only: any write is HTTP 405. |
| `GET /v1/calculation-formulas` | Saved formulas, every version. |
| `POST /v1/calculation-formulas` | Admin. Body `{name, formula_text, description?}`. The next version for the name. The same text again is `formula_unchanged`. |
| `GET /v1/calculation-formulas/{name}/versions/{version}` | One saved version. |
| `POST /v1/calculation-formulas/evaluate` | Admin. Tries a formula with terms. Stores nothing and is not a run. |
| `GET` / `PUT` / `DELETE /v1/analyses/{id}/analytes/{analyte_id}/calculation-config` | `PUT` body is `{calculation_order, configuration}`. |
| `PATCH /v1/analyses/{id}/analytes/{analyte_id}/calculation-order` | Body `{calculation_order}`. |
| `POST /v1/analyses/{id}/new-version` | See above. |
| `GET /v1/analyses/{id}/versions` and `/versions/{version}` | Snapshots. |

There is no route that serves constants and none that runs R. R is reached only through the typed route registry from earlier slices.

Existing conventions hold. A refusal is HTTP 400 with `{"code", "message"}` and, for a configuration problem, the `stage` it names. A non-Admin who writes a formula gets HTTP 403 `formula_admin_only`. Unknown JSON fields are refused with `unknown_field`.

## The configuration JSON

```json
{
  "name": "Lead mean",
  "stages": [
    {
      "id": "cv",
      "kind": "catalog_function",
      "function": "replicate_mean_cv",
      "function_version": 1,
      "bindings": {
        "replicates": {"kind": "run_field", "entry_type": "experiment_sample_data", "field_name": "Replicates"}
      },
      "on_fail": {"outcome": "run_failed", "flag": null, "gates": [], "precedence_place": 1}
    }
  ],
  "result": {"stage": "cv", "output": "mean"}
}
```

- `kind` is `catalog_function`, `saved_formula` (`formula_name`, `formula_version`), or `ad_hoc_formula` (`formula_text`). The server sets an ad hoc formula's version: 1, and one more each time an admin changes the text.
- A catalog function is the one named in the closed catalog at the pinned `function_version`. A name outside it is `catalog_function_unknown`. There is no builder control that adds a function, and no endpoint writes the catalog.
- `result` is a pointer to the stage output that will be published as the analyte's result when the experiment is published (slice S13). Every stage output is a calculated value, not a result. The key name `result` is kept. It is required, and nothing writes to a result table before publication.
- A stage may read only earlier stages. A forward or unknown stage is `stage_order_violation`.

### Bindings (CALC-REQ-23, 50, OQ-CALC-46)

Each input is bound with one of four kinds:

| Kind | Fields | Use |
|------|--------|-----|
| `run_field` | `entry_type`, `field_name`, optional `unit_id` | A value from the run's entry data. |
| `stage_output` | `stage`, `output`, optional `unit_id` | An output of an earlier stage. |
| `reference` | `analyte_id`, `value` | The same-run value of another analyte on this analysis. That analyte must have a strictly earlier `calculation_order`. Never the analyte itself. |
| `direct` | `value` | A decimal string written into the configuration (`"5.00"`). A JSON number is refused. The one token is `limit_compare.comparison`. |

- A direct value is part of the configuration, so it is versioned with the analysis version. From S9 the calculation attempt also records it in `values_used` (OQ-CALC-46, provisional). See [calculation-configuration-s9.md](calculation-configuration-s9.md).
- There is no constants picker and no constants identifiers. The #258 constants are not a menu in S7.
- Which record a `reference` reads (replicate or average) is not decided yet (OQ-CALC-40). The S9 runner reads it only when the Test has exactly one row for that analyte, and stops with `reference_ambiguous` otherwise.
- A formula term is bound by name. Bare names and `[bracketed names]` are terms. A formula term binding may not carry a `unit_id`.

### Units (CALC-REQ-28)

- Inputs in one unit group must share one unit. A `1` input takes only a dimensionless unit. A `%` input is a percentage. Token, identity, and count inputs take no unit.
- A stage's output unit carries to the stages that read it. A mismatch is `unit_binding_mismatch`, naming the stage.
- `convert_units` unit names are not modelled in S7.

## On-fail declarations (CALC-REQ-48)

Every stage declares what its failure does. All four keys must be present: `outcome`, `flag` (may be null), `gates` (later stage ids), and `precedence_place`.

| Outcome | Meaning |
|---------|---------|
| `run_failed` | The run fails. |
| `dilution_invalid` | The dilution is marked invalid. |
| `sample_verdict` | The sample takes the `verdict` label. `verdict` is required for this outcome only. |
| `flag` | The calculated value carries the named flag. |

- `pass` is refused (`on_fail_pass_refused`). `on_fail_undeclared` is not something a user declares.
- A stage whose failure is a stage stop declares that stop code, with `precedence_place` `above_list`. A stage that cannot stop in that way may not (`on_fail_stage_stop_not_applicable`).
- `limit_compare` stages also declare `missing_limit_flag`. Other stages may not.
- Two stages cannot claim the same numbered place for different outcomes (`precedence_place_conflict`). Gaps in the numbering are allowed.
- Which stop each catalog function can raise is in `FAILURE_STOPS`: `fit_4pl` (`curve_not_fitted`, `r_non_finite`, `r_timeout`), `inverse_4pl` (`r_non_finite`, `r_timeout`), `fit_loglog_linear` and `inverse_loglog_linear` (`non_positive_log_input`, `r_non_finite`, `r_timeout`).

## Calculation order (OQ-CALC-35)

- `calculation_order` is a positive integer with no default, unique inside the analysis.
- A `reference` must point at a smaller order. A forward read, a cycle, or the analyte itself is `calculation_order_violation`. An order change is checked against every analyte that reads it.
- A duplicate order is `calculation_order_duplicate`. A missing, zero, negative, fractional, or non-integer order is `calculation_order_required` or `calculation_order_invalid`.
- A configuration that another analyte reads cannot be deleted (`configuration_in_use`).

## Formulas (CALC-REQ-23, OQ-CALC-52)

- Only an Administrator writes a formula, saved or ad hoc. Anyone with the Admin role counts as a lab admin. A non-Admin may save a catalog-only configuration, and may edit a configuration that holds an unchanged formula stage, but a new or changed formula stage is `formula_admin_only` (HTTP 403).
- Formulas are parsed to a syntax tree and evaluated in decimal arithmetic (precision 50, round half to even). Nothing is evaluated as code.
- Formulas reference results by name. There are no cell ranges: `A1:A3` is `formula_range_not_supported`. `{a, b, c}` is a list of arguments, not a range.
- Operators: `+ - * / ^`, comparisons, parentheses. Unary minus binds tighter than `^`, and `^` is left-associative, as in Excel.
- Functions: `AVERAGE`, `SUM`, `MIN`, `MAX`, `COUNT`, `STDEV` (n - 1), `STDEV.P` (n), `ABS`, `ROUND`, `SQRT`, `LOG10`, `LN`, `EXP`, `POWER`, `IF`, `AND`, `OR`, `NOT`, `LOOKUP`, `LINEST`, `FORECAST`, `TREND`. A formula result must be a single number.
- A missing value is `#N/A`. A knocked-out input is also `#N/A`. Errors are `#DIV/0!`, `#VALUE!`, `#N/A`, and `#NUM!`.
- A formula error stops that calculation and shows the Excel error text. In an experiment every calculation still runs, and the ones that error stay blank.
- The dry run (`POST /v1/calculation-formulas/evaluate`) returns HTTP 200 with `{value, error, detail}`. A term is a decimal string, `null`, or `{"knocked_out": true}`.
- Limits on a formula: 2000 characters, depth 32, 500 nodes, 100 items in a list.

## Not in S7

- No run, no stage runner, no attempt, and no recompute (S9).
- No proposal, activation, or review by the configuring agent (S8). No route sets `lims.calculation_activate`.
- No screen.
- No limits table, LOQ, or acceptance ranges (#259).
- No generic "run R" endpoint.
