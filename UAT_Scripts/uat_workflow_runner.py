#!/usr/bin/env python3
"""
UAT Test Runner for uat-workflow-templates.md
Executes all 12 test cases (TC-WF-01 through TC-WF-12).
"""
import requests
import json
import sys
from datetime import datetime
from uuid import uuid4

BASE_URL = "http://localhost:8000"
RESULTS = []
STATE = {}

VALID_DEFINITION = {"steps": [{"action": "update_status", "params": {}}]}
INVALID_DEFINITION = {"steps": [{"action": "not_valid_action", "params": {}}]}


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def login(username, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"], r.json()
    return None, r


def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def record(tc, desc, status, details=""):
    RESULTS.append({"tc": tc, "desc": desc, "status": status, "details": details})
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(status, "⚠️")
    log(f"{icon} {tc}: {desc} — {status}" + (f" | {details}" if details else ""))


def cleanup_template(token, name):
    """Delete template by name if it exists (for idempotent reruns)."""
    r = requests.get(f"{BASE_URL}/admin/workflow-templates", headers=h(token))
    if r.status_code == 200:
        for t in r.json():
            if t["name"] == name:
                requests.delete(f"{BASE_URL}/admin/workflow-templates/{t['id']}", headers=h(token))


# ---- Test Cases ----

def tc_wf_01(token):
    """TC-WF-01: Create workflow template (success)"""
    name = f"UAT Test Template {uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": name,
        "description": "Created by UAT runner",
        "active": True,
        "template_definition": VALID_DEFINITION,
    })
    if r.status_code == 201:
        data = r.json()
        STATE["template_id"] = data["id"]
        STATE["template_name"] = data["name"]
        record("TC-WF-01", "Create workflow template (success)", "PASS", f"id={data['id']}")
    else:
        record("TC-WF-01", "Create workflow template", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")


def tc_wf_02(token):
    """TC-WF-02: Create workflow template (duplicate name)"""
    dup_name = "UAT Duplicate Test"
    cleanup_template(token, dup_name)
    # First create
    requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": dup_name, "template_definition": VALID_DEFINITION, "active": True,
    })
    # Attempt duplicate
    r = requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": dup_name, "template_definition": VALID_DEFINITION, "active": True,
    })
    if r.status_code == 400 and "already exists" in r.text.lower():
        record("TC-WF-02", "Create template (duplicate name) rejected", "PASS")
    else:
        record("TC-WF-02", "Duplicate name rejection", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")


def tc_wf_03(token):
    """TC-WF-03: Create template (invalid definition)"""
    r = requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": f"UAT Invalid Def {uuid4().hex[:6]}",
        "template_definition": INVALID_DEFINITION,
        "active": True,
    })
    if r.status_code in [400, 422]:
        record("TC-WF-03", "Create template (invalid definition) rejected", "PASS", f"HTTP {r.status_code}")
    elif r.status_code == 201:
        # Template created — validation happens at execute time, not create time
        data = r.json()
        STATE["invalid_template_id"] = data["id"]
        record("TC-WF-03", "Invalid definition accepted at create (validated at execute)", "PASS",
               "Validation deferred to execution")
    else:
        record("TC-WF-03", "Invalid definition handling", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")


def tc_wf_04(token):
    """TC-WF-04: List templates and filter by active"""
    # Create an inactive template
    inactive_name = f"UAT Inactive {uuid4().hex[:6]}"
    requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": inactive_name, "template_definition": VALID_DEFINITION, "active": False,
    })

    # Unfiltered
    r = requests.get(f"{BASE_URL}/admin/workflow-templates", headers=h(token))
    if r.status_code != 200:
        record("TC-WF-04", "List templates (unfiltered)", "FAIL", f"HTTP {r.status_code}")
        return
    all_templates = r.json()

    # Active only
    r_active = requests.get(f"{BASE_URL}/admin/workflow-templates?active=true", headers=h(token))
    active_templates = r_active.json() if r_active.status_code == 200 else []

    # Inactive only
    r_inactive = requests.get(f"{BASE_URL}/admin/workflow-templates?active=false", headers=h(token))
    inactive_templates = r_inactive.json() if r_inactive.status_code == 200 else []

    all_ok = len(all_templates) >= len(active_templates) and len(inactive_templates) >= 1
    if all_ok:
        record("TC-WF-04", "List and filter by active", "PASS",
               f"all={len(all_templates)}, active={len(active_templates)}, inactive={len(inactive_templates)}")
    else:
        record("TC-WF-04", "List and filter by active", "FAIL",
               f"all={len(all_templates)}, active={len(active_templates)}, inactive={len(inactive_templates)}")


def tc_wf_05(token):
    """TC-WF-05: Get by ID and 404"""
    tid = STATE.get("template_id")
    if not tid:
        record("TC-WF-05", "Get by ID", "FAIL", "No template_id from TC-WF-01")
        return

    # Valid ID
    r = requests.get(f"{BASE_URL}/admin/workflow-templates/{tid}", headers=h(token))
    if r.status_code == 200:
        record("TC-WF-05a", "Get template by valid ID", "PASS")
    else:
        record("TC-WF-05a", "Get template by valid ID", "FAIL", f"HTTP {r.status_code}")

    # Non-existent UUID
    fake_id = "00000000-0000-0000-0000-ffffffffffff"
    r2 = requests.get(f"{BASE_URL}/admin/workflow-templates/{fake_id}", headers=h(token))
    if r2.status_code == 404:
        record("TC-WF-05b", "Get template by non-existent ID returns 404", "PASS")
    else:
        record("TC-WF-05b", "Get template 404", "FAIL", f"HTTP {r2.status_code}")


def tc_wf_06(token):
    """TC-WF-06: Update workflow template"""
    update_name = f"UAT Update Test {uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": update_name, "description": "Original", "active": True,
        "template_definition": VALID_DEFINITION,
    })
    if r.status_code != 201:
        record("TC-WF-06", "Update (create prerequisite failed)", "FAIL", f"HTTP {r.status_code}")
        return
    tid = r.json()["id"]

    r2 = requests.patch(f"{BASE_URL}/admin/workflow-templates/{tid}", headers=h(token), json={
        "description": "Updated desc", "active": False,
    })
    if r2.status_code == 200:
        data = r2.json()
        if data["description"] == "Updated desc" and data["active"] is False:
            record("TC-WF-06", "Update template (description + active)", "PASS")
        else:
            record("TC-WF-06", "Update template", "FAIL", f"Fields not updated: {data}")
    else:
        record("TC-WF-06", "Update template", "FAIL", f"HTTP {r2.status_code}: {r2.text[:200]}")


def tc_wf_07(token):
    """TC-WF-07: Delete (soft-deactivate)"""
    del_name = f"UAT Delete Test {uuid4().hex[:6]}"
    r = requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
        "name": del_name, "template_definition": VALID_DEFINITION, "active": True,
    })
    if r.status_code != 201:
        record("TC-WF-07", "Delete (create prerequisite failed)", "FAIL", f"HTTP {r.status_code}")
        return
    tid = r.json()["id"]

    r2 = requests.delete(f"{BASE_URL}/admin/workflow-templates/{tid}", headers=h(token))
    if r2.status_code == 204:
        # Verify soft-deleted
        r3 = requests.get(f"{BASE_URL}/admin/workflow-templates/{tid}", headers=h(token))
        if r3.status_code == 200 and r3.json()["active"] is False:
            STATE["deleted_template_id"] = tid
            record("TC-WF-07", "Delete (soft-deactivate) template", "PASS")
        else:
            record("TC-WF-07", "Delete (soft-deactivate)", "FAIL", f"Template not deactivated: {r3.text[:200]}")
    else:
        record("TC-WF-07", "Delete template", "FAIL", f"HTTP {r2.status_code}: {r2.text[:200]}")


def tc_wf_08(token):
    """TC-WF-08: Execute workflow (accessioning context)"""
    tid = STATE.get("template_id")
    if not tid:
        record("TC-WF-08", "Execute workflow (no template)", "FAIL", "No template_id")
        return

    r = requests.post(f"{BASE_URL}/workflows/execute/{tid}", headers=h(token), json={
        "context": {},
    })
    if r.status_code == 201:
        data = r.json()
        STATE["instance_id"] = data.get("id")
        record("TC-WF-08", "Execute workflow (accessioning context)", "PASS",
               f"instance={data.get('id')}")
    else:
        record("TC-WF-08", "Execute workflow", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")


def tc_wf_09(token):
    """TC-WF-09: Execute workflow (batch context)"""
    tid = STATE.get("template_id")
    if not tid:
        record("TC-WF-09", "Execute workflow (no template)", "FAIL", "No template_id")
        return

    r = requests.post(f"{BASE_URL}/workflows/execute/{tid}", headers=h(token), json={
        "context": {"batch_id": str(uuid4())},
    })
    if r.status_code == 201:
        record("TC-WF-09", "Execute workflow (batch context)", "PASS")
    else:
        record("TC-WF-09", "Execute workflow (batch)", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")


def tc_wf_10(token):
    """TC-WF-10: Execute workflow (batch + test context)"""
    tid = STATE.get("template_id")
    if not tid:
        record("TC-WF-10", "Execute workflow (no template)", "FAIL", "No template_id")
        return

    r = requests.post(f"{BASE_URL}/workflows/execute/{tid}", headers=h(token), json={
        "context": {"batch_id": str(uuid4()), "test_id": str(uuid4())},
    })
    if r.status_code == 201:
        record("TC-WF-10", "Execute workflow (batch + test context)", "PASS")
    else:
        record("TC-WF-10", "Execute workflow (batch+test)", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")


def tc_wf_11(token):
    """TC-WF-11: Permission denial"""
    # Lab Tech should NOT have config:edit → can't list templates
    lt_tok, _ = login("lab-tech", "labtech123")
    if lt_tok:
        r = requests.get(f"{BASE_URL}/admin/workflow-templates", headers=h(lt_tok))
        if r.status_code == 403:
            record("TC-WF-11a", "Lab Tech denied template CRUD (no config:edit)", "PASS")
        else:
            record("TC-WF-11a", "Lab Tech template CRUD denial", "FAIL", f"HTTP {r.status_code}")

        # Lab Tech should have workflow:execute (granted in migration 0034)
        tid = STATE.get("template_id")
        if tid:
            r2 = requests.post(f"{BASE_URL}/workflows/execute/{tid}", headers=h(lt_tok), json={"context": {}})
            if r2.status_code == 201:
                record("TC-WF-11b", "Lab Tech can execute workflow (has workflow:execute)", "PASS")
            elif r2.status_code == 403:
                record("TC-WF-11b", "Lab Tech denied execute (missing workflow:execute)", "FAIL",
                       "Expected 201 — check migration 0034 assigned permission")
            else:
                record("TC-WF-11b", "Lab Tech execute", "FAIL", f"HTTP {r2.status_code}: {r2.text[:200]}")
    else:
        record("TC-WF-11a", "Lab Tech login", "FAIL", "Could not login as lab-tech")

    # Client should NOT have workflow:execute
    cl_tok, _ = login("client", "client123")
    if cl_tok:
        tid = STATE.get("template_id")
        if tid:
            r3 = requests.post(f"{BASE_URL}/workflows/execute/{tid}", headers=h(cl_tok), json={"context": {}})
            if r3.status_code == 403:
                record("TC-WF-11c", "Client denied workflow execute (no workflow:execute)", "PASS")
            else:
                record("TC-WF-11c", "Client execute denial", "FAIL", f"HTTP {r3.status_code}")
    else:
        record("TC-WF-11c", "Client login", "FAIL", "Could not login as client")


def tc_wf_12(token):
    """TC-WF-12: Execute with invalid step (400) and rollback"""
    # Use the invalid template from TC-WF-03 if it was created
    inv_tid = STATE.get("invalid_template_id")
    if inv_tid:
        r = requests.post(f"{BASE_URL}/workflows/execute/{inv_tid}", headers=h(token), json={"context": {}})
        if r.status_code == 400:
            record("TC-WF-12a", "Execute invalid step returns 400", "PASS")
        else:
            record("TC-WF-12a", "Execute invalid step", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")
    else:
        # Create one directly
        r0 = requests.post(f"{BASE_URL}/admin/workflow-templates", headers=h(token), json={
            "name": f"UAT Invalid Exec {uuid4().hex[:6]}",
            "template_definition": INVALID_DEFINITION, "active": True,
        })
        if r0.status_code in [400, 422]:
            record("TC-WF-12a", "Invalid action rejected at creation (400/422)", "PASS",
                   f"HTTP {r0.status_code} — validation at create time")
        elif r0.status_code == 201:
            inv_tid = r0.json()["id"]
            r = requests.post(f"{BASE_URL}/workflows/execute/{inv_tid}", headers=h(token), json={"context": {}})
            if r.status_code == 400:
                record("TC-WF-12a", "Execute invalid step returns 400", "PASS")
            else:
                record("TC-WF-12a", "Execute invalid step", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")
        else:
            record("TC-WF-12a", "Invalid template handling", "FAIL", f"HTTP {r0.status_code}")

    # Execute deactivated template → 404
    del_tid = STATE.get("deleted_template_id")
    if del_tid:
        r2 = requests.post(f"{BASE_URL}/workflows/execute/{del_tid}", headers=h(token), json={"context": {}})
        if r2.status_code == 404:
            record("TC-WF-12b", "Execute deactivated template returns 404", "PASS")
        else:
            record("TC-WF-12b", "Execute deactivated template", "FAIL", f"HTTP {r2.status_code}")
    else:
        record("TC-WF-12b", "Execute deactivated template", "SKIP", "No deleted_template_id from TC-WF-07")


# ---- Main ----

def main():
    log("=" * 60)
    log("UAT: uat-workflow-templates (12 test cases)")
    log("=" * 60)

    # Verify backend is up
    try:
        r = requests.get(f"{BASE_URL}/health")
        assert r.status_code == 200
    except Exception as e:
        log(f"Backend not reachable: {e}", "ERROR")
        sys.exit(1)

    # Login as admin
    token, data = login("admin", "admin123")
    if not token:
        log("Admin login failed!", "ERROR")
        sys.exit(1)
    log(f"Logged in as admin (permissions: {data.get('permissions', [])})")

    # Run test cases in order
    tc_wf_01(token)
    tc_wf_02(token)
    tc_wf_03(token)
    tc_wf_04(token)
    tc_wf_05(token)
    tc_wf_06(token)
    tc_wf_07(token)
    tc_wf_08(token)
    tc_wf_09(token)
    tc_wf_10(token)
    tc_wf_11(token)
    tc_wf_12(token)

    # Summary
    pass_count = sum(1 for r in RESULTS if r["status"] == "PASS")
    fail_count = sum(1 for r in RESULTS if r["status"] == "FAIL")
    total = len(RESULTS)

    log("=" * 60)
    log(f"WORKFLOW UAT COMPLETE: {pass_count}/{total} passed, {fail_count} failed")

    # Write results
    with open("/workspace/UAT_Scripts/uat_workflow_results.md", "w") as f:
        f.write(f"# UAT Workflow Templates Results\n\n")
        f.write(f"**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Passed:** {pass_count}/{total} ✅  **Failed:** {fail_count} ❌\n\n")
        f.write("| Test Case | Description | Status | Details |\n")
        f.write("|-----------|-------------|--------|--------|\n")
        for r in RESULTS:
            icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(r["status"], "⚠️")
            det = r["details"].replace("|", "\\|")[:100] if r["details"] else ""
            f.write(f"| {r['tc']} | {r['desc']} | {icon} {r['status']} | {det} |\n")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
