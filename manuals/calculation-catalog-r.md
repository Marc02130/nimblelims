# R-side catalog functions (S3)

The four R-side catalog functions: `fit_4pl`, `inverse_4pl`, `fit_loglog_linear`, and `inverse_loglog_linear`, each at version 1. This page is the developer view of CALC-REQ-8, CALC-REQ-9, CALC-REQ-12, CALC-REQ-17, CALC-REQ-24, and CALC-REQ-37. It builds on the S1 pin ([r-calculator-pin.md](r-calculator-pin.md)) and the S2 harness ([calculation-kats.md](calculation-kats.md)).

**Release state:** all four versions are declared and **not released**. They have no KAT cases, because no citable reference values are in the repository (CALC-REQ-6, OQ-CALC-13). The S2 release check refuses each of them with `kat_absent`. Synthetic data, including the instrument CSVs under `UAT_Scripts/instrument-exports/` and `backend/tests/fixtures/elisa/`, is not a citable source and is not used for KATs.

Nothing in S3 writes an attempt or a result, reads a configuration, or adds an API route or a screen. Backend catalog functions are S4.

## Where it lives

| Piece | File |
|-------|------|
| R routes, one per function version | `services/r-calculator/R/catalog.R`, registered in `services/r-calculator/plumber.R` |
| Backend gates, R calls, and declarations | `backend/app/services/calculation_catalog_r.py` |
| R route unit tests, in the image only | `services/r-calculator/tests/test_catalog.R`, run by `ci-pin.sh` |
| Backend unit tests (stub R, plus pinned-image tests) | `backend/tests/test_calculation_catalog_r_s3.py` |
| CI step for the pinned-image tests | `services/r-calculator/scripts/ci-catalog.sh`, after `ci-kat.sh` |

None of the tests is a KAT, and none carries an SOP citation. They use synthetic curves generated from known parameters.

## The R/backend split (CALC-REQ-37)

The backend runs every gate first, in Python `decimal`, on the decimal strings it was given:

- missing data
- the four-level count for `fit_4pl`
- the in-range check before each inversion
- the non-positive check before any log

An outcome a gate decides (a stop, a qualified `<` or `>`, or `missing_input`) makes no R call. `StageResult.r_called` records whether R was called.

R does only the fit or the inversion. Each call goes through `RCalculatorClient.execute_calculation_request`, so it passes the S1 lock, image digest, and sandbox gate every time. A refusal there (`lock_mismatch`, `missing_digest`, `sandbox`, `r_service`) is raised unchanged. A timeout (`r_timeout`, `backend_timeout`) becomes a stage stop with that code.

## Round-trip strings and `r_non_finite`

Inputs to R are decimal strings in the JSON number grammar, for example `"0.026"` or `"1.5e-3"`. R reads each one with the C library `strtod` (through `jsonlite`), which is correctly rounded. A JSON number, `"NaN"`, `"Inf"`, an unknown field (for example `model` or `code`), or a missing field is refused with HTTP 400 and code `invalid_input`. Nothing falls back to a default model. A path that is not one of the four routes, for example `/catalog/fit_5pl/v1` or `/catalog/fit_4pl/v2`, returns 404.

R returns each output as its shortest round-trip string (`shortest_round_trip()` in `R/serialise.R`). The backend keeps that string unchanged as the unrounded value.

A NaN, Inf, -Inf, or NA output stops the stage with `r_non_finite`, in R before serialising and again in the backend for any output that is not a finite decimal string. That includes a JSON number or a missing key. The stop returns no number and is never mapped to a qualifier, a zero, or a verdict.

A stage stop from R is HTTP 200 with `{"stop": "<code>", "detail": "..."}`. A stop code that the function version does not declare is refused as `r_service`.

## Functions

All four are called from the backend as Python functions taking an `r_client` (an `RCalculatorClient`). Each returns a `StageResult` with `outputs` (decimal strings), `r_called`, `stop`, `detail`, `qualifier`, `end`, `flags`, and `dropped`.

### `fit_4pl` v1: `POST /catalog/fit_4pl/v1`

`fit_4pl(points, r_client)`. Each point has `concentration`, `response`, and `replicate`.

- A replicate with no numeric response is excluded and counted in `points_excluded`. It is never treated as zero.
- Fewer than four concentration levels with a numeric response stops with `curve_not_fitted`, and R is not called.
- A negative concentration is refused.
- R fits drc `LL.4`: response = c + (d − c) / (1 + exp(b (ln x − ln e))). It uses ordinary least squares with no weights and no parameter bounds.
- Outputs are `bottom` (c), `top` (d), `slope` (b), `inflection` (e), and `r_squared` = 1 − SS_res / SS_tot, plus `points_used` and `points_excluded`.
- A fit that does not converge stops with `curve_not_fitted`.

R body: `{"concentration": [...], "response": [...]}`.

### `inverse_4pl` v1: `POST /catalog/inverse_4pl/v1`

`inverse_4pl(curve, response, low_calibrator_mean_response, high_calibrator_mean_response, r_client)`.

- No numeric response gives no concentration and the flag `missing_input`.
- The curve's direction comes from the two calibrator means. A response past the high-concentration calibrator's mean returns qualifier `>` with `end` `high`. A response past the low-concentration calibrator's mean returns qualifier `<` with `end` `low`. Neither stores a number or calls R, so the function never extrapolates.
- A response equal to an end mean is in range.
- A response that is in range but not strictly between `bottom` and `top` has no inverse. It is flagged `response_at_asymptote` and is not given a number.
- Otherwise R computes x = e · ((d − c) / (y − c) − 1)^(1/b).
- A slope of 0, or equal low and high means, is refused.

R body: `{"bottom", "top", "slope", "inflection", "response"}`.

### `fit_loglog_linear` v1: `POST /catalog/fit_loglog_linear/v1`

`fit_loglog_linear(points, r_client)`. Each point has `x`, `y` (a mean, or no value), `point_id`, and optionally `replicates`, the values that entered that mean.

- An x ≤ 0, a y ≤ 0, or a replicate ≤ 0 stops with `non_positive_log_input`. Nothing reaches `log10`.
- A point with no y is dropped, and its `point_id` is recorded in `dropped`.
- If no point has a y, there is no fit and the flag is `missing_input`.
- R fits `lm(log10(y) ~ log10(x))`. Outputs are `slope`, `intercept`, and `r`, the Pearson correlation of log10 x and log10 y. They come with `points_used` and `points_dropped`.
- A single point gives an undefined slope and stops with `r_non_finite`.

R body: `{"x": [...], "y": [...]}`.

### `inverse_loglog_linear` v1: `POST /catalog/inverse_loglog_linear/v1`

`inverse_loglog_linear(fit, y, lowest_x_mean_y, highest_x_mean_y, r_client)`.

- No y gives the flag `missing_input`.
- An endpoint mean ≤ 0 stops with `non_positive_log_input`.
- With a negative slope, a y below the highest-x mean returns `>` and a y above the lowest-x mean returns `<`.
- With a positive slope, a y above the highest-x mean returns `>` and a y below the lowest-x mean returns `<`.
- Neither qualified case calls R.
- Otherwise R computes x = 10^((log10 y − intercept) / slope). An overflow stops with `r_non_finite`.
- A slope of 0, or endpoint means whose order does not match the sign of the slope, is refused.

R body: `{"slope", "intercept", "y"}`.

The kind name, label, and limit number of a qualified result, and the dilute-and-rerun prompt, come from configuration and the UI in later slices. S3 returns only the qualifier and the end.

## Timeouts

The S1 calculation timeout hook is installed on each catalog route, and the route tests check this. `POST /fit` and `POST /svg/full` keep their own behaviour, including the 5-second profiled CI bound in `R/fit.R`.

## Running the tests

```bash
bash services/r-calculator/scripts/ci-pin.sh            # includes tests/test_catalog.R in the image
PYTHON=<python with backend/requirements.txt> \
  bash services/r-calculator/scripts/ci-catalog.sh lims-r-pin-a
```

`ci-catalog.sh` runs `tests/test_calculation_catalog_r_s3.py` with `KAT_R_CALCULATOR_URL` set to the pinned container. It fails if any pinned-image test is skipped. Without that variable, as in the plain backend test job, the pinned-image tests are skipped and the stub-R tests run.

## Source material needed before release

Each version needs at least one cited KAT case before the release check accepts it. Expected values come from the SOP when it has them (OQ-CALC-13). The following is not in the repository:

- `fit_4pl`: a published or independently computed 4PL calibrator set, with its four parameters, the unit, and a stated tolerance.
- `inverse_4pl`: a published back-calculation example, from a response to a concentration on stated 4PL parameters.
- `fit_loglog_linear`: a worked log-log standard set with a known slope, intercept, and r. One example would be the STE-1.2 section 8 worked example; the STE-1.2 PDF is not in the repository.
- `inverse_loglog_linear`: a worked inversion example on a stated log-log fit.

The S2 harness passes scalar inputs only. A real fit KAT needs array inputs, so adding these cases will need a small harness change at that point.
