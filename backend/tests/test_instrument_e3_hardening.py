"""E3 instrument hardening: void reason, tracking pin, DB guards, template active."""
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError

from models.instrument import InstrumentMaintenanceAudit, InstrumentScheduleAudit
from tests.test_instrument_e2_type_slots import _create_run, _create_template, _start_run
from tests.test_instrument_hardening_e1 import _role_user, _run_as_lims_app, _schedule
from tests.test_instrument_tracking import _instrument, _login, _name, _seeded_type


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _grant_if_missing(conn, table, privilege):
    allowed = conn.execute(
        text("SELECT has_table_privilege('lims_app', :t, :p)"),
        {"t": table, "p": privilege},
    ).scalar()
    if not allowed:
        conn.execute(text(f"GRANT {privilege} ON TABLE {table} TO lims_app"))
    return not allowed


def test_void_event_requires_reason_api_and_audit(
    client, admin_h, db_session, test_admin_user
):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat()},
    )
    created = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    missing = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": False},
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["detail"]["code"] == "void_reason_required"
    blank = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": False, "reason": "   "},
    )
    assert blank.status_code == 422, blank.text
    assert blank.json()["detail"]["code"] == "void_reason_required"
    ok = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": False, "reason": "  misdated  "},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["active"] is False
    assert ok.json()["void_reason"] == "misdated"
    db_session.expire_all()
    voids = (
        db_session.query(InstrumentScheduleAudit)
        .filter(
            InstrumentScheduleAudit.event_id == event_id,
            InstrumentScheduleAudit.action == "event_void",
        )
        .all()
    )
    assert len(voids) == 1
    assert voids[0].reason == "misdated"


def test_void_reason_db_check_and_trigger(migrated_engine, client, admin_h, test_admin_user):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    created = client.post(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "schedule_id": sched["id"],
            "performed_on": date.today().isoformat(),
            "performed_by_user_id": str(test_admin_user.id),
            "passed": True,
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)) as blank:
        _run_as_lims_app(
            migrated_engine,
            test_admin_user.id,
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = '   ' WHERE id = :id",
            {"id": event_id},
        )
    assert "void_reason_required" in str(blank.value.orig) or "ck_instrument_events_void_reason" in str(
        blank.value.orig
    )
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)):
        _run_as_lims_app(
            migrated_engine,
            test_admin_user.id,
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = :r WHERE id = :id",
            {"id": event_id, "r": "x" * 1001},
        )
    _run_as_lims_app(
        migrated_engine,
        test_admin_user.id,
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = 'db reason' WHERE id = :id",
        {"id": event_id},
    )


def test_lab_manager_cannot_toggle_maintenance_tracked_admin_can(
    client, admin_h, db_session, test_org, test_admin_user
):
    manager = _role_user(db_session, test_org, "Lab Manager", extra_perms=("experiment:manage",))
    mgr_h = _login(client, manager.username, "pass-word-1")
    inst = _instrument(client, admin_h, maintenance_tracked=False)
    turn_on = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=mgr_h,
        json={"maintenance_tracked": True},
    )
    assert turn_on.status_code == 403, turn_on.text
    still = client.get(f"/v1/instruments/{inst['id']}", headers=admin_h).json()
    assert still["maintenance_tracked"] is False
    admin_on = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": True},
    )
    assert admin_on.status_code == 200, admin_on.text
    assert admin_on.json()["maintenance_tracked"] is True
    turn_off = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=mgr_h,
        json={"maintenance_tracked": False},
    )
    assert turn_off.status_code == 403, turn_off.text
    admin_off = client.patch(
        f"/v1/instruments/{inst['id']}",
        headers=admin_h,
        json={"maintenance_tracked": False},
    )
    assert admin_off.status_code == 200, admin_off.text
    assert admin_off.json()["maintenance_tracked"] is False
    db_session.expire_all()
    audits = (
        db_session.query(InstrumentMaintenanceAudit)
        .filter(InstrumentMaintenanceAudit.instrument_id == inst["id"])
        .order_by(InstrumentMaintenanceAudit.created_at)
        .all()
    )
    values = [(a.previous_value, a.new_value) for a in audits]
    assert ("false", "true") in values
    assert ("true", "false") in values
    assert all(a.created_by == test_admin_user.id for a in audits if a.new_value in ("true", "false"))


def test_inactive_template_hidden_from_tech_picker_visible_in_manager_catalog(
    client, admin_h, db_session, test_org, run_analysis_id, cohort_sample_id
):
    tech = _role_user(db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",))
    manager = _role_user(db_session, test_org, "Lab Manager", extra_perms=("experiment:manage",))
    tech_h = _login(client, tech.username, "pass-word-1")
    mgr_h = _login(client, manager.username, "pass-word-1")
    template = _create_template(client, admin_h, name=_name("HideMe"))
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    assert created.status_code == 201, created.text
    retired = client.patch(
        f"/v1/experiment-templates/{template['id']}",
        headers=admin_h,
        json={"active": False},
    )
    assert retired.status_code == 200, retired.text
    assert retired.json()["active"] is False

    tech_list = client.get(
        "/v1/experiment-templates?page=1&size=500",
        headers=tech_h,
    )
    assert tech_list.status_code == 200, tech_list.text
    tech_ids = {row["id"] for row in tech_list.json()["templates"]}
    assert template["id"] not in tech_ids

    tech_forced = client.get(
        "/v1/experiment-templates?include_inactive=true&page=1&size=500",
        headers=tech_h,
    )
    assert tech_forced.status_code == 200, tech_forced.text
    forced_ids = {row["id"] for row in tech_forced.json()["templates"]}
    assert template["id"] not in forced_ids

    mgr_list = client.get(
        "/v1/experiment-templates?include_inactive=true&page=1&size=500",
        headers=mgr_h,
    )
    assert mgr_list.status_code == 200, mgr_list.text
    mgr_ids = {row["id"] for row in mgr_list.json()["templates"]}
    assert template["id"] in mgr_ids

    admin_list = client.get(
        "/v1/experiment-templates?include_inactive=true&page=1&size=500",
        headers=admin_h,
    )
    assert template["id"] in {row["id"] for row in admin_list.json()["templates"]}

    shown = client.get(f"/v1/lims-runs/{created.json()['id']}", headers=admin_h)
    assert shown.status_code == 200, shown.text
    assert shown.json()["experiment_template_id"] == template["id"]

    create_again = _create_run(client, admin_h, template["id"], run_analysis_id)
    assert create_again.status_code == 422, create_again.text
    assert create_again.json()["detail"]["code"] == "template_inactive"

    start = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert start.status_code == 422, start.text
    assert start.json()["detail"]["code"] == "template_inactive"


def test_db_refuses_foreign_substitution_and_cancel_after_import(
    migrated_engine, client, admin_h, db_session, test_org, run_analysis_id, cohort_sample_id
):
    tech = _role_user(db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",))
    other = _role_user(db_session, test_org, "Lab Technician", extra_perms=("experiment:manage",))
    template = _create_template(client, admin_h)
    owned = _create_run(client, _login(client, other.username, "pass-word-1"), template["id"], run_analysis_id)
    assert owned.status_code == 201, owned.text
    started = _start_run(client, admin_h, owned.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    imported = client.post(
        f"/v1/lims-runs/{owned.json()['id']}/import",
        headers=admin_h,
        json={"rows": [{"well_position": "A1", "row_data": {"well": "A1"}}]},
    )
    assert imported.status_code == 200, imported.text
    type_id = uuid.UUID(qpcr["id"])
    run_id = uuid.UUID(owned.json()["id"])

    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "lims_runs", "UPDATE")
        _grant_if_missing(conn, "lims_run_type_substitutions", "INSERT")

    with pytest.raises((ProgrammingError, InternalError)) as sub:
        _run_as_lims_app(
            migrated_engine,
            tech.id,
            "INSERT INTO lims_run_type_substitutions "
            "(lims_run_id, to_instrument_type_id, reason, created_by) "
            "VALUES (:r, :t, 'not mine', :u)",
            {"r": run_id, "t": type_id, "u": tech.id},
        )
    assert "substitute_not_own_run" in str(sub.value.orig)

    with pytest.raises((ProgrammingError, InternalError)) as apply:
        _run_as_lims_app(
            migrated_engine,
            tech.id,
            "UPDATE lims_runs SET instrument_type_id = :t WHERE id = :id",
            {"t": type_id, "id": run_id},
        )
    assert "substitute_not_own_run" in str(apply.value.orig)

    with pytest.raises((ProgrammingError, InternalError)) as cancel:
        _run_as_lims_app(
            migrated_engine,
            tech.id,
            "UPDATE lims_runs SET status = 'canceled' WHERE id = :id",
            {"id": run_id},
        )
    assert "run_has_imported_data" in str(cancel.value.orig)


def test_imported_rows_are_immutable_for_lims_app(migrated_engine):
    with migrated_engine.connect() as conn:
        for table in ("lims_run_imports", "lims_run_data"):
            for privilege in ("UPDATE", "DELETE"):
                allowed = conn.execute(
                    text("SELECT has_table_privilege('lims_app', :t, :p)"),
                    {"t": table, "p": privilege},
                ).scalar()
                assert allowed is False, f"{table} {privilege}"
            assert conn.execute(
                text("SELECT has_table_privilege('lims_app', :t, 'SELECT')"),
                {"t": table},
            ).scalar() is True
            assert conn.execute(
                text("SELECT has_table_privilege('lims_app', :t, 'INSERT')"),
                {"t": table},
            ).scalar() is True

    with migrated_engine.begin() as conn:
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        uid = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, 'e3i', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e3i-{uid.hex[:6]}",
                "e": f"e3i-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'failed', :u, :u)"
            ),
            {"id": run_id, "n": f"e3fail-{run_id.hex[:6]}", "u": uid},
        )
        import_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_imports (id, lims_run_id, filename, imported_by) "
                "VALUES (:id, :r, 'kept.csv', :u)"
            ),
            {"id": import_id, "r": run_id, "u": uid},
        )
        data_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_data (id, lims_run_id, row_data, import_id, created_by) "
                "VALUES (:id, :r, '{}'::jsonb, :i, :u)"
            ),
            {"id": data_id, "r": run_id, "i": import_id, "u": uid},
        )

    with pytest.raises(ProgrammingError):
        _run_as_lims_app(
            migrated_engine,
            uid,
            "DELETE FROM lims_run_imports WHERE id = :id",
            {"id": import_id},
        )
    with pytest.raises(ProgrammingError):
        _run_as_lims_app(
            migrated_engine,
            uid,
            "UPDATE lims_run_imports SET filename = 'x' WHERE id = :id",
            {"id": import_id},
        )
    with pytest.raises(ProgrammingError):
        _run_as_lims_app(
            migrated_engine,
            uid,
            "DELETE FROM lims_run_data WHERE id = :id",
            {"id": data_id},
        )
    with pytest.raises(ProgrammingError):
        _run_as_lims_app(
            migrated_engine,
            uid,
            "UPDATE lims_run_data SET row_data = '{\"x\":1}'::jsonb WHERE id = :id",
            {"id": data_id},
        )
    with migrated_engine.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM lims_run_imports WHERE id = :id"),
            {"id": import_id},
        ).scalar() == 1
        assert conn.execute(
            text("SELECT count(*) FROM lims_run_data WHERE id = :id"),
            {"id": data_id},
        ).scalar() == 1


def test_reason_length_check_on_substitution(migrated_engine):
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
                "VALUES (:id, 'e3r', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e3r-{uid.hex[:6]}",
                "e": f"e3r-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'draft', :u, :u)"
            ),
            {"id": run_id, "n": f"e3rr-{run_id.hex[:6]}", "u": uid},
        )
        with pytest.raises((IntegrityError, InternalError, ProgrammingError)):
            conn.execute(
                text(
                    "INSERT INTO lims_run_type_substitutions "
                    "(lims_run_id, to_instrument_type_id, reason, created_by) "
                    "VALUES (:r, :t, :reason, :u)"
                ),
                {"r": run_id, "t": type_id, "u": uid, "reason": "x" * 1001},
            )
