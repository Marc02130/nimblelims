"""Günter E2 review fixes: 0115 downgrade guard, 0116 ledger, CRO import, slots."""
import importlib.util
import json
import threading
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import InternalError, ProgrammingError
from sqlalchemy.orm import sessionmaker

from app.core.db_errors import pgcode
from models.experiment import Experiment
from models.entry import Entry
from models.flexible_experiment import DataParser, ParserAnalysis
from models.instrument import InstrumentScheduleAudit
from models.user import User
from tests.test_flexible_experiment import PLATE_READER_TYPE_ID, VALID_TEMPLATE_DEF
from tests.test_instrument_e2_type_slots import _create_run, _create_template, _start_run
from tests.test_instrument_hardening_e1 import _run_as_lims_app
from tests.test_instrument_tracking import _instrument, _login, _name, _seeded_type

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION_0115 = BACKEND / "db/migrations/versions/0115_instrument_type_slots.py"
MIGRATION_0116 = BACKEND / "db/migrations/versions/0116_e2_review_fixes.py"


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _load_migration(path):
    spec = importlib.util.spec_from_file_location("m" + path.name[:4], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _simple_parser_config():
    return {
        "columns": [{"source_col": "Well", "field_name": "well", "data_type": "string"}],
        "well_col": "Well",
    }


def _add_cro_parser(db_session, analysis_id, cro_source_id):
    parser = DataParser(
        name=_name("CroP"),
        parser_config=_simple_parser_config(),
        cro_source_id=cro_source_id,
        version_group_id=uuid.uuid4(),
        version=1,
        active=True,
    )
    db_session.add(parser)
    db_session.flush()
    db_session.add(ParserAnalysis(parser_id=parser.id, analysis_id=analysis_id, is_default=True))
    db_session.commit()
    return parser


def test_m1_0115_downgrade_refuses_data_and_passes_when_empty(migrated_engine):
    m0115 = _load_migration(MIGRATION_0115)
    connection = migrated_engine.connect()
    transaction = connection.begin()
    try:
        conn = connection
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        uid = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "n": f"m1-{uid.hex[:6]}",
                "u": f"m1-{uid.hex[:6]}",
                "e": f"m1-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        run_id = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, instrument_type_id, created_by, modified_by) "
                "VALUES (:id, :n, 'draft', :t, :u, :u)"
            ),
            {"id": run_id, "n": f"m1r-{run_id.hex[:6]}", "t": type_id, "u": uid},
        )
        conn.execute(
            text(
                "INSERT INTO lims_run_type_substitutions "
                "(id, lims_run_id, from_instrument_type_id, to_instrument_type_id, reason, created_by) "
                "VALUES (:id, :r, :t, :t, 'seed', :u)"
            ),
            {"id": uuid.uuid4(), "r": run_id, "t": type_id, "u": uid},
        )
        inst = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instruments (id, name, instrument_type_id, status, active, "
                "maintenance_tracked, created_by, modified_by) "
                "VALUES (:id, :n, :t, 'in_service', true, true, :u, :u)"
            ),
            {"id": inst, "n": f"M1-{inst.hex[:6]}", "t": type_id, "u": uid},
        )
        conn.execute(
            text(
                "INSERT INTO instrument_uses "
                "(id, instrument_id, lims_run_id, used_on, entry_id, slot_key, created_by, modified_by) "
                "VALUES (:id, :i, :r, CURRENT_DATE, NULL, 'reader', :u, :u)"
            ),
            {"id": uuid.uuid4(), "i": inst, "r": run_id, "u": uid},
        )
        conn.execute(
            text(
                "INSERT INTO instrument_schedule_audits "
                "(id, instrument_id, action, reason, created_by) "
                "VALUES (:id, :i, 'first_due', 'why', :u)"
            ),
            {"id": uuid.uuid4(), "i": inst, "u": uid},
        )
        with pytest.raises(RuntimeError, match="0115 downgrade refuses"):
            m0115.refuse_downgrade_if_slot_data(conn)
    finally:
        transaction.rollback()
        connection.close()


def test_m1_0115_downgrade_empty_passes_then_rolls_back(migrated_engine):
    m0115 = _load_migration(MIGRATION_0115)
    connection = migrated_engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(text("DELETE FROM lims_run_type_substitutions"))
        connection.execute(text("UPDATE lims_runs SET instrument_type_id = NULL"))
        connection.execute(text("UPDATE instrument_uses SET entry_id = NULL, slot_key = NULL"))
        connection.execute(text("UPDATE instrument_schedule_audits SET reason = NULL"))
        m0115.refuse_downgrade_if_slot_data(connection)
    finally:
        transaction.rollback()
        connection.close()


def test_m2_ledger_flips_untyped_templates_on_nonempty_db(migrated_engine):
    m0116 = _load_migration(MIGRATION_0116)
    connection = migrated_engine.connect()
    transaction = connection.begin()
    try:
        conn = connection
        admin = conn.execute(
            text(
                "SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id "
                "WHERE r.name = 'Administrator' LIMIT 1"
            )
        ).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        assert admin and type_id
        referenced = uuid.uuid4()
        unreferenced = uuid.uuid4()
        typed = uuid.uuid4()
        plain = uuid.uuid4()
        run_id = uuid.uuid4()
        typed_run = uuid.uuid4()
        untyped_slot = {
            "entries": [
                {
                    "entry_type": "instrument",
                    "predefined_entry_key": "instruments",
                    "config": {
                        "slots": [
                            {
                                "key": "run_import",
                                "label": "Import",
                                "run_import": True,
                            }
                        ]
                    },
                }
            ]
        }
        typed_slot = {
            "entries": [
                {
                    "entry_type": "instrument",
                    "predefined_entry_key": "instruments",
                    "config": {
                        "slots": [
                            {
                                "key": "run_import",
                                "label": "Import",
                                "run_import": True,
                                "instrument_type_id": str(type_id),
                            }
                        ]
                    },
                }
            ]
        }
        for tid, name, definition, active in (
            (referenced, f"m2-ref-{referenced.hex[:6]}", {"entries": []}, True),
            (unreferenced, f"m2-unref-{unreferenced.hex[:6]}", untyped_slot, True),
            (typed, f"m2-typed-{typed.hex[:6]}", typed_slot, True),
            (plain, f"m2-plain-{plain.hex[:6]}", {"experiment_name": "plain"}, True),
        ):
            conn.execute(
                text(
                    "INSERT INTO experiment_templates "
                    "(id, name, template_definition, active, created_by, modified_by) "
                    "VALUES (:id, :n, CAST(:d AS jsonb), :a, :u, :u)"
                ),
                {"id": tid, "n": name, "d": json.dumps(definition), "a": active, "u": admin},
            )
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, experiment_template_id, created_by, modified_by) "
                "VALUES (:id, :n, 'draft', :t, :u, :u)"
            ),
            {"id": run_id, "n": f"m2r-{run_id.hex[:6]}", "t": referenced, "u": admin},
        )
        conn.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, experiment_template_id, created_by, modified_by) "
                "VALUES (:id, :n, 'draft', :t, :u, :u)"
            ),
            {"id": typed_run, "n": f"m2t-{typed_run.hex[:6]}", "t": typed, "u": admin},
        )
        before_templates = conn.execute(text("SELECT count(*) FROM experiment_templates")).scalar()
        before_runs = conn.execute(text("SELECT count(*) FROM lims_runs")).scalar()
        run_snap = conn.execute(
            text(
                "SELECT id, experiment_template_id, status, name FROM lims_runs "
                "WHERE id IN (:a, :b) ORDER BY id"
            ),
            {"a": run_id, "b": typed_run},
        ).all()
        m0116.ledger_untyped_lims_run_templates(conn)
        after_templates = conn.execute(text("SELECT count(*) FROM experiment_templates")).scalar()
        after_runs = conn.execute(text("SELECT count(*) FROM lims_runs")).scalar()
        assert after_templates == before_templates
        assert after_runs == before_runs
        after_snap = conn.execute(
            text(
                "SELECT id, experiment_template_id, status, name FROM lims_runs "
                "WHERE id IN (:a, :b) ORDER BY id"
            ),
            {"a": run_id, "b": typed_run},
        ).all()
        assert after_snap == run_snap
        states = {
            row[0]: (row[1], row[2])
            for row in conn.execute(
                text(
                    "SELECT id, active, modified_by FROM experiment_templates "
                    "WHERE id IN (:a, :b, :c, :d)"
                ),
                {"a": referenced, "b": unreferenced, "c": typed, "d": plain},
            ).all()
        }
        assert states[referenced][0] is False
        assert states[unreferenced][0] is False
        assert states[typed][0] is True
        assert states[plain][0] is True
        assert states[referenced][1] == admin
        assert states[unreferenced][1] == admin
        ledger = conn.execute(
            text(
                "SELECT experiment_template_id, reason, created_by "
                "FROM instrument_template_inactivations "
                "WHERE experiment_template_id IN (:a, :b, :c, :d) "
                "ORDER BY experiment_template_id"
            ),
            {"a": referenced, "b": unreferenced, "c": typed, "d": plain},
        ).all()
        ids = {row[0] for row in ledger}
        assert ids == {referenced, unreferenced}
        assert {row[1] for row in ledger} == {"0115_untyped_lims_run_template"}
        assert {row[2] for row in ledger} == {admin}
    finally:
        transaction.rollback()
        connection.close()


def test_m2_ledger_privileges_and_force_rls(migrated_engine):
    with migrated_engine.connect() as conn:
        for privilege, allowed in (
            ("SELECT", True),
            ("INSERT", True),
            ("UPDATE", False),
            ("DELETE", False),
        ):
            got = conn.execute(
                text("SELECT has_table_privilege('lims_app', 'instrument_template_inactivations', :p)"),
                {"p": privilege},
            ).scalar()
            assert got is allowed, privilege
        forced = conn.execute(
            text(
                "SELECT relforcerowsecurity FROM pg_class "
                "WHERE relname = 'instrument_template_inactivations'"
            )
        ).scalar()
        assert forced is True


def test_m3_cro_source_import_refused_on_standard_run(
    client, admin_h, db_session, run_analysis_id, cohort_sample_id
):
    cro = client.post("/v1/cro-sources", headers=admin_h, json={"name": _name("CRO")})
    assert cro.status_code == 201, cro.text
    parser = _add_cro_parser(db_session, run_analysis_id, cro.json()["id"])
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    data = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={
            "cro_source_id": cro.json()["id"],
            "parser_id": str(parser.id),
            "rows": [{"well_position": "A1", "row_data": {"well": "A1"}}],
        },
    )
    assert data.status_code == 422, data.text
    assert data.json()["detail"]["code"] == "cro_import_requires_cro_run"
    file_refused = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import-file",
        headers=admin_h,
        files={"file": ("plate.csv", b"Well\nA1\n", "text/csv")},
        data={"cro_source_id": cro.json()["id"], "parser_id": str(parser.id)},
    )
    assert file_refused.status_code == 422, file_refused.text
    assert file_refused.json()["detail"]["code"] == "cro_import_requires_cro_run"


def test_m3_cro_source_import_still_skips_on_cro_run(
    client, admin_h, db_session, run_analysis_id, cohort_sample_id
):
    cro = client.post("/v1/cro-sources", headers=admin_h, json={"name": _name("CRO-ok")})
    assert cro.status_code == 201, cro.text
    parser = _add_cro_parser(db_session, run_analysis_id, cro.json()["id"])
    template = client.post(
        "/v1/experiment-templates",
        headers=admin_h,
        json={
            "name": _name("CRO-T"),
            "lifecycle_type": "cro",
            "template_definition": {
                **VALID_TEMPLATE_DEF,
                "entries": [
                    {
                        "entry_type": "instrument",
                        "predefined_entry_key": "instruments",
                        "name": "Instruments",
                        "config": {
                            "slots": [
                                {
                                    "key": "run_import",
                                    "label": "Import",
                                    "instrument_type_id": PLATE_READER_TYPE_ID,
                                    "required": True,
                                    "run_import": True,
                                }
                            ]
                        },
                    }
                ],
            },
        },
    )
    assert template.status_code == 201, template.text
    created = _create_run(client, admin_h, template.json()["id"], run_analysis_id)
    assert created.status_code == 201, created.text
    ordered = client.patch(f"/v1/lims-runs/{created.json()['id']}/order", headers=admin_h)
    assert ordered.status_code == 200, ordered.text
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    data = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import",
        headers=admin_h,
        json={
            "cro_source_id": cro.json()["id"],
            "parser_id": str(parser.id),
            "rows": [{"well_position": "A1", "row_data": {"well": "A1"}}],
        },
    )
    assert data.status_code == 200, data.text
    file_ok = client.post(
        f"/v1/lims-runs/{created.json()['id']}/import-file",
        headers=admin_h,
        files={"file": ("plate.csv", b"Well\nA1\n", "text/csv")},
        data={"cro_source_id": cro.json()["id"], "parser_id": str(parser.id)},
    )
    assert file_ok.status_code == 200, file_ok.text


def test_m4_entry_must_belong_to_experiment_and_not_a_run(
    client, admin_h, db_session, test_admin_user, run_analysis_id, cohort_sample_id
):
    type_id = _seeded_type(client, admin_h)["id"]
    inst = _instrument(client, admin_h, instrument_type_id=type_id)
    exp = Experiment(name=_name("ExpA"), created_by=test_admin_user.id, modified_by=test_admin_user.id)
    other = Experiment(name=_name("ExpB"), created_by=test_admin_user.id, modified_by=test_admin_user.id)
    db_session.add_all([exp, other])
    db_session.flush()
    entry = Entry(
        experiment_id=exp.id,
        entry_type="instrument",
        name="Instruments",
        predefined_entry_key="instruments",
        sort_order=0,
        config={
            "slots": [
                {
                    "key": "reader",
                    "label": "Reader",
                    "instrument_type_id": type_id,
                    "required": True,
                }
            ],
            "allowed_instrument_ids": [inst["id"]],
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(entry)
    db_session.commit()
    template = _create_template(client, admin_h)
    created = _create_run(client, admin_h, template["id"], run_analysis_id)
    started = _start_run(client, admin_h, created.json()["id"], cohort_sample_id)
    assert started.status_code == 200, started.text
    both = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "lims_run_id": created.json()["id"],
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert both.status_code == 422, both.text
    assert both.json()["detail"]["code"] == "use_target_conflict"
    missing_exp = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "lims_run_id": created.json()["id"],
            "entry_id": str(entry.id),
            "slot_key": "reader",
            "experiment_id": None,
        },
    )
    # Pydantic may drop null experiment_id; still a conflict when run+entry are sent.
    assert missing_exp.status_code == 422, missing_exp.text
    mismatch = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "experiment_id": str(other.id),
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert mismatch.status_code == 422, mismatch.text
    assert mismatch.json()["detail"]["code"] == "entry_experiment_mismatch"
    missing = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(uuid.uuid4()),
            "slot_key": "reader",
        },
    )
    assert missing.status_code == 404, missing.text
    ok = client.post(
        "/v1/instrument-uses",
        headers=admin_h,
        json={
            "instrument_id": inst["id"],
            "experiment_id": str(exp.id),
            "entry_id": str(entry.id),
            "slot_key": "reader",
        },
    )
    assert ok.status_code == 201, ok.text


def test_m4_entry_without_experiment_is_422(client, admin_h, db_session, test_admin_user):
    type_id = _seeded_type(client, admin_h)["id"]
    inst = _instrument(client, admin_h, instrument_type_id=type_id)
    exp = Experiment(name=_name("ExpC"), created_by=test_admin_user.id, modified_by=test_admin_user.id)
    db_session.add(exp)
    db_session.flush()
    entry = Entry(
        experiment_id=exp.id,
        entry_type="instrument",
        name="Instruments",
        predefined_entry_key="instruments",
        sort_order=0,
        config={
            "slots": [
                {
                    "key": "reader",
                    "label": "Reader",
                    "instrument_type_id": type_id,
                    "required": True,
                }
            ],
            "allowed_instrument_ids": [inst["id"]],
        },
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(entry)
    db_session.commit()
    from app.routers.instrument_ops import record_instrument_use
    from app.schemas.instrument_ops import InstrumentUseCreate

    body = InstrumentUseCreate(
        instrument_id=inst["id"],
        lims_run_id=None,
        experiment_id=None,
        entry_id=entry.id,
        slot_key="reader",
    )
    with pytest.raises(HTTPException) as raised:
        record_instrument_use(body, current_user=test_admin_user, db=db_session)
    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "entry_experiment_required"


def _seed_schedule_event(migrated_engine, *, next_due=None, passed=True):
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO lab_settings (id, timezone) "
                "VALUES ('b1a16ae0-0000-4000-8000-000000000001', 'UTC') "
                "ON CONFLICT (id) DO UPDATE SET timezone = 'UTC'"
            )
        )
        admin = conn.execute(text("SELECT id FROM roles WHERE name = 'Administrator'")).scalar()
        tech = conn.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar()
        client_id = conn.execute(text("SELECT id FROM clients LIMIT 1")).scalar()
        type_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'Plate reader' LIMIT 1")
        ).scalar()
        kind_id = conn.execute(
            text("SELECT id FROM list_entries WHERE name = 'PM' LIMIT 1")
        ).scalar()
        uid = uuid.uuid4()
        tech_uid = uuid.uuid4()
        other = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": uid,
                "n": f"e2rf-{uid.hex[:6]}",
                "u": f"e2rf-{uid.hex[:6]}",
                "e": f"e2rf-{uid.hex[:6]}@x.org",
                "r": admin,
                "c": client_id,
            },
        )
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": tech_uid,
                "n": f"e2rft-{tech_uid.hex[:6]}",
                "u": f"e2rft-{tech_uid.hex[:6]}",
                "e": f"e2rft-{tech_uid.hex[:6]}@x.org",
                "r": tech,
                "c": client_id,
            },
        )
        conn.execute(
            text(
                "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
            ),
            {
                "id": other,
                "n": f"e2rfo-{other.hex[:6]}",
                "u": f"e2rfo-{other.hex[:6]}",
                "e": f"e2rfo-{other.hex[:6]}@x.org",
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
            {"id": inst, "n": f"E2rf-{inst.hex[:6]}", "t": type_id, "u": uid},
        )
        sched = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instrument_maintenance_schedules "
                "(id, instrument_id, kind_id, interval_days, next_due, last_done, "
                "active, created_by, modified_by) "
                "VALUES (:id, :i, :k, 10, :due, NULL, true, :u, :u)"
            ),
            {"id": sched, "i": inst, "k": kind_id, "u": uid, "due": next_due},
        )
        event = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO instrument_maintenance_events "
                "(id, instrument_id, schedule_id, performed_on, performed_by_user_id, "
                "passed, active, created_by, modified_by) "
                "VALUES (:id, :i, :s, CURRENT_DATE, :u, :p, true, :u, :u)"
            ),
            {"id": event, "i": inst, "s": sched, "u": uid, "p": passed},
        )
    return {
        "uid": uid,
        "tech": tech_uid,
        "other": other,
        "inst": inst,
        "sched": sched,
        "event": event,
    }


def test_m5_void_waits_on_held_schedule_lock(migrated_engine):
    from app.routers.instrument_ops import update_event
    from app.schemas.instrument_ops import MaintenanceEventUpdate

    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    Session = sessionmaker(bind=migrated_engine, autoflush=False)
    inside = threading.Event()
    release = threading.Event()
    box: dict = {}

    def hold():
        from models.instrument import InstrumentMaintenanceSchedule

        with Session() as s:
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(ids["uid"])},
            )
            s.query(InstrumentMaintenanceSchedule).filter(
                InstrumentMaintenanceSchedule.id == ids["sched"]
            ).with_for_update().first()
            inside.set()
            assert release.wait(5), "test did not release the lock holder"
            s.commit()

    def do_void():
        from app.core.lab_time import publish_lab_zone

        with Session() as s:
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(ids["uid"])},
            )
            publish_lab_zone(s)
            user = s.get(User, ids["uid"])
            try:
                box["value"] = update_event(
                    ids["event"],
                    MaintenanceEventUpdate(active=False, reason="void under lock"),
                    current_user=user,
                    db=s,
                )
            except HTTPException as exc:
                box["error"] = exc
            except Exception as exc:
                box["unexpected"] = exc

    holder = threading.Thread(target=hold, daemon=True)
    waiter = threading.Thread(target=do_void, daemon=True)
    holder.start()
    assert inside.wait(5)
    waiter.start()
    deadline = time.monotonic() + 5
    waiting = False
    while time.monotonic() < deadline:
        with migrated_engine.connect() as conn:
            waiting = conn.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock' "
                    "AND query ILIKE '%instrument_maintenance_schedules%' "
                    "AND pid <> pg_backend_pid()"
                )
            ).scalar()
            conn.rollback()
        if waiting:
            break
        time.sleep(0.05)
    assert waiting, "void did not wait on FOR UPDATE of the schedule"
    release.set()
    holder.join(5)
    waiter.join(5)
    assert "unexpected" not in box, box.get("unexpected")
    assert "error" not in box, box.get("error")
    assert box.get("value") is not None


def test_first_due_lock_timeout_is_409_schedule_busy(migrated_engine):
    from app.routers.instrument_ops import set_first_due
    from app.schemas.instrument_ops import FirstDueCreate
    from models.instrument import InstrumentMaintenanceSchedule

    ids = _seed_schedule_event(migrated_engine, next_due=None)
    Session = sessionmaker(bind=migrated_engine, autoflush=False)
    inside = threading.Event()
    release = threading.Event()
    box: dict = {}

    def hold():
        with Session() as s:
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(ids["uid"])},
            )
            s.query(InstrumentMaintenanceSchedule).filter(
                InstrumentMaintenanceSchedule.id == ids["sched"]
            ).with_for_update().first()
            inside.set()
            assert release.wait(5), "test did not release the lock holder"
            s.commit()

    def do_first_due():
        with Session() as s:
            s.execute(
                text("SELECT set_config('app.current_user_id', :u, true)"),
                {"u": str(ids["uid"])},
            )
            s.execute(text("SET LOCAL lock_timeout = '200ms'"))
            user = s.get(User, ids["uid"])
            try:
                set_first_due(
                    ids["sched"],
                    FirstDueCreate(next_due=date.today() + timedelta(days=2)),
                    current_user=user,
                    db=s,
                )
                box["ok"] = True
            except HTTPException as exc:
                box["status"] = exc.status_code
                box["code"] = (exc.detail or {}).get("code") if isinstance(exc.detail, dict) else None

    holder = threading.Thread(target=hold)
    waiter = threading.Thread(target=do_first_due)
    holder.start()
    assert inside.wait(5)
    waiter.start()
    waiter.join(5)
    release.set()
    holder.join(5)
    assert box.get("status") == 409
    assert box.get("code") == "schedule_busy"


def test_refuse_void_only_passing_event_is_security_definer(migrated_engine):
    with migrated_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT p.prosecdef, p.proconfig, "
                "has_function_privilege('public', 'refuse_void_only_passing_event()', 'EXECUTE'), "
                "has_function_privilege('lims_app', 'refuse_void_only_passing_event()', 'EXECUTE') "
                "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'public' AND p.proname = 'refuse_void_only_passing_event'"
            )
        ).one()
        assert row[0] is True
        config = row[1] or []
        assert any("search_path=pg_catalog, public" in item for item in config)
        assert row[2] is False
        assert row[3] is True


def test_void_guard_set_role_exact_error_and_forged_actor(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    failed = _seed_schedule_event(migrated_engine, next_due=date.today(), passed=False)
    void_sql = (
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = 'db void' WHERE id = :id"
    )
    note_sql = "UPDATE instrument_maintenance_events SET note = 'tech' WHERE id = :id"
    with pytest.raises((ProgrammingError, InternalError)) as raised:
        _run_as_lims_app(migrated_engine, ids["tech"], void_sql, {"id": ids["event"]})
    assert pgcode(raised.value) == "42501"
    assert "maintenance_event_update_forbidden" in str(raised.value.orig)
    with pytest.raises((ProgrammingError, InternalError)) as note_raised:
        _run_as_lims_app(migrated_engine, ids["tech"], note_sql, {"id": ids["event"]})
    assert pgcode(note_raised.value) == "42501"
    assert "maintenance_event_update_forbidden" in str(note_raised.value.orig)
    with pytest.raises((ProgrammingError, InternalError)) as failed_raised:
        _run_as_lims_app(migrated_engine, failed["tech"], void_sql, {"id": failed["event"]})
    assert pgcode(failed_raised.value) == "42501"
    assert "maintenance_event_update_forbidden" in str(failed_raised.value.orig)
    _run_as_lims_app(migrated_engine, ids["uid"], void_sql, {"id": ids["event"]})
    template_id = uuid.uuid4()
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO experiment_templates "
                "(id, name, template_definition, active, created_by, modified_by) "
                "VALUES (:id, :n, '{}'::jsonb, true, :u, :u)"
            ),
            {"id": template_id, "n": f"e2rf-t-{template_id.hex[:6]}", "u": ids["uid"]},
        )
    with pytest.raises(ProgrammingError) as forged:
        _run_as_lims_app(
            migrated_engine,
            ids["uid"],
            "INSERT INTO instrument_schedule_audits "
            "(id, instrument_id, schedule_id, event_id, action, created_by) "
            "VALUES (:id, :i, :s, :e, 'event_restore', :u)",
            {
                "id": uuid.uuid4(),
                "i": ids["inst"],
                "s": ids["sched"],
                "e": ids["event"],
                "u": ids["other"],
            },
        )
    assert pgcode(forged.value) == "42501"
    with pytest.raises(ProgrammingError) as ledger_forged:
        _run_as_lims_app(
            migrated_engine,
            ids["uid"],
            "INSERT INTO instrument_template_inactivations "
            "(experiment_template_id, reason, created_by) "
            "VALUES (:t, 'forged', :u)",
            {"t": template_id, "u": ids["other"]},
        )
    assert pgcode(ledger_forged.value) == "42501"


def test_voided_event_cannot_be_restored(client, admin_h, db_session, test_admin_user):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    kinds = client.get("/lists/maintenance_types/entries", headers=admin_h).json()
    if isinstance(kinds, dict):
        kinds = kinds.get("entries") or kinds.get("items") or []
    kind_id = next(row["id"] for row in kinds if row["name"] == "PM")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind_id, "interval_days": 10},
    ).json()
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat()},
    )
    first = client.post(
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
    second = client.post(
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
    assert first.status_code == 201 and second.status_code == 201
    event_id = first.json()["id"]
    voided = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": False, "reason": "void one"},
    )
    assert voided.status_code == 200, voided.text
    restored = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": True, "reason": "put back"},
    )
    assert restored.status_code == 422, restored.text
    assert restored.json()["detail"]["code"] == "voided_event_stays_voided"
    again = client.patch(
        f"/v1/instrument-maintenance-events/{event_id}",
        headers=admin_h,
        json={"active": False, "reason": "void again"},
    )
    assert again.status_code == 422, again.text
    assert again.json()["detail"]["code"] == "voided_event_stays_voided"
    missing = client.post(
        f"/v1/instrument-maintenance-events/{event_id}/restore",
        headers=admin_h,
        json={"reason": "put back"},
    )
    assert missing.status_code in (404, 405), missing.text
    db_session.expire_all()
    restores = (
        db_session.query(InstrumentScheduleAudit)
        .filter(
            InstrumentScheduleAudit.event_id == event_id,
            InstrumentScheduleAudit.action == "event_restore",
        )
        .all()
    )
    assert restores == []
    listed = client.get(
        "/v1/instrument-maintenance-events",
        headers=admin_h,
        params={"include_voided": True, "instrument_id": inst["id"]},
    )
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json() if item["id"] == event_id)
    assert row["active"] is False


def test_reason_fields_max_length_1000(client, admin_h):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    kinds = client.get("/lists/maintenance_types/entries", headers=admin_h).json()
    if isinstance(kinds, dict):
        kinds = kinds.get("entries") or kinds.get("items") or []
    kind_id = next(row["id"] for row in kinds if row["name"] == "PM")
    sched = client.post(
        "/v1/instrument-maintenance-schedules",
        headers=admin_h,
        json={"instrument_id": inst["id"], "kind_id": kind_id, "interval_days": 10},
    ).json()
    too_long = "x" * 1001
    first = client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": too_long},
    )
    assert first.status_code == 422, first.text


def test_create_entry_validates_instrument_slots(client, admin_h):
    experiment = client.post("/v1/experiments", headers=admin_h, json={"name": _name("E")})
    assert experiment.status_code == 201, experiment.text
    refused = client.post(
        f"/v1/experiments/{experiment.json()['id']}/entries",
        headers=admin_h,
        json={
            "experiment_id": experiment.json()["id"],
            "entry_type": "instrument",
            "name": "Instruments",
            "predefined_entry_key": "instruments",
            "config": {
                "slots": [
                    {
                        "key": "run_import",
                        "label": "Import",
                        "run_import": True,
                    }
                ]
            },
        },
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"]["code"] == "instrument_entry_invalid"
    ok = client.post(
        f"/v1/experiments/{experiment.json()['id']}/entries",
        headers=admin_h,
        json={
            "experiment_id": experiment.json()["id"],
            "entry_type": "instrument",
            "name": "Instruments",
            "predefined_entry_key": "instruments",
            "config": {
                "slots": [
                    {
                        "key": "run_import",
                        "label": "Import",
                        "instrument_type_id": PLATE_READER_TYPE_ID,
                        "run_import": True,
                    }
                ]
            },
        },
    )
    assert ok.status_code == 201, ok.text


def test_0116_revision_id_and_single_head():
    text_src = MIGRATION_0116.read_text()
    assert 'revision = "0116_e2_review_fixes"' in text_src
    assert len("0116_e2_review_fixes") <= 32
    assert 'down_revision = "0115_instrument_type_slots"' in text_src
    assert "GRANT DELETE" not in text_src
    assert "REVOKE UPDATE ON instrument_template_inactivations FROM lims_app" in text_src
    assert "REVOKE DELETE ON instrument_template_inactivations FROM lims_app" in text_src
    assert "SECURITY DEFINER" in text_src
    assert "SET search_path = pg_catalog, public" in text_src
    heads = [p.name for p in (BACKEND / "db/migrations/versions").glob("0116*.py")]
    assert heads == ["0116_e2_review_fixes.py"]
