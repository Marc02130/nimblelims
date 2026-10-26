"""E1 instrument hardening: first due, roles, agent, type-default retirement."""
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError, InternalError, ProgrammingError

from app.services import configuring_agent_allow as allow
from app.services import configuring_agent_catalog as cat
from app.services.configuring_agent_apply import CannotExpress, execute_step
from models.flexible_experiment import LimsRun, LimsRunImport
from models.instrument import InstrumentMaintenanceAudit
from tests.test_instrument_tracking import (
    _instrument,
    _list_entry,
    _login,
    _name,
    _seeded_type,
)

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _role_user(db_session, test_org, role_name, extra_perms=()):
    from app.core.security import get_password_hash
    from models.user import Permission, Role, User
    from tests.conftest import _get_or_create, _grant

    role = _get_or_create(db_session, Role, role_name, role_name)
    perms = [
        _get_or_create(db_session, Permission, name, name) for name in extra_perms
    ]
    if perms:
        _grant(db_session, role, perms)
    username = f"{role_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    user = User(
        name=role_name,
        username=username,
        email=f"{username}@x.org",
        password_hash=get_password_hash("pass-word-1"),
        role_id=role.id,
        client_id=test_org.id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _schedule(client, admin_h, inst_id, interval=30):
    kind = _list_entry(client, admin_h, "maintenance_types", "PM")
    created = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={
            "instrument_id": inst_id,
            "kind_id": kind["id"],
            "interval_days": interval,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def test_agent_asks_and_sets_maintenance_tracked(client, admin_h, db_session, test_admin_user):
    asked = allow.classify_call("POST", "/v1/instruments", {"name": "Qubit"})
    assert asked.ok is False
    assert "Answer before confirming" in (asked.gap or "")
    assert allow.classify_call(
        "POST", "/v1/instruments", {"name": "Qubit", "maintenance_tracked": True}
    ).ok
    assert allow.classify_call(
        "POST", "/v1/instruments", {"name": "Qubit", "maintenance_tracked": False}
    ).ok
    type_id = _seeded_type(client, admin_h)["id"]
    for flag in (True, False):
        name = _name("Asked")
        changes = execute_step(
            db_session,
            test_admin_user,
            "POST",
            "/v1/instruments",
            {
                "name": name,
                "instrument_type_id": type_id,
                "maintenance_tracked": flag,
            },
        )
        assert changes[0].kind == "instrument"
        row = client.get(f"/v1/instruments/{changes[0].id}", headers=admin_h).json()
        assert row["maintenance_tracked"] is flag


def test_awaiting_first_due_blocks_uses_and_imports(
    client, admin_h, db_session, test_admin_user, run_analysis_id, cohort_sample_id
):
    from tests.test_flexible_experiment import VALID_TEMPLATE_DEF

    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"])
    elig = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert elig["allowed"] is False
    assert elig["code"] == "instrument_awaiting_first_due"

    run = LimsRun(name=_name("Await"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    used = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={"instrument_id": inst["id"], "lims_run_id": str(run.id)},
    )
    assert used.status_code == 422
    assert used.json()["detail"]["code"] == "instrument_awaiting_first_due"

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
            "name": _name("Import await"),
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
    data_refused = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={**rows, "instrument_id": inst["id"]},
    )
    assert data_refused.status_code == 422, data_refused.text
    assert data_refused.json()["detail"]["code"] == "instrument_awaiting_first_due"
    file_refused = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import-file",
        files={"file": ("plate.csv", b"well,value\nA1,1\n", "text/csv")},
        data={"instrument_id": inst["id"]},
        headers=admin_h,
    )
    assert file_refused.status_code == 422, file_refused.text
    assert file_refused.json()["detail"]["code"] == "instrument_awaiting_first_due"

    due = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today() + timedelta(days=30))},
    )
    assert due.status_code == 200, due.text
    cleared = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert cleared["allowed"] is True


def test_first_due_and_schedule_writes_are_lab_manager_only(
    client, admin_h, db_session, test_org
):
    inst = _instrument(client, admin_h)
    sched = _schedule(client, admin_h, inst["id"])
    manager = _role_user(
        db_session, test_org, "Lab Manager", extra_perms=("experiment:manage",)
    )
    tech = _role_user(
        db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",)
    )
    editor = _role_user(
        db_session, test_org, "Configuration Editor", extra_perms=("config:edit",)
    )
    manager_h = _login(client, manager.username, "pass-word-1")
    tech_h = _login(client, tech.username, "pass-word-1")
    editor_h = _login(client, editor.username, "pass-word-1")
    kind = _list_entry(client, admin_h, "maintenance_types", "PM")
    body = {
        "instrument_id": inst["id"],
        "kind_id": kind["id"],
        "interval_days": 14,
    }
    assert client.post(
        "/v1/instrument-maintenance-schedules", headers=manager_h, json=body
    ).status_code == 201
    for headers in (tech_h, editor_h):
        refused = client.post(
            "/v1/instrument-maintenance-schedules", headers=headers, json=body
        )
        assert refused.status_code == 403, refused.text
        patched = client.patch(
            f"/v1/instrument-maintenance-schedules/{sched['id']}",
            headers=headers,
            json={"interval_days": 21},
        )
        assert patched.status_code == 403, patched.text
        due = client.post(
            f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
            headers=headers,
            json={"next_due": str(date.today())},
        )
        assert due.status_code == 403, due.text
    first = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=manager_h,
        json={"next_due": str(date.today())},
    )
    assert first.status_code == 200, first.text
    admin_again = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today() + timedelta(days=1))},
    )
    assert admin_again.status_code == 422
    assert admin_again.json()["detail"]["code"] == "first_due_already_set"


def test_agent_refuses_schedules_and_due_fields():
    from app.services.configuring_agent_apply import _dispatch

    for method, path, body in (
        ("POST", "/v1/instrument-maintenance-schedules", {"interval_days": 30}),
        ("PATCH", "/v1/instrument-maintenance-schedules/abc", {"interval_days": 7}),
        ("POST", "/v1/instrument-maintenance-schedules/abc/first-due", {"next_due": "2026-01-01"}),
        ("POST", "/v1/instruments", {"name": "X", "next_due": "2026-01-01"}),
        ("PATCH", "/v1/instruments/abc", {"last_done": "2026-01-01"}),
    ):
        classified = allow.classify_call(method, path, body)
        assert classified.ok is False
        try:
            execute_step(None, None, method, path, body)
        except CannotExpress:
            pass
        else:
            raise AssertionError(f"apply should refuse {method} {path}")
    try:
        _dispatch(None, None, "POST", "/v1/instrument-maintenance-schedules", {}, "other")
    except CannotExpress as exc:
        assert "schedules" in exc.gap or "first due" in exc.gap
    else:
        raise AssertionError("dispatch should refuse schedules")
    paths = {row["path"] for row in cat.route_formats()}
    assert "/v1/instrument-maintenance-schedules" not in paths
    assert not any(path.endswith("/first-due") for path in paths)


def test_event_recomputes_only_after_first_due(client, admin_h, test_admin_user):
    inst = _instrument(client, admin_h)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    performed = date.today() - timedelta(days=3)
    before = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(performed),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert before.status_code == 201, before.text
    still = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()
    assert still["last_done"] is None
    assert still["next_due"] is None
    due = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today())},
    )
    assert due.status_code == 200, due.text
    after_event = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(performed),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert after_event.status_code == 201, after_event.text
    advanced = client.get(
        f"/v1/instrument-maintenance-schedules/{sched['id']}", headers=admin_h
    ).json()
    assert advanced["last_done"] == str(performed)
    assert advanced["next_due"] == str(performed + timedelta(days=10))


def test_voided_only_event_returns_to_awaiting_first_due(
    client, admin_h, db_session, test_admin_user
):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today())},
    )
    first_day = date.today() - timedelta(days=4)
    first = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": str(first_day),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert first.status_code == 201, first.text
    client.patch(
        f"/v1/instrument-maintenance-events/{first.json()['id']}",
        headers=admin_h,
        json={"active": False},
    )
    awaiting = client.get(f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h).json()
    assert awaiting["code"] == "instrument_awaiting_first_due"
    run = LimsRun(name=_name("Voided"), created_by=test_admin_user.id)
    db_session.add(run)
    db_session.commit()
    refused = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={"instrument_id": inst["id"], "lims_run_id": str(run.id)},
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "instrument_awaiting_first_due"

    other = _instrument(client, admin_h, maintenance_tracked=True)
    other_sched = _schedule(client, admin_h, other["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{other_sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today())},
    )
    first_keep = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": other["id"],
            "schedule_id": other_sched["id"],
            "performed_on": str(date.today() - timedelta(days=6)),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    second_keep = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": other["id"],
            "schedule_id": other_sched["id"],
            "performed_on": str(date.today() - timedelta(days=1)),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert first_keep.status_code == 201 and second_keep.status_code == 201
    client.patch(
        f"/v1/instrument-maintenance-events/{second_keep.json()['id']}",
        headers=admin_h,
        json={"active": False},
    )
    still = client.get(f"/v1/instruments/{other['id']}/eligibility", headers=admin_h).json()
    assert still["allowed"] is True

    reset = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": str(date.today() + timedelta(days=7))},
    )
    assert reset.status_code == 200, reset.text
    assert client.get(
        f"/v1/instruments/{inst['id']}/eligibility", headers=admin_h
    ).json()["allowed"] is True


def test_api_patch_off_writes_one_audit_row(client, admin_h, db_session):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    patched = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": False},
    )
    assert patched.status_code == 200
    rows = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == inst["id"])
        .all()
    )
    assert len(rows) == 1
    assert rows[0].previous_value is True
    assert rows[0].new_value is False


def test_type_default_is_refused_and_table_is_retired(client, admin_h, migrated_engine):
    created = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("No default"), "maintenance_tracked": True},
    )
    assert created.status_code == 422, created.text
    typed = client.post(
        "/v1/instrument-types",
        headers=admin_h,
        json={"name": _name("Plain")},
    )
    assert typed.status_code == 201, typed.text
    patched = client.patch(
        f"/v1/instrument-types/{typed.json()['id']}",
        headers=admin_h,
        json={"maintenance_tracked": True},
    )
    assert patched.status_code == 422, patched.text
    classify = allow.classify_call(
        "POST", "/v1/instrument-types", {"name": "X", "maintenance_tracked": True}
    )
    assert classify.ok is False
    try:
        execute_step(
            None, None, "POST", "/v1/instrument-types", {"name": "X", "maintenance_tracked": True}
        )
    except CannotExpress as exc:
        assert "plain list" in exc.gap
    else:
        raise AssertionError("apply should refuse a type maintenance_tracked")
    with migrated_engine.connect() as conn:
        for privilege in ("INSERT", "UPDATE", "DELETE"):
            allowed = conn.execute(
                text("SELECT has_table_privilege('lims_app', 'instrument_type_defaults', :p)"),
                {"p": privilege},
            ).scalar()
            assert allowed is False, privilege
        readable = conn.execute(
            text("SELECT has_table_privilege('lims_app', 'instrument_type_defaults', 'SELECT')")
        ).scalar()
        assert readable is True
        comment = conn.execute(
            text(
                "SELECT obj_description('instrument_type_defaults'::regclass)"
            )
        ).scalar()
        assert comment and "Retired" in comment


def test_db_schedule_enforcement_as_lims_app(migrated_engine):
    users = {}
    with migrated_engine.begin() as conn:
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        manager = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Manager'")).scalar()
        tech = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar()
        editor = conn.execute(
            text("SELECT id FROM roles WHERE name = 'Configuration Editor'")
        ).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        kind_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'PM' LIMIT 1")
        ).scalar()
        assert all([admin, manager, tech, editor, client_id, type_id, kind_id])
        for key, role in (
            ("admin", admin),
            ("manager", manager),
            ("tech", tech),
            ("editor", editor),
        ):
            uid = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                    "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
                ),
                {
                    "id": uid,
                    "n": key,
                    "u": f"e1-{key}-{uid.hex[:6]}",
                    "e": f"e1-{key}-{uid.hex[:6]}@x.org",
                    "r": role,
                    "c": client_id,
                },
            )
            users[key] = uid
        inst = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instruments (id, name, instrument_type_id, status, active, "
                "maintenance_tracked, created_by, modified_by) "
                "VALUES (:id, :n, :t, 'in_service', true, true, :u, :u)"
            ),
            {"id": inst, "n": f"E1-{inst.hex[:6]}", "t": type_id, "u": users["admin"]},
        )
        sched = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instrument_maintenance_schedules "
                "(id, instrument_id, kind_id, interval_days, next_due, last_done, active, created_by, modified_by) "
                "VALUES (:id, :i, :k, 10, CURRENT_DATE, NULL, true, :u, :u)"
            ),
            {"id": sched, "i": inst, "k": kind_id, "u": users["admin"]},
        )
        event = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instrument_maintenance_events "
                "(id, instrument_id, schedule_id, performed_on, performed_by_user_id, passed, active, created_by, modified_by) "
                "VALUES (:id, :i, :s, CURRENT_DATE - 2, :u, true, true, :u, :u)"
            ),
            {"id": event, "i": inst, "s": sched, "u": users["admin"]},
        )

    refused = (DataError, IntegrityError, InternalError, ProgrammingError)

    def run_as(user_id, sql, params):
        with migrated_engine.connect() as s:
            s.execute(text("SET ROLE lims_app"))
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(user_id)},
            )
            s.execute(text(sql), params)
            s.commit()

    insert_sql = (
        "INSERT INTO instrument_maintenance_schedules "
        "(id, instrument_id, kind_id, interval_days, active, created_by, modified_by) "
        "VALUES (:id, :i, :k, 30, true, :u, :u)"
    )
    insert_params = {
        "id": uuid.uuid4(),
        "i": inst,
        "k": kind_id,
        "u": users["admin"],
    }
    try:
        run_as(users["tech"], insert_sql, insert_params)
        raise AssertionError("technician INSERT should fail")
    except refused:
        pass
    try:
        run_as(
            users["tech"],
            "UPDATE instrument_maintenance_schedules SET interval_days = 99 WHERE id = :id",
            {"id": sched},
        )
        raise AssertionError("technician interval UPDATE should fail")
    except refused:
        pass
    try:
        run_as(
            users["tech"],
            "UPDATE instrument_maintenance_schedules SET next_due = CURRENT_DATE + 99 WHERE id = :id",
            {"id": sched},
        )
        raise AssertionError("technician arbitrary next_due UPDATE should fail")
    except refused:
        pass
    run_as(
        users["tech"],
        "UPDATE instrument_maintenance_schedules "
        "SET last_done = CURRENT_DATE - 2, next_due = (CURRENT_DATE - 2) + 10 "
        "WHERE id = :id",
        {"id": sched},
    )
    try:
        run_as(users["editor"], insert_sql, {**insert_params, "id": uuid.uuid4()})
        raise AssertionError("configuration editor INSERT should fail")
    except refused:
        pass

    extra = uuid.uuid4()
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO instruments (id, name, instrument_type_id, status, active, "
                "maintenance_tracked, created_by, modified_by) "
                "VALUES (:id, :n, :t, 'in_service', true, false, :u, :u)"
            ),
            {"id": extra, "n": f"E1m-{extra.hex[:6]}", "t": type_id, "u": users["admin"]},
        )
    for key in ("manager", "admin"):
        run_as(
            users[key],
            insert_sql,
            {"id": uuid.uuid4(), "i": extra, "k": kind_id, "u": users[key]},
        )


def test_m2_audits_append_only_as_lims_app(migrated_engine):
    with migrated_engine.begin() as conn:
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        uid = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, 'e1a', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e1a-{uid.hex[:6]}",
                "e": f"e1a-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        inst = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instruments (id, name, instrument_type_id, status, active, "
                "maintenance_tracked, created_by, modified_by) "
                "VALUES (:id, :n, :t, 'in_service', true, true, :u, :u)"
            ),
            {"id": inst, "n": f"E1a-{inst.hex[:6]}", "t": type_id, "u": uid},
        )
        audit = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instrument_maintenance_audits "
                "(id, instrument_id, previous_value, new_value, created_by) "
                "VALUES (:id, :i, true, false, :u)"
            ),
            {"id": audit, "i": inst, "u": uid},
        )
    with migrated_engine.connect() as conn:
        for privilege in ("UPDATE", "DELETE"):
            allowed = conn.execute(
                text("SELECT has_table_privilege('lims_app', 'instrument_maintenance_audits', :p)"),
                {"p": privilege},
            ).scalar()
            assert allowed is False, privilege
        conn.execute(text("SET ROLE lims_app"))
        conn.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(uid)})
        updated = conn.execute(
            text("UPDATE instrument_maintenance_audits SET new_value = true WHERE id = :id"),
            {"id": audit},
        )
        deleted = conn.execute(
            text("DELETE FROM instrument_maintenance_audits WHERE id = :id"),
            {"id": audit},
        )
        assert updated.rowcount == 0
        assert deleted.rowcount == 0
        conn.rollback()
    with migrated_engine.connect() as conn:
        left = conn.execute(
            text("SELECT new_value FROM instrument_maintenance_audits WHERE id = :id"),
            {"id": audit},
        ).scalar()
        assert left is False


def test_m3_admin_override_import(
    client, admin_h, db_session, test_admin_user, run_analysis_id, cohort_sample_id
):
    from tests.test_flexible_experiment import VALID_TEMPLATE_DEF

    template = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={"name": _name("Override"), "template_definition": VALID_TEMPLATE_DEF},
    )
    created = client.post(
        "/v1/lims-runs",
        headers=admin_h,
        json={
            "name": _name("Override run"),
            "experiment_template_id": template.json()["id"],
            "analysis_id": run_analysis_id,
        },
    )
    started = client.patch(
        f"/v1/lims-runs/{created.json()['id']}/start",
        headers=admin_h,
        json={"sample_ids": [cohort_sample_id]},
    )
    assert started.status_code == 200, started.text
    imported = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={"rows": [{"well_position": "A1", "row_data": {"viability_pct": 90}}]},
    )
    assert imported.status_code == 200, imported.text
    row = (
        db_session.query(LimsRunImport)
        .filter(LimsRunImport.lims_run_id == created.json()["id"])
        .one()
    )
    assert row.filename == "admin_override"
    assert row.parser_id is None
    assert row.imported_by == test_admin_user.id


def test_l4_l5_downgrade_guards():
    lock = (BACKEND / "db/migrations/versions/0112_instrument_legacy_lock.py").read_text()
    tracked = (BACKEND / "db/migrations/versions/0113_maintenance_tracked.py").read_text()
    assert "GRANT INSERT, UPDATE ON instrument_types_legacy" in lock
    assert "GRANT DELETE ON instrument_types_legacy" not in lock
    assert "instrument_maintenance_audits has rows" in tracked
