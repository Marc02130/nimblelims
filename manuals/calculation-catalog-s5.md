# Backend decimal catalog functions (S5)

The last three backend catalog functions: `replicate_mean_cv`, `spike_recovery`, and `limit_compare`, each at version 1. With the four R-side functions (S3) and the four earlier backend functions (S4), the catalog is the eleven functions in CALC-REQ-22. This page is the developer view of CALC-REQ-14, CALC-REQ-18, CALC-REQ-19, CALC-REQ-37, and CALC-REQ-22. It builds on the S2 harness ([calculation-kats.md](calculation-kats.md)) and the S4 decimal functions ([calculation-catalog-decimal.md](calculation-catalog-decimal.md)).

**Release state:** all three versions are declared, have KATs, and are **not released**. S5 does not call `write_release`. A later slice chooses where the release record is committed. The four R-side versions still have no KAT cases, so they are still not releasable.

Nothing in S5 writes an attempt or a result, reads a configuration, or adds a screen. The three routes below are a status-code contract for tests. They are not mounted on the LIMS app. The stage runner is S9. None of the three has an R route (CALC-REQ-24).

Marc's decisions for this slice (2026-11-17) are implemented here. The Spec was not edited.

## Where it lives

| Piece | File |
|-------|------|
| Functions, KAT cases, declarations, HTTP contract | `backend/app/services/calculation_catalog_s5.py` |
| The eleven-function list | `backend/app/services/calculation_catalog.py` |
| Pass/fail KAT match (empty unit) and token inputs | `backend/app/services/calculation_kat.py` |
| Unit tests and the KAT run | `backend/tests/test_calculation_catalog_s5.py` |

## Decimal context (CALC-REQ-37)

Every arithmetic step runs in Python `decimal` with precision 50 and `ROUND_HALF_EVEN`. `sqrt` uses that context. Products are computed first and there is one division last. Numeric inputs are decimal strings. A JSON number or a boolean is refused with `invalid_input`. A non-decimal string such as `N/A` or `""` is missing data, not a refusal, except a string that starts with `<` or `>` and is not a well-formed qualified value: that string is refused on `limit_compare`.

Arithmetic outputs are plain decimal strings. Trailing zeros in the coefficient are stripped. A result of zero is written `0`.

## HTTP status

| Outcome | Status | Body |
|---------|--------|------|
| A number or a verdict was computed | 200 | `outputs` holds strings. `r_called` is false. |
| `missing_input` | 200 | `outputs` is empty. `flags` is `["missing_input"]`. |
| A flag with or without a partial output (`replicate_missing`, `mean_zero`, `limit_above_el`, `limit_below_el`) | 200 | `flags`, and `outputs` when a number or nothing was stored. Not a `stop`. |
| No verdict and no flag (`missing_limit`, `unspecified`) | 200 | `outputs` is empty. `no_verdict` names the reason. `no_verdict` is not a review flag. |
| Refusal | 400 | `{"code": "invalid_input", "detail": "..."}` |

`missing_input` is neither a stop nor a refusal. A missing input is never replaced with zero.

## Decisions

- **OQ-CALC-5.** %CV uses the sample standard deviation: the sum of squared deviations is divided by n−1, then `sqrt`. That is Excel STDEV. The function does not read a unit. Onset times in seconds and concentrations both go through this one function. Which of those a LAL configuration binds is still open. This slice does not choose it.
- **OQ-CALC-6.** Recovery % = (spiked − unspiked) × 100 ÷ nominal spike. Confirmed. The nominal spike is an input. `0.05` is not in the function.
- **OQ-51, clarified.** There are two fields: the calculated result (the numeric value) and the reported result (the qualified text, such as `>100`). The formula chooses which one a step receives, and how `>100` is reported. `limit_compare` does not choose and does not format a reported result. It compares the one value the caller passes. A decimal string is the numeric feed. A qualified value is the reported feed. CALC-REQ-19's at-most rules for `<` and `>` are implemented as written. No conflict was found that would drop those rules: they judge a qualified value when that is what was passed, and they do not say this function writes the reported text. The earlier note that said never to pass or fail `>100` is replaced by this clarification.

## Functions

### `replicate_mean_cv` v1

`replicate_mean_cv(replicates)`. `replicates` is an array. The Spec does not name the field.

- Mean = sum ÷ n.
- %CV = (sample standard deviation × 100) ÷ mean. One division for the variance (by n−1), `sqrt`, then one division for the percent.
- No numeric replicate, including `null`, `[]`, or an array of only non-numeric strings, is `missing_input` and stores nothing.
- One numeric replicate stores the mean, stores no %CV, and sets `replicate_missing`. The Spec's phrase is "replicate missing". The code uses the same snake_case shape as `missing_input`. A non-numeric neighbour (`N/A`, `null`, a qualified string) is left out and is not zero. What the lab does with that flag (a missing tube, a split duplicate) stays OQ-CALC-8.
- A mean of 0, with two or more numeric replicates, stores `0`, stores no %CV, and sets `mean_zero`. The Spec says "a flag" and does not name it. This is not a stage stop: the mean stays. One replicate of `0` is `replicate_missing`, not `mean_zero`.
- A negative mean is stored, and the %CV is negative. The Spec does not refuse it.
- A JSON number, a boolean, or a bare string (not an array) is refused.
- The function has no unit parameter. The same code accepts onset times and concentrations.

KATs, absolute tolerance 0. Citations are hand arithmetic, not SOP citations.

- `replicate-mean-1400.1-1400.3`: mean `1400.2`. The %CV string is the precision-50 sample %CV, recorded outside the function. These two numbers are also valid onset times in s.
- `replicate-onset-time-100s-110s`: onset times 100 s and 110 s. Mean `105`. %CV is the precision-50 sample value. This is the CALC-REQ-14 pair 100 and 110.
- `replicate-concentration-0.01-0.02-0.03`: concentrations. Mean `0.02`, %CV `50`. Dividing by n instead of n−1 would not give 50.

Unit tests also run 480 s and 520 s, and 10 s, 20 s, and 30 s, through the public function, and the concentration triple through the public function as well as the KAT.

### `spike_recovery` v1

`spike_recovery(spiked, unspiked, nominal_spike)`. The Spec does not name the fields. `nominal_spike` is the nominal spike (Marc's "amount spiked"). All three are decimal strings in one shared unit. The output is recovery in `%`.

- The product `(spiked − unspiked) × 100` is formed first. One division by the nominal spike is last.
- No spiked value, no unspiked value, or no nominal spike is `missing_input`. The Spec names only the missing spiked value. The other two use the same rule so nothing is imputed.
- A qualified string such as `<0.01` or `>0.06` is not a decimal, so it is `missing_input`. OQ-CALC-7 (how a not-detected unspiked value enters) stays open. This function does not interpret the qualifier.
- A nominal spike that is not greater than 0 is refused, including when the other inputs are missing. The Spec does not say what a zero nominal does. Dividing by it is not a number.
- A recovery of 0 is stored as `0`. A negative recovery is stored. Neither stops.
- There is no default nominal. `0.05` appears only as a KAT input.

KATs, absolute tolerance 0, from the Spec examples (not assay rules):

- `0.06`, `0.01`, `0.05` → `100`
- `0.026`, `0.001`, `0.05` → `50`
- `0.171`, `0.071`, `0.05` → `200`

The binary value of `(0.171 - 0.071) * 100 / 0.05` is not 200. The decimal result is `200`. The calls make no R call.

### `limit_compare` v1

`limit_compare(value, *, comparison, limit=None, low=None, high=None, absolute=False, kind=None)`.

`comparison` is `at_most`, `at_least`, or `within`. The Spec does not name that field. There is no default. Any other comparison is refused.

The value is whichever field the formula binds:

- A decimal string is a numeric value (a calculated result, if that is what the formula bound).
- `<` or `>` immediately followed by a decimal string, or an object `{"qualifier", "limit", "kind"}`, is a qualified value (a reported result such as `>100`, if that is what the formula bound).

The function never sees both fields. It does not write `calculated` or `reported`.

Numeric rules, with no rounding before the compare:

- `at_most`: value ≤ limit passes.
- `at_least`: value ≥ limit passes.
- `within`: low ≤ value ≤ high passes. A low bound above the high bound is refused, including when the value is missing.
- `absolute` true compares `|value|` and leaves the bound as given. It is a JSON boolean. Absent means false. It applies only to a numeric value. Setting it on a qualified value is refused. The Spec does not say what absolute means for a qualified value.

Qualified rules, at most only (CALC-REQ-19):

- Stored `<` with limit L: L ≤ bound passes. L > bound gives no verdict and `limit_above_el`.
- Stored `>` with limit U: U ≥ bound fails. U < bound gives no verdict and `limit_below_el`.
- Every stored `>` uses that rule. The function does not take a separate "end" and does not distinguish an above-curve `>` from another high-cutoff `>`.
- A kind supplied with the qualified value is returned on pass, fail, and no verdict. Two `<` kinds with the same limit both pass and come back as those two kinds. The Spec says the second kind stays stored as that kind. The response field is `kind`. It is not a new flag.
- The qualifier symbol and the limit text are echoed as `qualifier` and `qualifier_limit` so the stored form is not rewritten. `>100` stays the text `100` after `>`. The verdict, when there is one, is still `pass` or `fail`.

Where the Spec does not give a qualified rule:

- A qualified value on `at_least` or `within` returns no verdict, no flag, and `no_verdict` `unspecified`. The at-most rules are not copied onto those forms. `unspecified` is not a review flag.
- No value is `missing_input` (HTTP 200, empty outputs). No bound for the form is `no_verdict` `missing_limit`, with no flag. The stage declaration names the missing-limit flag (CALC-REQ-48). This function does not emit `el_missing`. A missing value wins over a missing bound. A qualified value with a missing bound is still echoed.

A pass/fail output has no unit (CALC-REQ-28). The catalog unit string is empty. The KAT harness matches `pass` and `fail` exactly, with absolute tolerance 0 and that empty unit. A comparison form is a token input, not a decimal. Qualified values are not KAT inputs, because the harness value for `value` is a decimal string. Those cases are unit tests, the same way S4 tests within-type conversion outside the KAT.

KATs, absolute tolerance 0:

- `0.5` at most `0.5` passes. `0.6` at most `0.5` fails. The unused low and high on those cases are `0` and `1`, so a within-compare of `0.6` would have passed.
- `|-0.98|` at least `0.980` passes. `|-0.97995|` at least `0.980` fails.
- `50` and `200` within `50`–`200` pass. `49` fails. The unused limit on the `49` case is `1000`, so an at-most compare would have passed.

## The closed catalog (CALC-REQ-22)

`closed_catalog()` returns exactly these eleven names, in this order: `fit_4pl`, `inverse_4pl`, `fit_loglog_linear`, `inverse_loglog_linear`, `replicate_mean_cv`, `spike_recovery`, `limit_compare`, `apply_dilution`, `convert_units`, `subtract`, `copy_raw`.

No name starts with `elisa_` or `lal_`. The list is a tuple in code. The module has no register or add function. The LIMS app does not import it. There is no catalog table. A route, a screen, a database write, a runtime flag, or an agent cannot add an entry, because none of those paths exist. A new entry is a change to this code.

The four R-side versions still have empty KAT lists. CALC-REQ-5 says every catalog function has a KAT. S5 does not backfill the R-side cases.

## KATs and the fingerprint

`run_kats` on the three versions runs 13 cases. Each uses absolute tolerance 0. Backend cases make no HTTP call. `prepare_release("s5-decimal-v1")` succeeds in memory against that run. Nothing writes the file.

`version_fingerprint` hashes the declaration and the source of `compute`. The public functions are what the HTTP routes call. `replicate_mean_cv` and `spike_recovery` call `compute` for the success path. `limit_compare` calls `numeric_verdict` for a numeric value. The KAT `compute` calls that same function. The qualified rules live on the public function, which is why they are unit tests rather than harness cases.

## Not in this slice

- Which quantity a LAL configuration's %CV uses (onset time or concentration). The function accepts either binding.
- How a qualified unspiked value is turned into a decimal before `spike_recovery` (OQ-CALC-7).
- What the lab does with `replicate_missing` (OQ-CALC-8).
- A formula that chooses calculated versus reported, and anything that writes those two fields (S7, S9).
- The stage's missing-limit flag name, including `el_missing`.
- R-side KATs, a committed release record, an attempt, or a result write.
- S6.
