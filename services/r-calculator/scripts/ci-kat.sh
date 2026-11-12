#!/bin/bash
# CALC-REQ-5 harness on the built, pinned image. Run from the repository root
# after ci-pin.sh, which leaves the pinned container running. The backend KAT
# runner calls the container over HTTP; every R call passes the lock and
# sandbox gate. The run log is written to KAT_RUN_LOG_PATH and printed.
# Usage: ci-kat.sh [r-container]
set -euo pipefail

root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"

container=${1:-lims-r-pin-a}
python_bin=${PYTHON:-python3}
run_log=${KAT_RUN_LOG_PATH:-/tmp/kat-run-log.json}

ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container")
if [ -z "$ip" ]; then
  echo "no address for ${container}" >&2
  exit 1
fi

rm -f "$run_log"
(
  cd backend
  KAT_R_CALCULATOR_URL="http://${ip}:8000" \
  KAT_RUN_LOG_PATH="$run_log" \
  ENVIRONMENT=test \
  ALLOW_INSECURE_DEFAULTS=true \
  SECRET_KEY=pytest-secret-key-not-for-production \
  DATABASE_URL=postgresql://lims_app@127.0.0.1:5432/lims_db \
    "$python_bin" -m pytest -q --tb=short -p no:cacheprovider \
      "tests/test_calculation_kat_s2.py::test_r_side_harness_kats_on_the_pinned_image"
)

if [ ! -s "$run_log" ]; then
  echo "KAT run log was not written" >&2
  exit 1
fi
cat "$run_log"
echo "ci-kat ok"
