# UAT: calculations S4, backend decimal catalog functions

**Scope:** CALC-REQ-38, 51, 53, 39, 28, and 37 for `apply_dilution`, `subtract`, `copy_raw`, and `convert_units`, each at version 1. No R call, no R route, no configuration, no attempt or result write, and no screen.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**KATs:** one case per function, absolute tolerance 0. Citations are the Spec acceptance criteria worked by hand. They are not SOP citations. See [manuals/calculation-catalog-decimal.md](../manuals/calculation-catalog-decimal.md).

## Setup

1. Check out `calculations` at the S4 commit. Docker is required for the migration test.
2. Install `backend/requirements.txt` into a Python 3.12 environment.

## Backend suite

3. `cd backend && python -m pytest -q tests/test_calculation_catalog_decimal_s4.py` passes, including `test_seeded_units_and_lookup_do_not_use_rls`.
4. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py tests/test_calculation_kat_s2.py tests/test_calculation_release_s2.py tests/test_calculation_catalog_r_s3.py` still passes. The R catalog versions still have no KAT cases.

## Acceptance criteria, as KATs (tolerance 0, no R)

5. `test_kats_pass_at_tolerance_zero_and_do_not_call_r` runs the four cases through `run_kats`. Every case passes, `r_called` is false, and the observed strings are exact:
   - `apply_dilution`: `0.026 × 100 = 2.6`.
   - `subtract`: `2.572 − 0.050 = 2.522`.
   - `copy_raw`: `0.026` is both `calculated` and `reported`.
   - `convert_units` per amount: `2.6 / 10 = 0.26`.
6. `test_subtract_2_572_minus_0_050_is_exactly_2_522` shows the binary subtraction is not `2.522`.
7. `test_convert_units_division_uses_precision_50` divides 1 by 3 and the result has 50 threes after the decimal point.

## Each function

8. `apply_dilution`: a missing factor or a missing value is `missing_input` and stores nothing. A factor below 1 (`0.999`, `0`, `0.0`, `-1`, `1e-1`) is refused with `invalid_input`. A factor of `1`, `1.0`, or `1e0` is allowed. A negative value is multiplied. A JSON number is refused.
9. `subtract`: a zero difference is the string `0` and does not stop. A missing minuend or subtrahend is `missing_input` and is not replaced with zero. A negative difference is stored.
10. `copy_raw`: `0.026` is written to both outputs. `0.0260`, `1.50`, `1.5e-3`, `-0.026`, and `0` keep their characters. A JSON number is refused and is not a stop. OQ-CALC-39 is not implemented: there is no unit stop inside this function.
11. `convert_units`:
    - Mode `per_amount` divides. A missing amount is `missing_input`. An amount of `0`, `0.0`, or a negative amount is refused. A negative value is divided.
    - Mode `within_type` uses the multipliers. `1000000000` pg/mL (multiplier `0.000000001`) becomes `1` g/L. `1000` mg (multiplier `0.001`) becomes `1` g. The same unit (`OD` to `OD`) keeps the value.
    - A cross-type pair is refused: `EU/mL` (activity) to `mg/mL` (concentration), and `OD` (absorbance) to `s` (time), even though both multipliers are 1. CALC-REQ-28 calls this a stop. CALC-REQ-39 and this slice's plan call it a refusal. The test expects HTTP 400 `invalid_input`.
    - An unknown unit such as `EU/kg` stops with HTTP 200 and `unit_not_found`, and the detail names the unit. `EU/kg` is not seeded.
    - A blank unit name is `missing_input`. A null or zero multiplier is refused. An unknown mode is refused and does not default to either mode.

## Units seed and the lookup (CALC-REQ-28, OQ-CALC-44)

12. `test_0122_is_the_single_alembic_head`: revision `0122_calculation_units_seed` revises `0121_shared_reason_rules`, the id is at most 32 characters, upgrade does not `DELETE FROM units` and does not `ENABLE ROW LEVEL SECURITY`, and it is the only Alembic head.
13. `test_seeded_units_and_lookup_do_not_use_rls`, as `app_test_role`:
    - `units` has `relrowsecurity` false, `relforcerowsecurity` false, and no `pg_policy` row. `multiplier` is `numeric(20, 10)`.
    - `OD`, `s`, and `1` each load with multiplier `1` and types `absorbance`, `time`, and `dimensionless`.
    - `1000000000` pg/mL converts to `1` g/L through the database lookup.
    - `EU/mL` to `mg/mL` is refused. `EU/kg` stops with `unit_not_found`.
14. The lookup SQL reads `multiplier::text`. It does not `SET row_security` and it does not call `convert_to_base_unit` or `convert_from_base_unit`. Marc decided on 2026-11-15 that this lookup does not run under row-level security. The Spec still lists OQ-CALC-44 as Open. This pass does not edit the Spec.

## HTTP contract, and where the routes are not

15. `test_http_success_and_missing_input_are_200_with_string_outputs`: a computed value and a `missing_input` are both HTTP 200. Output values are strings. `r_called` is false.
16. `test_http_refusal_is_400_and_stop_is_200`: a factor below 1, a non-positive amount, a JSON number, a cross-type conversion, and an unknown field are HTTP 400 `invalid_input`. `unit_not_found` is HTTP 200.
17. `test_decimal_routes_are_not_mounted_on_the_lims_app_or_in_r`: `app.main` does not include the decimal router. `plumber.R` and `R/catalog.R` do not grow a route. The R catalog declarations do not gain these four names.

## Release state

18. `test_kats_pass_at_tolerance_zero_and_do_not_call_r` calls `prepare_release("s4-decimal-v1")` in memory and it succeeds. The module source does not call `write_release`. No release file is written. The four versions stay at version 1, side `backend`, with `route` empty.

## Unchanged

19. The S1 pin, the S2 harness fixtures, and the S3 R routes are unchanged. `bash services/r-calculator/scripts/ci-pin.sh` still ends with `ci-pin ok` when the R tree is unchanged. The route set in the pinned image is still `/health`, `/fit`, `/svg/full`, `/kat-harness/round-trip`, and the four R catalog routes.

## Not in this pass

- No S5 function (`replicate_mean_cv`, `spike_recovery`, `limit_compare`).
- No lab-added unit such as `EU/kg`.
- No run-time `copy_raw` unit mismatch (OQ-CALC-39, S9).
- No reference resolution for `subtract`.
- No committed release record, no LIMS API route, no screen.
- No merge to `main`.
