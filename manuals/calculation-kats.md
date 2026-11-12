# Calculation KATs and release records (S2)

Known-answer tests (KATs), their run log, and the release record for catalog function versions. This page is the operator and developer view of CALC-REQ-5, CALC-REQ-6, CALC-REQ-7, CALC-REQ-29, and CALC-REQ-33. It builds on the S1 pin ([r-calculator-pin.md](r-calculator-pin.md)).

S2 is the harness only. There are no catalog functions yet (S3 to S5), no real KAT cases, and no ELISA or LAL cases (S14). The only cases in the repo are harness fixtures used to prove the runner and the release check.

## Where it lives

| Piece | File |
|-------|------|
| KAT case, function version, runner, run log | `backend/app/services/calculation_kat.py` |
| Release record and release check | `backend/app/services/calculation_release.py` |
| Shortest round-trip serialiser (R) | `services/r-calculator/R/serialise.R` |
| Serialiser unit test, in the image only | `services/r-calculator/tests/test_serialise.R` |
| Harness-fixture R route | `POST /kat-harness/round-trip` in `services/r-calculator/plumber.R` |
| Harness fixtures (not catalog KATs) | `backend/tests/fixtures/calculation_kat_harness.py` |
| CI step | `services/r-calculator/scripts/ci-kat.sh`, after `ci-pin.sh` |

## Function versions and KAT cases

A function version declares its name, integer version, R or backend side, a plain-language formula, every input and output with its unit, defaults, its stop rule, its missing-data rule, and its KATs. An R-side version names its R route. A backend version names its decimal code.

A KAT case supplies every input itself, as a decimal string with a unit. It gives the expected value of every output with its unit, a tolerance for every output, and a source citation. A case reads nothing from a configuration.

- An absolute tolerance is in the output's unit. A relative tolerance is a fraction of the expected value and has unit `1`.
- A case with no citation, a unit that is not the declared unit, a missing tolerance, or a value that is not a decimal string fails before it runs.

## Running KATs

`run_kats(versions, health=..., r_client=...)` first checks the R service's `/health` with the S1 gate (lock hash, built image digest, and sandbox). If that check refuses, no run log is produced. A host R process, or an image built without the pin's tree, cannot pass.

- R-side cases are POSTed to the version's route on the pinned image through `RCalculatorClient.execute_calculation_request`. Every call passes the gate again. R returns outputs as JSON strings; a JSON number fails the case.
- Backend cases run the version's decimal code in Python `decimal` (precision 50, ROUND_HALF_EVEN). Any HTTP request made while a backend case runs fails that case.

The run log is JSON. It names the lock hash and the built image digest it ran on and the time. For each case it lists the case id, function name and version, R or backend, the citation, pass or fail, any error, and for each output the observed value, expected value, unit, and tolerance.

In CI, `ci-kat.sh` runs the harness fixtures against the container `ci-pin.sh` left running and prints the run log. Locally, after `ci-pin.sh`:

```bash
bash services/r-calculator/scripts/ci-kat.sh lims-r-pin-a
```

Set `PYTHON` to a Python with `backend/requirements.txt` installed. Set `KAT_RUN_LOG_PATH` to choose where the run log is written (default `/tmp/kat-run-log.json`).

## Serialiser unit test

`shortest_round_trip()` returns the fewest significant digits that parse back to the same double under R's own parser and under a correctly rounded parser (the C library `strtod`, through `jsonlite`). Fixed notation is used for 0 and for 1e-4 ≤ |x| < 1e16; otherwise scientific, as Python `repr()` does. Where R's parser misreads the shortest correctly rounded string, the result has one more digit.

`tests/test_serialise.R` runs only inside the pinned image. Outside it, the script stops with "a host-R run of the serialiser test does not count". `ci-pin.sh` runs it:

```bash
docker run --rm --network none --entrypoint Rscript nimblelims-r-calculator:pin-a tests/test_serialise.R
```

## Release records

The catalog is code (CALC-REQ-22), so a release record is a JSON file written once and committed through a reviewed pull request. No API route, screen, database row, or agent writes one.

A record holds the release id, the lock hash, the SHA-256 of the KAT run log, the releases it depends on, and for each function version it adds: name, version, a fingerprint of its definition, and its KAT case ids.

`prepare_release()` refuses, and nothing is written, when:

- A version has a failing KAT on the release's lock hash (`kat_failed`).
- A version has no KATs, the run log is missing, the run log is on another lock hash, a case was not run, or the run was against an older definition of the version (`kat_absent`).
- The version is already released (`released_version_immutable`).
- The catalog no longer matches a released version's fingerprint (`released_version_edited`) or drops it (`released_version_removed`).
- The release id is taken (`duplicate_release`), is not a plain lowercase file name (`invalid_release_id`), names an unknown release (`unknown_dependency`), or adds nothing (`empty_release`).

`write_release()` creates `<release_id>.json` and never replaces an existing file. A release adds versions only. Every other version and every earlier record stays as it was.

The fingerprint covers the formula description, defaults, inputs and outputs with units, stop rule, missing-data rule, KAT cases (and so their tolerances), and the implementation: the backend function's source, or the bytes of the R files the version lists. Any change to those is a new version.

This is a software-release check. It is not a lab validation gate, which is out of scope.

## Not in S2

- Catalog functions, real KAT cases, and their expected values. Expected values for real cases come from the SOP when the SOP has them (OQ-CALC-13).
- ELISA and LAL reference-configuration KATs (S14).
- A committed release ledger. The first catalog release (S3 onward) chooses where records are committed.
- Configurations, attempts, and result writes.
