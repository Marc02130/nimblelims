"""Outside calls must not run inside an idle DB transaction (UAT e47c53f).

Postgres kills a connection idle in a transaction after
idle_in_transaction_session_timeout (60 s in production, 1 s here).

* Dose-response: _run_fit read the run's data, then waited on R (up to 60 s)
  with the read transaction idle. The connection was killed, the result write
  failed, the finally that clears fit_in_progress failed on the dead
  connection, and every retry got 409.
* Configuring agent: POST .../runs read the run's steps for the response; the
  request session is cleaned up only after the background model call, so that
  read sat idle in a transaction and was killed at 60 s.
"""
import time
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.database import get_db
from app.main import app
from app.services import configuring_agent_service as svc
from app.services.dose_response_fit import DoseResponseFitService
from models.client import Client
from models.configuring_agent import Configuration
from models.flexible_experiment import LimsRun
from models.user import Permission, Role, User, role_permissions
from tests.test_dose_response import (
    _make_data_row, _make_list_entry, _make_run, _make_sample, _make_template, _make_well, _sigmoid_r_result,
)

IDLE_MS = 1000
SLOW_S = 2.5


def _idle_in_tx(engine, app_name):
    with engine.connect() as c:
        return c.execute(text(
            "SELECT count(*) FROM pg_stat_activity WHERE state LIKE 'idle in transaction%' "
            "AND application_name = :a"), {"a": app_name}).scalar()


@pytest.fixture
def real(db_engine):
    """Committed rows on a session whose idle-in-transaction timeout is 1 s."""
    url = db_engine.url.render_as_string(hide_password=False)
    app_name = f"idle-{uuid.uuid4().hex[:8]}"
    engine = create_engine(url, connect_args={
        "options": f"-c idle_in_transaction_session_timeout={IDLE_MS}", "application_name": app_name})
    Session = sessionmaker(bind=engine, autoflush=False)
    tag = uuid.uuid4().hex[:8]
    made_perms = []
    with Session() as s:
        org = Client(name=f"Idle {tag}")
        role = Role(name=f"idle {tag}", description="idle")
        s.add_all([org, role])
        s.flush()
        for name in ("config:edit", "schema:edit", "layout:edit"):
            p = s.query(Permission).filter(Permission.name == name).one_or_none()
            if p is None:
                p = Permission(name=name, description=name)
                s.add(p)
                s.flush()
                made_perms.append(p.id)
            s.execute(role_permissions.insert().values(role_id=role.id, permission_id=p.id))
        user = User(name="Idle", username=f"idle{tag}", email=f"idle{tag}@x", password_hash="x",
                    role_id=role.id, client_id=org.id, must_change_password=False)
        s.add(user)
        s.commit()
        ids = {"user": user.id, "org": org.id, "role": role.id}
    yield Session, ids, engine, app_name
    uid = ids["user"]
    with engine.begin() as c:
        runs = "SELECT id FROM lims_runs WHERE created_by = :u"
        tmpls = "SELECT id FROM experiment_templates WHERE created_by = :u"
        for sql in (
            f"DELETE FROM dose_response_results WHERE lims_run_id IN ({runs})",
            f"DELETE FROM lims_run_data WHERE lims_run_id IN ({runs})",
            "DELETE FROM lims_runs WHERE created_by = :u",
            f"DELETE FROM template_well_definitions WHERE template_id IN ({tmpls})",
            "DELETE FROM experiment_templates WHERE created_by = :u",
            "DELETE FROM samples WHERE created_by = :u",
            "DELETE FROM projects WHERE created_by = :u",
            "DELETE FROM configuration_steps WHERE run_id IN (SELECT id FROM configuration_runs WHERE created_by = :u)",
            "DELETE FROM configuration_runs WHERE created_by = :u",
            "DELETE FROM configurations WHERE created_by = :u",
            "DELETE FROM list_entries WHERE created_by = :u",
            "DELETE FROM lists WHERE created_by = :u",
        ):
            c.execute(text(sql), {"u": uid})
        c.execute(text("DELETE FROM users WHERE id = :i"), {"i": uid})
        c.execute(text("DELETE FROM role_permissions WHERE role_id = :i"), {"i": ids["role"]})
        c.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
        c.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
        for pid in made_perms:
            c.execute(text("DELETE FROM permissions WHERE id = :i"), {"i": pid})
    engine.dispose()


def _dr_run(Session, ids):
    with Session() as s:
        uid, cid = ids["user"], ids["org"]
        pos = _make_sample(s, uid, cid, _make_list_entry(s, "positive_control", uid, code="positive").id)
        neg = _make_sample(s, uid, cid, _make_list_entry(s, "negative_control", uid, code="negative").id)
        test = _make_sample(s, uid, cid, None)
        tmpl = _make_template(s, uid)
        run = _make_run(s, tmpl.id, uid)
        _make_well(s, tmpl.id, cid, "A1", 1.0)
        for sample, well, sig in ((pos, "B1", 100.0), (pos, "B2", 100.0), (neg, "C1", 0.0),
                                  (neg, "C2", 0.0), (test, "A1", 50.0)):
            _make_data_row(s, run.id, sample.id, well, sig, uid)
        s.commit()
        return run.id, test.id


def _fit(Session, ids, run_id, r_client):
    with Session() as s:
        return DoseResponseFitService(s, s.get(User, ids["user"]), r_client=r_client).trigger_fit(run_id)


def _flag(Session, run_id):
    with Session() as s:
        return s.get(LimsRun, run_id).fit_in_progress


def test_slow_r_fit_outlives_the_idle_timeout_and_retry_is_not_409(real):
    Session, ids, engine, _ = real
    run_id, sample_id = _dr_run(Session, ids)

    def slow_fit(compounds, config):
        time.sleep(SLOW_S)
        return [_sigmoid_r_result(sample_id)]

    slow = MagicMock()
    slow.fit.side_effect = slow_fit
    out = _fit(Session, ids, run_id, slow)
    assert out["fitted"] == 1, out
    assert _flag(Session, run_id) is False
    # Retry: no stuck in-progress flag, so no 409.
    fast = MagicMock()
    fast.fit.return_value = [_sigmoid_r_result(sample_id)]
    assert _fit(Session, ids, run_id, fast)["fitted"] == 1
    assert _flag(Session, run_id) is False


def test_flag_is_cleared_even_when_the_connection_dies_during_the_r_call(real, db_engine):
    """The old failure: the fit's connection is killed while R runs. The fit
    fails, but the in-progress flag is cleared on a fresh connection and the
    retry succeeds instead of 409."""
    Session, ids, engine, app_name = real
    run_id, sample_id = _dr_run(Session, ids)

    def fit_then_kill(compounds, config):
        with db_engine.connect() as c:  # another app_name: kills every pooled fit connection
            c.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                           "WHERE application_name = :a AND pid <> pg_backend_pid()"), {"a": app_name})
        return [_sigmoid_r_result(sample_id)]

    killer = MagicMock()
    killer.fit.side_effect = fit_then_kill
    with pytest.raises(Exception):
        _fit(Session, ids, run_id, killer)
    assert _flag(Session, run_id) is False
    fast = MagicMock()
    fast.fit.return_value = [_sigmoid_r_result(sample_id)]
    assert _fit(Session, ids, run_id, fast)["fitted"] == 1


def test_no_transaction_is_open_during_the_r_call(real):
    Session, ids, engine, app_name = real
    run_id, sample_id = _dr_run(Session, ids)
    seen = {}

    def check(compounds, config):
        seen["idle_tx"] = _idle_in_tx(engine, app_name)
        return [_sigmoid_r_result(sample_id)]

    r = MagicMock()
    r.fit.side_effect = check
    _fit(Session, ids, run_id, r)
    assert seen == {"idle_tx": 0}


def test_agent_run_start_leaves_no_session_idle_in_transaction(real, monkeypatch):
    Session, ids, engine, app_name = real
    from tests.test_configuring_agent_locks import PROVIDER

    monkeypatch.setattr(svc, "_key_for_run", lambda _db: (PROVIDER, "test-key"))
    monkeypatch.setattr(svc, "_excerpt", lambda *_a, **_k: ["excerpt"])
    monkeypatch.setattr(svc, "_ready_documents", lambda *_a, **_k: 1)
    monkeypatch.delenv("CONFIGURING_AGENT_ASYNC", raising=False)
    seen = {}

    def slow_model(*_a, **_k):
        time.sleep(SLOW_S)  # longer than the 1 s idle timeout
        seen["idle_tx"] = _idle_in_tx(engine, app_name)
        return {"steps": []}

    monkeypatch.setattr(svc, "propose", slow_model)
    monkeypatch.setattr(svc, "BACKGROUND_SESSION_FACTORY", Session)
    with Session() as s:
        cfg = Configuration(id=uuid.uuid4(), client_id=ids["org"], name="Idle cfg", created_by=ids["user"])
        s.add(cfg)
        s.commit()
        cfg_id = cfg.id
        user = s.get(User, ids["user"])
        token = create_access_token({"sub": str(user.id), "username": user.username, "role": "idle",
                                     "permissions": ["config:edit", "schema:edit", "layout:edit"]})

    def per_request():
        from app.core.lab_time import publish_lab_zone

        db = Session()
        try:
            publish_lab_zone(db)
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = per_request
    try:
        with TestClient(app) as client:
            r = client.post(f"/v1/configuring-agent/configurations/{cfg_id}/runs",
                            headers={"Authorization": f"Bearer {token}"}, json={"goal_note": "goal"})
            assert r.status_code == 202, r.text
            run_id = r.json()["id"]
    finally:
        app.dependency_overrides.pop(get_db, None)
    # The background task ran (TestClient waits for it); during the model call
    # nothing of ours was idle in a transaction, and nothing was killed.
    assert seen == {"idle_tx": 0}
    with Session() as s:
        from models.configuring_agent import ConfigurationRun
        row = s.get(ConfigurationRun, uuid.UUID(run_id))
        assert row.status != "failed" and row.error_message is None, (row.status, row.error_message)
