# R calculator pin (S1)

The R service is pinned before any catalog function or known-answer test. Later calculation slices stay closed until they are authorized. This page is the operator view of CALC-REQ-2, CALC-REQ-3, CALC-REQ-4, and CALC-REQ-4a.

## What is pinned

- The Dockerfile starts `FROM rocker/r-ver@sha256:<digest>`. There is no floating tag.
- R packages are installed only by `renv::restore()` from the committed `services/r-calculator/renv.lock`. The image build does not call `install.packages`.
- The lock hash is SHA-256 of `<base>\n<renv>\n<tree>` (no trailing line feed).
  - `<base>` is the 64-hex digest in that `FROM` line.
  - `<renv>` is SHA-256 of the raw `renv.lock` bytes.
  - `<tree>` is `git rev-parse <commit>:services/r-calculator`.
- The built image id is `R_IMAGE_DIGEST` (`sha256:` and 64 lowercase hex digits). It is supplied when the container starts. It is not part of the lock hash.

`GET /health` reports `base`, `renv`, `tree`, `lock_hash`, `R_IMAGE_DIGEST`, and a `sandbox` object. The backend recomputes the expected lock hash from the commit. It does not use the Docker socket.

## Sandbox

Compose runs `r-calculator` as uid 1000, with a read-only root, a tmpfs on `/tmp`, no host port, and no route off the `r-internal` network. CPU, memory, and PID limits are set. Deploy and CI check that with `services/r-calculator/scripts/inspect-sandbox.sh`. The API process does not run Docker.

OQ-CALC-16 uses the Spec default: R stops a calculation request after 50 seconds, and the backend stops waiting after 60 seconds. The R limit is a plumber `aroundexec` hook. Plumber calls that hook with the endpoint function, so the limit is in force while the handler runs. `POST /fit` and `POST /svg/full` are not given the hook. They are not under the lock or sandbox refusal. Their existing client timeout is still 60 seconds. The 5 second bound inside curve profiling is unchanged. `tests/test_pin.R` sends a short overrun through plumber and expects HTTP 504 with `r_timeout`. The same short limit does not stop `/fit` or `/svg/full`. No attempt row is written for that timeout; the attempt store is S9.

A calculation call that fails the lock or sandbox check is refused and writes nothing. S1 has no calculation-attempt table, so the acceptance lines that say the attempt records `r_timeout` or `backend_timeout` are proved when that store exists (S9). The timeouts themselves are in place.

## Build

From the repository root, on the commit you are deploying:

```bash
bash services/r-calculator/scripts/ci-pin.sh
```

That builds the image twice, checks the lock hash against a recompute that does not build, runs the sandbox inspect, and runs `tests/test_pin.R` inside the image.

To build only the image for Compose:

```bash
eval "$(python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "backend")
from app.services.calculation_runtime import expected_lock_from_commit
lock = expected_lock_from_commit(Path('.').resolve())
print(f"export R_BASE_DIGEST={lock.base}")
print(f"export R_TREE={lock.tree}")
PY
)"
docker compose build r-calculator
export R_IMAGE_DIGEST="$(docker compose images -q r-calculator | head -n 1)"
```

`R_IMAGE_DIGEST` must be `sha256:` plus 64 lowercase hex digits. If it is unset or the lock hash does not match, calculation calls are refused. The rest of the API, including dose-response fit, still starts.
