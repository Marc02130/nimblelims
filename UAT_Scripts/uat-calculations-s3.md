# UAT: calculations S3, R-side catalog functions

**Scope:** CALC-REQ-8, 9, 12, 17, 24, and 37 for `fit_4pl`, `inverse_4pl`, `fit_loglog_linear`, and `inverse_loglog_linear`, each at version 1. No backend catalog function (S4), no configuration, no attempt or result write, no API route, and no screen.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** none. No citable reference values are in the repository, so the four versions have no KAT cases and stay unreleased. All tests in this pass are unit tests on synthetic curves. None is a KAT and none carries an SOP citation. See [manuals/calculation-catalog-r.md](../manuals/calculation-catalog-r.md).

## Setup

1. Check out `calculations` at the S3 commit. Docker is required.
2. From the repo root, run `bash services/r-calculator/scripts/ci-pin.sh`. It must end with `ci-pin ok`.
3. Install `backend/requirements.txt` into a Python 3.12 environment.

## R routes in the pinned image

4. In the `ci-pin.sh` output, `test_catalog.R ok` appears after `serialiser test ok`. It ran `docker run ... nimblelims-r-calculator:pin-a tests/test_catalog.R` inside the pinned image.
5. That test checks the following:
   - `fit_4pl` recovers b = 1.5, c = 0.05, d = 2.5, e = 40 from exact LL.4 data, within relative 1e-4.
   - Three levels stop with `curve_not_fitted`.
   - `model` and `code` fields, JSON numbers, `"NaN"`, a missing field, and a negative concentration are each refused with 400 `invalid_input`.
   - `/catalog/fit_5pl/v1`, `/catalog/fit_4pl/v2`, `/catalog/run`, and `/run-r` return 404.
   - `inverse_4pl` returns 30 for the response at 30.
   - A response above the top stops with `r_non_finite`.
   - The log-log fit recovers slope −0.8 and intercept 0.5.
   - An x of 0 or a y of 0 stops with `non_positive_log_input`.
   - A single point, and an overflowing inverse, stop with `r_non_finite`.
   - A slope of 0 is refused.
   - Each catalog route carries the calculation timeout hook, and `/fit` and `/svg/full` do not.
   - The route set is exactly `/health`, `/fit`, `/svg/full`, `/kat-harness/round-trip`, and the four catalog routes.
6. Run `cd services/r-calculator && Rscript tests/test_catalog.R` on host R, if host R is installed. It stops with "a host-R run of the catalog route test does not count".

## Backend gates and the R/backend split (CALC-REQ-37)

7. `cd backend && python -m pytest -q tests/test_calculation_catalog_r_s3.py` passes. The three pinned-image tests are skipped here.
8. CALC-REQ-8: `test_fit_4pl_three_levels_stops_curve_not_fitted_without_r` and `test_fit_4pl_missing_responses_can_drop_it_below_four_levels` stop with `curve_not_fitted` and make no R call. `test_fit_4pl_missing_response_is_excluded_and_counted` reports `points_excluded` `1`.
9. CALC-REQ-9: `test_inverse_4pl_past_either_end_is_qualified_with_no_r_call` returns `>` with `end` `high`, or `<` with `end` `low`, and no number. `test_inverse_4pl_at_or_beyond_an_asymptote_is_flagged_not_a_number` returns `response_at_asymptote`. `test_inverse_4pl_range_check_is_decimal_not_binary` decides in range on the decimal strings.
10. CALC-REQ-12 and 17: `test_fit_loglog_linear_non_positive_stops_before_r` stops with `non_positive_log_input` for an x, y, or replicate ≤ 0 with no R call. `test_fit_loglog_linear_drops_a_point_with_no_y_and_names_it` records the dropped point id. `test_inverse_loglog_linear_follows_the_sign_of_the_slope` checks `<` and `>` for both slope signs.
11. CALC-REQ-24: `test_fit_4pl_sends_decimal_strings_and_keeps_r_strings` sends decimal strings and keeps R's strings unchanged. `test_fit_4pl_non_finite_r_output_stops_r_non_finite` stops with `r_non_finite` for `NaN`, `Inf`, `-Inf`, `NA`, a missing value, a JSON number, and a string that is not a decimal.
12. `test_timeout_is_a_stage_stop_with_no_result` turns `r_timeout` and `backend_timeout` into stage stops. `test_gate_refusal_is_raised_not_a_stop` raises `lock_mismatch`, `sandbox`, and `missing_digest` unchanged.

## On the pinned image

13. Run `PYTHON=<that python> bash services/r-calculator/scripts/ci-catalog.sh lims-r-pin-a`. It ends with `ci-catalog ok` and no test is skipped.
14. `test_4pl_fit_and_inverse_on_the_pinned_image` fits a synthetic 4PL curve through the S1 gate, back-calculates 30, and qualifies 2.49 as `<` (low end) and 0.01 as `>` (high end) with no further R call. drc's LL.4 decreases when the slope is positive.
15. `test_loglog_fit_and_inverse_on_the_pinned_image` fits slope −0.8, back-calculates 0.2, and qualifies 0.5 as `>`.

## Release state

16. `test_no_r_side_version_has_kat_cases_yet` passes. `test_release_of_an_r_side_version_is_refused_for_an_absent_kat_run` is refused with `kat_absent` for each of the four versions, both with no run log and with an empty run log. No release record is written.

## Unchanged

17. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py tests/test_calculation_kat_s2.py tests/test_calculation_release_s2.py` still passes. `bash services/r-calculator/scripts/ci-kat.sh lims-r-pin-a` still ends with `ci-kat ok`.
18. `test_dose_response_routes_are_still_not_calculation_calls`: `POST /fit` and `POST /svg/full` are still refused as calculation calls. `R/fit.R` is unchanged, including the 5 s profiled-CI bound.

## Not in this pass

- No KAT case and no release for any of the four versions.
- No backend catalog function, configuration, attempt, or result write.
- No merge to `main`.
