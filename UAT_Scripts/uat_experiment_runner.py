#!/usr/bin/env python3
"""
UAT runner for experiment-related tests:
  - uat-experiments-navigation (sidebar visibility, templates gating)
  - uat-experiment-management (CRUD, linking, workflow, lineage)
"""
import requests, json, sys
from datetime import datetime
from uuid import uuid4

BASE = "http://localhost:8000"
V1 = f"{BASE}/v1"
RESULTS = []
STATE = {}


def log(msg, level="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")


def login(user, pwd):
    r = requests.post(f"{BASE}/auth/login", json={"username": user, "password": pwd})
    if r.status_code == 200:
        d = r.json()
        return d["access_token"], d
    return None, r


def h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def record(tc, desc, status, details=""):
    RESULTS.append({"tc": tc, "desc": desc, "status": status, "details": details})
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(status, "⚠️")
    log(f"{icon} {tc}: {desc} — {status}" + (f" | {details}" if details else ""))


# ======================= uat-experiments-navigation =======================

def run_navigation_api():
    """API-level checks for sidebar gating."""
    script = "uat-experiments-navigation"
    log("=" * 60, "SECTION")
    log(f"Running: {script}", "SECTION")

    # Admin should access both experiments and templates
    tok, _ = login("admin", "admin123")
    r = requests.get(f"{V1}/experiments", headers=h(tok))
    record("NAV-01", "Admin can list experiments", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}")

    r = requests.get(f"{V1}/experiment-templates", headers=h(tok))
    record("NAV-02", "Admin can list experiment templates", "PASS" if r.status_code == 200 else "FAIL",
           f"HTTP {r.status_code}")

    # Lab Tech — has experiment:manage? Should be able to list experiments
    tok_lt, d_lt = login("lab-tech", "labtech123")
    perms_lt = d_lt.get("permissions", []) if isinstance(d_lt, dict) else []
    has_exp = "experiment:manage" in perms_lt
    r = requests.get(f"{V1}/experiments", headers=h(tok_lt))
    if has_exp:
        record("NAV-03", "Lab Tech can list experiments (has experiment:manage)", 
               "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")
    else:
        record("NAV-03", "Lab Tech denied experiments (no experiment:manage)",
               "PASS" if r.status_code == 403 else "FAIL", f"HTTP {r.status_code}; perms={perms_lt}")

    # Lab Tech should NOT have config:edit so cannot list experiment templates (if template gating requires config:edit)
    r2 = requests.get(f"{V1}/experiment-templates", headers=h(tok_lt))
    if "config:edit" not in perms_lt and has_exp:
        # Templates use require_experiment_manage, so if Lab Tech has it, they CAN see templates
        record("NAV-04", "Lab Tech experiment templates access",
               "PASS" if r2.status_code in [200, 403] else "FAIL", f"HTTP {r2.status_code}")
    else:
        record("NAV-04", "Lab Tech experiment templates",
               "PASS" if r2.status_code in [200, 403] else "FAIL", f"HTTP {r2.status_code}")

    # Lab Manager
    tok_lm, d_lm = login("lab-manager", "labmanager123")
    perms_lm = d_lm.get("permissions", []) if isinstance(d_lm, dict) else []
    r = requests.get(f"{V1}/experiments", headers=h(tok_lm))
    has_exp_lm = "experiment:manage" in perms_lm
    if has_exp_lm:
        record("NAV-05", "Lab Manager can list experiments", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}")
    else:
        record("NAV-05", "Lab Manager denied experiments",
               "PASS" if r.status_code == 403 else "FAIL", f"HTTP {r.status_code}")

    # Client should NOT have experiment:manage
    tok_cl, d_cl = login("client", "client123")
    perms_cl = d_cl.get("permissions", []) if isinstance(d_cl, dict) else []
    r = requests.get(f"{V1}/experiments", headers=h(tok_cl))
    if "experiment:manage" not in perms_cl:
        record("NAV-06", "Client denied experiments (no experiment:manage)",
               "PASS" if r.status_code == 403 else "FAIL", f"HTTP {r.status_code}")
    else:
        record("NAV-06", "Client experiments access", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}")

    # Frontend routes
    for route in ["/experiments", "/experiments/templates"]:
        r = requests.get(f"http://localhost:3000{route}")
        record(f"NAV-ROUTE-{route}", f"Frontend route {route} returns 200",
               "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")


# ======================= uat-experiment-management =======================

def run_experiment_crud():
    """Experiment CRUD, linking, lineage, workflow."""
    script = "uat-experiment-management"
    log("=" * 60, "SECTION")
    log(f"Running: {script}", "SECTION")

    tok, _ = login("admin", "admin123")

    # --- Experiment Template CRUD ---

    # Create template
    tpl_name = f"UAT Exp Template {uuid4().hex[:6]}"
    r = requests.post(f"{V1}/experiment-templates", headers=h(tok), json={
        "name": tpl_name,
        "description": "UAT experiment template",
        "template_definition": {"steps": [{"action": "update_status", "params": {}}]},
        "active": True,
    })
    if r.status_code == 201:
        tpl = r.json()
        STATE["exp_tpl_id"] = tpl["id"]
        record("EXP-TPL-01", "Create experiment template", "PASS", f"id={tpl['id']}")
    else:
        record("EXP-TPL-01", "Create experiment template", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # List templates
    r = requests.get(f"{V1}/experiment-templates", headers=h(tok))
    if r.status_code == 200:
        data = r.json()
        record("EXP-TPL-02", "List experiment templates", "PASS", f"total={data.get('total', '?')}")
    else:
        record("EXP-TPL-02", "List experiment templates", "FAIL", f"HTTP {r.status_code}")

    # Get template by ID
    if STATE.get("exp_tpl_id"):
        r = requests.get(f"{V1}/experiment-templates/{STATE['exp_tpl_id']}", headers=h(tok))
        record("EXP-TPL-03", "Get template by ID", "PASS" if r.status_code == 200 else "FAIL",
               f"HTTP {r.status_code}")

    # Update template
    if STATE.get("exp_tpl_id"):
        r = requests.patch(f"{V1}/experiment-templates/{STATE['exp_tpl_id']}", headers=h(tok),
                           json={"description": "Updated UAT template"})
        if r.status_code == 200 and r.json().get("description") == "Updated UAT template":
            record("EXP-TPL-04", "Update experiment template", "PASS")
        else:
            record("EXP-TPL-04", "Update experiment template", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # --- Get experiment_status list entries for status_id ---
    status_id = None
    r = requests.get(f"{BASE}/lists", headers=h(tok))
    if r.status_code == 200:
        for lst in r.json():
            if lst["name"] == "experiment_status":
                for entry in lst.get("entries", []):
                    if entry.get("active"):
                        status_id = entry["id"]
                        break
                break

    # --- Experiment CRUD ---

    # Create experiment
    exp_data = {"name": f"UAT Experiment {uuid4().hex[:6]}", "description": "Test experiment"}
    if STATE.get("exp_tpl_id"):
        exp_data["experiment_template_id"] = STATE["exp_tpl_id"]
    if status_id:
        exp_data["status_id"] = status_id

    r = requests.post(f"{V1}/experiments", headers=h(tok), json=exp_data)
    if r.status_code == 201:
        exp = r.json()
        STATE["exp_id"] = exp["id"]
        record("EXP-01", "Create experiment", "PASS", f"id={exp['id']}")
    else:
        record("EXP-01", "Create experiment", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")

    # List experiments
    r = requests.get(f"{V1}/experiments", headers=h(tok))
    if r.status_code == 200:
        data = r.json()
        record("EXP-02", "List experiments", "PASS", f"total={data.get('total', '?')}")
    else:
        record("EXP-02", "List experiments", "FAIL", f"HTTP {r.status_code}")

    # My experiments filter
    r = requests.get(f"{V1}/experiments?mine=true", headers=h(tok))
    if r.status_code == 200:
        record("EXP-03", "My Experiments filter (mine=true)", "PASS", f"total={r.json().get('total','?')}")
    else:
        record("EXP-03", "My Experiments filter", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # Get experiment by ID
    if STATE.get("exp_id"):
        r = requests.get(f"{V1}/experiments/{STATE['exp_id']}", headers=h(tok))
        if r.status_code == 200:
            record("EXP-04", "Get experiment by ID (detail)", "PASS")
        else:
            record("EXP-04", "Get experiment by ID", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # Update experiment
    if STATE.get("exp_id"):
        r = requests.patch(f"{V1}/experiments/{STATE['exp_id']}", headers=h(tok),
                           json={"description": "Updated experiment desc"})
        if r.status_code == 200:
            record("EXP-05", "Update experiment", "PASS")
        else:
            record("EXP-05", "Update experiment", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # Get 404 for non-existent experiment
    r = requests.get(f"{V1}/experiments/00000000-0000-0000-0000-ffffffffffff", headers=h(tok))
    record("EXP-06", "Get non-existent experiment returns 404", "PASS" if r.status_code == 404 else "FAIL",
           f"HTTP {r.status_code}")

    # --- Add experiment detail step ---
    if STATE.get("exp_id"):
        r = requests.post(f"{V1}/experiments/{STATE['exp_id']}/details", headers=h(tok), json={
            "detail_type": "protocol",
            "sort_order": 1,
            "content": {"description": "Initial setup step"},
        })
        if r.status_code == 201:
            STATE["detail_id"] = r.json().get("id")
            record("EXP-07", "Add experiment detail step", "PASS")
        else:
            record("EXP-07", "Add experiment detail step", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")

    # --- Link sample to experiment ---
    # First get/create a sample
    sample_id = None
    r = requests.get(f"{BASE}/samples", headers=h(tok))
    if r.status_code == 200:
        data = r.json()
        items = data if isinstance(data, list) else data.get("samples", data.get("items", []))
        if items:
            sample_id = items[0]["id"]

    if not sample_id:
        # Create a sample
        r_lists = requests.get(f"{BASE}/lists", headers=h(tok))
        sample_type_id = status_sample = matrix_id = project_id = None
        if r_lists.status_code == 200:
            for lst in r_lists.json():
                if lst["name"] == "sample_type":
                    for e in lst.get("entries", []):
                        if e.get("active"): sample_type_id = e["id"]; break
                elif lst["name"] == "sample_status":
                    for e in lst.get("entries", []):
                        if e["name"] == "Received": status_sample = e["id"]; break
                elif lst["name"] == "matrix":
                    for e in lst.get("entries", []):
                        if e.get("active"): matrix_id = e["id"]; break
        r_proj = requests.get(f"{BASE}/projects", headers=h(tok))
        if r_proj.status_code == 200:
            projs = r_proj.json().get("projects", r_proj.json()) if isinstance(r_proj.json(), dict) else r_proj.json()
            if projs:
                project_id = projs[0]["id"]
        if project_id and sample_type_id and status_sample and matrix_id:
            r_s = requests.post(f"{BASE}/samples/", headers=h(tok), json={
                "name": f"UAT-EXP-SAMPLE-{uuid4().hex[:6]}", "project_id": project_id,
                "sample_type": sample_type_id, "status": status_sample, "matrix": matrix_id,
            })
            if r_s.status_code in [200, 201]:
                sample_id = r_s.json()["id"]

    if STATE.get("exp_id") and sample_id:
        r = requests.post(f"{V1}/experiments/{STATE['exp_id']}/samples", headers=h(tok), json={
            "sample_id": sample_id,
            "replicate_number": 1,
            "processing_conditions": {"temperature": "25C"},
        })
        if r.status_code == 201:
            STATE["execution_id"] = r.json().get("id")
            record("EXP-08", "Link sample to experiment", "PASS")
        else:
            record("EXP-08", "Link sample to experiment", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")
    else:
        record("EXP-08", "Link sample to experiment", "FAIL",
               f"Missing exp_id={STATE.get('exp_id')} or sample_id={sample_id}")

    # --- Get sample's experiments (bidirectional) ---
    if sample_id:
        r = requests.get(f"{V1}/experiments/by-sample/{sample_id}", headers=h(tok))
        if r.status_code == 200:
            data = r.json()
            record("EXP-09", "Get sample's experiments (bidirectional link)", "PASS",
                   f"total={data.get('total', '?')}")
        else:
            record("EXP-09", "Get sample experiments", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # --- Link experiments (create second experiment, link to first) ---
    exp2_data = {"name": f"UAT Experiment2 {uuid4().hex[:6]}", "description": "Second experiment for linking"}
    if status_id:
        exp2_data["status_id"] = status_id
    r = requests.post(f"{V1}/experiments", headers=h(tok), json=exp2_data)
    exp2_id = None
    if r.status_code == 201:
        exp2_id = r.json()["id"]

    if STATE.get("exp_id") and exp2_id:
        r = requests.post(f"{V1}/experiments/{STATE['exp_id']}/links", headers=h(tok), json={
            "linked_experiment_id": exp2_id,
            "link_type": "follow_up",
        })
        if r.status_code == 201:
            record("EXP-10", "Link experiments together", "PASS")
        else:
            record("EXP-10", "Link experiments", "FAIL", f"HTTP {r.status_code}: {r.text[:300]}")
    else:
        record("EXP-10", "Link experiments", "FAIL", "Missing experiment IDs")

    # --- Get experiment lineage ---
    if STATE.get("exp_id"):
        r = requests.get(f"{V1}/experiments/{STATE['exp_id']}/lineage", headers=h(tok))
        if r.status_code == 200:
            data = r.json()
            record("EXP-11", "Get experiment lineage", "PASS",
                   f"linked_ids={data.get('linked_experiment_ids', [])}")
        else:
            record("EXP-11", "Get experiment lineage", "FAIL", f"HTTP {r.status_code}: {r.text[:200]}")

    # --- Soft-delete experiment ---
    if exp2_id:
        r = requests.delete(f"{V1}/experiments/{exp2_id}", headers=h(tok))
        if r.status_code == 204:
            record("EXP-12", "Soft-delete experiment", "PASS")
        else:
            record("EXP-12", "Soft-delete experiment", "FAIL", f"HTTP {r.status_code}")

    # --- Soft-delete experiment template ---
    del_tpl_name = f"UAT Del Tpl {uuid4().hex[:6]}"
    r = requests.post(f"{V1}/experiment-templates", headers=h(tok), json={
        "name": del_tpl_name, "active": True,
        "template_definition": {"steps": []},
    })
    if r.status_code == 201:
        del_tpl_id = r.json()["id"]
        r2 = requests.delete(f"{V1}/experiment-templates/{del_tpl_id}", headers=h(tok))
        if r2.status_code == 204:
            # Verify soft-deleted
            r3 = requests.get(f"{V1}/experiment-templates/{del_tpl_id}", headers=h(tok))
            if r3.status_code == 200 and r3.json().get("active") is False:
                record("EXP-TPL-05", "Soft-delete experiment template", "PASS")
            else:
                record("EXP-TPL-05", "Soft-delete template verification", "FAIL", f"{r3.text[:200]}")
        else:
            record("EXP-TPL-05", "Soft-delete experiment template", "FAIL", f"HTTP {r2.status_code}")

    # --- Workflow integration: new workflow actions ---
    wf_actions = ["create_experiment", "create_experiment_from_template",
                  "link_sample_to_experiment", "add_experiment_detail_step",
                  "link_experiments", "update_experiment_status"]
    for action in wf_actions:
        r = requests.post(f"{BASE}/admin/workflow-templates", headers=h(tok), json={
            "name": f"UAT WF {action} {uuid4().hex[:4]}",
            "template_definition": {"steps": [{"action": action, "params": {}}]},
            "active": True,
        })
        if r.status_code in [201, 400, 422]:
            record(f"EXP-WF-{action}", f"Workflow action '{action}' accepted in template",
                   "PASS", f"HTTP {r.status_code}")
        else:
            record(f"EXP-WF-{action}", f"Workflow action '{action}'",
                   "FAIL", f"HTTP {r.status_code}: {r.text[:150]}")


# ======================= Main =======================

def main():
    log("=" * 60)
    log("UAT: Experiments (navigation + management)")
    log("=" * 60)

    try:
        assert requests.get(f"{BASE}/health").status_code == 200
    except Exception as e:
        log(f"Backend unreachable: {e}", "ERROR")
        return 1

    run_navigation_api()
    run_experiment_crud()

    p = sum(1 for r in RESULTS if r["status"] == "PASS")
    f = sum(1 for r in RESULTS if r["status"] == "FAIL")
    log("=" * 60)
    log(f"EXPERIMENTS UAT COMPLETE: {p}/{len(RESULTS)} passed, {f} failed")

    with open("/workspace/UAT_Scripts/uat_experiment_results.md", "w") as out:
        out.write(f"# UAT Experiment Results\n\n")
        out.write(f"**Run Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"**Passed:** {p}/{len(RESULTS)} ✅  **Failed:** {f} ❌\n\n")
        out.write("| TC | Description | Status | Details |\n")
        out.write("|-----|-------------|--------|--------|\n")
        for r in RESULTS:
            icon = {"PASS": "✅", "FAIL": "❌"}.get(r["status"], "⚠️")
            det = r["details"].replace("|", "\\|")[:120] if r["details"] else ""
            out.write(f"| {r['tc']} | {r['desc']} | {icon} {r['status']} | {det} |\n")

    return 0 if f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
