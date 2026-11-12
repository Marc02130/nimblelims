#!/bin/bash
# Deploy and CI check for CALC-REQ-4a. The backend never runs this and never
# receives the Docker socket. Usage:
#   inspect-sandbox.sh <r-container> [backend-container]
set -euo pipefail

r_container=${1:-lims-r-calculator}
backend_container=${2:-}

python3 - "$r_container" <<'PY'
import json, subprocess, sys
name = sys.argv[1]
raw = subprocess.check_output(["docker", "inspect", name])
data = json.loads(raw)[0]
host = data["HostConfig"]
config = data.get("Config") or {}
errors = []
if host.get("ReadonlyRootfs") is not True:
    errors.append("root filesystem is not read-only")
if not host.get("Memory"):
    errors.append("memory limit is unset")
if not host.get("NanoCpus") and not host.get("CpuQuota"):
    errors.append("cpu limit is unset")
pids = host.get("PidsLimit")
if pids is None or pids <= 0:
    errors.append("pid limit is unset")
# EXPOSE records the container port with a null binding. That is not a host port.
# A published port has a non-empty binding list.
ports = (data.get("NetworkSettings") or {}).get("Ports") or {}
for port, binding in ports.items():
    if binding:
        errors.append(f"host port is published for {port}")
bindings = host.get("PortBindings") or {}
for port, binding in bindings.items():
    if binding:
        errors.append(f"host port is published for {port}")
user = config.get("User") or ""
if user in ("", "0", "root", "0:0"):
    errors.append(f"container user is root ({user!r})")
tmpfs = host.get("Tmpfs") or {}
if "/tmp" not in tmpfs:
    errors.append("tmpfs scratch /tmp is missing")
for item in config.get("Env") or []:
    env_name = item.split("=", 1)[0]
    if env_name == "DATABASE_URL" or env_name.endswith("_KEY") or env_name.endswith("_SECRET"):
        errors.append(f"forbidden env {env_name}")
if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print("docker inspect sandbox ok")
PY

uid=$(docker exec "$r_container" id -u)
if [[ "$uid" == "0" ]]; then
  echo "process uid is 0" >&2
  exit 1
fi
docker exec "$r_container" sh -c 'echo scratch > /tmp/pin-scratch-probe && test -f /tmp/pin-scratch-probe'
if docker exec "$r_container" sh -c 'echo nope > /app/pin-outside-probe'; then
  echo "write outside tmpfs scratch succeeded" >&2
  exit 1
fi
if docker exec "$r_container" timeout 2 bash -c 'echo >/dev/tcp/1.1.1.1/443'; then
  echo "outbound connection succeeded" >&2
  exit 1
fi

if [[ -n "$backend_container" ]]; then
  python3 - "$backend_container" <<'PY'
import json, subprocess, sys
name = sys.argv[1]
try:
    raw = subprocess.check_output(["docker", "inspect", name], stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    sys.exit(0)
data = json.loads(raw)[0]
for mount in data.get("Mounts") or []:
    src = mount.get("Source") or ""
    dest = mount.get("Destination") or ""
    if "docker.sock" in src or dest == "/var/run/docker.sock":
        raise SystemExit("backend has the Docker socket mounted")
print("backend has no Docker socket")
PY
fi
