#!/bin/bash
# S3 R-side catalog functions against the built, pinned image. Run from the
# repository root after ci-pin.sh, which leaves the pinned container running.
# The backend functions call the container over HTTP through the lock and
# sandbox gate. These are unit tests, not KATs; no catalog version has KATs yet.
# Usage: ci-catalog.sh [r-container]
set -euo pipefail

root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"

container=${1:-lims-r-pin-a}
python_bin=${PYTHON:-python3}

ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container")
if [ -z "$ip" ]; then
  echo "no address for ${container}" >&2
  exit 1
fi

(
  cd backend
  KAT_R_CALCULATOR_URL="http://${ip}:8000" \
  ENVIRONMENT=test \
  ALLOW_INSECURE_DEFAULTS=true \
  SECRET_KEY=pytest-secret-key-not-for-production \
  DATABASE_URL=postgresql://lims_app@127.0.0.1:5432/lims_db \
    "$python_bin" -m pytest -q --tb=short -p no:cacheprovider -rs \
      tests/test_calculation_catalog_r_s3.py
) | tee /tmp/ci-catalog.log

if grep -q "skipped" /tmp/ci-catalog.log; then
  echo "a pinned-image catalog test was skipped" >&2
  exit 1
fi
echo "ci-catalog ok"
