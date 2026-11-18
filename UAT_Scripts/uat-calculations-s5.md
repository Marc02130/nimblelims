# UAT: calculations S5, replicate mean, spike recovery, and limit compare

**Scope:** CALC-REQ-14, 18, 19, 37, and 22 for `replicate_mean_cv`, `spike_recovery`, and `limit_compare`, each at version 1. No R call, no R route, no configuration, no attempt or result write, and no screen. S6 is not in this pass.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** 13 cases, absolute tolerance 0. Citations are hand arithmetic recorded with the case, not SOP text. See [manuals/calculation-catalog-s5.md](../manuals/calculation-catalog-s5.md).

## Setup

1. Check out `calculations` at the S5 commit.
2. Install `backend/requirements.txt` into a Python 3.12 environment. These tests do not need Docker.

## Backend suite

3. `cd backend && python -m pytest -q tests/test_calculation_catalog_s5.py` passes.
4. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py tests/test_calculation_kat_s2.py tests/test_calculation_release_s2.py tests/test_calculation_catalog_r_s3.py tests/test_calculation_catalog_decimal_s4.py` still passes. The live R-image cases skip unless `KAT_R_CALCULATOR_URL` is set. The S4 migration test needs Docker.

## Sample %CV, onset time, and concentration (CALC-REQ-14)

5. `test_kats_pass_at_tolerance_zero_and_do_not_call_r` runs 13 cases through `run_kats`. Every case passes, `r_called` is false, and the observed strings are exact:
   - `1400.1` and `1400.3`: mean `1400.2`.
   - Onset times `100` s and `110` s: mean `105`, and the recorded sample %CV.
   - Concentrations `0.01`, `0.02`, and `0.03`: mean `0.02`, %CV `50`.
6. `test_cv_uses_sample_standard_deviation_not_population`: replicates `1`, `2`, and `3` give mean `2` and %CV `50`. The population standard deviation does not give 50. This is divide-by-n−1 (Marc, 2026-11-17, Excel STDEV).
7. `test_onset_times_in_seconds_use_the_same_function`: `100`/`110`, `480`/`520`, and `10`/`20`/`30` seconds. The function takes no unit argument and the compute source does not mention onset, concentration, or seconds.
8. `test_concentration_replicates_use_the_same_function`: the concentration triple, and `0.026` with `0.028` whose mean is `0.027`. Which of onset time or concentration a LAL configuration binds is still open. Both inputs work.
9. One numeric replicate stores the mean, no %CV, and `replicate_missing`. A neighbour `N/A` or `null` is left out, not treated as zero. No numeric replicate (`null`, `[]`, only `N/A`, only `>100` / `<0.1`) is HTTP 200 `missing_input` with empty outputs.
10. Two replicates whose mean is 0 (`1` and `-1`, or `0` and `0`) store mean `0`, no %CV, and `mean_zero`. That is HTTP 200 and not a stop. A single `0` is `replicate_missing`, not `mean_zero`. The Spec says "a flag" and does not name `mean_zero`.
11. Equal replicates store %CV `0`. A negative mean is stored and the %CV is negative. A JSON number or a bare string is refused with `invalid_input`.

## Spike recovery (CALC-REQ-18)

12. The three Spec examples are exact: `0.06`, `0.01`, `0.05` → `100`; `0.026`, `0.001`, `0.05` → `50`; `0.171`, `0.071`, `0.05` → `200`. The binary expression for the third is not 200.
13. `test_spike_does_not_hardcode_the_nominal`: the function source has no `0.05`. Spiked `2`, unspiked `1`, nominal `4` gives `25`.
14. A missing spiked, unspiked, or nominal value, including a qualified string, is `missing_input` and is not replaced with zero. OQ-CALC-7 stays open: this function does not interpret a qualified unspiked value.
15. A nominal of `0`, `0.0`, or a negative nominal is HTTP 400 `invalid_input`, including when the other inputs are missing. A recovery of 0 is the string `0`. A negative recovery is stored.

## Limit compare (CALC-REQ-19)

16. `test_limit_compare_uses_the_value_it_is_fed`: numeric `90` at most `100` passes. The same function, fed `>100` at most `100`, fails and echoes qualifier `>` with limit text `100`. Numeric `150` at most `100` fails. `>100` at most `150` is no verdict and `limit_below_el`. The function does not choose calculated versus reported and does not format a reported result.
17. `0.5` at most `0.5` passes and `0.6` fails. `0.50` at most `0.500` passes. `50` and `200` within `50`–`200` pass. `49` and `201` fail.
18. `|-0.98|` at least `0.980` passes. `|-0.97995|` at least `0.980` fails. The value is not rounded onto the bound. Without the absolute switch, `-0.98` at least `0.980` fails.
19. Qualified `<0.4` and `<0.5` at most `0.5` pass. `<0.6` gives no verdict and `limit_above_el`. Two kinds, `below_range` and `non_detect`, both stored `<` with limit `0.4`, both pass, and each kind comes back unchanged.
20. Qualified `>0.5` at most `0.5` fails. `>0.4` at most `0.5` gives no verdict and `limit_below_el`.
21. A qualified value on `at_least` or `within` gives no verdict, no flag, and `no_verdict` `unspecified`. The Spec states the qualified rules for at most only. Those rules are not copied onto the other forms. `unspecified` is not a review flag.
22. No value is `missing_input`. No bound is `no_verdict` `missing_limit` and sets no flag. `el_missing` is not emitted. The stage names that flag later. A missing value wins over a missing bound. A low bound above the high bound is refused even when the value is missing.
23. An unknown comparison, a JSON number, absolute on a qualified value, a kind on a numeric value, two different kinds, and a malformed `> 100` are HTTP 400 `invalid_input`. The compare functions do not contain the literals `0.5` or `0.980`.

## HTTP contract, catalog, and where the routes are not

24. A computed value, a `missing_input`, a `mean_zero` flag, and a `limit_above_el` flag are HTTP 200. Output values are strings. `r_called` is false. A JSON number, a non-positive nominal, and an unknown field are HTTP 400 `invalid_input`.
25. `test_s5_routes_are_not_mounted_on_the_lims_app_or_in_r`: `app.main` does not import the S5 module. `plumber.R` and `R/catalog.R` do not grow a route for these three names.
26. `test_catalog_lists_exactly_eleven_code_entries`: `closed_catalog()` is the eleven Spec names, in Spec order, with no `elisa_*` or `lal_*`. There is no register function. The four S4 names are unchanged. The four R-side versions still have no KATs.
27. `test_kats_pass_at_tolerance_zero_and_do_not_call_r` calls `prepare_release("s5-decimal-v1")` in memory and it succeeds. The module source does not call `write_release`.

## Unchanged

28. The S1 pin, the S2 harness fixtures, the S3 R routes, and the S4 functions are unchanged aside from the harness accepting a token input and an empty-unit pass/fail output. `bash services/r-calculator/scripts/ci-pin.sh` still ends with `ci-pin ok` when the R tree is unchanged.

## Not in this pass

- No choice of LAL %CV on onset time versus concentration. Both inputs are accepted.
- No interpretation of a qualified unspiked value (OQ-CALC-7).
- No formula binder, no calculated/reported write, no attempt (S7, S9).
- No `el_missing` flag from this function.
- No R-side KATs and no committed release record.
- No S6.
- No merge to `main`.
