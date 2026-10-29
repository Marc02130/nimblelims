"""E3 instrument hardening: void reason, tracking pin, DB guards, template active."""
import uuid
from datetime import date

import pytest
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError

from app.core.db_errors import pgcode

from models.instrument import InstrumentMaintenanceAudit, InstrumentScheduleAudit
from tests.test_instrument_e2_review_fixes import _seed_schedule_event
from tests.test_instrument_e2_type_slots import _create_run, _create_template, _start_run
from tests.test_instrument_hardening_e1 import (
    _role_user,
    _run_as_direct_lims_app,
    _run_as_lims_app,
    _schedule,
)
from tests.test_instrument_tracking import _instrument, _login, _name


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


@contextmanager
def _import_write_grants(engine):
    tables = ("lims_run_imports", "lims_run_data")
    with engine.begin() as conn:
        for table in tables:
            conn.execute(text(f"GRANT UPDATE ON TABLE {table} TO lims_app"))
            conn.execute(text(f"GRANT DELETE ON TABLE {table} TO lims_app"))
    try:
        yield
    finally:
        with engine.begin() as conn:
            for table in tables:
                conn.execute(text(f"REVOKE UPDATE ON TABLE {table} FROM lims_app"))
                conn.execute(text(f"REVOKE DELETE ON TABLE {table} FROM lims_app"))


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


def test_void_reason_db_check_and_trigger(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)) as blank:
        _run_as_lims_app(
            migrated_engine,
            ids["uid"],
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = '   ' WHERE id = :id",
            {"id": ids["event"]},
        )
    assert "void_reason_required" in str(blank.value.orig) or "ck_instrument_events_void_reason" in str(
        blank.value.orig
    )
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)):
        _run_as_lims_app(
            migrated_engine,
            ids["uid"],
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = :r WHERE id = :id",
            {"id": ids["event"], "r": "x" * 1001},
        )
    _run_as_lims_app(
        migrated_engine,
        ids["uid"],
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = 'db reason' WHERE id = :id",
        {"id": ids["event"]},
    )
    _run_as_lims_app(
        migrated_engine,
        ids["uid"],
        "UPDATE instrument_maintenance_events "
        "SET active = true, void_reason = NULL WHERE id = :id",
        {"id": ids["event"]},
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
    assert (False, True) in values
    assert (True, False) in values
    assert all(a.created_by == test_admin_user.id for a in audits if a.new_value in (True, False))


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

    admin_inactive_only = client.get(
        "/v1/experiment-templates?active=false&page=1&size=500",
        headers=admin_h,
    )
    assert admin_inactive_only.status_code == 200, admin_inactive_only.text
    inactive_ids = {row["id"] for row in admin_inactive_only.json()["templates"]}
    assert template["id"] in inactive_ids
    assert all(row["active"] is False for row in admin_inactive_only.json()["templates"])

    tech_active_false = client.get(
        "/v1/experiment-templates?active=false&page=1&size=500",
        headers=tech_h,
    )
    assert template["id"] not in {row["id"] for row in tech_active_false.json()["templates"]}
    assert all(row["active"] is True for row in tech_active_false.json()["templates"])

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


def test_db_refuses_foreign_substitution_and_cancel_after_import(migrated_engine):
    with migrated_engine.begin() as conn:
        tech_role = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        owner = uuid.uuid4()
        tech = uuid.uuid4()
        for uid, label in ((owner, "own"), (tech, "tech")):
            conn.execute(
                text(
                    "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                    "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
                ),
                {
                    "id": uid,
                    "n": f"e3s-{label}-{uid.hex[:6]}",
                    "u": f"e3s-{label}-{uid.hex[:6]}",
                    "e": f"e3s-{label}-{uid.hex[:6]}@x.org",
                    "r": tech_role,
                    "c": client_id,
                },
            )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'running', :u, :u)"
            ),
            {"id": run_id, "n": f"e3sub-{run_id.hex[:6]}", "u": owner},
        )
        conn.execute(
            text(
                "INSERT INTO lims_run_imports (id, lims_run_id, filename, imported_by) "
                "VALUES (:id, :r, 'admin_override', :u)"
            ),
            {"id": uuid.uuid4(), "r": run_id, "u": owner},
        )
        for table, privilege in (
            ("lims_runs", "SELECT"),
            ("lims_runs", "UPDATE"),
            ("lims_run_type_substitutions", "INSERT"),
            ("users", "SELECT"),
        ):
            _grant_if_missing(conn, table, privilege)

    with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as sub:
        _run_as_lims_app(
            migrated_engine,
            tech,
            "INSERT INTO lims_run_type_substitutions "
            "(lims_run_id, to_instrument_type_id, reason, created_by) "
            "VALUES (:r, :t, 'not mine', :u)",
            {"r": run_id, "t": type_id, "u": tech},
        )
    assert "substitute_not_own_run" in str(sub.value.orig)

    with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as apply:
        _run_as_lims_app(
            migrated_engine,
            tech,
            "UPDATE lims_runs SET instrument_type_id = :t WHERE id = :id",
            {"t": type_id, "id": run_id},
        )
    assert "substitute_not_own_run" in str(apply.value.orig)

    with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as cancel:
        _run_as_lims_app(
            migrated_engine,
            tech,
            "UPDATE lims_runs SET status = 'canceled' WHERE id = :id",
            {"id": run_id},
        )
    assert "run_has_imported_data" in str(cancel.value.orig)


def test_imported_rows_are_immutable_for_lims_app(migrated_engine):
    with migrated_engine.begin() as conn:
        for table in ("lims_run_imports", "lims_run_data"):
            _grant_if_missing(conn, table, "SELECT")
            _grant_if_missing(conn, table, "INSERT")
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
                "VALUES (:id, :r, 'admin_override', :u)"
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
            "UPDATE lims_run_data SET row_data = CAST(:payload AS jsonb) WHERE id = :id",
            {"id": data_id, "payload": '{"changed":true}'},
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


def test_blank_current_user_id_guc_is_sentinel(migrated_engine):
    with migrated_engine.connect() as conn:
        conn.execute(text("RESET ROLE"))
        conn.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        value = conn.execute(text("SELECT current_user_id()")).scalar()
        assert str(value) == "00000000-0000-0000-0000-000000000000"


def test_0117_revision_id_and_single_head():
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    text_src = (backend / "db/migrations/versions/0117_e3_hardening.py").read_text()
    assert 'revision = "0117_e3_hardening"' in text_src
    assert len("0117_e3_hardening") <= 32
    assert 'down_revision = "0116_e2_review_fixes"' in text_src
    assert "GRANT DELETE" not in text_src
    assert "NULLIF(current_setting('app.current_user_id', true), '')" in text_src
    assert "skip_app_row_guard" in text_src
    assert "session_user = 'lims_app'" in text_src
    assert "IS DISTINCT FROM 'lims_app' THEN" not in text_src
    assert "0117 refuses CHECK" in text_src
    assert "run_created_by_immutable" in text_src
    assert "REVOKE UPDATE ON lims_run_imports FROM lims_app" in text_src
    assert "REVOKE DELETE ON lims_run_imports FROM lims_app" in text_src
    assert "from db.append_only_tables import" not in text_src
    assert "ARRAY['lims_migrate', 'schema_apply', 'postgres']" in text_src
    heads = [p.name for p in (backend / "db/migrations/versions").glob("0117*.py")]
    assert heads == ["0117_e3_hardening.py"]


def test_0118_revision_id_and_single_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    text_src = (backend / "db/migrations/versions/0118_e3_followups.py").read_text()
    assert 'revision = "0118_e3_followups"' in text_src
    assert len("0118_e3_followups") <= 32
    assert 'down_revision = "0117_e3_hardening"' in text_src
    assert "GRANT DELETE" not in text_src
    assert "REVOKE DELETE ON TABLE lab_settings FROM lims_app" in text_src
    assert "_WS = r\"E' \\t\\r\\n'\"" in text_src
    assert "btrim(reason, {_WS})" in text_src
    assert "from app.core.bootstrap_roles import" not in text_src
    assert "0118 refuses CHECK" in text_src
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "db/migrations"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, heads
    assert len(heads[0]) <= 32
    files = [p.name for p in (backend / "db/migrations/versions").glob("0118*.py")]
    assert files == ["0118_e3_followups.py"]


def test_direct_lims_app_void_and_reset_role_still_enforce(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)) as blank:
        _run_as_direct_lims_app(
            migrated_engine,
            ids["uid"],
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = '   ' WHERE id = :id",
            {"id": ids["event"]},
        )
    assert "void_reason_required" in str(blank.value.orig)
    assert pgcode(blank.value) == "23514"
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)) as after_reset:
        _run_as_direct_lims_app(
            migrated_engine,
            ids["uid"],
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = '   ' WHERE id = :id",
            {"id": ids["event"]},
            reset_role=True,
        )
    assert "void_reason_required" in str(after_reset.value.orig)
    assert pgcode(after_reset.value) == "23514"


def test_direct_lims_app_substitution_cancel_import_and_created_by(migrated_engine):
    with migrated_engine.begin() as conn:
        tech_role = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        owner = uuid.uuid4()
        tech = uuid.uuid4()
        for uid, label in ((owner, "own"), (tech, "tech")):
            conn.execute(
                text(
                    "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                    "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
                ),
                {
                    "id": uid,
                    "n": f"e3d-{label}-{uid.hex[:6]}",
                    "u": f"e3d-{label}-{uid.hex[:6]}",
                    "e": f"e3d-{label}-{uid.hex[:6]}@x.org",
                    "r": tech_role,
                    "c": client_id,
                },
            )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'running', :u, :u)"
            ),
            {"id": run_id, "n": f"e3d-{run_id.hex[:6]}", "u": owner},
        )
        import_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_imports (id, lims_run_id, filename, imported_by) "
                "VALUES (:id, :r, 'admin_override', :u)"
            ),
            {"id": import_id, "r": run_id, "u": owner},
        )
        data_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_data (id, lims_run_id, row_data, import_id, created_by) "
                "VALUES (:id, :r, '{}'::jsonb, :i, :u)"
            ),
            {"id": data_id, "r": run_id, "i": import_id, "u": owner},
        )
    with _import_write_grants(migrated_engine):
        with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as sub:
            _run_as_direct_lims_app(
                migrated_engine,
                tech,
                "INSERT INTO lims_run_type_substitutions "
                "(lims_run_id, to_instrument_type_id, reason, created_by) "
                "VALUES (:r, :t, 'not mine', :u)",
                {"r": run_id, "t": type_id, "u": tech},
            )
        assert "substitute_not_own_run" in str(sub.value.orig)
        assert pgcode(sub.value) == "42501"

        with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as apply:
            _run_as_direct_lims_app(
                migrated_engine,
                tech,
                "UPDATE lims_runs SET instrument_type_id = :t WHERE id = :id",
                {"t": type_id, "id": run_id},
            )
        assert "substitute_not_own_run" in str(apply.value.orig)
        assert pgcode(apply.value) == "42501"

        with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as cancel:
            _run_as_direct_lims_app(
                migrated_engine,
                tech,
                "UPDATE lims_runs SET status = 'canceled' WHERE id = :id",
                {"id": run_id},
            )
        assert "run_has_imported_data" in str(cancel.value.orig)
        assert pgcode(cancel.value) == "23514"

        with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as stolen:
            _run_as_direct_lims_app(
                migrated_engine,
                tech,
                "UPDATE lims_runs SET created_by = :u WHERE id = :id",
                {"u": tech, "id": run_id},
            )
        assert "run_created_by_immutable" in str(stolen.value.orig)
        assert pgcode(stolen.value) == "42501"

        with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as imp:
            _run_as_direct_lims_app(
                migrated_engine,
                tech,
                "UPDATE lims_run_imports SET filename = 'x' WHERE id = :id",
                {"id": import_id},
            )
        assert "imported_row_immutable" in str(imp.value.orig)
        assert pgcode(imp.value) == "42501"

        with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as data:
            _run_as_direct_lims_app(
                migrated_engine,
                tech,
                "DELETE FROM lims_run_data WHERE id = :id",
                {"id": data_id},
            )
        assert "imported_row_immutable" in str(data.value.orig)
        assert pgcode(data.value) == "42501"


def test_whitespace_only_reasons_are_blank_api_and_db(
    client, admin_h, db_session, test_admin_user, run_analysis_id, cohort_sample_id
):
    from tests.test_instrument_tracking import _seeded_type

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
    for blank in ("\t", "\n", "\r", "\r\n", " \t\n "):
        refused = client.patch(
            f"/v1/instrument-maintenance-events/{event_id}",
            headers=admin_h,
            json={"active": False, "reason": blank},
        )
        assert refused.status_code == 422, (blank, refused.text)
        assert refused.json()["detail"]["code"] == "void_reason_required"

    template = _create_template(client, admin_h)
    run = _create_run(client, admin_h, template["id"], run_analysis_id)
    assert run.status_code == 201, run.text
    started = _start_run(client, admin_h, run.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    qpcr = _seeded_type(client, admin_h, "qPCR")
    for blank in ("\t", "\n", " \t\n "):
        refused = client.post(
            f"/v1/lims-runs/{run.json()['id']}/substitute-instrument-type",
            headers=admin_h,
            json={"instrument_type_id": qpcr["id"], "reason": blank},
        )
        assert refused.status_code == 422, (blank, refused.text)


def test_whitespace_only_reasons_fail_db_checks(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
    for blank in ("\t", "\n", "\r\n", " \t\n "):
        with pytest.raises((IntegrityError, InternalError, ProgrammingError)) as err:
            _run_as_lims_app(
                migrated_engine,
                ids["uid"],
                "UPDATE instrument_maintenance_events "
                "SET active = false, void_reason = :r WHERE id = :id",
                {"id": ids["event"], "r": blank},
            )
        msg = str(err.value.orig)
        assert "void_reason_required" in msg or "ck_instrument_events_void_reason" in msg

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
                "VALUES (:id, 'e3ws', :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "u": f"e3ws-{uid.hex[:6]}",
                "e": f"e3ws-{uid.hex[:6]}@x.org",
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
            {"id": run_id, "n": f"e3ws-{run_id.hex[:6]}", "u": uid},
        )
        for blank in ("\t", "\n", "\r\n"):
            with pytest.raises((IntegrityError, InternalError, ProgrammingError)):
                conn.execute(
                    text(
                        "INSERT INTO lims_run_type_substitutions "
                        "(lims_run_id, to_instrument_type_id, reason, created_by) "
                        "VALUES (:r, :t, :reason, :u)"
                    ),
                    {"r": run_id, "t": type_id, "u": uid, "reason": blank},
                )


def test_lab_settings_delete_revoked_for_app_role(migrated_engine):
    with migrated_engine.connect() as conn:
        allowed = conn.execute(
            text("SELECT has_table_privilege('lims_app', 'lab_settings', 'DELETE')")
        ).scalar()
        assert allowed is False
        for privilege in ("SELECT", "INSERT", "UPDATE"):
            assert conn.execute(
                text("SELECT has_table_privilege('lims_app', 'lab_settings', :p)"),
                {"p": privilege},
            ).scalar() is True


def test_direct_lims_app_guards_survive_reset_and_set_role_none(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    modes = ({}, {"reset_role": True}, {"set_role_none": True})
    for mode in modes:
        with pytest.raises((IntegrityError, InternalError, ProgrammingError)) as blank:
            _run_as_direct_lims_app(
                migrated_engine,
                ids["uid"],
                "UPDATE instrument_maintenance_events "
                "SET active = false, void_reason = E'\\t' WHERE id = :id",
                {"id": ids["event"]},
                **mode,
            )
        assert "void_reason_required" in str(blank.value.orig)
        assert pgcode(blank.value) == "23514"

    with migrated_engine.begin() as conn:
        tech_role = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        owner = uuid.uuid4()
        tech = uuid.uuid4()
        for uid, label in ((owner, "own"), (tech, "tech")):
            conn.execute(
                text(
                    "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                    "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
                ),
                {
                    "id": uid,
                    "n": f"e3n-{label}-{uid.hex[:6]}",
                    "u": f"e3n-{label}-{uid.hex[:6]}",
                    "e": f"e3n-{label}-{uid.hex[:6]}@x.org",
                    "r": tech_role,
                    "c": client_id,
                },
            )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, created_by, modified_by) "
                "VALUES (:id, :n, 'running', :u, :u)"
            ),
            {"id": run_id, "n": f"e3n-{run_id.hex[:6]}", "u": owner},
        )
        import_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_imports (id, lims_run_id, filename, imported_by) "
                "VALUES (:id, :r, 'admin_override', :u)"
            ),
            {"id": import_id, "r": run_id, "u": owner},
        )
        data_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_run_data (id, lims_run_id, row_data, import_id, created_by) "
                "VALUES (:id, :r, '{}'::jsonb, :i, :u)"
            ),
            {"id": data_id, "r": run_id, "i": import_id, "u": owner},
        )
    guards = (
        (
            "INSERT INTO lims_run_type_substitutions "
            "(lims_run_id, to_instrument_type_id, reason, created_by) "
            "VALUES (:r, :t, 'not mine', :u)",
            {"r": run_id, "t": type_id, "u": tech},
            "substitute_not_own_run",
        ),
        (
            "UPDATE lims_runs SET instrument_type_id = :t WHERE id = :id",
            {"t": type_id, "id": run_id},
            "substitute_not_own_run",
        ),
        (
            "UPDATE lims_runs SET status = 'canceled' WHERE id = :id",
            {"id": run_id},
            "run_has_imported_data",
        ),
        (
            "UPDATE lims_runs SET created_by = :u WHERE id = :id",
            {"u": tech, "id": run_id},
            "run_created_by_immutable",
        ),
        (
            "UPDATE lims_run_imports SET filename = 'x' WHERE id = :id",
            {"id": import_id},
            "imported_row_immutable",
        ),
        (
            "DELETE FROM lims_run_data WHERE id = :id",
            {"id": data_id},
            "imported_row_immutable",
        ),
    )
    expected_state = {
        "substitute_not_own_run": "42501",
        "run_has_imported_data": "23514",
        "run_created_by_immutable": "42501",
        "imported_row_immutable": "42501",
    }
    with _import_write_grants(migrated_engine):
        for sql, params, needle in guards:
            for mode in modes:
                with pytest.raises((ProgrammingError, InternalError, IntegrityError)) as err:
                    _run_as_direct_lims_app(
                        migrated_engine, tech, sql, params, **mode
                    )
                assert needle in str(err.value.orig), (needle, mode, err.value.orig)
                assert pgcode(err.value) == expected_state[needle], (
                    needle,
                    mode,
                    pgcode(err.value),
                )


_UNICODE_REASON_CASES = (
    ("nbsp", "\u00a0"),
    *( (f"u{code:04x}", chr(code)) for code in range(0x2000, 0x200B) ),
    ("u3000", "\u3000"),
    ("zwsp", "\u200b"),
    ("bom", "\ufeff"),
)


def test_unicode_whitespace_reason_behavior_is_recorded(
    client, admin_h, db_session, test_admin_user, migrated_engine
):
    """Record API vs DB for Unicode whitespace. Marc decides whether they should match."""
    from app.core.visible_text import has_visible_text

    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat()},
    )
    api_rows = []
    for name, char in _UNICODE_REASON_CASES:
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
        refused = client.patch(
            f"/v1/instrument-maintenance-events/{created.json()['id']}",
            headers=admin_h,
            json={"active": False, "reason": char},
        )
        code = None
        if refused.status_code == 422:
            detail = refused.json().get("detail")
            code = detail.get("code") if isinstance(detail, dict) else "pydantic"
        api_rows.append(
            (
                name,
                has_visible_text(char),
                refused.status_code,
                code,
            )
        )

    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
    db_rows = []
    for name, char in _UNICODE_REASON_CASES:
        try:
            _run_as_lims_app(
                migrated_engine,
                ids["uid"],
                "UPDATE instrument_maintenance_events "
                "SET active = false, void_reason = :r WHERE id = :id",
                {"id": ids["event"], "r": char},
            )
            db_rows.append((name, "accepted", None))
            # FLAG: the manager-only trigger still allows active false→true.
            _run_as_lims_app(
                migrated_engine,
                ids["uid"],
                "UPDATE instrument_maintenance_events "
                "SET active = true, void_reason = NULL WHERE id = :id",
                {"id": ids["event"]},
            )
        except (IntegrityError, InternalError, ProgrammingError) as exc:
            db_rows.append((name, "rejected", pgcode(exc)))

    # Current observed behavior. Do not "fix" API or DB here.
    unicode_spaces = ("nbsp",) + tuple(f"u{code:04x}" for code in range(0x2000, 0x200B)) + ("u3000",)
    assert api_rows == [
        *((name, False, 422, "void_reason_required") for name in unicode_spaces),
        ("zwsp", True, 200, None),
        ("bom", True, 200, None),
    ]
    db_expected = [("nbsp", "accepted", None)]
    for code in range(0x2000, 0x200B):
        if code == 0x2007:
            db_expected.append((f"u{code:04x}", "accepted", None))
        else:
            db_expected.append((f"u{code:04x}", "rejected", "23514"))
    db_expected.extend(
        [
            ("u3000", "rejected", "23514"),
            ("zwsp", "accepted", None),
            ("bom", "accepted", None),
        ]
    )
    assert db_rows == db_expected


def test_db_manager_can_still_reactivate_voided_event(migrated_engine):
    """FLAG: API refuses restore; a Lab Manager / Admin UPDATE as lims_app does not.

    refuse_void_only_passing_event checks manager/admin, void_reason on
    true→false, and locks the schedule. It does not refuse false→true.
    Blocking that at the DB needs a migration Edmund has not approved.
    """
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    failed = _seed_schedule_event(migrated_engine, next_due=date.today(), passed=False)
    void_sql = (
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = 'db void' WHERE id = :id"
    )
    restore_sql = (
        "UPDATE instrument_maintenance_events "
        "SET active = true WHERE id = :id"
    )
    _run_as_lims_app(migrated_engine, ids["uid"], void_sql, {"id": ids["event"]})
    _run_as_lims_app(migrated_engine, ids["uid"], restore_sql, {"id": ids["event"]})
    _run_as_lims_app(migrated_engine, failed["uid"], void_sql, {"id": failed["event"]})
    _run_as_lims_app(migrated_engine, failed["uid"], restore_sql, {"id": failed["event"]})
    with migrated_engine.connect() as conn:
        passing = conn.execute(
            text("SELECT active FROM instrument_maintenance_events WHERE id = :id"),
            {"id": ids["event"]},
        ).scalar()
        failed_active = conn.execute(
            text("SELECT active FROM instrument_maintenance_events WHERE id = :id"),
            {"id": failed["event"]},
        ).scalar()
    assert passing is True
    assert failed_active is True
