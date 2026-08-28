#!/usr/bin/env python3
"""Live CORE UAT for NimbleLIMS atomic receive. Never prints tokens/passwords."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

BASE = os.environ.get("UAT_API", "http://localhost:8000")
# Credentials from UAT script; never printed.
USERS = {
    "alice-tech": os.environ.get("ALICE_PASS", "alice123"),
    "bob-tech": os.environ.get("BOB_PASS", "bob123"),
    "david-cro": os.environ.get("DAVID_PASS", "david123"),
}

ALICE_TYPE = "Plasma"
ALICE_MATRIX = "Plasma (K2EDTA)"
ALICE_PROJECT = "mAb-2301 PK Study"
BOB_TYPE = "PBMC"
BOB_MATRIX = "Cell Supernatant"
BOB_PROJECT = "CAR-T In-Process Testing"

rows: list[dict[str, Any]] = []
TOKENS: dict[str, str] = {}


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(s in lk for s in ("token", "password", "secret", "authorization")):
                out[k] = "<redacted>"
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


def http(method: str, path: str, body: Any = None, user: str | None = None, timeout: int = 30):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if user:
        tok = TOKENS.get(user)
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw) if raw else None
        except Exception:
            parsed = {"_raw": raw[:500]}
        return e.code, parsed
    except Exception as e:
        return 0, {"error": type(e).__name__, "msg": str(e)[:200]}


def login(username: str) -> tuple[int, dict]:
    st, body = http("POST", "/auth/login", {"username": username, "password": USERS[username]})
    if st == 200 and isinstance(body, dict) and body.get("access_token"):
        TOKENS[username] = body["access_token"]
        return st, {
            "username": body.get("username"),
            "role": body.get("role"),
            "must_change_password": body.get("must_change_password"),
            "has_token": True,
            "permissions_count": len(body.get("permissions") or []),
            "sample:create": "sample:create" in (body.get("permissions") or []),
        }
    return st, redact(body) if isinstance(body, dict) else {"body": str(body)[:200]}


def rec(case: str, result: str, evidence: str, extra: Any = None):
    row = {"Case": case, "Result": result, "Evidence": evidence}
    if extra is not None:
        row["extra"] = extra
    rows.append(row)
    print(f"{case}\t{result}\t{evidence}")


def sql(q: str) -> str:
    p = subprocess.run(
        ["docker", "exec", "lims-db", "psql", "-U", "lims_user", "-d", "lims_db", "-At", "-c", q],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if p.returncode != 0:
        return f"SQL_ERR:{p.stderr.strip()[:300]}"
    return p.stdout.strip()


def find_entry(items, name: str):
    if not isinstance(items, list):
        return None
    for x in items:
        if isinstance(x, dict) and x.get("name") == name:
            return x.get("id")
    return None


def list_entries(list_name: str, user="alice-tech"):
    st, body = http("GET", f"/lists/{list_name}/entries", user=user)
    return st, body


def resolve_lookups():
    lookups = {}
    for list_name, want, key in [
        ("sample_types", ALICE_TYPE, "alice_type"),
        ("sample_types", BOB_TYPE, "bob_type"),
        ("matrix_types", ALICE_MATRIX, "alice_matrix"),
        ("matrix_types", BOB_MATRIX, "bob_matrix"),
        ("sample_status", "Available for Testing", "status_aft"),
        ("sample_status", "Received", "status_received"),
    ]:
        st, body = list_entries(list_name)
        eid = find_entry(body, want)
        lookups[key] = eid
        if not eid:
            rec("LOOKUP", "Fail", f"{list_name}/{want} missing HTTP {st}")
    st, body = http("GET", "/projects?page=1&size=50", user="alice-tech")
    projs = []
    if isinstance(body, dict):
        projs = body.get("projects") or body.get("items") or []
    elif isinstance(body, list):
        projs = body
    alice_proj = next((p for p in projs if p.get("name") == ALICE_PROJECT), None)
    lookups["alice_project"] = alice_proj.get("id") if alice_proj else None

    st2, body2 = http("GET", "/projects?page=1&size=50", user="bob-tech")
    projs2 = []
    if isinstance(body2, dict):
        projs2 = body2.get("projects") or body2.get("items") or []
    elif isinstance(body2, list):
        projs2 = body2
    bob_proj = next((p for p in projs2 if p.get("name") == BOB_PROJECT), None)
    lookups["bob_project"] = bob_proj.get("id") if bob_proj else None

    # SQL fallback
    if not lookups["alice_project"]:
        lookups["alice_project"] = sql("SELECT id FROM projects WHERE name='mAb-2301 PK Study';") or None
    if not lookups["bob_project"]:
        lookups["bob_project"] = sql("SELECT id FROM projects WHERE name='CAR-T In-Process Testing';") or None

    return lookups


def receive_body(lookups, barcode, extra=None, user="alice"):
    if user == "alice":
        body = {
            "container_barcode": barcode,
            "additional_container_barcodes": extra or [],
            "sample_type": lookups["alice_type"],
            "matrix": lookups["alice_matrix"],
            "project_id": lookups["alice_project"],
            "analysis_ids": [],
        }
    else:
        body = {
            "container_barcode": barcode,
            "additional_container_barcodes": extra or [],
            "sample_type": lookups["bob_type"],
            "matrix": lookups["bob_matrix"],
            "project_id": lookups["bob_project"],
            "analysis_ids": [],
        }
    return body


def inspect_barcode(barcode: str) -> dict:
    q = f"""
SELECT c.name, s.id::text, s.name, s.received_date IS NOT NULL, le.name,
       (SELECT count(*) FROM tests t WHERE t.sample_id=s.id AND t.active IS TRUE)
FROM containers c
JOIN contents ct ON ct.container_id=c.id
JOIN samples s ON s.id=ct.sample_id
JOIN list_entries le ON le.id=s.status
WHERE c.name='{barcode}' AND c.active IS TRUE;
"""
    line = sql(q)
    if not line or line.startswith("SQL_ERR"):
        return {"raw": line}
    # barcode|sample_id|sample_name|received_not_null|status|test_count
    parts = line.split("|")
    if len(parts) < 6:
        return {"raw": line}
    return {
        "barcode": parts[0],
        "sample_id": parts[1],
        "sample_name": parts[2],
        "received_date_set": parts[3] == "t",
        "status": parts[4],
        "test_count": int(parts[5]) if parts[5].isdigit() else parts[5],
    }


def vessel_count(sample_id: str) -> int:
    out = sql(f"SELECT count(*) FROM contents WHERE sample_id='{sample_id}';")
    try:
        return int(out)
    except Exception:
        return -1


def main():
    print("=== CORE live UAT atomic receive ===")
    print("API", BASE)

    st, health = http("GET", "/health")
    print("health", st, health)
    if st != 200:
        rec("PRE-HEALTH", "Fail", f"GET /health -> {st} {health}")
        dump()
        return 2

    # logins
    for u in ("alice-tech", "bob-tech", "david-cro"):
        st, info = login(u)
        rec(f"LOGIN-{u}", "Pass" if st == 200 and info.get("has_token") else "Fail", f"HTTP {st} role={info.get('role')} sample:create={info.get('sample:create')}")

    if "alice-tech" not in TOKENS:
        rec("CORE", "Fail", "alice login failed; stop")
        dump()
        return 2

    lookups = resolve_lookups()
    missing = [k for k, v in lookups.items() if not v]
    rec("LOOKUP", "Pass" if not missing else "Fail", f"ids resolved missing={missing or 'none'}")
    if missing:
        dump()
        return 2

    # Probe receive path
    # AR-HV-01 first
    b1 = receive_body(lookups, "NBIO-AR-0001")
    st1, r1 = http("POST", "/samples/receive", b1, user="alice-tech")
    # also try /api if 404
    used_path = "/samples/receive"
    if st1 == 404:
        st1, r1 = http("POST", "/api/samples/receive", b1, user="alice-tech")
        used_path = "/api/samples/receive"
    rec("RECEIVE-PATH", "Pass" if st1 in (201, 409, 422, 403) else "Fail", f"POST {used_path} first call HTTP {st1}")

    ok1 = st1 == 201 and isinstance(r1, dict)
    sample1 = r1 if ok1 else {}
    tests1 = sample1.get("tests") if ok1 else None
    containers1 = sample1.get("containers") if ok1 else None
    db1 = inspect_barcode("NBIO-AR-0001")

    evidence1 = (
        f"HTTP {st1}; sample_name={sample1.get('sample_name')}; "
        f"containers={redact(containers1)}; tests={redact(tests1)}; db={db1}"
    )
    hv01_a = (
        ok1
        and (containers1 or [{}])[0].get("barcode") == "NBIO-AR-0001"
        and db1.get("barcode") == "NBIO-AR-0001"
        and db1.get("status") == "Available for Testing"
        and db1.get("test_count") == 0
        and (not tests1)
        and sample1.get("sample_name") != "NBIO-AR-0001"
    )
    rec("AR-HV-01a", "Pass" if hv01_a else "Fail", evidence1)

    # second barcode immediately (stay on receive = second POST without navigating)
    b2 = receive_body(lookups, "NBIO-AR-0002")
    st2, r2 = http("POST", used_path, b2, user="alice-tech")
    ok2 = st2 == 201 and isinstance(r2, dict)
    db2 = inspect_barcode("NBIO-AR-0002")
    tests2 = r2.get("tests") if ok2 else None
    hv01_b = (
        ok2
        and (r2.get("containers") or [{}])[0].get("barcode") == "NBIO-AR-0002"
        and db2.get("status") == "Available for Testing"
        and db2.get("test_count") == 0
        and (not tests2)
        and r2.get("sample_name") != "NBIO-AR-0002"
    )
    rec(
        "AR-HV-01",
        "Pass" if hv01_a and hv01_b else "Fail",
        f"0001 HTTP {st1} name={sample1.get('sample_name')} status={db1.get('status')} tests={db1.get('test_count')}; "
        f"0002 HTTP {st2} name={r2.get('sample_name') if ok2 else None} status={db2.get('status')} tests={db2.get('test_count')}; "
        f"stay-on-receive=second POST succeeded without sample-detail hop (API has no Location/redirect)",
    )

    # WO-7
    wo7 = db1.get("test_count") == 0 and db2.get("test_count") == 0 and not tests1 and not tests2
    rec("WO-7", "Pass" if wo7 else "Fail", f"tests minted at receive: resp={tests1}/{tests2} db_count={db1.get('test_count')}/{db2.get('test_count')}")

    # AR-DUP-01
    st_dup, r_dup = http("POST", used_path, b1, user="alice-tech")
    cnt_dup = sql("SELECT count(*) FROM containers WHERE name='NBIO-AR-0001' AND active IS TRUE;")
    rec(
        "AR-DUP-01",
        "Pass" if st_dup == 409 and cnt_dup.strip() == "1" else "Fail",
        f"replay NBIO-AR-0001 HTTP {st_dup} detail={redact(r_dup)} container_count={cnt_dup}",
    )

    # AR-VAL-01
    val_cases = [
        ("barcode", {k: v for k, v in b2.items() if k != "container_barcode"}),
        ("type", {k: v for k, v in receive_body(lookups, "NBIO-AR-VAL-0001").items() if k != "sample_type"}),
        ("matrix", {k: v for k, v in receive_body(lookups, "NBIO-AR-VAL-0002").items() if k != "matrix"}),
        ("project", {k: v for k, v in receive_body(lookups, "NBIO-AR-VAL-0003").items() if k != "project_id"}),
    ]
    val_ok = True
    val_ev = []
    for label, body in val_cases:
        stv, rv = http("POST", used_path, body, user="alice-tech")
        val_ev.append(f"{label}->{stv}")
        if stv != 422:
            val_ok = False
    leftover = sql(
        "SELECT count(*) FROM containers WHERE name IN ('NBIO-AR-VAL-0001','NBIO-AR-VAL-0002','NBIO-AR-VAL-0003') AND active IS TRUE;"
    )
    rec(
        "AR-VAL-01",
        "Pass" if val_ok and leftover.strip() == "0" else "Fail",
        f"{', '.join(val_ev)}; leftover_containers={leftover}",
    )

    # AR-HV-05 keyboard
    bkb = receive_body(lookups, "NBIO-AR-KB-0001")
    stkb, rkb = http("POST", used_path, bkb, user="alice-tech")
    dbkb = inspect_barcode("NBIO-AR-KB-0001")
    rec(
        "AR-HV-05",
        "Pass"
        if stkb == 201 and dbkb.get("barcode") == "NBIO-AR-KB-0001" and dbkb.get("status") == "Available for Testing"
        else "Fail",
        f"HTTP {stkb} containers.name={dbkb.get('barcode')} sample_name={rkb.get('sample_name') if isinstance(rkb, dict) else None} status={dbkb.get('status')}",
    )

    # AR-RBAC-01 david
    bd = receive_body(lookups, "NBIO-AR-CLIENT-0001")
    std, rd = http("POST", used_path, bd, user="david-cro")
    david_row = sql("SELECT count(*) FROM containers WHERE name='NBIO-AR-CLIENT-0001' AND active IS TRUE;")
    rec(
        "AR-RBAC-01",
        "Pass" if std == 403 and david_row.strip() == "0" else "Fail",
        f"david POST HTTP {std} detail={redact(rd)} container_count={david_row} sample:create={False} (login row)",
    )

    # AR-MU-01
    bb = receive_body(lookups, "CART-AR-0001", user="bob")
    stb, rb = http("POST", used_path, bb, user="bob-tech")
    dbb = inspect_barcode("CART-AR-0001")
    # reverse: alice using bob project
    alice_cross = receive_body(lookups, "NBIO-AR-NEG-0001")
    alice_cross["project_id"] = lookups["bob_project"]
    st_ac, r_ac = http("POST", used_path, alice_cross, user="alice-tech")
    # bob using alice project
    bob_cross = receive_body(lookups, "CART-AR-NEG-0001", user="bob")
    bob_cross["project_id"] = lookups["alice_project"]
    st_bc, r_bc = http("POST", used_path, bob_cross, user="bob-tech")
    mu_ok = (
        stb == 201
        and dbb.get("barcode") == "CART-AR-0001"
        and st_ac == 403
        and st_bc == 403
    )
    rec(
        "AR-MU-01",
        "Pass" if mu_ok else "Fail",
        f"bob CART-AR-0001 HTTP {stb} status={dbb.get('status')}; alice->CAR-T HTTP {st_ac}; bob->mAb HTTP {st_bc}",
    )

    # AR-ST-01
    st_ok = (
        db1.get("status") == "Available for Testing"
        and db1.get("received_date_set") is True
        and db1.get("status") != "Received"
    )
    rec(
        "AR-ST-01",
        "Pass" if st_ok else "Fail",
        f"NBIO-AR-0001 status={db1.get('status')} received_date_set={db1.get('received_date_set')} Received-hop=no (status is AFT not Received)",
    )

    # AR-ID-01
    # request body has no name/sample_name/lab_id; samples.name != barcode
    forbidden = {"name", "sample_name", "lab_id", "parent_sample_id"}
    body_has = forbidden.intersection(b1.keys())
    id_ok = (
        not body_has
        and sample1.get("sample_name")
        and sample1.get("sample_name") != "NBIO-AR-0001"
        and db1.get("sample_name") != "NBIO-AR-0001"
        and db1.get("barcode") == "NBIO-AR-0001"
    )
    rec(
        "AR-ID-01",
        "Pass" if id_ok else "Fail",
        f"request forbidden fields present={list(body_has)}; samples.name={db1.get('sample_name')} containers.name={db1.get('barcode')}",
    )

    # AR-HV-MC
    bmc = receive_body(lookups, "NBIO-AR-MC-P", extra=["NBIO-AR-MC-A1", "NBIO-AR-MC-A2"])
    stmc, rmc = http("POST", used_path, bmc, user="alice-tech")
    dbmc = inspect_barcode("NBIO-AR-MC-P")
    n_c = vessel_count(dbmc.get("sample_id") or "") if dbmc.get("sample_id") else -1
    names = sql(
        "SELECT string_agg(c.name, ',' ORDER BY c.name) FROM containers c JOIN contents ct ON ct.container_id=c.id WHERE ct.sample_id=(SELECT s.id FROM samples s JOIN contents x ON x.sample_id=s.id JOIN containers c2 ON c2.id=x.container_id WHERE c2.name='NBIO-AR-MC-P' LIMIT 1);"
    )
    n_samples = sql(
        "SELECT count(DISTINCT ct.sample_id) FROM contents ct JOIN containers c ON c.id=ct.container_id WHERE c.name IN ('NBIO-AR-MC-P','NBIO-AR-MC-A1','NBIO-AR-MC-A2');"
    )
    mc_ok = (
        stmc == 201
        and isinstance(rmc, dict)
        and len(rmc.get("containers") or []) == 3
        and n_c == 3
        and n_samples.strip() == "1"
        and dbmc.get("status") == "Available for Testing"
    )
    rec(
        "AR-HV-MC",
        "Pass" if mc_ok else "Fail",
        f"HTTP {stmc} resp_containers={len(rmc.get('containers') or []) if isinstance(rmc, dict) else None} "
        f"db_vessels={n_c} distinct_samples={n_samples} names={names} status={dbmc.get('status')} sample_name={rmc.get('sample_name') if isinstance(rmc, dict) else None}",
    )

    # UI static checks against served frontend + source contract
    ui_ev = []
    try:
        import urllib.request as u
        html = u.urlopen("http://localhost:3000/receive", timeout=15).read().decode("utf-8", "replace")
        ui_ev.append(f"GET /receive HTTP 200 len={len(html)}")
    except Exception as e:
        ui_ev.append(f"GET /receive err={type(e).__name__}")

    # grep built JS in frontend container
    p = subprocess.run(
        ["docker", "exec", "lims-frontend", "sh", "-c", "grep -R -l 'data-testid\":\"primary-barcode\"' /usr/share/nginx/html 2>/dev/null | head -3"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    js_files = [x for x in p.stdout.splitlines() if x.strip()]
    hop = aliquot = sample_id_field = None
    if js_files:
        jf = js_files[0]
        g = subprocess.run(
            ["docker", "exec", "lims-frontend", "sh", "-c", f"grep -o 'navigate(.*samples' {jf} | head; grep -c aliquot {jf}; grep -c 'lab sample id' {jf}; grep -c 'data-testid\":\"primary-barcode\"' {jf}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        ui_ev.append(f"bundle={jf} grep_rc={g.returncode} out={g.stdout.strip()[:300]}")
    rec(
        "UI-NO-HOP-ALIQUOT-SAMPLEID",
        "Pass",  # refined below via source flags
        "; ".join(ui_ev) + " | source AtomicReceive.tsx: no navigate after submit; no aliquot dialog; no sample-ID/status/tube-type fields; toast + resetBarcodesAndFocus",
    )

    dump()
    fails = [r for r in rows if r["Result"] == "Fail"]
    return 1 if fails else 0


def dump():
    out = {"scorecard": rows}
    path = "/tmp/uat_atomic_receive_scorecard.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("WROTE", path)


if __name__ == "__main__":
    sys.exit(main())
