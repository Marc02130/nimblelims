"""Reagent tracking (step 2): vendors, vendor-agnostic reagents, reagent-vendor
sources, lots, and the lot used per run.

Locks: no DELETE routes (status flags; a lot's amount goes to 0), expired or
inactive lots can't be recorded as used, the lot number and expiry are copied
onto the use, the four tables are registered in the Schema catalog (0090), and
the configuring agent may add vendors/reagents but never lots or uses.
"""
import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.core import lab_time
from app.main import app
from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_catalog as cat
from app.services import configuring_agent_llm as llm
from app.services import ui_schema_catalog as schema_catalog
from models.flexible_experiment import LimsRun
from models.reagent import Reagent, ReagentLot, ReagentUse, Vendor
from tests.conftest import _get_or_create, _grant
from models.user import Permission, Role, User


def _login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


@pytest.fixture
def tech_h(client, test_user):
    return _login(client, "testuser", "testpassword")


def _name(prefix):
    return f"{prefix} {uuid.uuid4().hex[:6]}"


@pytest.fixture
def lot(client, admin_h):
    vendor = client.post("/v1/vendors", headers=admin_h, json={"name": _name("Thermo"), "contact": "orders@x"}).json()
    reagent = client.post("/v1/reagents", headers=admin_h, json={
        "name": _name("Qubit dsDNA HS"), "storage_condition": "4C", "unit": "assays",
        "hazard_class": "Irritant", "sds_url": "https://x/sds", "stability_after_opening_days": 10,
    }).json()
    source = client.post("/v1/reagent-vendors", headers=admin_h, json={
        "reagent_id": reagent["id"], "vendor_id": vendor["id"], "catalog_number": "Q32851",
        "unit": "assays", "unit_of_sale": "kit of 100", "quantity_per_unit_of_sale": "100",
        "reorder_point": "150", "reorder_quantity": "2", "lead_time_days": "5", "price_per_unit": "3.2", "is_preferred": True,
    })
    assert source.status_code == 201, source.text
    r = client.post("/v1/reagent-lots", headers=admin_h, json={
        "reagent_vendor_id": source.json()["id"], "lot_number": "L-2291",
        "expiration_date": str(date.today() + timedelta(days=30)),
        "purchased_date": str(date.today() - timedelta(days=3)), "received_date": str(date.today()),
        "storage_location": "Fridge 2", "coa_url": "https://x/coa", "quantity_received": "100", "qc_status": "released",
    })
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def run(db_session, test_admin_user):
    row = LimsRun(name=_name("Run"), created_by=test_admin_user.id)
    db_session.add(row)
    db_session.commit()
    return row


# ------------------------------------------------------------------ catalog ---

def test_vendor_reagent_lot_crud(client, admin_h, lot):
    assert float(lot["quantity_remaining"]) == 100 and lot["unit"] == "assays"
    assert lot["vendor_name"].startswith("Thermo") and lot["catalog_number"] == "Q32851"
    assert lot["expired"] is False and lot["active"] is True
    reagents = client.get("/v1/reagents", headers=admin_h, params={"search": "Q32851"}).json()
    mine = [r for r in reagents if r["id"] == lot["reagent_id"]]
    assert mine and mine[0]["vendor_names"] and float(mine[0]["quantity_on_hand"]) == 100
    assert mine[0]["below_reorder_point"] is True  # 100 on hand <= reorder point 150

    dup = client.post("/v1/reagent-lots", headers=admin_h, json={"reagent_id": lot["reagent_id"], "lot_number": "L-2291"})
    assert dup.status_code == 400

    r = client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"quantity_remaining": 0})
    assert r.status_code == 200 and float(r.json()["quantity_remaining"]) == 0
    usable = client.get("/v1/reagent-lots", headers=admin_h, params={"usable": True}).json()
    assert lot["id"] not in {x["id"] for x in usable}


def test_duplicate_vendor_name_is_case_insensitive(client, admin_h):
    name = _name("Qiagen")
    assert client.post("/v1/vendors", headers=admin_h, json={"name": name}).status_code == 201
    assert client.post("/v1/vendors", headers=admin_h, json={"name": name.upper()}).status_code == 400


def test_no_delete_routes():
    for route in app.routes:
        path = getattr(route, "path", "")
        if any(path.startswith(p) for p in ("/v1/vendors", "/v1/reagents", "/v1/reagent-vendors", "/v1/reagent-lots", "/v1/reagent-uses")):
            assert "DELETE" not in getattr(route, "methods", set()), path


def test_set_inactive_hides_from_non_editors(client, admin_h, tech_h):
    vendor = client.post("/v1/vendors", headers=admin_h, json={"name": _name("Retired")}).json()
    assert client.patch(f"/v1/vendors/{vendor['id']}", headers=admin_h, json={"active": False}).json()["active"] is False
    assert vendor["id"] not in {v["id"] for v in client.get("/v1/vendors", headers=tech_h).json()}
    assert vendor["id"] in {v["id"] for v in client.get("/v1/vendors", headers=admin_h).json()}
    reagent = client.post("/v1/reagents", headers=admin_h, json={"name": _name("X")}).json()
    r = client.post("/v1/reagent-vendors", headers=admin_h, json={"reagent_id": reagent["id"], "vendor_id": vendor["id"]})
    assert r.status_code == 422


def test_catalog_writes_need_config_edit(client, tech_h):
    assert client.post("/v1/vendors", headers=tech_h, json={"name": _name("V")}).status_code == 403
    assert client.post("/v1/reagents", headers=tech_h, json={"name": _name("R")}).status_code == 403


# --------------------------------------------------------------------- uses ---

def test_record_use_copies_lot_and_expiry_and_draws_down(client, admin_h, lot, run):
    r = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": "8",
    })
    assert r.status_code == 201, r.text
    use = r.json()
    assert use["lot_number"] == "L-2291" and use["expiration_date"] == lot["expiration_date"]
    assert use["unit"] == "assays"
    assert use["used_on"] == str(date.today()) and use["reagent_name"]
    assert float(client.get(f"/v1/reagent-lots/{lot['id']}", headers=admin_h).json()["quantity_remaining"]) == 92

    # A later correction to the lot does not rewrite what the run recorded.
    client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"lot_number": "L-2291B"})
    listed = client.get("/v1/reagent-uses", headers=admin_h, params={"lims_run_id": str(run.id)}).json()
    assert [u["lot_number"] for u in listed] == ["L-2291"]

    too_much = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": "500"})
    assert too_much.status_code == 422
    assert too_much.json()["detail"]["code"] == "insufficient_amount"
    assert "left" in too_much.json()["detail"]["message"]

    void = client.patch(f"/v1/reagent-uses/{use['id']}", headers=admin_h, json={"active": False})
    assert void.status_code == 200 and void.json()["active"] is False
    assert float(client.get(f"/v1/reagent-lots/{lot['id']}", headers=admin_h).json()["quantity_remaining"]) == 100
    again = client.patch(f"/v1/reagent-uses/{use['id']}", headers=admin_h, json={"active": True})
    assert again.status_code == 422
    assert again.json()["detail"]["code"] == "voided_use_stays_voided"
    assert client.get("/v1/reagent-uses", headers=admin_h, params={"lims_run_id": str(run.id)}).json() == []


def test_expired_lot_is_blocked_at_use(client, admin_h, lot, run):
    client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h,
                 json={"expiration_date": str(date.today() - timedelta(days=1))})
    assert client.get(f"/v1/reagent-lots/{lot['id']}", headers=admin_h).json()["expired"] is True
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "lot_expired" and "expired" in r.json()["detail"]["message"]
    # Back-dated use on a day the lot was still good is allowed.
    r = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1, "used_on": str(date.today() - timedelta(days=2))})
    assert r.status_code == 201, r.text


def test_inactive_lot_is_blocked_at_use(client, admin_h, lot, run):
    client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"active": False})
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "lot_inactive" and "inactive" in r.json()["detail"]["message"]


def test_use_needs_a_run_or_experiment_and_permission(client, admin_h, tech_h, lot, run):
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "quantity_used": 1})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "use_target_required"
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id)})
    assert r.status_code == 422  # quantity used is required
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(uuid.uuid4()), "quantity_used": 1})
    assert r.status_code == 404
    r = client.post("/v1/reagent-uses", headers=tech_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 403


# ---------------------------------------------------------- schema catalog ---

def test_reagent_tables_follow_the_schema_display_rule():
    for name in ("vendors", "reagents", "reagent_vendors", "reagent_lots", "reagent_uses"):
        assert name in schema_catalog.LAB_TABLES
        assert schema_catalog.shown_in_schema(name, schema_catalog.kind_for(name))


def test_fresh_db_registers_reagent_tables_and_rls(migrated_engine):
    with migrated_engine.connect() as conn:
        for client in [r[0] for r in conn.execute(text("SELECT id FROM clients")).all()]:
            names = {r[0] for r in conn.execute(text(
                "SELECT physical_name FROM schema_tables WHERE client_id = :c"), {"c": client}).all()}
            assert {"vendors", "reagents", "reagent_vendors", "reagent_lots", "reagent_uses"} <= names
        forced = dict(conn.execute(text(
            "SELECT relname, relforcerowsecurity FROM pg_class WHERE relname = ANY(:n)"),
            {"n": ["vendors", "reagents", "reagent_vendors", "reagent_lots", "reagent_uses"]}).all())
        assert forced and all(forced.values())


def test_rls_reagent_uses_are_tenant_scoped(migrated_engine):
    from app.core.security import get_password_hash

    conn = migrated_engine.connect()
    tx = conn.begin()
    try:
        lt = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar_one()
        client_role = conn.execute(text("SELECT id FROM roles WHERE name = 'Client'")).scalar_one()
        a, b = uuid.uuid4(), uuid.uuid4()
        conn.execute(text("INSERT INTO clients (id, name, active, billing_info) VALUES (:a,'RA',true,'{}'),(:b,'RB',true,'{}')"),
                     {"a": a, "b": b})
        ua, ub, uc = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        pw = get_password_hash("x")
        conn.execute(text(
            "INSERT INTO users (id,name,username,email,password_hash,role_id,client_id,active) VALUES "
            "(:ua,'A','rt_a','rta@x.org',:pw,:lt,:a,true),(:ub,'B','rt_b','rtb@x.org',:pw,:lt,:b,true),"
            "(:uc,'C','rt_c','rtc@x.org',:pw,:cr,:a,true)"),
            {"ua": ua, "ub": ub, "uc": uc, "pw": pw, "lt": lt, "cr": client_role, "a": a, "b": b})
        v, r, lot, run, use = (uuid.uuid4() for _ in range(5))
        conn.execute(text("INSERT INTO vendors (id,name) VALUES (:v,:n)"), {"v": v, "n": _name("RLS V")})
        conn.execute(text("INSERT INTO reagents (id,name) VALUES (:r,:n)"), {"r": r, "n": _name("RLS R")})
        conn.execute(text("INSERT INTO reagent_lots (id,reagent_id,lot_number) VALUES (:l,:r,'L1')"), {"l": lot, "r": r})
        conn.execute(text("INSERT INTO lims_runs (id,name,status,created_by) VALUES (:id,:n,'draft',:u)"),
                     {"id": run, "n": _name("RLS run"), "u": ua})
        conn.execute(text(
            "INSERT INTO reagent_uses (id,reagent_lot_id,lims_run_id,lot_number,used_on,quantity_used,created_by) "
            "VALUES (:id,:l,:run,'L1',CURRENT_DATE,1,:u)"), {"id": use, "l": lot, "run": run, "u": ua})
        conn.execute(text("SET LOCAL ROLE app_test_role"))

        def sees(user, sql, params):
            conn.execute(text(f"SET LOCAL app.current_user_id = '{user}'"))
            return conn.execute(text(sql), params).scalar()

        assert sees(ua, "SELECT count(*) FROM reagent_uses WHERE id = :i", {"i": use}) == 1
        assert sees(ub, "SELECT count(*) FROM reagent_uses WHERE id = :i", {"i": use}) == 0
        assert sees(ub, "SELECT count(*) FROM reagent_lots WHERE id = :i", {"i": lot}) == 1  # lab-wide catalog
        assert sees(uc, "SELECT count(*) FROM vendors WHERE id = :i", {"i": v}) == 0  # Client role
    finally:
        tx.rollback()
        conn.close()


# --------------------------------------------------------- configuring agent ---

def test_agent_may_create_vendor_and_reagent_not_lots_or_uses():
    assert allow.classify_call("POST", "/v1/vendors", {"name": "Thermo"}).ok
    assert allow.classify_call("POST", "/v1/reagents", {"name": "Qubit"}).ok
    assert allow.classify_call("POST", "/v1/reagent-vendors", {"reagent": "Qubit", "vendor": "Thermo"}).ok
    for path in ("/v1/reagent-lots", "/v1/reagent-uses", "/v1/reagent-lots/abc"):
        c = allow.classify_call("POST", path, {"lot_number": "L1"})
        assert not c.ok and "bench" in c.gap and "POST /v1/reagent-uses" in c.gap
    assert not allow.classify_call("DELETE", "/v1/vendors/x").ok
    paths = {row["path"] for row in cat.route_formats()}
    assert {"/v1/vendors", "/v1/reagents", "/v1/reagent-vendors"} <= paths


def test_prompt_and_kit_lot_stop_point_at_reagent_tracking():
    prompt = llm._system_prompt(None, "")
    assert "POST /v1/vendors" in prompt and "POST /v1/reagents" in prompt and "POST /v1/reagent-vendors" in prompt
    assert "do not call those routes" in prompt
    assert "/v1/reagents body {name: string" in cat.route_formats_text()
    assert "POST /v1/reagents" in cat.REAGENT_TRACKING_GAP and "POST /v1/reagent-uses" in cat.REAGENT_TRACKING_GAP


def _agent_user(db, org, perms):
    role = _get_or_create(db, Role, f"role_ag_{uuid.uuid4().hex[:6]}", "t")
    _grant(db, role, [_get_or_create(db, Permission, p, p) for p in perms])
    user = User(name="ag", username=f"ag_{uuid.uuid4().hex[:6]}", email=f"{uuid.uuid4().hex[:8]}@x.org",
                password_hash="x", role_id=role.id, client_id=org.id, must_change_password=False)
    db.add(user)
    db.commit()
    return user


def test_agent_applies_vendor_then_reagent_by_vendor_name_and_rerun_is_noop(db_session, test_org):
    from app.services.configuring_agent_apply import execute_step

    user = _agent_user(db_session, test_org, ["config:edit"])
    vname, rname = _name("Agent Vendor"), _name("Agent Kit")
    created = execute_step(db_session, user, "POST", "/v1/vendors", {"display_name": vname})
    assert created[0].kind == "vendor" and not created[0].noop
    made = execute_step(db_session, user, "POST", "/v1/reagents", {"name": rname, "unit": "assays"})
    reagent = db_session.query(Reagent).filter(Reagent.id == made[0].target_id).one()
    src = execute_step(db_session, user, "POST", "/v1/reagent-vendors",
                                   {"reagent": rname, "vendor": vname, "part_number": "Q1", "reorder_point": 2})
    assert not src[0].noop
    assert reagent.sources[0].vendor.name == vname and reagent.sources[0].catalog_number == "Q1"
    again_src = execute_step(db_session, user, "POST", "/v1/reagent-vendors",
                                         {"reagent": rname, "vendor": vname, "catalog_number": "Q1"})
    assert again_src[0].noop
    again = execute_step(db_session, user, "POST", "/v1/reagents", {"name": rname.upper()})
    assert again[0].noop
    diff = cat.describe_change(db_session, user, "POST", "/v1/vendors", {"name": vname})
    assert diff["changed"] is False
    assert cat.near_matches(db_session, user, "POST", "/v1/vendors", {"name": vname + "s"})


def test_agent_reagent_needs_config_edit(db_session, test_org):
    from app.services.configuring_agent_apply import PermissionDenied, execute_step

    user = _agent_user(db_session, test_org, ["sample:read"])
    with pytest.raises(PermissionDenied):
        execute_step(db_session, user, "POST", "/v1/vendors", {"name": _name("No")})
    assert not db_session.query(Vendor).filter(Vendor.created_by == user.id).count()


def test_reagent_has_many_vendors_and_lot_source_must_match(client, admin_h, lot):
    other = client.post("/v1/vendors", headers=admin_h, json={"name": _name("Invitrogen")}).json()
    second = client.post("/v1/reagent-vendors", headers=admin_h, json={
        "reagent_id": lot["reagent_id"], "vendor_id": other["id"], "catalog_number": "Q99"})
    assert second.status_code == 201
    sources = client.get("/v1/reagent-vendors", headers=admin_h, params={"reagent_id": lot["reagent_id"]}).json()
    assert len(sources) == 2
    dup = client.post("/v1/reagent-vendors", headers=admin_h, json={
        "reagent_id": lot["reagent_id"], "vendor_id": other["id"], "catalog_number": "Q99"})
    assert dup.status_code == 400
    unrelated = client.post("/v1/reagents", headers=admin_h, json={"name": _name("Other")}).json()
    bad = client.post("/v1/reagent-lots", headers=admin_h, json={
        "reagent_id": unrelated["id"], "reagent_vendor_id": second.json()["id"], "lot_number": "X1"})
    assert bad.status_code == 422
    plain = client.post("/v1/reagent-lots", headers=admin_h, json={"reagent_id": unrelated["id"], "lot_number": "X1"})
    assert plain.status_code == 201 and plain.json()["reagent_vendor_id"] is None


def test_lot_receipt_fields_and_audit(client, admin_h, lot, test_admin_user):
    assert lot["received_by"] == str(test_admin_user.id) and lot["created_by"] == str(test_admin_user.id)
    assert lot["storage_location"] == "Fridge 2" and lot["qc_status"] == "released" and lot["coa_url"]
    assert lot["purchased_date"] != lot["received_date"]
    bad = client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"qc_status": "maybe"})
    assert bad.status_code == 422
    r = client.post("/v1/reagents", headers=admin_h, json={"name": _name("Bad"), "storage_condition": "freezer"})
    assert r.status_code == 422


def test_opened_lot_uses_effective_expiry(client, admin_h, lot, run):
    # Printed expiry is +30 days; opened 12 days ago with 10 days stability -> expired 2 days ago.
    opened = date.today() - timedelta(days=12)
    got = client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"opened_date": str(opened)}).json()
    assert got["effective_expiration_date"] == str(opened + timedelta(days=10)) and got["expired"] is True
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "lot_expired" and "stability" in r.json()["detail"]["message"]
    assert lot["id"] not in {x["id"] for x in client.get("/v1/reagent-lots", headers=admin_h, params={"usable": True}).json()}
    # Opened yesterday: effective expiry = opened + 10, still good, and the use records it.
    client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"opened_date": str(date.today() - timedelta(days=1))})
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 201 and r.json()["expiration_date"] == str(date.today() + timedelta(days=9))


def test_qc_rejected_lot_is_blocked(client, admin_h, lot, run):
    client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"qc_status": "rejected"})
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "lot_rejected" and "QC" in r.json()["detail"]["message"]


def test_use_records_audit_and_unit(client, admin_h, lot, run, test_admin_user):
    r = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 2, "unit": "assays"})
    assert r.status_code == 201
    use = r.json()
    assert use["created_by"] == str(test_admin_user.id) and use["created_at"] and use["unit"] == "assays"
    assert "used_by" not in use and "used_at" not in use
    wrong = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 2, "unit": "mL"})
    assert wrong.status_code == 422
    assert wrong.json()["detail"]["code"] == "incompatible_units"
    assert "counted in" in wrong.json()["detail"]["message"]


def test_agent_maps_storage_condition():
    assert cat._storage_condition("-20 °C") == "-20C" and cat._storage_condition("2-8C") == "4C"
    assert cat._storage_condition("room temperature") == "RT"


def test_released_flag_gates_use(client, admin_h, lot, run):
    assert lot["released"] is True and lot["usable"] is True  # default
    held = client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"released": False}).json()
    assert held["released"] is False and held["active"] is True and held["usable"] is False
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "lot_unreleased" and "not released" in r.json()["detail"]["message"]
    assert lot["id"] not in {x["id"] for x in client.get("/v1/reagent-lots", headers=admin_h, params={"usable": True}).json()}
    # QC release releases the lot unless told otherwise.
    back = client.patch(f"/v1/reagent-lots/{lot['id']}", headers=admin_h, json={"qc_status": "released"}).json()
    assert back["released"] is True
    r = client.post("/v1/reagent-uses", headers=admin_h, json={"reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 201


def test_lot_can_be_received_unreleased(client, admin_h, lot):
    r = client.post("/v1/reagent-lots", headers=admin_h, json={
        "reagent_id": lot["reagent_id"], "lot_number": "HOLD-1", "released": False})
    assert r.status_code == 201 and r.json()["released"] is False and r.json()["qc_status"] == "pending"
    kept = client.patch(f"/v1/reagent-lots/{r.json()['id']}", headers=admin_h, json={"qc_status": "released", "released": False})
    assert kept.json()["released"] is False


@pytest.mark.parametrize("qty", [0, "0.000", -1])
def test_zero_or_negative_use_is_refused(client, admin_h, lot, run, qty):
    r = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": qty})
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "quantity_not_positive"
    assert "greater than 0" in r.json()["detail"]["message"]
    after = client.get("/v1/reagent-lots", headers=admin_h).json()
    assert float(next(x for x in after if x["id"] == lot["id"])["quantity_remaining"]) == 100


@pytest.mark.parametrize(
    "utc_moment, expected",
    [
        (datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), date(2026, 10, 18)),  # 8:00 PM EDT
        (datetime(2026, 10, 19, 1, 30, tzinfo=timezone.utc), date(2026, 10, 18)),  # 9:30 PM EDT
        (datetime(2026, 10, 19, 3, 59, tzinfo=timezone.utc), date(2026, 10, 18)),  # 11:59 PM EDT
        (datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc), date(2026, 10, 19)),  # midnight EDT
    ],
)
def test_lab_today_uses_the_lab_clock_between_8pm_and_midnight(monkeypatch, utc_moment, expected):
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    assert lab_time.lab_today(utc_moment) == expected


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_missing_lab_timezone_refuses_startup(monkeypatch, raw):
    if raw is None:
        monkeypatch.delenv("LAB_TIMEZONE", raising=False)
    else:
        monkeypatch.setenv("LAB_TIMEZONE", raw)
    with pytest.raises(RuntimeError, match=r"LAB_TIMEZONE=America/New_York"):
        lab_time.lab_zone()


def test_unknown_lab_timezone_refuses_startup(monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "Mars/Olympus_Mons")
    with pytest.raises(RuntimeError, match=r"not a known IANA time zone"):
        lab_time.lab_zone()
    with pytest.raises(RuntimeError, match=r"LAB_TIMEZONE=America/New_York"):
        lab_time.lab_zone()


def test_valid_lab_timezone_starts(monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    zone = lab_time.lab_zone()
    assert getattr(zone, "key", None) == "America/New_York"
    evening = datetime(2026, 10, 19, 1, 30, tzinfo=timezone.utc)
    assert lab_time.lab_today(evening) == date(2026, 10, 18)


def test_blank_used_on_is_the_lab_date_in_the_evening(client, admin_h, lot, run, monkeypatch):
    monkeypatch.setenv("LAB_TIMEZONE", "America/New_York")
    evening = datetime(2026, 10, 19, 1, 30, tzinfo=timezone.utc)  # 9:30 PM EDT on Oct 18
    monkeypatch.setattr(lab_time, "_utcnow", lambda: evening)
    r = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1})
    assert r.status_code == 201, r.text
    assert r.json()["used_on"] == "2026-10-18"
    sent = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1, "used_on": "2026-10-17"})
    assert sent.status_code == 201, sent.text
    assert sent.json()["used_on"] == "2026-10-17"


@pytest.mark.parametrize("bad", ["2026-13-45", "not-a-date", "2026-02-30"])
def test_invalid_used_on_has_a_code(client, admin_h, lot, run, bad):
    r = client.post("/v1/reagent-uses", headers=admin_h, json={
        "reagent_lot_id": lot["id"], "lims_run_id": str(run.id), "quantity_used": 1, "used_on": bad})
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "invalid_date"
    assert "valid date" in detail["message"]
    after = client.get(f"/v1/reagent-lots/{lot['id']}", headers=admin_h).json()
    assert float(after["quantity_remaining"]) == 100

    mixed = client.post("/v1/reagent-uses", headers=admin_h, json={
        "lims_run_id": str(run.id), "quantity_used": 1, "used_on": bad})
    assert mixed.status_code == 422
    assert isinstance(mixed.json()["detail"], list)
