# UAT: calculations S1, pin the R service

**Scope:** CALC-REQ-2, CALC-REQ-3, CALC-REQ-4, CALC-REQ-4a, and the CALC-REQ-1 order (pin only). S2–S14 are out of scope. No catalog route, no KAT product case, no calculation attempt, no result write.

**Branch:** `calculations`. Do not merge to `main` from this slice alone.

**Decisions used:** OQ-CALC-16 default, R 50 s and backend 60 s. `POST /fit` and `POST /svg/full` stay on the shipped dose-response path and are not refused by the new lock or sandbox check. The lines in CALC-REQ-4a that require an attempt row with `r_timeout` or `backend_timeout` wait for S9.

## Setup

1. Check out `calculations` at the S1 commit.
2. From the repo root, run `bash services/r-calculator/scripts/ci-pin.sh`. It needs Docker. It builds the R image twice from this commit.

## CALC-REQ-2

3. Open `services/r-calculator/Dockerfile`. Every `FROM` line contains `@sha256:`.
4. In the `ci-pin.sh` output, the two builds print the same `lock_hash`. Their image ids may differ.
5. That hash equals the hash printed by recomputing from the commit (the script's `EXPECTED_LOCK_HASH`) without a third build.

## CALC-REQ-3

6. `Dockerfile` does not contain `install.packages(`. `restore.R` calls `renv::restore` on `renv.lock`.
7. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py::test_one_package_version_changes_the_lock_hash` passes. Changing one package version in the lock bytes changes the lock hash.

## CALC-REQ-4

8. `GET /health` from the script's containers includes `base`, `renv`, `tree`, `lock_hash`, and `R_IMAGE_DIGEST`.
9. `cd backend && python -m pytest -q tests/test_calculation_pin_s1.py` passes. A mismatched expected hash, a missing `R_IMAGE_DIGEST`, and an ill-formed digest each refuse the calculation call, name the cause, and leave the write list empty.

## CALC-REQ-4a

10. `ci-pin.sh` reports `docker inspect sandbox ok`. The running container's uid is not 0, a write under `/tmp` succeeds, a write under `/app` fails, and a connection to `1.1.1.1:443` fails.
11. `/health` `sandbox` booleans are all true and `uid` is not 0.
12. The pytest file refuses a call when any sandbox boolean is false or missing, when `uid` is 0, and when the sandbox object is missing.
13. The backend service in `docker-compose.yml` does not mount `/var/run/docker.sock`.
14. `services/r-calculator/R/request_timeout.R` sets `REQUEST_TIMEOUT_SECONDS` to 50. `CALCULATION_BACKEND_TIMEOUT_SECONDS` is 60. The pytest maps an R 504 `r_timeout` and a backend wait timeout to those codes and does not write. It does not insert an attempt row; that store is S9.
15. `RCalculatorClient.fit` and `full_svg` do not call `begin_calculation_call`. `R/fit.R` still bounds profiled confidence intervals at 5 seconds.
16. `ci-pin.sh` runs `tests/test_pin.R` inside the image. That script routes a short overrun through plumber. The response is HTTP 504 and `code` is `r_timeout`, and the handler does not finish. A slow `POST /fit` and a slow `POST /svg/full` on that test router finish. The shipped router has the hook on `/health` at 50 seconds and no hook on `/fit` or `/svg/full`. `GET /health` still returns status `ok`.

## Not in this pass

- No catalog function, no KAT case, no ELISA or LAL seed.
- No calculation attempt table and no result write.
- No merge to `main`.
