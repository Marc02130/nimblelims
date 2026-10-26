"""Follow-ups on the run row lock (#231). No plate math.

1. Publish and fail (and every other status change) serialize on the lock.
2. A lock wait that times out is a 409 ``run_busy``, not a 500.
3. The lock is FOR NO KEY UPDATE; import_file parses before it locks.
4. Fail vs import, import_file, and one contention run as ``lims_app``.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.database import _engine_kwargs
from app.repositories.flexible_experiment_repository import LimsRunRepository
from app.schemas.flexible_experiment import LimsRunDataRow, LimsRunUpdate
from app.services import lims_run_service as service_module
from app.services.lims_run_service import LimsRunService
from models.analysis import Analysis, AnalysisAnalyte, Analyte
from models.client import Client
from models.flexible_experiment import (
    DataParser,
    LimsRun,
    LimsRunData,
    LimsRunStatus,
    ParserAnalysis,
)
from models.instrument import INSTRUMENT_TYPES_LIST_ID, CroSource, Instrument
from models.list import ListEntry
from models.user import Role, User
from tests.test_elisa_run_gaps import GEN5, PARSER
from tests.test_flexible_experiment import PLATE_READER_TYPE_ID
from tests.test_run_229_followups import (
    LOCK_WAIT_S,
    _in_thread,
    _pause_after,
    _waits_on_run_lock,
)

ROW = [LimsRunDataRow(row_data={"corr": "1.0"})]


# ---------- committed rows on the superuser test database ----------


@pytest.fixture
def committed(db_engine):
    """Factory for a committed run in a given status, cleaned up afterwards."""
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, pool_size=4, max_overflow=2, **_engine_kwargs(url))
    Session = sessionmaker(bind=engine, autoflush=False)
    made: list[dict] = []

    def make(run_status: LimsRunStatus) -> dict:
        tag = uuid.uuid4().hex[:8]
        with Session() as s:
            org = Client(name=f"R231 {tag}")
            role = Role(name=f"r231 {tag}", description="r231")
            s.add_all([org, role])
            s.flush()
            user = User(name=f"R231 {tag}", username=f"r231{tag}", email=f"r231{tag}@x", password_hash="x",
                        role_id=role.id, client_id=org.id, must_change_password=False)
            s.add(user)
            s.flush()
            analysis = Analysis(name=f"R231 {tag}", created_by=user.id, modified_by=user.id)
            analyte = Analyte(name=f"R231_{tag}", created_by=user.id, modified_by=user.id)
            s.add_all([analysis, analyte])
            s.flush()
            s.add(AnalysisAnalyte(analysis_id=analysis.id, analyte_id=analyte.id))
            cro = CroSource(name=f"R231 CRO {tag}")
            s.add(cro)
            s.flush()
            parser = DataParser(
                name=f"R231 parser {tag}",
                parser_config={"columns": []},
                cro_source_id=cro.id,
                version_group_id=uuid.uuid4(),
                version=1,
                active=True,
            )
            s.add(parser)
            s.flush()
            s.add(ParserAnalysis(parser_id=parser.id, analysis_id=analysis.id, is_default=True))
            run = LimsRun(
                name=f"R231 run {tag}",
                analysis_id=analysis.id,
                status=run_status,
                instrument_type_id=uuid.UUID(PLATE_READER_TYPE_ID),
                created_by=user.id,
                modified_by=user.id,
            )
            s.add(run)
            s.commit()
            ids = dict(user=user.id, run=run.id, analysis=analysis.id, analyte=analyte.id,
                       role=role.id, org=org.id, cro=cro.id, parser=parser.id)
        made.append(ids)
        return ids

    yield Session, make
    with engine.begin() as c:
        for ids in made:
            c.execute(text("DELETE FROM lims_run_data WHERE lims_run_id = :i"), {"i": ids["run"]})
            c.execute(text("DELETE FROM lims_run_imports WHERE lims_run_id = :i"), {"i": ids["run"]})
            c.execute(text("DELETE FROM lims_runs WHERE id = :i"), {"i": ids["run"]})
            c.execute(text("DELETE FROM parser_analyses WHERE analysis_id = :i"), {"i": ids["analysis"]})
            c.execute(text("DELETE FROM data_parsers WHERE id = :i"), {"i": ids["parser"]})
            c.execute(text("DELETE FROM cro_sources WHERE id = :i"), {"i": ids["cro"]})
            c.execute(text("DELETE FROM analysis_analytes WHERE analysis_id = :i"), {"i": ids["analysis"]})
            c.execute(text("DELETE FROM analyses WHERE id = :i"), {"i": ids["analysis"]})
            c.execute(text("DELETE FROM analytes WHERE id = :i"), {"i": ids["analyte"]})
            c.execute(text("DELETE FROM users WHERE id = :i"), {"i": ids["user"]})
            c.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
            c.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
    engine.dispose()


@pytest.fixture
def lab_zone(committed):
    """Publish reads the lab day. Set the zone on committed rows and put it back after."""
    from models.lab_setting import LAB_SETTINGS_ID, LabSetting

    Session, _make = committed
    with Session() as s:
        row = s.get(LabSetting, LAB_SETTINGS_ID)
        previous = None if row is None else row.timezone
        if row is None:
            s.add(LabSetting(id=LAB_SETTINGS_ID, timezone="UTC"))
        elif not (row.timezone or "").strip():
            row.timezone = "UTC"
        s.commit()
    from app.core import lab_time

    published = (lab_time._published_zone, lab_time._published_error)
    with Session() as s:
        lab_time.publish_lab_zone(s)
    yield
    lab_time._published_zone, lab_time._published_error = published
    with Session() as s:
        row = s.get(LabSetting, LAB_SETTINGS_ID)
        if previous is None and row is not None:
            s.delete(row)
        elif row is not None:
            row.timezone = previous
        s.commit()


def _service(s, ids) -> LimsRunService:
    return LimsRunService(s, current_user=s.get(User, ids["user"]))


def _import_data(svc, ids):
    """Sourced JSON import. Non-admin roles need a CRO or instrument; the role stays Lab Technician."""
    return svc.import_data(ids["run"], ROW, cro_source_id=ids["cro"])


def _publisher(s, ids) -> LimsRunService:
    """WO-7 Test minting is covered by the publish tests; here only the lock is under test."""
    svc = _service(s, ids)
    svc._require_wo7_tests = lambda run: None
    return svc


def _contend(Session, ids, holder, pause_on, waiter):
    """Run ``holder`` paused inside its transaction, then ``waiter``; both outcomes."""
    inside, release = threading.Event(), threading.Event()

    def hold():
        with Session() as s:
            svc = holder[0](s, ids)
            _pause_after(getattr(svc, pause_on[0]), pause_on[1], inside, release)
            return holder[1](svc)

    def wait():
        with Session() as s:
            return waiter[1](waiter[0](s, ids))

    first, first_box = _in_thread(hold)
    assert inside.wait(LOCK_WAIT_S), first_box
    second, second_box = _in_thread(wait)
    try:
        assert _waits_on_run_lock(Session, ids["run"]), "second caller did not wait on the run row lock"
        assert second.is_alive()
    finally:
        release.set()
    first.join(LOCK_WAIT_S * 2)
    second.join(LOCK_WAIT_S * 2)
    assert "unexpected" not in first_box and "unexpected" not in second_box, (first_box, second_box)
    return first_box, second_box


def _status(Session, ids):
    with Session() as s:
        run = s.get(LimsRun, ids["run"])
        rows = s.query(LimsRunData).filter(LimsRunData.lims_run_id == ids["run"]).count()
        return run.status, run.published_at, rows


# ---------- 1: publish vs fail ----------


def test_fail_waits_for_a_publish_in_flight_then_refuses(committed, lab_zone):
    Session, make = committed
    ids = make(LimsRunStatus.complete)
    published, failed = _contend(
        Session, ids,
        holder=(_publisher, lambda svc: svc.publish_run(ids["run"]).status),
        pause_on=("run_repo", "update_status"),
        waiter=(_service, lambda svc: svc.fail_run(ids["run"], "QC-H out of range").status),
    )
    assert published.get("value") == LimsRunStatus.published, published
    assert failed["error"].status_code == 400
    assert "from 'published' to 'failed'" in failed["error"].detail
    status, published_at, _rows = _status(Session, ids)
    assert status == LimsRunStatus.published
    assert published_at is not None


def test_publish_waits_for_a_fail_in_flight_then_refuses(committed, lab_zone):
    Session, make = committed
    ids = make(LimsRunStatus.complete)
    failed, published = _contend(
        Session, ids,
        holder=(_service, lambda svc: svc.fail_run(ids["run"], "QC-H out of range").status),
        pause_on=("run_repo", "update_status"),
        waiter=(_publisher, lambda svc: svc.publish_run(ids["run"]).status),
    )
    assert failed.get("value") == LimsRunStatus.failed, failed
    assert published["error"].status_code == 400
    assert "from 'failed' to 'published'" in published["error"].detail
    status, published_at, _rows = _status(Session, ids)
    assert status == LimsRunStatus.failed
    assert published_at is None


def test_review_waits_for_a_fail_in_flight_then_refuses(committed):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    failed, reviewed = _contend(
        Session, ids,
        holder=(_service, lambda svc: svc.fail_run(ids["run"], "Edge effect").status),
        pause_on=("run_repo", "update_status"),
        waiter=(_service, lambda svc: svc.move_to_review(ids["run"]).status),
    )
    assert failed.get("value") == LimsRunStatus.failed, failed
    assert reviewed["error"].status_code == 400
    assert "from 'failed' to 'complete'" in reviewed["error"].detail
    assert _status(Session, ids)[0] == LimsRunStatus.failed


def test_every_status_change_takes_the_run_lock():
    """Each path that changes a run's status (or what import relies on) locks first."""
    import inspect

    for name in (
        "update_run", "order_run", "start_run", "set_cohort", "mark_results_received",
        "move_to_review", "publish_run", "cancel_run", "fail_run", "import_data", "import_file",
    ):
        source = inspect.getsource(getattr(LimsRunService, name))
        assert "self._get_run_for_update(run_id)" in source, name


def test_every_status_change_waits_on_a_held_run_lock(committed):
    """Each status-changing path waits on the row lock. Proved by waiting, not by reading source."""
    Session, make = committed

    def actions_for(ids):
        def do_import_file(svc):
            svc.data_parser_svc.resolve_for_import = lambda **_kw: SimpleNamespace(
                id=ids["parser"],
                parser_config=PARSER,
                instrument_id=None,
                cro_source_id=ids["cro"],
            )
            return svc.import_file(
                ids["run"],
                GEN5.read_bytes(),
                filename=GEN5.name,
                cro_source_id=ids["cro"],
            )

        return {
            "update_run": lambda svc: svc.update_run(ids["run"], LimsRunUpdate(description="x")),
            "order_run": lambda svc: svc.order_run(ids["run"]),
            "start_run": lambda svc: svc.start_run(ids["run"]),
            "set_cohort": lambda svc: svc.set_cohort(ids["run"], [uuid.uuid4()]),
            "mark_results_received": lambda svc: svc.mark_results_received(ids["run"]),
            "move_to_review": lambda svc: svc.move_to_review(ids["run"]),
            "publish_run": lambda svc: svc.publish_run(ids["run"]),
            "cancel_run": lambda svc: svc.cancel_run(ids["run"]),
            "fail_run": lambda svc: svc.fail_run(ids["run"], "held lock"),
            "import_data": lambda svc: _import_data(svc, ids),
            "import_file": do_import_file,
        }

    # A fresh run per action so a waiter that commits after we release cannot
    # change the next path's starting status.
    names = (
        "update_run", "order_run", "start_run", "set_cohort", "mark_results_received",
        "move_to_review", "publish_run", "cancel_run", "fail_run", "import_data", "import_file",
    )
    for name in names:
        ids = make(LimsRunStatus.running)
        action = actions_for(ids)[name]
        holder = _hold_row_lock(Session, ids)
        waiter = Session()
        thread = None
        box: dict = {}
        try:
            thread, box = _in_thread(lambda a=action, w=waiter, i=ids: a(_service(w, i)))
            assert _waits_on_run_lock(Session, ids["run"]), name
            assert thread.is_alive(), name
        finally:
            holder.rollback()
            holder.close()
            if thread is not None:
                thread.join(LOCK_WAIT_S * 2)
            waiter.rollback()
            waiter.close()
        assert "unexpected" not in box, (name, box)


# ---------- 2: lock timeout is 409 run_busy ----------


def _hold_row_lock(Session, ids):
    holder = Session()
    holder.execute(
        text("SELECT id FROM lims_runs WHERE id = :i FOR UPDATE"), {"i": ids["run"]}
    )
    return holder


@pytest.mark.parametrize(
    "timeouts",
    ["SET lock_timeout = '200ms'", "SET lock_timeout = 0; SET statement_timeout = '200ms'"],
    ids=["lock_timeout", "statement_timeout"],
)
def test_a_lock_wait_that_times_out_is_409_run_busy(committed, timeouts):
    from app.main import app
    from app.routers.lims_runs import _run_service

    Session, make = committed
    ids = make(LimsRunStatus.running)
    holder = _hold_row_lock(Session, ids)
    waiter = Session()
    try:
        for statement in timeouts.split("; "):
            waiter.execute(text(statement))
        app.dependency_overrides[_run_service] = lambda: _service(waiter, ids)
        with TestClient(app) as http:
            started = time.monotonic()
            response = http.patch(f"/v1/lims-runs/{ids['run']}/cancel")
            elapsed = time.monotonic() - started
    finally:
        app.dependency_overrides.pop(_run_service, None)
        waiter.close()
        holder.rollback()
        holder.close()
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "run_busy"
    assert elapsed < LOCK_WAIT_S
    assert _status(Session, ids)[0] == LimsRunStatus.running


def _lock_timeout_error(Session, lock_sql, wait_sql, params) -> OperationalError:
    holder, waiter = Session(), Session()
    try:
        holder.execute(text(lock_sql), params)
        waiter.execute(text("SET lock_timeout = '200ms'"))
        with pytest.raises(OperationalError) as raised:
            waiter.execute(text(wait_sql), params)
        return raised.value
    finally:
        waiter.rollback()
        waiter.close()
        holder.rollback()
        holder.close()


def test_global_handler_maps_lock_timeouts_to_409(committed):
    from app.main import _lock_timeout_is_409

    Session, make = committed
    ids = make(LimsRunStatus.running)
    on_run = _lock_timeout_error(
        Session,
        "SELECT id FROM lims_runs WHERE id = :i FOR UPDATE",
        "UPDATE lims_runs SET description = description WHERE id = :i",
        {"i": ids["run"]},
    )
    on_client = _lock_timeout_error(
        Session,
        "SELECT id FROM clients WHERE id = :i FOR UPDATE",
        "UPDATE clients SET name = name WHERE id = :i",
        {"i": ids["org"]},
    )
    for exc, code in ((on_run, "run_busy"), (on_client, "row_busy")):
        response = asyncio.run(_lock_timeout_is_409(None, exc))
        assert response.status_code == 409
        assert json.loads(response.body)["detail"]["code"] == code

    with Session() as s:
        s.execute(text("SET statement_timeout = '50ms'"))
        with pytest.raises(OperationalError) as slow:
            s.execute(text("SELECT pg_sleep(1)"))
    with pytest.raises(OperationalError):
        asyncio.run(_lock_timeout_is_409(None, slow.value))


# ---------- 3: FOR NO KEY UPDATE; import_file parses before locking ----------


def test_the_run_lock_is_no_key_update_and_does_not_block_references(committed):
    """A row that references the run can be inserted while the run is locked."""
    Session, make = committed
    ids = make(LimsRunStatus.running)
    locker = Session()
    other = Session()
    try:
        _service(locker, ids)._get_run_for_update(ids["run"])
        other.execute(text("SET lock_timeout = '500ms'"))
        # The KEY SHARE lock a foreign key check takes is granted (FOR UPDATE would block it).
        other.execute(
            text("SELECT id FROM lims_runs WHERE id = :i FOR KEY SHARE"), {"i": ids["run"]}
        )
        # A second status change still waits.
        with pytest.raises(OperationalError) as raised:
            other.execute(text("SELECT id FROM lims_runs WHERE id = :i FOR NO KEY UPDATE"), {"i": ids["run"]})
        assert raised.value.orig.pgcode == "55P03"
    finally:
        other.rollback()
        other.close()
        locker.rollback()
        locker.close()


def _fake_parser():
    return SimpleNamespace(id=uuid.uuid4(), parser_config=PARSER, instrument_id=None, cro_source_id=None)


def _import_file(svc, ids):
    svc.data_parser_svc.resolve_for_import = lambda **_kw: _fake_parser()
    return svc.import_file(ids["run"], GEN5.read_bytes(), filename=GEN5.name)


def test_import_file_does_not_hold_the_lock_while_parsing(committed, monkeypatch):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    parsing, release = threading.Event(), threading.Event()
    real = service_module.InstrumentDataService

    class PausedParse(real):
        def parse(self, *args, **kwargs):
            out = super().parse(*args, **kwargs)
            parsing.set()
            assert release.wait(LOCK_WAIT_S)
            return out

    monkeypatch.setattr(service_module, "InstrumentDataService", PausedParse)

    def do_import():
        with Session() as s:
            return _import_file(_service(s, ids), ids)

    importer, imported = _in_thread(do_import)
    try:
        assert parsing.wait(LOCK_WAIT_S), imported
        with Session() as s:
            s.execute(text("SET lock_timeout = '500ms'"))
            assert _service(s, ids).cancel_run(ids["run"]).status == LimsRunStatus.canceled
    finally:
        release.set()
    importer.join(LOCK_WAIT_S * 2)
    error = imported.get("error")
    assert error is not None, imported
    assert error.status_code == 400
    assert "current status is 'canceled'" in error.detail
    assert _status(Session, ids)[0] == LimsRunStatus.canceled
    assert _status(Session, ids)[2] == 0


def test_import_file_waits_for_a_cancel_in_flight_after_parsing(committed, monkeypatch):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    parsed = threading.Event()
    real = service_module.InstrumentDataService

    class MarkedParse(real):
        def parse(self, *args, **kwargs):
            out = super().parse(*args, **kwargs)
            parsed.set()
            return out

    monkeypatch.setattr(service_module, "InstrumentDataService", MarkedParse)
    canceled, imported = _contend(
        Session, ids,
        holder=(_service, lambda svc: svc.cancel_run(ids["run"]).status),
        pause_on=("run_repo", "update_status"),
        waiter=(_service, lambda svc: _import_file(svc, ids)),
    )
    assert parsed.is_set()
    assert canceled.get("value") == LimsRunStatus.canceled, canceled
    assert imported["error"].status_code == 400
    assert "current status is 'canceled'" in imported["error"].detail
    assert _status(Session, ids)[2] == 0


# ---------- 4: fail vs import ----------


def test_fail_waits_for_an_import_in_flight_and_keeps_the_rows(committed):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    imported, failed = _contend(
        Session, ids,
        holder=(_service, lambda svc: _import_data(svc, ids).imported),
        pause_on=("data_repo", "bulk_create"),
        waiter=(_service, lambda svc: svc.fail_run(ids["run"], "Wrong plate map")),
    )
    assert imported.get("value") == 1, imported
    run = failed.get("value")
    assert run is not None, failed
    status, _published, rows = _status(Session, ids)
    assert status == LimsRunStatus.failed
    assert rows == 1


def test_import_waits_for_a_fail_in_flight_then_refuses(committed):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    failed, imported = _contend(
        Session, ids,
        holder=(_service, lambda svc: svc.fail_run(ids["run"], "Wrong plate map").status),
        pause_on=("run_repo", "update_status"),
        waiter=(_service, lambda svc: _import_data(svc, ids).imported),
    )
    assert failed.get("value") == LimsRunStatus.failed, failed
    assert imported["error"].status_code == 400
    assert "current status is 'failed'" in imported["error"].detail
    assert _status(Session, ids)[2] == 0


# ---------- 4: one contention as lims_app (RLS and privileges apply) ----------

_APP_PRIVILEGES = (
    ("lims_runs", "SELECT"),
    ("lims_runs", "UPDATE"),
    ("lims_run_data", "SELECT"),
    ("lims_run_data", "INSERT"),
    ("lims_run_imports", "SELECT"),
    ("lims_run_imports", "INSERT"),
    ("cro_sources", "SELECT"),
    ("data_parsers", "SELECT"),
    ("parser_analyses", "SELECT"),
    ("users", "SELECT"),
    ("roles", "SELECT"),
)


@pytest.fixture
def lims_app_world(migrated_engine):
    """A Lab Technician's running run on the migrated database, plus lims_app sessions.

    The test database grants lims_app nothing on these tables (production does,
    through zz-roles). Only the privileges missing here are granted, and exactly
    those are revoked afterwards. No DELETE is granted.
    """
    url = migrated_engine.url.render_as_string(hide_password=False)
    admin = create_engine(url, poolclass=NullPool)
    tag = uuid.uuid4().hex[:8]
    with admin.begin() as c:
        lab = c.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar_one()
        granted = [
            (table, privilege)
            for table, privilege in _APP_PRIVILEGES
            if not c.execute(
                text("SELECT has_table_privilege('lims_app', :t, :p)"), {"t": table, "p": privilege}
            ).scalar()
        ]
        for table, privilege in granted:
            c.execute(text(f"GRANT {privilege} ON TABLE {table} TO lims_app"))
        ids = {
            k: uuid.uuid4()
            for k in ("org", "user", "other_org", "other_user", "analysis", "run", "cro", "parser")
        }
        for org, user, label in (("org", "user", "a"), ("other_org", "other_user", "b")):
            c.execute(
                text("INSERT INTO clients (id, name, active, billing_info) VALUES (:id, :n, true, '{}')"),
                {"id": ids[org], "n": f"R231-{label}-{tag}"},
            )
            c.execute(
                text(
                    "INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) "
                    "VALUES (:id, :n, :u, :e, 'x', :r, :c, true)"
                ),
                {"id": ids[user], "n": f"R231 {label} {tag}", "u": f"r231{label}{tag}",
                 "e": f"r231{label}{tag}@x.org", "r": lab, "c": ids[org]},
            )
        c.execute(
            text("INSERT INTO analyses (id, name, active, created_by, modified_by) VALUES (:id, :n, true, :u, :u)"),
            {"id": ids["analysis"], "n": f"R231 {tag}", "u": ids["user"]},
        )
        c.execute(
            text(
                "INSERT INTO lims_runs (id, name, status, analysis_id, created_by, modified_by) "
                "VALUES (:id, :n, 'running', :a, :u, :u)"
            ),
            {"id": ids["run"], "n": f"R231 run {tag}", "a": ids["analysis"], "u": ids["user"]},
        )
        c.execute(
            text("INSERT INTO cro_sources (id, name, active) VALUES (:id, :n, true)"),
            {"id": ids["cro"], "n": f"R231-cro-{tag}"},
        )
        c.execute(
            text(
                "INSERT INTO data_parsers (id, name, parser_config, cro_source_id, "
                "version_group_id, version, active) "
                "VALUES (:id, :n, CAST(:cfg AS jsonb), :c, :g, 1, true)"
            ),
            {
                "id": ids["parser"],
                "n": f"R231 parser {tag}",
                "cfg": '{"columns": []}',
                "c": ids["cro"],
                "g": uuid.uuid4(),
            },
        )
        c.execute(
            text(
                "INSERT INTO parser_analyses (parser_id, analysis_id, is_default) "
                "VALUES (:p, :a, true)"
            ),
            {"p": ids["parser"], "a": ids["analysis"]},
        )

    app_engine = create_engine(url, poolclass=NullPool, connect_args=_engine_kwargs(url)["connect_args"])
    AppSession = sessionmaker(bind=app_engine, autoflush=False)

    def as_lims_app(user_key: str = "user"):
        s = AppSession()
        s.execute(text("SET ROLE lims_app"))
        s.execute(text("SELECT set_config('app.current_user_id', :u, false)"), {"u": str(ids[user_key])})
        flags = s.execute(
            text("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
        assert tuple(flags) == ("lims_app", False, False)
        return s

    yield as_lims_app, sessionmaker(bind=admin), ids
    app_engine.dispose()
    with admin.begin() as c:
        c.execute(text("DELETE FROM lims_run_data WHERE lims_run_id = :i"), {"i": ids["run"]})
        c.execute(text("DELETE FROM lims_run_imports WHERE lims_run_id = :i"), {"i": ids["run"]})
        c.execute(text("DELETE FROM lims_runs WHERE id = :i"), {"i": ids["run"]})
        c.execute(text("DELETE FROM parser_analyses WHERE parser_id = :i"), {"i": ids["parser"]})
        c.execute(text("DELETE FROM data_parsers WHERE id = :i"), {"i": ids["parser"]})
        c.execute(text("DELETE FROM cro_sources WHERE id = :i"), {"i": ids["cro"]})
        c.execute(text("DELETE FROM analyses WHERE id = :i"), {"i": ids["analysis"]})
        c.execute(text("DELETE FROM users WHERE id IN (:a, :b)"), {"a": ids["user"], "b": ids["other_user"]})
        c.execute(text("DELETE FROM clients WHERE id IN (:a, :b)"), {"a": ids["org"], "b": ids["other_org"]})
        for table, privilege in granted:
            c.execute(text(f"REVOKE {privilege} ON TABLE {table} FROM lims_app"))
    admin.dispose()


def test_cancel_and_import_serialize_as_lims_app_under_rls(lims_app_world):
    as_lims_app, AdminSession, ids = lims_app_world

    def service(s, user_key="user"):
        user = SimpleNamespace(id=ids[user_key])
        return LimsRunService(s, current_user=user)

    other = as_lims_app("other_user")
    try:
        with pytest.raises(HTTPException) as hidden:
            service(other, "other_user")._get_run_for_update(ids["run"])
        assert hidden.value.status_code == 404
    finally:
        other.rollback()
        other.close()

    inside, release = threading.Event(), threading.Event()

    def do_import():
        s = as_lims_app()
        try:
            svc = service(s)
            _pause_after(svc.data_repo, "bulk_create", inside, release)
            return _import_data(svc, ids).imported
        finally:
            s.close()

    def do_cancel():
        s = as_lims_app()
        try:
            return service(s).cancel_run(ids["run"]).status
        finally:
            s.close()

    importer, imported = _in_thread(do_import)
    assert inside.wait(LOCK_WAIT_S), imported
    canceler, canceled = _in_thread(do_cancel)
    try:
        assert _waits_on_run_lock(AdminSession, ids["run"]), "cancel did not wait on the run row lock"
        assert canceler.is_alive()
    finally:
        release.set()
    importer.join(LOCK_WAIT_S * 2)
    canceler.join(LOCK_WAIT_S * 2)

    assert imported.get("value") == 1, imported
    assert canceled["error"].status_code == 422, canceled
    assert canceled["error"].detail["code"] == "run_has_imported_data"
    check = as_lims_app()
    try:
        status = check.execute(text("SELECT status FROM lims_runs WHERE id = :i"), {"i": ids["run"]}).scalar()
        rows = check.execute(
            text("SELECT count(*) FROM lims_run_data WHERE lims_run_id = :i"), {"i": ids["run"]}
        ).scalar()
    finally:
        check.close()
    assert status == "running"
    assert rows == 1


def _add_instrument(Session, tag: str):
    with Session() as s:
        itype = (
            s.query(ListEntry)
            .filter(ListEntry.list_id == uuid.UUID(INSTRUMENT_TYPES_LIST_ID))
            .first()
        )
        assert itype is not None
        inst = Instrument(
            name=f"R231 inst {tag}",
            instrument_type_id=itype.id,
            status="in_service",
            maintenance_tracked=False,
            active=True,
        )
        s.add(inst)
        s.commit()
        return inst.id


def _bind_run_type(Session, run_id, instrument_id):
    """Copy the instrument's type onto the run so import type-check is not leftover-null."""
    with Session() as s:
        inst = s.get(Instrument, instrument_id)
        run = s.get(LimsRun, run_id)
        run.instrument_type_id = inst.instrument_type_id
        s.commit()


def _retire_instrument(Session, instrument_id):
    with Session() as s:
        inst = s.get(Instrument, instrument_id)
        inst.status = "retired"
        inst.active = False
        s.commit()


def _drop_instrument(Session, instrument_id):
    with Session() as s:
        s.execute(text("DELETE FROM instruments WHERE id = :i"), {"i": instrument_id})
        s.commit()


def test_import_file_rechecks_explicit_instrument_after_the_run_lock(committed, monkeypatch):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    inst_id = _add_instrument(Session, uuid.uuid4().hex[:8])
    _bind_run_type(Session, ids["run"], inst_id)
    parsing, release = threading.Event(), threading.Event()
    real = service_module.InstrumentDataService

    class PausedParse(real):
        def parse(self, *args, **kwargs):
            out = super().parse(*args, **kwargs)
            parsing.set()
            assert release.wait(LOCK_WAIT_S)
            return out

    monkeypatch.setattr(service_module, "InstrumentDataService", PausedParse)

    def do_import():
        with Session() as s:
            svc = _service(s, ids)
            svc.data_parser_svc.resolve_for_import = lambda **_kw: SimpleNamespace(
                id=ids["parser"], parser_config=PARSER, instrument_id=inst_id, cro_source_id=None
            )
            return svc.import_file(
                ids["run"], GEN5.read_bytes(), filename=GEN5.name, instrument_id=inst_id
            )

    importer, imported = _in_thread(do_import)
    try:
        assert parsing.wait(LOCK_WAIT_S), imported
        _retire_instrument(Session, inst_id)
    finally:
        release.set()
    importer.join(LOCK_WAIT_S * 2)
    _drop_instrument(Session, inst_id)
    error = imported.get("error")
    assert error is not None, imported
    assert error.status_code == 422
    assert error.detail["code"] == "instrument_retired"
    assert _status(Session, ids)[2] == 0


def test_import_file_rechecks_resolved_instrument_after_the_run_lock(committed, monkeypatch):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    inst_id = _add_instrument(Session, uuid.uuid4().hex[:8])
    _bind_run_type(Session, ids["run"], inst_id)
    parsing, release = threading.Event(), threading.Event()
    real = service_module.InstrumentDataService

    class PausedParse(real):
        def parse(self, *args, **kwargs):
            out = super().parse(*args, **kwargs)
            parsing.set()
            assert release.wait(LOCK_WAIT_S)
            return out

    monkeypatch.setattr(service_module, "InstrumentDataService", PausedParse)

    def do_import():
        with Session() as s:
            svc = _service(s, ids)
            svc.data_parser_svc.resolve_for_import = lambda **_kw: SimpleNamespace(
                id=ids["parser"], parser_config=PARSER, instrument_id=inst_id, cro_source_id=None
            )
            return svc.import_file(ids["run"], GEN5.read_bytes(), filename=GEN5.name)

    importer, imported = _in_thread(do_import)
    try:
        assert parsing.wait(LOCK_WAIT_S), imported
        _retire_instrument(Session, inst_id)
    finally:
        release.set()
    importer.join(LOCK_WAIT_S * 2)
    _drop_instrument(Session, inst_id)
    error = imported.get("error")
    assert error is not None, imported
    assert error.status_code == 422
    assert error.detail["code"] == "instrument_retired"
    assert _status(Session, ids)[2] == 0


def test_update_status_refuses_an_illegal_transition(committed):
    Session, make = committed
    ids = make(LimsRunStatus.published)
    with Session() as s:
        run = s.get(LimsRun, ids["run"])
        with pytest.raises(ValueError, match="from 'published' to 'failed'"):
            LimsRunRepository(s).update_status(run, LimsRunStatus.failed, ids["user"])
        s.rollback()
    status, published_at, _rows = _status(Session, ids)
    assert status == LimsRunStatus.published
    assert published_at is None


def test_update_status_waits_on_a_held_run_lock(committed):
    Session, make = committed
    ids = make(LimsRunStatus.running)
    holder = _hold_row_lock(Session, ids)
    waiter = Session()
    thread = None
    box: dict = {}
    try:
        def write():
            run = waiter.get(LimsRun, ids["run"])
            return LimsRunRepository(waiter).update_status(run, LimsRunStatus.failed, ids["user"])

        thread, box = _in_thread(write)
        assert _waits_on_run_lock(Session, ids["run"])
        assert thread.is_alive()
    finally:
        holder.rollback()
        holder.close()
        if thread is not None:
            thread.join(LOCK_WAIT_S * 2)
        waiter.rollback()
        waiter.close()
    assert "unexpected" not in box, box
    assert _status(Session, ids)[0] == LimsRunStatus.running


def test_fail_run_validates_before_it_sets_any_fields(committed):
    Session, make = committed
    ids = make(LimsRunStatus.published)
    with Session() as s:
        with pytest.raises(HTTPException) as raised:
            _service(s, ids).fail_run(ids["run"], "too late")
        assert raised.value.status_code == 400
        assert "from 'published' to 'failed'" in raised.value.detail
        s.flush()
        s.commit()
    with Session() as s:
        run = s.get(LimsRun, ids["run"])
        assert run.status == LimsRunStatus.published
        assert run.status_reason is None
        assert run.rejected_at is None
        assert run.failed_by is None
