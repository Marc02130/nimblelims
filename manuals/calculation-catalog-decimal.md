# Backend decimal catalog functions (S4)

The four backend catalog functions: `apply_dilution`, `subtract`, `copy_raw`, and `convert_units`, each at version 1. This page is the developer view of CALC-REQ-38, CALC-REQ-51, CALC-REQ-53, CALC-REQ-39, CALC-REQ-28, and CALC-REQ-37. It builds on the S2 harness ([calculation-kats.md](calculation-kats.md)) and sits beside the R-side catalog ([calculation-catalog-r.md](calculation-catalog-r.md)).

**Release state:** all four versions are declared, have one KAT each, and are **not released**. S4 does not call `write_release`. A later slice chooses where the release record is committed.

Nothing in S4 writes an attempt or a result, reads a configuration, or adds a screen. The four routes below are a status-code contract for tests. They are not mounted on the LIMS app. The stage runner is S9. None of the four has an R route (CALC-REQ-24).

## Where it lives

| Piece | File |
|-------|------|
| Functions, KAT cases, declarations, factor lookup, HTTP contract | `backend/app/services/calculation_catalog_decimal.py` |
| Additive units seed (`OD`, `s`, `1`) | `backend/db/migrations/versions/0122_calculation_units_seed.py` |
| Unit tests and the KAT run | `backend/tests/test_calculation_catalog_decimal_s4.py` |
| Harness the KATs run on | `backend/app/services/calculation_kat.py` |

## Decimal context (CALC-REQ-37)

Every arithmetic step runs in Python `decimal` with precision 50 and `ROUND_HALF_EVEN`. Products are computed first and there is one division last. Inputs are decimal strings. A JSON number or a boolean is refused with `invalid_input`. A non-decimal string such as `N/A` or `""` is missing data, not a refusal.

Arithmetic outputs are plain decimal strings. Trailing zeros in the coefficient are stripped, so `2.600` is written `2.6`. A difference of zero is written `0`. `copy_raw` does not do this: it writes the input characters unchanged.

## HTTP status

| Outcome | Status | Body |
|---------|--------|------|
| A number was computed | 200 | `outputs` holds decimal strings. `r_called` is false. |
| `missing_input` | 200 | `outputs` is empty. `flags` is `["missing_input"]`. |
| Stage stop (`unit_not_found`) | 200 | `stop` and `detail`. No number. |
| Refusal | 400 | `{"code": "invalid_input", "detail": "..."}` |

A dilution factor below 1, an amount that is not greater than 0, a cross-type conversion, a null or non-positive multiplier, an unknown mode, and an unknown JSON field are refusals. They are not stage stops.

`missing_input` is neither a stop nor a refusal. A missing input is never replaced with zero.

## Functions

### `apply_dilution` v1

`apply_dilution(value, dilution_factor)`. Output = value × dilution factor, in the value's unit. The factor is dimensionless (unit `1`).

- No factor, or no value, is `missing_input`. The factor is checked first, so a factor below 1 is still a refusal when the value is missing.
- A factor below 1, including `0` and a negative factor, is refused. A factor of exactly 1 is allowed.
- A negative value is multiplied. The Spec does not refuse negative values on this function.

KAT `apply-dilution-0.026-times-100`: `0.026 × 100 = 2.6`, absolute tolerance 0. Citation is the CALC-REQ-38 acceptance criterion, worked by hand. It is not an SOP.

### `subtract` v1

`subtract(minuend, subtrahend)`. Output = minuend − subtrahend, in the shared unit.

- A missing minuend or subtrahend is `missing_input`. This function does not resolve a reference. Reference stops (CALC-REQ-50) happen before it runs, in S9.
- A difference of zero is stored as `0` and does not stop.
- A negative difference is stored. It is not a refusal.

KAT `subtract-2.572-minus-0.050`: `2.572 − 0.050 = 2.522`, absolute tolerance 0. The same subtraction in binary floating point is not `2.522`.

### `copy_raw` v1

`copy_raw(value)`. The same characters are written to `calculated` and to `reported`. There is no conversion and no change of text. `0.026` writes `0.026` to both. `0.0260`, `1.50`, and `1.5e-3` are kept as written.

- No input is `missing_input`. A JSON number is refused.
- A difference between file units and the pairing unit is OQ-CALC-39. It is not a stop inside this function. That check is S9.

The public function returns the original string. The KAT harness parses every input to `Decimal` before it calls `compute`, so the KAT case checks the value `0.026`, and the character-preserving cases are unit tests of `copy_raw` itself. A future release fingerprint covers `copy_raw_compute` (the harness path), which formats a `Decimal`. The public function is the one the HTTP route calls.

KAT `copy-raw-0.026`: both outputs are `0.026`, absolute tolerance 0.

### `convert_units` v1

`convert_units(value, *, mode, amount=None, from_unit=None, to_unit=None, lookup=None, session=None)`.

The Spec names two modes and does not name the selector. The parameter is `mode`:

- `within_type`: output = (value × from-unit multiplier) / to-unit multiplier. The two multipliers come from `units.multiplier`, read as text and parsed as `Decimal`. The column is `numeric(20, 10)`.
- `per_amount`: output = value / amount. The function writes the number only. It does not assign the output unit.

There is no default mode. Any other mode is refused.

- In `per_amount`, a missing amount is `missing_input`. An amount that is not greater than 0 is refused. A missing value is `missing_input`.
- In `within_type`, a missing unit name is `missing_input`. A name that is not an active row stops with `unit_not_found`. The detail names the unit. The Spec does not lock that spelling. CALC-REQ-28 calls a missing unit a stop, and calls a cross-type conversion a stop as well. CALC-REQ-39 and the S4 plan call a cross-type conversion a refusal. This slice refuses it (HTTP 400) and lists the contradiction; the Spec is unchanged.
- A null multiplier, or a multiplier that is not greater than 0, is refused. The Spec does not say what to do with one.
- Inactive units are treated as not found (`active IS TRUE`), matching the shipped unit helpers.

The KAT harness only accepts decimal strings, so a unit name cannot be a KAT input. The catalog KAT is the per-amount acceptance criterion. Within-type conversion is covered by unit tests and by the database lookup test.

KAT `convert-units-2.6-over-10`: `2.6 / 10 = 0.26`, absolute tolerance 0.

## Factor lookup and row-level security (OQ-CALC-44)

Marc decided on 2026-11-15 that the `convert_units` lookup of `units.multiplier` does **not** run under row-level security. `units` is shared reference data. It has no RLS policy, and this lookup does not enable one, does not `SET row_security`, and does not filter by a client. The Spec still marks OQ-CALC-44 Open. That text was not edited. The decision is implemented here.

`load_unit_factor(session, name)` selects `u.multiplier::text` joined to the unit's type. It does not call `convert_to_base_unit` or `convert_from_base_unit`. Those helpers return binary floats.

## Units seed (CALC-REQ-28)

Migration `0122_calculation_units_seed` is additive. It inserts three unit types and three units, each with multiplier 1:

| Unit | Type |
|------|------|
| `OD` | `absorbance` |
| `s` | `time` |
| `1` | `dimensionless` |

Upgrade only inserts. A row that already has the same name and already matches (active, multiplier 1, the same type) is left alone. A row that has the name but does not match makes upgrade raise, and that row is not updated. Downgrade deletes only the rows whose description is the seed description, then the type if no unit still references it.

Lab-added units such as `EU/kg` are not seeded.

## KATs and the fingerprint

Each KAT uses absolute tolerance `0` because the result is exact in decimal. `run_kats` sets the precision-50 context and wraps the run so that any HTTP call fails the case. No backend KAT calls R.

`version_fingerprint` hashes the declaration and the source of `compute` only. `within_type_quotient` is a separate function, so it is not in that hash. The versions are not released, so the hash is not stored. `prepare_release("s4-decimal-v1")` succeeds in memory. Nothing writes the file.

## Not in this slice

- Replicate mean and CV, spike recovery, and limit compare (S5).
- A run-time stop when `copy_raw` file units differ from the pairing unit (OQ-CALC-39, S9).
- Reference resolution for `subtract` (S9).
- A committed release record.
- An R route, a LIMS API route, a configuration, an attempt, or a result write.
