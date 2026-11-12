# UAT: calculations S2, KAT harness, run log, and release record

**Scope:** CALC-REQ-5 (harness and run log), CALC-REQ-6 (citation per case), CALC-REQ-7, CALC-REQ-29, CALC-REQ-33. Harness only. No catalog function, no real KAT case, no ELISA or LAL case, no lab validation gate.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**Fixtures:** every case in this pass is a harness fixture in `backend/tests/fixtures/calculation_kat_harness.py`. Each is named `harness_fixture_*` and each citation starts "KAT harness test fixture". None is a catalog KAT and none comes from an SOP.

## Setup

1. Check out `calculations` at the S2 commit. Docker is required.
2. From the repo root, run `bash services/r-calculator/scripts/ci-pin.sh`. It must end with `ci-pin ok`.
3. Install `backend/requirements.txt` into a Python 3.12 environment.

## Serialiser unit test (CALC-REQ-5)

4. In the `ci-pin.sh` output, `serialiser test ok` appears after `test_pin.R ok`. That run is `docker run ... nimblelims-r-calculator:pin-a tests/test_serialise.R` inside the pinned image.
5. The test covers `0.026`, `-0.98`, `0.1 + 0.2` (`0.30000000000000004`), and `1/3` (`0.3333333333333333`), and checks each string parses back to the same double under R's parser.
6. Run `cd services/r-calculator && Rscript tests/test_serialise.R` on host R, if host R is installed. It stops with "a host-R run of the serialiser test does not count". A host-R run does not pass.

## R-side and backend KATs, run log (CALC-REQ-5, CALC-REQ-6)

7. Run `PYTHON=<that python> bash services/r-calculator/scripts/ci-kat.sh lims-r-pin-a`. It ends with `ci-kat ok` and prints the run log.
8. The run log `lock_hash` equals the lock hash `ci-pin.sh` printed. `image_digest` is the `pin-a` image id.
9. Each case shows `function`, `version`, `side` (`r` or `backend`), `citation`, `result`, and per output `observed`, `expected`, `tolerance`, and `unit`.
10. The four `harness_fixture_r_round_trip` passing cases have `side` `r` and `result` `pass`. `hf-r-deliberately-wrong` has `result` `fail`, observed `0.1`, expected `0.2`.
11. `hf-sum-exact` has `side` `backend`, observed `2.572`, tolerance `absolute` `0`, `result` `pass`.
12. Start an R container from an image built without the pin's build args (for example `docker build -t r-unpinned services/r-calculator`, then `docker run -d --name lims-r-unpinned -e R_IMAGE_DIGEST=sha256:<64 hex> r-unpinned`) and run `ci-kat.sh lims-r-unpinned`. It fails with `lock hash mismatch` and writes no run log.
13. `cd backend && python -m pytest -q tests/test_calculation_kat_s2.py` passes. It covers a backend KAT that calls R (fails), a case with no citation (fails), unit and tolerance mistakes (fail), an R JSON number (fails), and a refused `/health` (no run log).

## Release record (CALC-REQ-7, 29, 33)

14. `cd backend && python -m pytest -q tests/test_calculation_release_s2.py` passes.
15. CALC-REQ-7: `test_release_with_a_failing_kat_is_refused` is refused with `kat_failed`. `test_release_with_an_absent_kat_run_is_refused` is refused with `kat_absent` for no run log, a version not in the run, a run on another lock hash, and a version with no KATs. Nothing is written.
16. CALC-REQ-29: `test_edit_to_a_released_version_is_refused_and_a_new_version_succeeds`. The edited v1 is refused (`released_version_edited`), re-releasing v1 is refused (`released_version_immutable`), the same change as v2 is released, and `r1.json` is byte-identical afterwards.
17. CALC-REQ-33: `test_a_new_version_of_one_function_leaves_every_other_version_unchanged`. After releasing `harness_fixture_backend_a` v2, every earlier record is byte-identical, and every earlier released version is still released with the same fingerprint.
18. `ci-kat.sh` also runs the release check on the in-image run log: the R fixture version with the failing case is refused and the version with only passing cases is accepted on that lock hash.

## Unchanged

19. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py` still passes. `POST /fit` and `POST /svg/full` are unchanged and are not calculation calls. The 5 s profiled-CI bound in `R/fit.R` is unchanged.

## Not in this pass

- No catalog function, no real KAT case, no ELISA or LAL case.
- No committed release record. The first catalog release chooses where records are committed.
- No lab validation gate.
- No merge to `main`.
