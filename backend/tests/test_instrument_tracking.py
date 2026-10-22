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


def test_schema_catalog_registers_new_tables_and_drops_types():
    assert "instrument_types" not in schema_catalog.SYSTEM_TABLES
    assert "instrument_types" not in schema_catalog.LAB_TABLES
    for name in (
        "instrument_maintenance_schedules",
        "instrument_maintenance_events",
        "instrument_downtime",
        "instrument_uses",
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
        dropped = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='instrument_types'"
            )
        ).scalar()
        assert dropped is None


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
            "interval_days": 30,
            "next_due": str(date.today() - timedelta(days=1)),
        },
    )
    assert sched.status_code == 201, sched.text
    overdue = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert overdue["allowed"] is False
    assert overdue["code"] == "instrument_overdue"

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
        json={"active": False},
    )
    assert voided.status_code == 200
    recomputed = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()
    assert recomputed["last_done"] == str(first_day)
    assert recomputed["next_due"] == str(first_day + timedelta(days=10))


def test_agent_may_create_instruments_and_schedules_not_events_or_downtime():
    assert allow.classify_call("POST", "/v1/instruments", {"name": "Qubit"}).ok
    assert allow.classify_call("PATCH", "/v1/instruments/abc", {"active": False}).ok
    assert allow.classify_call("POST", "/v1/instrument-maintenance-schedules", {"interval_days": 30}).ok
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
    assert "/v1/instrument-maintenance-schedules" in paths


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
BEFORE = "0107_elisa_run_gaps"


def test_migration_carries_types_and_downgrade_is_safe(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    type_id = uuid.uuid4()
    inst_id = uuid.uuid4()
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
                    "INSERT INTO instruments (id, name, instrument_type_id, serial_number) "
                    "VALUES (:id, :n, :t, :s)"
                ),
                {"id": inst_id, "n": "GC-1", "t": type_id, "s": "SN-1"},
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
