"""Instrument tracking: eligibility, maintenance, downtime, uses, RLS, agent."""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_catalog as cat
from app.services import ui_schema_catalog as schema_catalog
from models.flexible_experiment import LimsRun


def _login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _name(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _seeded_type(client, admin_h, name="Plate reader"):
    rows = client.get("/v1/instrument-types", headers=admin_h).json()
    for row in rows:
        if row["name"] == name:
            return row
    return client.post(
        "/v1/instrument-types", headers=admin_h, json={"name": _name(name)}
    ).json()


def _instrument(client, admin_h, **extra):
    body = {
        "name": _name("Inst"),
        "instrument_type_id": extra.pop("instrument_type_id", None) or _seeded_type(client, admin_h)["id"],
        "status": "in_service",
        **extra,
    }
    r = client.post("/v1/instruments", headers=admin_h, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _list_entry(client, admin_h, list_name, entry_name):
    entries = client.get(f"/lists/{list_name}/entries", headers=admin_h).json()
    if isinstance(entries, dict):
        entries = entries.get("entries") or entries.get("items") or []
    return next(row for row in entries if row["name"] == entry_name)


def _add_and_retire_entry(client, admin_h, list_name, name):
    created = client.post(
        f"/lists/{list_name}/entries",
        headers=admin_h,
        json={"name": name},
    )
    assert created.status_code == 201, created.text
    retired = client.delete(
        f"/lists/{list_name}/entries/{created.json()['id']}",
        headers=admin_h,
    )
    assert retired.status_code == 204, retired.text
    return created.json()


def test_schema_catalog_registers_new_tables_and_drops_types():
    assert "instrument_types" not in schema_catalog.SYSTEM_TABLES
    assert "instrument_types" not in schema_catalog.LAB_TABLES
    for name in (
        "instrument_maintenance_schedules",
        "instrument_maintenance_events",
        "instrument_downtime",
        "instrument_uses",
        "instrument_type_defaults",
        "lims_run_type_substitutions",
        "instrument_template_inactivations",
        "instrument_entry_slot_audits",
    ):
        assert name in schema_catalog.LAB_TABLES
        assert schema_catalog.shown_in_schema(name, schema_catalog.kind_for(name))


def test_fresh_db_registers_instrument_tables_and_rls(migrated_engine):
    with migrated_engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT DISTINCT physical_name FROM schema_tables")).all()}
        assert "instrument_types" not in names
        assert {
            "instrument_maintenance_schedules",
            "instrument_maintenance_events",
            "instrument_downtime",
            "instrument_uses",
            "instrument_type_defaults",
            "instrument_template_inactivations",
            "instrument_entry_slot_audits",
        } <= names
        forced = dict(
            conn.execute(
                text("SELECT relname, relforcerowsecurity FROM pg_class WHERE relname = ANY(:n)"),
                {
                    "n": [
                        "instruments",
                        "cro_sources",
                        "instrument_maintenance_schedules",
                        "instrument_maintenance_events",
                        "instrument_downtime",
                        "instrument_uses",
                        "instrument_type_defaults",
                        "instrument_maintenance_audits",
                        "instrument_schedule_audits",
                        "lims_run_type_substitutions",
                        "instrument_template_inactivations",
                        "instrument_entry_slot_audits",
                    ]
                },
            ).all()
        )
        assert forced and all(forced.values())
        leftover = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='instrument_types_legacy'"
            )
        ).scalar()
        assert leftover == 1
        forced_legacy = conn.execute(
            text(
                "SELECT relforcerowsecurity FROM pg_class "
                "WHERE relname = 'instrument_types_legacy'"
            )
        ).scalar()
        assert forced_legacy is True
        dropped = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='instrument_types'"
            )
        ).scalar()
        assert dropped is None


def test_lims_app_cannot_delete_instrument_tables(migrated_engine):
    tables = (
        "instruments",
        "cro_sources",
        "instrument_maintenance_schedules",
        "instrument_maintenance_events",
        "instrument_downtime",
        "instrument_uses",
        "instrument_type_defaults",
        "instrument_types_legacy",
        "instrument_maintenance_audits",
        "instrument_schedule_audits",
        "lims_run_type_substitutions",
        "instrument_template_inactivations",
        "instrument_entry_slot_audits",
        "lims_run_imports",
        "lims_run_data",
    )
    with migrated_engine.connect() as conn:
        for table in tables:
            can_delete = conn.execute(
                text("SELECT has_table_privilege('lims_app', :t, 'DELETE')"),
                {"t": table},
            ).scalar()
            assert can_delete is False, f"lims_app must not DELETE {table}"


def test_rls_instrument_uses_are_tenant_scoped(migrated_engine):
    from app.core.security import get_password_hash

    conn = migrated_engine.connect()
    tx = conn.begin()
    try:
        lt = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar_one()
        client_role = conn.execute(text("SELECT id FROM roles WHERE name = 'Client'")).scalar_one()
        a, b = uuid.uuid4(), uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO clients (id, name, active, billing_info) "
                "VALUES (:a,'IA',true,'{}'),(:b,'IB',true,'{}')"
            ),
            {"a": a, "b": b},
        )
        ua, ub, uc = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        pw = get_password_hash("x")
        conn.execute(
            text(
                "INSERT INTO users (id,name,username,email,password_hash,role_id,client_id,active) VALUES "
                "(:ua,'A','it_a','ita@x.org',:pw,:lt,:a,true),(:ub,'B','it_b','itb@x.org',:pw,:lt,:b,true),"
                "(:uc,'C','it_c','itc@x.org',:pw,:cr,:a,true)"
            ),
            {"ua": ua, "ub": ub, "uc": uc, "pw": pw, "lt": lt, "cr": client_role, "a": a, "b": b},
        )
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name='Plate reader' LIMIT 1")
        ).scalar()
        inst, run, use = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instruments (id,name,instrument_type_id,status) "
                "VALUES (:id,:n,:t,'in_service')"
            ),
            {"id": inst, "n": _name("RLS"), "t": type_id},
        )
        assert (
            conn.execute(
                text("SELECT maintenance_tracked FROM instruments WHERE id = :id"),
                {"id": inst},
            ).scalar()
            is False
        )
        conn.execute(
            text("INSERT INTO lims_runs (id,name,status,created_by) VALUES (:id,:n,'draft',:u)"),
            {"id": run, "n": _name("RLS run"), "u": ua},
        )
        conn.execute(
            text(
                "INSERT INTO instrument_uses (id,instrument_id,lims_run_id,used_on,created_by) "
                "VALUES (:id,:i,:run,CURRENT_DATE,:u)"
            ),
            {"id": use, "i": inst, "run": run, "u": ua},
        )
        conn.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON "
                "instrument_uses, instruments, lims_runs TO app_test_role"
            )
        )
        conn.execute(text("SET LOCAL ROLE app_test_role"))

        def sees(user, sql, params):
            conn.execute(text(f"SET LOCAL app.current_user_id = '{user}'"))
            return conn.execute(text(sql), params).scalar()

        assert sees(ua, "SELECT count(*) FROM instrument_uses WHERE id = :i", {"i": use}) == 1
        assert sees(ub, "SELECT count(*) FROM instrument_uses WHERE id = :i", {"i": use}) == 0
        assert sees(ub, "SELECT count(*) FROM instruments WHERE id = :i", {"i": inst}) == 1
        assert sees(uc, "SELECT count(*) FROM instruments WHERE id = :i", {"i": inst}) == 0
    finally:
        tx.rollback()
        conn.close()


def test_eligibility_block_reasons(client, admin_h, db_session, test_admin_user):
    inst = _instrument(client, admin_h)
    ok = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h)
    assert ok.status_code == 200
    assert ok.json()["allowed"] is True

    run = LimsRun(name=_name("Elig run"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()

    cases = [
        ({"active": False}, "instrument_inactive"),
        ({"status": "retired"}, "instrument_retired"),
        ({"status": "out_of_service"}, "instrument_out_of_service"),
    ]
    for patch, code in cases:
        row = _instrument(client, admin_h)
        client.patch(f"/v1/instruments/{row['id']}", headers=admin_h, json=patch)
        elig = client.get(f"/v1/instruments/{row['id']}/eligibility", headers=admin_h).json()
        assert elig["allowed"] is False
        assert elig["code"] == code
        refused = client.post(
            "/v1/instrument-uses",
            headers=admin_h,
            json={
                "instrument_id": row["id"],
                "lims_run_id": str(run.id),
                "used_on": str(date.today()),
            },
        )
        assert refused.status_code == 422, refused.text
        assert refused.json()["detail"]["code"] == code


def test_open_downtime_and_overdue_block(client, admin_h, db_session, test_admin_user):
    inst = _instrument(client, admin_h)
    reason = _list_entry(client, admin_h, "downtime_reasons", "Breakdown")
    down = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason_id": reason["id"],
        },
    )
    assert down.status_code == 201, down.text
    elig = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert elig["code"] == "instrument_down"

    ended = client.patch(
        f"/v1/instrument-downtime/{down.json()['id']}",
        headers=admin_h,
        json={"ended_at": datetime.now(timezone.utc).isoformat()},
    )
    assert ended.status_code == 200
    assert client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()["allowed"] is True

    kind = _list_entry(client, admin_h, "maintenance_types", "calibration")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "kind_id": kind["id"],
            "interval_days": 1,
        },
    )
    assert sched.status_code == 201, sched.text
    first_due = client.post(
        f"/v1/instrument-maintenance-schedules/{sched.json()['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today() - timedelta(days=1))},
    )
    assert first_due.status_code == 200, first_due.text
    performed = date.today() - timedelta(days=2)
    event = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched.json()["id"],
            "performed_on": str(performed),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert event.status_code == 201, event.text
    untracked = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert untracked["allowed"] is True
    assert untracked["maintenance_tracked"] is False
    client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": True},
    )
    overdue = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert overdue["allowed"] is False
    assert overdue["code"] == "instrument_overdue"
    assert overdue["maintenance_tracked"] is True

    run = LimsRun(name=_name("Run"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    refused = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "lims_run_id": str(run.id),
            "used_on": str(date.today()),
        },
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "instrument_overdue"


def test_passing_event_advances_and_void_recomputes(client, admin_h, test_admin_user):
    inst = _instrument(client, admin_h)
    kind = _list_entry(client, admin_h, "maintenance_types", "PM")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "kind_id": kind["id"],
            "interval_days": 10,
        },
    ).json()
    first_due = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today())},
    )
    assert first_due.status_code == 200, first_due.text
    first_day = date.today() - timedelta(days=20)
    missing = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(first_day),
            "passed": True,
        },
    )
    assert missing.status_code == 422
    user_id = str(test_admin_user.id)
    first = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(first_day),
            "performed_by_user_id": user_id,
            "passed": True,
        },
    )
    assert first.status_code == 201, first.text
    after = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()
    assert after["last_done"] == str(first_day)
    assert after["next_due"] == str(first_day + timedelta(days=10))

    later = date.today() - timedelta(days=5)
    second = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(later),
            "performed_by_user_id": user_id,
            "passed": True,
        },
    )
    assert second.status_code == 201, second.text
    after = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()
    assert after["last_done"] == str(later)
    assert after["next_due"] == str(later + timedelta(days=10))

    voided = client.patch(
        f"/v1/instrument-maintenance-events/{second.json()['id']}",
        headers=admin_h,
        json={"active": False, "reason": "void last event"},
    )
    assert voided.status_code == 200, voided.text
    recomputed = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()
    assert recomputed["last_done"] == str(first_day)
    assert recomputed["next_due"] == str(first_day + timedelta(days=10))


def test_schedule_create_and_update_ignore_due_fields(client, admin_h):
    inst = _instrument(client, admin_h)
    kind = _list_entry(client, admin_h, "maintenance_types", "PM")
    yesterday = str(date.today() - timedelta(days=1))
    created = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "kind_id": kind["id"],
            "interval_days": 30,
            "last_done": yesterday,
            "next_due": yesterday,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["last_done"] is None
    assert body["next_due"] is None
    patched = client.patch(
        f"/v1/instrument-maintenance-schedules/{body['id']}",
        headers=admin_h,
        json={"last_done": yesterday, "next_due": yesterday, "interval_days": 14},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["last_done"] is None
    assert patched.json()["next_due"] is None


def test_agent_refuses_schedule_due_and_active_fields():
    from app.services.configuring_agent_apply import CannotExpress, execute_step

    path = "/v1/instrument-maintenance-schedules"
    for extra in (
        {"last_done": "2020-01-01"},
        {"next_due": "2020-01-01"},
        {"active": False},
        {},
    ):
        body = {"instrument_id": "x", "kind_id": "y", "interval_days": 30, **extra}
        classified = allow.classify_call("POST", path, body)
        assert classified.ok is False
        assert classified.gap
        assert "schedules" in classified.gap or "first due" in classified.gap
        try:
            execute_step(None, None, "POST", path, body)
        except CannotExpress as exc:
            assert "schedules" in str(exc) or "first due" in str(exc)
        else:
            raise AssertionError("apply should refuse the schedule route")


def test_agent_may_create_instruments_and_schedules_not_events_or_downtime():
    asked = allow.classify_call("POST", "/v1/instruments", {"name": "Qubit"})
    assert asked.ok is False
    assert "track maintenance" in (asked.gap or "").lower()
    assert allow.classify_call(
        "POST",
        "/v1/instruments",
        {"name": "Qubit", "maintenance_tracked": False},
    ).ok
    blocked_status = allow.classify_call("PATCH", "/v1/instruments/abc", {"active": False})
    assert blocked_status.ok is False
    assert "status" in blocked_status.gap or "active" in blocked_status.gap
    assert allow.classify_call(
        "PATCH", "/v1/instruments/abc", {"maintenance_tracked": True}
    ).ok
    type_flag = allow.classify_call(
        "POST", "/v1/instrument-types", {"name": "Balance", "maintenance_tracked": True}
    )
    assert type_flag.ok is False
    assert "plain list" in (type_flag.gap or "")
    schedule_post = allow.classify_call(
        "POST", "/v1/instrument-maintenance-schedules", {"interval_days": 30}
    )
    assert schedule_post.ok is False
    assert "schedules" in (schedule_post.gap or "") or "first due" in (schedule_post.gap or "")
    refused_interval = allow.classify_call(
        "PATCH", "/v1/instrument-maintenance-schedules/abc", {"interval_days": 7}
    )
    assert refused_interval.ok is False
    assert "schedules" in (refused_interval.gap or "") or "first due" in (refused_interval.gap or "")
    for path in (
        "/v1/instrument-maintenance-events",
        "/v1/instrument-downtime",
        "/v1/instrument-uses",
    ):
        c = allow.classify_call("POST", path, {})
        assert not c.ok and "bench" in c.gap
    assert not allow.classify_call("DELETE", "/v1/instruments/x").ok
    paths = {row["path"] for row in cat.route_formats()}
    assert "/v1/instruments" in paths
    assert "/v1/instrument-types" in paths
    assert "/v1/instrument-maintenance-schedules" not in paths


def test_no_delete_routes_left_on_instrument_ops(client, admin_h):
    inst = _instrument(client, admin_h)
    kind = _list_entry(client, admin_h, "maintenance_types", "PM")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind["id"], "interval_days": 7},
    ).json()
    assert client.delete(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).status_code == 405
    retired = client.patch(
        f"/v1/instrument-maintenance-schedules/{sched['id']}",
        headers=admin_h,
        json={"active": False},
    )
    assert retired.status_code == 200
    assert retired.json()["active"] is False


BACKEND = Path(__file__).resolve().parents[1]
BEFORE = "0110_lims_run_failed_by"


def test_migration_carries_types_and_downgrade_is_safe(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    with migrated_engine.begin() as conn:
        conn.execute(text("DELETE FROM instrument_maintenance_audits"))
        conn.execute(text("DELETE FROM instrument_schedule_audits"))
        conn.execute(text("DELETE FROM lims_run_type_substitutions"))
        conn.execute(text("DELETE FROM lims_run_imports WHERE filename = 'admin_override'"))
    type_id = uuid.uuid4()
    inst_id = uuid.uuid4()
    inactive_id = uuid.uuid4()
    type_b = uuid.uuid4()
    inst_a = uuid.uuid4()
    inst_b = uuid.uuid4()
    extra_entry = uuid.uuid4()
    try:
        command.downgrade(cfg, BEFORE)
        with migrated_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO instrument_types (id, name, vendor, model, active) "
                    "VALUES (:id, :n, :v, :m, true)"
                ),
                {"id": type_id, "n": "Custom GC", "v": "Agilent", "m": "8890"},
            )
            conn.execute(
                text(
                    "INSERT INTO instrument_types (id, name, vendor, model, active) "
                    "VALUES (:id, :n, :v, :m, false)"
                ),
                {"id": inactive_id, "n": "Retired reader", "v": "OldCo", "m": "1"},
            )
            conn.execute(
                text(
                    "INSERT INTO instrument_types (id, name, vendor, model, active) "
                    "VALUES (:id, :n, :v, :m, true)"
                ),
                {"id": type_b, "n": "Custom GC B", "v": "Agilent", "m": "8890"},
            )
            conn.execute(
                text(
                    "INSERT INTO instruments (id, name, instrument_type_id, serial_number) "
                    "VALUES (:id, :n, :t, :s)"
                ),
                {"id": inst_id, "n": "GC-1", "t": type_id, "s": "SN-1"},
            )
            conn.execute(
                text(
                    "INSERT INTO instruments (id, name, instrument_type_id, serial_number) "
                    "VALUES (:id, :n, :t, :s), (:id2, :n2, :t2, :s)"
                ),
                {
                    "id": inst_a,
                    "n": "GC-A",
                    "t": type_id,
                    "s": "DUP-1",
                    "id2": inst_b,
                    "n2": "GC-B",
                    "t2": type_b,
                    "s": "DUP-1",
                },
            )
        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            inst = conn.execute(
                text(
                    "SELECT instrument_type_id, vendor_id, model, serial_number, status "
                    "FROM instruments WHERE id = :id"
                ),
                {"id": inst_id},
            ).mappings().one()
            assert inst["model"] == "8890"
            assert inst["serial_number"] == "SN-1"
            assert inst["status"] == "in_service"
            assert inst["vendor_id"] is not None
            vendor = conn.execute(
                text("SELECT name FROM vendors WHERE id = :id"),
                {"id": inst["vendor_id"]},
            ).scalar()
            assert vendor == "Agilent"
            type_name = conn.execute(
                text("SELECT name FROM list_entries WHERE id = :id"),
                {"id": inst["instrument_type_id"]},
            ).scalar()
            assert type_name == "Custom GC"
            leftover = conn.execute(
                text("SELECT name, vendor, model FROM instrument_types_legacy WHERE id = :id"),
                {"id": type_id},
            ).mappings().one()
            assert leftover["vendor"] == "Agilent"
            assert leftover["model"] == "8890"
            inactive = conn.execute(
                text("SELECT active FROM list_entries WHERE name = 'Retired reader'")
            ).scalar()
            assert inactive is False
            serials = {
                r[0]
                for r in conn.execute(
                    text("SELECT serial_number FROM instruments WHERE id IN (:a, :b)"),
                    {"a": inst_a, "b": inst_b},
                ).all()
            }
            assert len(serials) == 2
            tracked = conn.execute(
                text("SELECT maintenance_tracked FROM instruments WHERE id = :id"),
                {"id": inst_id},
            ).scalar()
            assert tracked is False
            list_id = conn.execute(
                text("SELECT id FROM lists WHERE name = 'instrument_types'")
            ).scalar()
            conn.execute(
                text(
                    "INSERT INTO list_entries (id, name, list_id, active, created_at, modified_at) "
                    "VALUES (:id, :n, :lid, true, NOW(), NOW())"
                ),
                {"id": extra_entry, "n": "Post-upgrade type", "lid": list_id},
            )
            conn.commit()
        command.downgrade(cfg, BEFORE)
        with migrated_engine.connect() as conn:
            restored = conn.execute(
                text("SELECT instrument_type_id FROM instruments WHERE id = :id"),
                {"id": inst_id},
            ).scalar()
            assert restored == type_id
            old = conn.execute(
                text("SELECT name, vendor FROM instrument_types WHERE id = :id"),
                {"id": type_id},
            ).mappings().one()
            assert old["name"] == "Custom GC"
            assert old["vendor"] == "Agilent"
            leftover_entry = conn.execute(
                text("SELECT name FROM list_entries WHERE id = :id"),
                {"id": extra_entry},
            ).scalar()
            assert leftover_entry == "Post-upgrade type"
        command.upgrade(cfg, "head")
    finally:
        command.upgrade(cfg, "head")
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate


def _track(client, admin_h, instrument_id, tracked=True):
    patched = client.patch(
        f"/v1/instruments/{instrument_id}",
        headers=admin_h,
        json={"maintenance_tracked": tracked},
    )
    assert patched.status_code == 200, patched.text
    return patched.json()


def test_interval_change_does_not_clear_overdue(client, admin_h, test_admin_user):
    inst = _instrument(client, admin_h)
    _track(client, admin_h, inst["id"])
    kind = _list_entry(client, admin_h, "maintenance_types", "calibration")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind["id"], "interval_days": 1},
    ).json()
    first_due = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today() - timedelta(days=1))},
    )
    assert first_due.status_code == 200, first_due.text
    event = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(date.today() - timedelta(days=2)),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert event.status_code == 201, event.text
    due_before = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()["next_due"]
    patched = client.patch(
        f"/v1/instrument-maintenance-schedules/{sched['id']}",
        headers=admin_h,
        json={"interval_days": 365},
    )
    assert patched.status_code == 200
    assert patched.json()["next_due"] == due_before
    elig = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert elig["code"] == "instrument_overdue"
    refused = allow.classify_call(
        "PATCH",
        f"/v1/instrument-maintenance-schedules/{sched['id']}",
        {"interval_days": 14},
    )
    assert refused.ok is False
    assert "schedules" in (refused.gap or "") or "first due" in (refused.gap or "")


def test_maintenance_off_ignores_schedule_downtime_and_retired_still_block(
    client, admin_h, db_session, test_admin_user
):
    inst = _instrument(client, admin_h)
    kind = _list_entry(client, admin_h, "maintenance_types", "PM")
    client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind["id"], "interval_days": 1},
    )
    client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "performed_on": str(date.today() - timedelta(days=10)),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    elig = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert elig["allowed"] is True
    assert elig["maintenance_tracked"] is False
    run = LimsRun(name=_name("Off"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    used = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={"instrument_id": inst["id"], "lims_run_id": str(run.id)},
    )
    assert used.status_code == 201, used.text
    assert used.json()["used_on"] == str(date.today())
    reason = _list_entry(client, admin_h, "downtime_reasons", "Breakdown")
    down = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason_id": reason["id"],
        },
    )
    assert down.status_code == 201
    assert client.get(
        f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h
    ).json()["code"] == "instrument_down"
    client.patch(
        f"/v1/instrument-downtime/{down.json()['id']}",
        headers=admin_h,
        json={"ended_at": datetime.now(timezone.utc).isoformat()},
    )
    client.patch(f"/v1/instruments/{inst['id']}", headers=admin_h, json={"status": "retired"})
    assert client.get(
        f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h
    ).json()["code"] == "instrument_retired"


def test_maintenance_on_requires_schedule_and_never_calibrated_is_overdue(
    client, admin_h, test_admin_user, monkeypatch
):
    inst = _instrument(client, admin_h)
    _track(client, admin_h, inst["id"])
    missing = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert missing["allowed"] is False
    assert missing["code"] == "instrument_no_schedule"
    kind = _list_entry(client, admin_h, "maintenance_types", "calibration")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind["id"], "interval_days": 7},
    ).json()
    assert sched["last_done"] is None
    assert sched["next_due"] is None
    awaiting = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert awaiting["code"] == "instrument_awaiting_first_due"
    first_due = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today() - timedelta(days=1))},
    )
    assert first_due.status_code == 200, first_due.text
    later = date.today() + timedelta(days=8)

    def _later():
        return later

    monkeypatch.setattr("app.services.instrument_eligibility.current_lab_day", _later)
    overdue = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert overdue["code"] == "instrument_overdue"
    monkeypatch.setattr("app.services.instrument_eligibility.current_lab_day", date.today)
    monkeypatch.setattr("app.routers.instrument_ops.current_lab_day", date.today)
    event = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(date.today()),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert event.status_code == 201, event.text
    cleared = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert cleared["allowed"] is True
    reason = _list_entry(client, admin_h, "downtime_reasons", "Breakdown")
    down = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason_id": reason["id"],
        },
    )
    assert down.status_code == 201
    assert client.get(
        f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h
    ).json()["code"] == "instrument_down"


def test_type_default_is_inherited_unless_explicit(client, admin_h):
    typed = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("Tracked type"), "maintenance_tracked": True},
    )
    assert typed.status_code == 422, typed.text
    plain = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("Plain type")},
    )
    assert plain.status_code == 201, plain.text
    assert "maintenance_tracked" not in plain.json()
    omitted = _instrument(client, admin_h, instrument_type_id=plain.json()["id"])
    assert omitted["maintenance_tracked"] is False
    explicit = _instrument(
        client,
        admin_h,
        instrument_type_id=plain.json()["id"],
        maintenance_tracked=True,
    )
    assert explicit["maintenance_tracked"] is True


def test_agent_off_requires_confirm_and_keeps_previous(client, admin_h, db_session, test_admin_user, test_org, monkeypatch):
    from app.services import configuring_agent_service as svc
    from models.configuring_agent import Configuration, ConfigurationItem
    from models.instrument import InstrumentMaintenanceAudit

    inst = _instrument(client, admin_h, maintenance_tracked=True)
    assert inst["maintenance_tracked"] is True
    off = {"maintenance_tracked": False}
    path = f"/v1/instruments/{inst['id']}"
    classified = allow.classify_call("PATCH", path, off)
    assert classified.ok is True
    assert allow.needs_second_confirm("PATCH", path, off, classified.kind) is False
    monkeypatch.setattr(svc, "_key_for_run", lambda _db: (
        type("P", (), {"agent_provider": "xai", "agent_model": "grok-test-model"})(),
        "test-key",
    ))
    monkeypatch.setattr(svc, "_excerpt", lambda *_a, **_k: ["excerpt"])
    monkeypatch.setattr(svc, "_ready_documents", lambda *_a, **_k: 1)
    monkeypatch.setattr(
        svc,
        "propose",
        lambda *_a, **_k: {
            "steps": [
                {
                    "group": "other",
                    "target": inst["name"],
                    "action": "Turn maintenance tracking off",
                    "why": "lab uses metrology",
                    "call": {
                        "method": "PATCH",
                        "path": f"/v1/instruments/{inst['id']}",
                        "body": {"maintenance_tracked": False},
                    },
                }
            ]
        },
    )
    configuration = Configuration(
        id=uuid.uuid4(),
        client_id=test_org.id,
        name=_name("Cfg"),
        created_by=test_admin_user.id,
    )
    db_session.add(configuration)
    db_session.commit()
    run = svc.start_run(db_session, test_admin_user, configuration.id, "goal")
    still = client.get(f"/v1/instruments/{inst['id']}", headers=admin_h).json()
    assert still["maintenance_tracked"] is True
    result, code = svc.apply_run(db_session, test_admin_user, run.id)
    assert code == 200, result.error_message
    assert result.status == "done"
    assert result.confirmed_by == test_admin_user.id
    assert result.confirmed_at is not None
    after = client.get(f"/v1/instruments/{inst['id']}", headers=admin_h).json()
    assert after["maintenance_tracked"] is False
    item = db_session.query(ConfigurationItem).filter_by(run_id=run.id).one()
    assert item.created_by == test_admin_user.id
    assert item.agent_assisted is True
    assert "previous=true" in (item.detail or "")
    audit = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == inst["id"])
        .one()
    )
    assert audit.previous_value is True
    assert audit.new_value is False
    assert audit.created_by == test_admin_user.id
    assert audit.created_at is not None


def test_json_import_requires_source_unless_admin(
    client, admin_h, db_session, test_admin_user, test_org, run_analysis_id, cohort_sample_id
):
    from app.core.security import get_password_hash
    from models.user import Permission, Role, User
    from tests.conftest import _get_or_create, _grant
    from tests.test_flexible_experiment import VALID_TEMPLATE_DEF

    template = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={"name": _name("T"), "template_definition": VALID_TEMPLATE_DEF},
    )
    assert template.status_code == 201, template.text
    created = client.post(
        "/v1/lims-runs",
        headers=admin_h,
        json={
            "name": _name("Import run"),
            "experiment_template_id": template.json()["id"],
            "analysis_id": run_analysis_id,
        },
    )
    assert created.status_code == 201, created.text
    started = client.patch(
        f"/v1/lims-runs/{created.json()['id']}/start",
        headers=admin_h,
        json={"sample_ids": [cohort_sample_id]},
    )
    assert started.status_code == 200, started.text
    rows = {"rows": [{"well_position": "A1", "row_data": {"viability_pct": 90}}]}
    role = _get_or_create(db_session, Role, "Lab Technician", "tech")
    _grant(db_session, role, [_get_or_create(db_session, Permission, "experiment:manage", "m")])
    user = User(
        name="tech-import",
        username="tech-import",
        email=f"tech-{uuid.uuid4().hex[:6]}@x.org",
        password_hash=get_password_hash("pass-word-1"),
        role_id=role.id,
        client_id=test_org.id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    tech = _login(client, "tech-import", "pass-word-1")
    refused = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=tech,
        json=rows,
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"]["code"] == "import_source_required"
    admin_ok = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json=rows,
    )
    assert admin_ok.status_code == 200, admin_ok.text


def test_performed_on_certificate_ended_at_used_on_and_inactive_type(
    client, admin_h, db_session, test_admin_user
):
    inst = _instrument(client, admin_h)
    future = str(date.today() + timedelta(days=1))
    late = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "performed_on": future,
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert late.status_code == 422
    assert late.json()["detail"]["code"] == "performed_on_in_future"
    bad_cert = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "performed_on": str(date.today()),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
            "certificate_url": "ftp://certs.example/file",
        },
    )
    assert bad_cert.status_code == 422
    assert bad_cert.json()["detail"]["code"] == "certificate_url_invalid"
    reason = _list_entry(client, admin_h, "downtime_reasons", "Breakdown")
    future_end = datetime.now(timezone.utc) + timedelta(days=1)
    down = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": future_end.isoformat(),
            "reason_id": reason["id"],
        },
    )
    assert down.status_code == 422
    assert down.json()["detail"]["code"] == "ended_at_in_future"
    typed = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("Inactive type")},
    ).json()
    client.patch(f"/v1/instrument-types/{typed['id']}", headers=admin_h, json={"active": False})
    refused_type = client.post(
        "/v1/instruments",
        headers=admin_h,
        json={"name": _name("Bad"), "instrument_type_id": typed["id"]},
    )
    assert refused_type.status_code == 422
    assert refused_type.json()["detail"]["code"] == "instrument_type_inactive"
    run = LimsRun(name=_name("Use"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    used = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "lims_run_id": str(run.id),
            "used_on": str(date.today() - timedelta(days=3)),
        },
    )
    assert used.status_code == 201
    assert used.json()["used_on"] == str(date.today())


def test_unvoid_use_rechecks_eligibility(client, admin_h, db_session, test_admin_user):
    inst = _instrument(client, admin_h)
    run = LimsRun(name=_name("Re"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    used = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={"instrument_id": inst["id"], "lims_run_id": str(run.id)},
    ).json()
    voided = client.patch(
        f"/v1/instrument-uses/{used['id']}", headers=admin_h, json={"active": False}
    )
    assert voided.status_code == 200
    client.patch(f"/v1/instruments/{inst['id']}", headers=admin_h, json={"status": "retired"})
    refused = client.patch(
        f"/v1/instrument-uses/{used['id']}", headers=admin_h, json={"active": True}
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "instrument_retired"
    client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"status": "in_service", "active": True},
    )
    restored = client.patch(
        f"/v1/instrument-uses/{used['id']}", headers=admin_h, json={"active": True}
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["active"] is True


def test_missing_seed_list_message_is_generic(client, admin_h, db_session):
    from models.list import List as ListModel

    row = db_session.query(ListModel).filter(ListModel.name == "maintenance_types").first()
    row.name = "maintenance_types_renamed"
    db_session.commit()
    inst = _instrument(client, admin_h)
    kind = uuid.uuid4()
    failed = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": str(kind), "interval_days": 7},
    )
    assert failed.status_code == 500
    assert failed.json()["detail"] == "A required list is not seeded"


def test_removed_list_entries_are_not_newly_selectable(client, admin_h):
    inst = _instrument(client, admin_h)
    pm = _list_entry(client, admin_h, "maintenance_types", "PM")
    removed_kind = _add_and_retire_entry(client, admin_h, "maintenance_types", _name("Kind"))
    other_kind = _add_and_retire_entry(client, admin_h, "maintenance_types", _name("Kind2"))
    missing = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": str(uuid.uuid4()), "interval_days": 10},
    )
    assert missing.status_code == 400, missing.text
    refused_create = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": removed_kind["id"], "interval_days": 10},
    )
    assert refused_create.status_code == 422, refused_create.text
    assert refused_create.json()["detail"]["code"] == "list_entry_inactive"
    used_kind = client.post(
        "/lists/maintenance_types/entries",
        headers=admin_h,
        json={"name": _name("KindKeep")},
    )
    assert used_kind.status_code == 201, used_kind.text
    created = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "kind_id": used_kind.json()["id"],
            "interval_days": 10,
        },
    )
    assert created.status_code == 201, created.text
    retire = client.delete(
        f"/lists/maintenance_types/entries/{used_kind.json()['id']}",
        headers=admin_h,
    )
    assert retire.status_code == 204, retire.text
    keep = client.patch(
        f"/v1/instrument-maintenance-schedules/{created.json()['id']}",
        headers=admin_h,
        json={"interval_days": 14},
    )
    assert keep.status_code == 200, keep.text
    same_kind = client.patch(
        f"/v1/instrument-maintenance-schedules/{created.json()['id']}",
        headers=admin_h,
        json={"kind_id": used_kind.json()["id"]},
    )
    assert same_kind.status_code == 200, same_kind.text
    switch_removed = client.patch(
        f"/v1/instrument-maintenance-schedules/{created.json()['id']}",
        headers=admin_h,
        json={"kind_id": other_kind["id"]},
    )
    assert switch_removed.status_code == 422, switch_removed.text
    assert switch_removed.json()["detail"]["code"] == "list_entry_inactive"
    switch_active = client.patch(
        f"/v1/instrument-maintenance-schedules/{created.json()['id']}",
        headers=admin_h,
        json={"kind_id": pm["id"]},
    )
    assert switch_active.status_code == 200, switch_active.text

    breakdown = _list_entry(client, admin_h, "downtime_reasons", "Breakdown")
    removed_reason = _add_and_retire_entry(client, admin_h, "downtime_reasons", _name("Down"))
    other_reason = _add_and_retire_entry(client, admin_h, "downtime_reasons", _name("Down2"))
    refused_down = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason_id": removed_reason["id"],
        },
    )
    assert refused_down.status_code == 422, refused_down.text
    assert refused_down.json()["detail"]["code"] == "list_entry_inactive"
    used_reason = client.post(
        "/lists/downtime_reasons/entries",
        headers=admin_h,
        json={"name": _name("DownKeep")},
    )
    assert used_reason.status_code == 201, used_reason.text
    down = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason_id": used_reason.json()["id"],
        },
    )
    assert down.status_code == 201, down.text
    assert client.delete(
        f"/lists/downtime_reasons/entries/{used_reason.json()['id']}",
        headers=admin_h,
    ).status_code == 204
    keep_down = client.patch(
        f"/v1/instrument-downtime/{down.json()['id']}",
        headers=admin_h,
        json={"note": "still that reason"},
    )
    assert keep_down.status_code == 200, keep_down.text
    same_reason = client.patch(
        f"/v1/instrument-downtime/{down.json()['id']}",
        headers=admin_h,
        json={"reason_id": used_reason.json()["id"]},
    )
    assert same_reason.status_code == 200, same_reason.text
    switch_down = client.patch(
        f"/v1/instrument-downtime/{down.json()['id']}",
        headers=admin_h,
        json={"reason_id": other_reason["id"]},
    )
    assert switch_down.status_code == 422, switch_down.text
    assert switch_down.json()["detail"]["code"] == "list_entry_inactive"
    ok_down = client.patch(
        f"/v1/instrument-downtime/{down.json()['id']}",
        headers=admin_h,
        json={"reason_id": breakdown["id"]},
    )
    assert ok_down.status_code == 200, ok_down.text
    fresh = client.post(
        "/v1/instrument-downtime",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "reason_id": breakdown["id"],
        },
    )
    assert fresh.status_code == 201, fresh.text
