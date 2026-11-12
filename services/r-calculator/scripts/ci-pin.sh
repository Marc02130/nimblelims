#!/bin/bash
# Prove CALC-REQ-2 / 4a on a built image: two builds of this commit share a
# lock hash, /health matches a recompute that does not build, and docker
# inspect shows the sandbox. Run from the repository root.
set -euo pipefail

root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"

eval "$(
  python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "backend")
from app.services.calculation_runtime import expected_lock_from_commit
lock = expected_lock_from_commit(Path(".").resolve())
print(f"export R_BASE_DIGEST={lock.base}")
print(f"export R_TREE={lock.tree}")
print(f"export EXPECTED_LOCK_HASH={lock.lock_hash}")
PY
)"

build_one() {
  local tag=$1
  local label=$2
  docker build \
    --label "nimble.pin.build=${label}" \
    --build-arg "R_BASE_DIGEST=${R_BASE_DIGEST}" \
    --build-arg "R_TREE=${R_TREE}" \
    -t "$tag" \
    services/r-calculator
}

build_one nimblelims-r-calculator:pin-a a
build_one nimblelims-r-calculator:pin-b b

id_a=$(docker image inspect --format '{{.Id}}' nimblelims-r-calculator:pin-a)
id_b=$(docker image inspect --format '{{.Id}}' nimblelims-r-calculator:pin-b)

docker network inspect r-pin-internal >/dev/null 2>&1 || docker network create --internal r-pin-internal

run_one() {
  local name=$1
  local image=$2
  local digest=$3
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker run -d --name "$name" \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,mode=1777,size=268435456 \
    --user 1000:1000 \
    --cpus 1 \
    --memory 1536m \
    --pids-limit 256 \
    --network r-pin-internal \
    -e "R_IMAGE_DIGEST=${digest}" \
    -e R_SCRATCH_PATH=/tmp \
    -e HOME=/tmp \
    -e TMPDIR=/tmp \
    -e TMP=/tmp \
    -e TEMP=/tmp \
    -e XDG_CACHE_HOME=/tmp \
    "$image"
}

run_one lims-r-pin-a nimblelims-r-calculator:pin-a "$id_a"
run_one lims-r-pin-b nimblelims-r-calculator:pin-b "$id_b"

wait_health() {
  local name=$1
  local i
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    if docker exec "$name" curl -fsS http://127.0.0.1:8000/health >"/tmp/${name}-health.json" 2>/dev/null; then
      return 0
    fi
    sleep 3
  done
  echo "health did not become ready for ${name}" >&2
  docker logs "$name" >&2 || true
  return 1
}

wait_health lims-r-pin-a
wait_health lims-r-pin-b

python3 - <<PY
import json
from pathlib import Path
expected = "${EXPECTED_LOCK_HASH}"
id_a = "${id_a}"
id_b = "${id_b}"
a = json.loads(Path("/tmp/lims-r-pin-a-health.json").read_text())
b = json.loads(Path("/tmp/lims-r-pin-b-health.json").read_text())
if a["lock_hash"] != expected or b["lock_hash"] != expected:
    raise SystemExit(f"lock hash mismatch {a['lock_hash']} {b['lock_hash']} expected {expected}")
if a["lock_hash"] != b["lock_hash"]:
    raise SystemExit("two builds reported different lock hashes")
if a.get("R_IMAGE_DIGEST") != id_a or b.get("R_IMAGE_DIGEST") != id_b:
    raise SystemExit("R_IMAGE_DIGEST was not the built image id")
sandbox = a["sandbox"]
fields = (
    "root_read_only",
    "scratch_tmpfs",
    "egress_blocked",
    "cpu_limited",
    "memory_limited",
    "pids_limited",
    "forbidden_env_absent",
)
for field in fields:
    if sandbox.get(field) is not True:
        raise SystemExit(f"sandbox.{field} is not true: {sandbox}")
if sandbox.get("uid") in (None, 0):
    raise SystemExit(f"sandbox.uid is not a non-root uid: {sandbox}")
for key in ("base", "renv", "tree", "lock_hash"):
    if not a.get(key):
        raise SystemExit(f"/health missing {key}")
print("two builds share lock hash", a["lock_hash"])
print("image ids", id_a, id_b)
PY

bash services/r-calculator/scripts/inspect-sandbox.sh lims-r-pin-a
docker run --rm --entrypoint Rscript nimblelims-r-calculator:pin-a tests/test_pin.R

# Image history and build args carry no database URL and no *_KEY / *_SECRET name.
docker history --no-trunc --format '{{.CreatedBy}}' nimblelims-r-calculator:pin-a > /tmp/r-pin-history.txt
python3 - /tmp/r-pin-history.txt <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
pat = re.compile(r"(?<![A-Za-z0-9])(?:DATABASE_URL|[A-Za-z0-9]+_(?:KEY|SECRET))(?![A-Za-z0-9])")
found = sorted(set(pat.findall(text)))
if found:
    raise SystemExit("image history has forbidden names: " + ", ".join(found))
print("image history has no forbidden env names")
PY

echo "ci-pin ok"
