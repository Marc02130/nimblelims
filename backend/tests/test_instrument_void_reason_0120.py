"""Void reason max 4000 (0120). Whitespace/NBSP/ZWSP/BOM stay in 0119 tests."""
import importlib.util
import os
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, InternalError, ProgrammingError

from app.core.required_reason import CHANGE_REASON_MAX, REASON_MAX, VOID_REASON_MAX
from tests.test_instrument_e2_review_fixes import _seed_schedule_event
from tests.test_instrument_e3_hardening import _grant_if_missing
from tests.test_instrument_hardening_e1 import _run_as_lims_app, _schedule
from tests.test_instrument_tracking import _instrument, _login

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION_0120 = BACKEND / "db/migrations/versions/0120_void_reason_4000.py"


@pytest.fixture
def admin_h(client, test_admin_user):
    return _login(client, "admin", "adminpassword")


def _constraint_def(conn):
    return conn.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_instrument_events_void_reason'"
        )
    ).scalar()


def _alembic_cfg(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _load_0120():
    spec = importlib.util.spec_from_file_location("m0120", MIGRATION_0120)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clip_void_reasons_to_1000(engine) -> None:
    """Test isolation only. 0120 itself never truncates."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE instrument_maintenance_events "
                "SET void_reason = left(void_reason, 1000) "
                "WHERE void_reason IS NOT NULL "
                "AND char_length(btrim(void_reason)) > 1000"
            )
        )


def test_shared_reason_max_is_4000():
    assert REASON_MAX == 4000
    assert VOID_REASON_MAX == REASON_MAX
    assert CHANGE_REASON_MAX == REASON_MAX


def test_0120_revision_id_and_single_head():
    text_src = MIGRATION_0120.read_text()
    assert 'revision = "0120_void_reason_4000"' in text_src
    assert len("0120_void_reason_4000") <= 32
    assert 'down_revision = "0119_instrument_reasons"' in text_src
    assert "GRANT DELETE" not in text_src
    assert "BETWEEN 1 AND 4000" in text_src
    assert "BETWEEN 1 AND 1000" in text_src
    assert "0120 downgrade refuses" in text_src
    assert "substring(" not in text_src.lower()
    assert "left(" not in text_src.lower()
    down = text_src[text_src.index("def downgrade()") :]
    assert "DELETE FROM instrument_maintenance_events" not in down
    assert "UPDATE instrument_maintenance_events" not in down
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "db/migrations"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert heads == ["0120_void_reason_4000"], heads


def test_void_reason_api_accepts_4000_and_rejects_4001(
    client, admin_h, test_admin_user
):
    inst = _instrument(client, admin_h, maintenance_tracked=True)
    sched = _schedule(client, admin_h, inst["id"], interval=10)
    client.post(
        f"/v1/instrument-maintenance-schedules/{sched['id']}/first-due",
        headers=admin_h,
        json={"next_due": date.today().isoformat(), "reason": "set first due"},
    )
    too_long = client.post(
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
    assert too_long.status_code == 201, too_long.text
    refused = client.patch(
        f"/v1/instrument-maintenance-events/{too_long.json()['id']}",
        headers=admin_h,
        json={"active": False, "reason": "x" * 4001},
    )
    assert refused.status_code == 422, refused.text
    ok_event = client.post(
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
    assert ok_event.status_code == 201, ok_event.text
    ok = client.patch(
        f"/v1/instrument-maintenance-events/{ok_event.json()['id']}",
        headers=admin_h,
        json={"active": False, "reason": "x" * 4000},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["void_reason"] == "x" * 4000


def test_void_reason_db_accepts_4000_and_rejects_4001(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
        defn = _constraint_def(conn)
    assert "4000" in defn
    with pytest.raises((IntegrityError, InternalError, ProgrammingError)):
        _run_as_lims_app(
            migrated_engine,
            ids["uid"],
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = :r WHERE id = :id",
            {"id": ids["event"], "r": "x" * 4001},
        )
    _run_as_lims_app(
        migrated_engine,
        ids["uid"],
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = :r WHERE id = :id",
        {"id": ids["event"], "r": "x" * 4000},
    )


def test_0120_downgrade_refuses_when_void_reason_longer_than_1000(migrated_engine):
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
    _run_as_lims_app(
        migrated_engine,
        ids["uid"],
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = :r WHERE id = :id",
        {"id": ids["event"], "r": "x" * 1001},
    )
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = _alembic_cfg(url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        m0120 = _load_0120()
        with migrated_engine.connect() as conn:
            with pytest.raises(RuntimeError, match="0120 downgrade refuses"):
                m0120.refuse_downgrade_if_long_void_reasons(conn)
            stored = conn.execute(
                text(
                    "SELECT char_length(void_reason) "
                    "FROM instrument_maintenance_events WHERE id = :id"
                ),
                {"id": ids["event"]},
            ).scalar()
            assert stored == 1001
        with pytest.raises(Exception, match="0120 downgrade refuses"):
            command.downgrade(cfg, "0119_instrument_reasons")
        with migrated_engine.connect() as conn:
            head = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            assert head == "0120_void_reason_4000"
            stored = conn.execute(
                text(
                    "SELECT char_length(void_reason) "
                    "FROM instrument_maintenance_events WHERE id = :id"
                ),
                {"id": ids["event"]},
            ).scalar()
            assert stored == 1001
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


def test_0120_downgrade_and_upgrade_when_reasons_fit_1000(migrated_engine):
    _clip_void_reasons_to_1000(migrated_engine)
    ids = _seed_schedule_event(migrated_engine, next_due=date.today())
    with migrated_engine.begin() as conn:
        _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
    _run_as_lims_app(
        migrated_engine,
        ids["uid"],
        "UPDATE instrument_maintenance_events "
        "SET active = false, void_reason = :r WHERE id = :id",
        {"id": ids["event"], "r": "x" * 1000},
    )
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = _alembic_cfg(url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    try:
        command.downgrade(cfg, "0119_instrument_reasons")
        with migrated_engine.connect() as conn:
            defn = _constraint_def(conn)
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        assert version == "0119_instrument_reasons"
        assert "1000" in defn
        other = _seed_schedule_event(migrated_engine, next_due=date.today())
        with migrated_engine.begin() as conn:
            _grant_if_missing(conn, "instrument_maintenance_events", "UPDATE")
        with pytest.raises((IntegrityError, InternalError, ProgrammingError)):
            _run_as_lims_app(
                migrated_engine,
                other["uid"],
                "UPDATE instrument_maintenance_events "
                "SET active = false, void_reason = :r WHERE id = :id",
                {"id": other["event"], "r": "x" * 1001},
            )
        command.upgrade(cfg, "head")
        with migrated_engine.connect() as conn:
            defn = _constraint_def(conn)
            version = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        assert version == "0120_void_reason_4000"
        assert "4000" in defn
        _run_as_lims_app(
            migrated_engine,
            other["uid"],
            "UPDATE instrument_maintenance_events "
            "SET active = false, void_reason = :r WHERE id = :id",
            {"id": other["event"], "r": "x" * 4000},
        )
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
