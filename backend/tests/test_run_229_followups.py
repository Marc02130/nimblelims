"""Follow-ups on the merged run-fail work (#229). No plate math.

1. Cancel and import serialize on the lims_runs row lock.
2. A name-only match on the run is refused when the key is an off-run
   client sample ID.
3. Fail records the actor in ``failed_by``.
4. Listing runs runs a bounded number of queries.
5. Configuring-agent uploads use the capped reader.
"""
from __future__ import annotations

import io
import threading
import time
import uuid
from typing import Callable

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.database import _engine_kwargs
from app.schemas.flexible_experiment import LimsRunDataRow
from app.services.import_sample_link import CLIENT_ID_OFF_RUN, link_rows
from app.services.lims_run_service import LimsRunService
from models.analysis import Analysis
from models.client import Client
from models.flexible_experiment import LimsRun, LimsRunData, LimsRunStatus
from models.user import Role, User
from tests.test_elisa_run_gaps import _analysis, _run, _sample, _template

LOCK_WAIT_S = 5.0


@pytest.fixture
def auth_headers(client: TestClient, test_admin_user):
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpassword"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------- 1: cancel and import serialize ----------


@pytest.fixture
def committed_run(db_engine):
    """A running run on committed rows, so two connections can contend for it."""
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, pool_size=4, max_overflow=0, **_engine_kwargs(url))
    Session = sessionmaker(bind=engine, autoflush=False)
    tag = uuid.uuid4().hex[:8]
    with Session() as s:
        org = Client(name=f"R229 {tag}")
        role = Role(name=f"r229 {tag}", description="r229")
        s.add_all([org, role])
        s.flush()
        user = User(name=f"R229 {tag}", username=f"r229{tag}", email=f"r229{tag}@x", password_hash="x",
                    role_id=role.id, client_id=org.id, must_change_password=False)
        s.add(user)
        s.flush()
        analysis = Analysis(name=f"R229 {tag}", created_by=user.id, modified_by=user.id)
        s.add(analysis)
        s.flush()
        run = LimsRun(name=f"R229 run {tag}", analysis_id=analysis.id, status=LimsRunStatus.running,
                      created_by=user.id, modified_by=user.id)
        s.add(run)
        s.commit()
        ids = dict(user=user.id, run=run.id, analysis=analysis.id, role=role.id, org=org.id)
    yield Session, ids
    with engine.begin() as c:
        c.execute(text("DELETE FROM lims_run_data WHERE lims_run_id = :i"), {"i": ids["run"]})
        c.execute(text("DELETE FROM lims_runs WHERE id = :i"), {"i": ids["run"]})
        c.execute(text("DELETE FROM analyses WHERE id = :i"), {"i": ids["analysis"]})
        c.execute(text("DELETE FROM users WHERE id = :i"), {"i": ids["user"]})
        c.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
        c.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
    engine.dispose()


def _service(s, ids) -> LimsRunService:
    return LimsRunService(s, current_user=s.get(User, ids["user"]))


def _pause_after(obj, name: str, inside: threading.Event, release: threading.Event) -> None:
    """Make ``obj.name`` do its work, then hold the transaction open until released."""
    original: Callable = getattr(obj, name)

    def paused(*args, **kwargs):
        out = original(*args, **kwargs)
        inside.set()
        assert release.wait(LOCK_WAIT_S), "test did not release the lock holder"
        return out

    setattr(obj, name, paused)


def _in_thread(fn) -> tuple[threading.Thread, dict]:
    box: dict = {}

    def target():
        try:
            box["value"] = fn()
        except HTTPException as exc:
            box["error"] = exc
        except Exception as exc:  # surfaced by the assertions below
            box["unexpected"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    return thread, box


def _waits_on_run_lock(Session, run_id) -> bool:
    """True once another backend is blocked on a lock while locking this run."""
    deadline = time.monotonic() + LOCK_WAIT_S
    with Session() as s:
        while time.monotonic() < deadline:
            waiting = s.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock' "
                    "AND query ILIKE '%lims_runs%FOR%UPDATE%' AND pid <> pg_backend_pid()"
                )
            ).scalar()
            s.rollback()
            if waiting:
                return True
            time.sleep(0.05)
    return False


def test_cancel_waits_for_an_import_in_flight_then_refuses(committed_run):
    Session, ids = committed_run
    inside, release = threading.Event(), threading.Event()

    def do_import():
        with Session() as s:
            svc = _service(s, ids)
            _pause_after(svc.data_repo, "bulk_create", inside, release)
            return svc.import_data(ids["run"], [LimsRunDataRow(row_data={"corr": "1.0"})]).imported

    def do_cancel():
        with Session() as s:
            return _service(s, ids).cancel_run(ids["run"]).status

    importer, imported = _in_thread(do_import)
    assert inside.wait(LOCK_WAIT_S), imported
    canceler, canceled = _in_thread(do_cancel)
    try:
        assert _waits_on_run_lock(Session, ids["run"]), "cancel did not wait on the run row lock"
        assert canceler.is_alive()
    finally:
        release.set()
    importer.join(LOCK_WAIT_S * 2)
    canceler.join(LOCK_WAIT_S * 2)

    assert imported.get("value") == 1, imported
    error = canceled.get("error")
    assert error is not None, canceled
    assert error.status_code == 422
    assert error.detail["code"] == "run_has_imported_data"
    with Session() as s:
        assert s.get(LimsRun, ids["run"]).status == LimsRunStatus.running
        assert s.query(LimsRunData).filter(LimsRunData.lims_run_id == ids["run"]).count() == 1


def test_import_waits_for_a_cancel_in_flight_then_refuses(committed_run):
    Session, ids = committed_run
    inside, release = threading.Event(), threading.Event()

    def do_cancel():
        with Session() as s:
            svc = _service(s, ids)
            _pause_after(svc.run_repo, "update_status", inside, release)
            return svc.cancel_run(ids["run"]).status

    def do_import():
        with Session() as s:
            svc = _service(s, ids)
            return svc.import_data(ids["run"], [LimsRunDataRow(row_data={"corr": "1.0"})]).imported

    canceler, canceled = _in_thread(do_cancel)
    assert inside.wait(LOCK_WAIT_S), canceled
    importer, imported = _in_thread(do_import)
    try:
        assert _waits_on_run_lock(Session, ids["run"]), "import did not wait on the run row lock"
        assert importer.is_alive()
    finally:
        release.set()
    canceler.join(LOCK_WAIT_S * 2)
    importer.join(LOCK_WAIT_S * 2)

    assert canceled.get("value") == LimsRunStatus.canceled, canceled
    error = imported.get("error")
    assert error is not None, imported
    assert error.status_code == 400
    assert "current status is 'canceled'" in error.detail
    with Session() as s:
        assert s.get(LimsRun, ids["run"]).status == LimsRunStatus.canceled
        assert s.query(LimsRunData).filter(LimsRunData.lims_run_id == ids["run"]).count() == 0


# ---------- 2: name-only match when the client ID is off the run ----------


def test_name_on_run_is_refused_when_the_client_id_is_an_off_run_sample(
    client, auth_headers, db_session, test_admin_user, test_org
):
    key = f"K229-{uuid.uuid4().hex[:6]}"
    off_by_client = _sample(db_session, test_admin_user, test_org, key)
    on_by_name = _sample(db_session, test_admin_user, test_org, f"N229-{uuid.uuid4().hex[:6]}")
    on_by_name.name = key
    db_session.commit()

    rows = [{"well_position": "A1", "sample_key": key, "row_data": {"corr": "1"}}]
    unmatched = link_rows(
        db_session,
        rows,
        parser_config={"sample_col": "__explicit__", "columns": []},
        on_run={on_by_name.id},
    )
    assert rows[0]["sample_id"] is None
    assert rows[0]["link_note"] == CLIENT_ID_OFF_RUN
    assert unmatched == [
        {"row_index": 0, "well_position": "A1", "sample_key": key, "reason": CLIENT_ID_OFF_RUN}
    ]

    analysis, _analyte = _analysis(db_session, test_admin_user)
    run_id = _run(client, auth_headers, _template(client, auth_headers), str(analysis.id), str(on_by_name.id))
    imported = client.post(
        f"/v1/lims-runs/{run_id}/import",
        json={"rows": [{"well_position": "A1", "sample_key": key, "row_data": {"corr": "1"}}]},
        headers=auth_headers,
    )
    assert imported.status_code == 200, imported.text
    row = imported.json()["rows"][0]
    assert row["sample_id"] is None
    assert row["link_note"] == CLIENT_ID_OFF_RUN
    assert off_by_client.id != on_by_name.id


# ---------- 3: failed_by ----------


def test_fail_records_the_actor_in_failed_by(
    client, auth_headers, db_session, test_admin_user, test_org
):
    sample = _sample(db_session, test_admin_user, test_org, f"F229-{uuid.uuid4().hex[:6]}")
    analysis, _analyte = _analysis(db_session, test_admin_user)
    run_id = _run(client, auth_headers, _template(client, auth_headers), str(analysis.id), str(sample.id))
    before = client.get(f"/v1/lims-runs/{run_id}", headers=auth_headers).json()
    assert before["failed_by"] is None

    failed = client.post(
        f"/v1/lims-runs/{run_id}/fail", json={"reason": "Edge effect"}, headers=auth_headers
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["failed_by"] == str(test_admin_user.id)
    run = db_session.get(LimsRun, uuid.UUID(run_id))
    db_session.refresh(run)
    assert run.failed_by == test_admin_user.id
    listed = client.get("/v1/lims-runs", params={"size": 100}, headers=auth_headers).json()["runs"]
    assert next(r for r in listed if r["id"] == run_id)["failed_by"] == str(test_admin_user.id)


def test_failed_by_is_a_nullable_restrict_fk_and_is_catalogued(migrated_engine):
    with migrated_engine.connect() as conn:
        nullable = conn.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'lims_runs' AND column_name = 'failed_by'"
            )
        ).scalar()
        assert nullable == "YES"
        fk = conn.execute(
            text(
                """
                SELECT c.confrelid::regclass::text, c.confdeltype
                FROM pg_constraint c
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
                WHERE c.contype = 'f' AND c.conrelid = 'lims_runs'::regclass AND a.attname = 'failed_by'
                """
            )
        ).one()
        assert fk[0] == "users"
        assert fk[1] == "r"
        registered = conn.execute(
            text("SELECT id FROM schema_tables WHERE physical_name = 'lims_runs'")
        ).scalars().all()
        assert registered, "no client registers lims_runs; the sync check would be vacuous"
        catalogued = conn.execute(
            text(
                "SELECT c.table_id, c.is_fk, c.fk_table, c.nullable FROM schema_columns c "
                "JOIN schema_tables t ON t.id = c.table_id "
                "WHERE t.physical_name = 'lims_runs' AND c.physical_name = 'failed_by'"
            )
        ).all()
        assert {row[0] for row in catalogued} == set(registered)
        assert all(row[1] is True and row[2] == "users" and row[3] is True for row in catalogued)


# ---------- 4: listing runs is not N+1 ----------


def _count_list_queries(client, auth_headers, db_session, size: int) -> tuple[int, list[str]]:
    db_session.expunge_all()
    statements: list[str] = []
    conn = db_session.connection()

    def count(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(conn, "before_cursor_execute", count)
    try:
        response = client.get("/v1/lims-runs", params={"size": size}, headers=auth_headers)
    finally:
        event.remove(conn, "before_cursor_execute", count)
    assert response.status_code == 200, response.text
    assert len(response.json()["runs"]) == size
    return len(statements), statements


def test_listing_runs_uses_the_same_number_of_queries_for_any_page_size(
    client, auth_headers, db_session, test_admin_user, test_org
):
    analysis, _analyte = _analysis(db_session, test_admin_user)
    for i in range(8):
        sample = _sample(db_session, test_admin_user, test_org, f"L229-{i}-{uuid.uuid4().hex[:6]}")
        run_id = _run(client, auth_headers, _template(client, auth_headers), str(analysis.id), str(sample.id))
        if i % 2:
            imported = client.post(
                f"/v1/lims-runs/{run_id}/import",
                json={"rows": [{"row_data": {"corr": "1"}}]},
                headers=auth_headers,
            )
            assert imported.status_code == 200, imported.text

    small, _ = _count_list_queries(client, auth_headers, db_session, 2)
    large, statements = _count_list_queries(client, auth_headers, db_session, 8)
    assert large == small, statements
    assert sum("lims_run_data" in sql for sql in statements) == 1, statements
    assert sum("experiment_templates" in sql for sql in statements) == 1, statements


# ---------- 5: configuring-agent upload cap ----------


def test_configuring_agent_upload_over_the_cap_is_413_and_stores_nothing(
    client, auth_headers, db_session
):
    from app.services.configuring_agent_service import MAX_FILE_BYTES
    from models.configuring_agent import ConfigurationDocument

    created = client.post(
        "/v1/configuring-agent/configurations",
        json={"name": f"Cap {uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]
    response = client.post(
        f"/v1/configuring-agent/configurations/{cid}/documents",
        files={"file": ("big.txt", io.BytesIO(b"a" * (MAX_FILE_BYTES + 1)), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 413, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "upload_too_large"
    assert detail["max_bytes"] == MAX_FILE_BYTES
    stored = (
        db_session.query(ConfigurationDocument)
        .filter(ConfigurationDocument.configuration_id == uuid.UUID(cid))
        .count()
    )
    assert stored == 0
