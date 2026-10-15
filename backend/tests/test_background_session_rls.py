"""Background sessions carry the originating request's RLS context.

Before this, SOP-parse background sessions set no user/client. Under real RLS
(the app connects as the non-superuser lims_app) a contextless session sees no
client rows, so the task found no job and silently did nothing; run as a
superuser it would have been unscoped. Now user_id/client_id are captured at
request time and applied to every background session (app.database.
background_session), and the task fails closed without them.

Real RLS: migrated DB, connections as the non-superuser app_test_role.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app import database
from app.database import MissingRlsContext, background_session
from app.services.sop_parse_service import SOPParseService

RESULT = '{"template_definition": {}, "parser_config": {}, "worklist_config": {}}'


@pytest.fixture(scope="module")
def rls(migrated_engine):
    url = migrated_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, connect_args={"options": "-c role=app_test_role"})
    Factory = sessionmaker(bind=engine, autoflush=False)
    # Same hook production's SessionLocal has: re-apply the context after commits.
    event.listen(Factory, "after_begin", database._apply_rls_gucs_on_begin)

    ids = {k: uuid.uuid4() for k in ("ca", "cb", "ua", "ub", "ja", "jb")}
    s = {k: str(v) for k, v in ids.items()}
    with migrated_engine.begin() as c:  # superuser: seed without RLS
        lt = c.execute(text("SELECT id FROM roles WHERE name = 'Lab Technician'")).scalar_one()
        c.execute(text("INSERT INTO clients (id, name, active, billing_info) VALUES "
                       "(:ca, :na, true, '{}'), (:cb, :nb, true, '{}')"),
                  {**s, "na": f"BG A {s['ca'][:6]}", "nb": f"BG B {s['cb'][:6]}"})
        c.execute(text("INSERT INTO users (id, name, username, email, password_hash, role_id, client_id, active) VALUES "
                       "(:ua, 'BG A', :una, :ea, 'x', :lt, :ca, true), (:ub, 'BG B', :unb, :eb, 'x', :lt, :cb, true)"),
                  {**s, "lt": lt, "una": f"bga{s['ua'][:8]}", "unb": f"bgb{s['ub'][:8]}",
                   "ea": f"{s['ua'][:8]}@a.x", "eb": f"{s['ub'][:8]}@b.x"})
        c.execute(text("INSERT INTO sop_parse_jobs (id, status, sop_filename, created_by) VALUES "
                       "(:ja, 'pending', 'a.txt', :ua), (:jb, 'pending', 'b.txt', :ub)"), s)
    yield Factory, ids, migrated_engine
    with migrated_engine.begin() as c:
        c.execute(text("DELETE FROM sop_parse_jobs WHERE id IN (:ja, :jb)"), s)
        c.execute(text("DELETE FROM users WHERE id IN (:ua, :ub)"), s)
        c.execute(text("DELETE FROM clients WHERE id IN (:ca, :cb)"), s)
    engine.dispose()


def _status(engine, job_id):
    with engine.connect() as c:  # superuser read
        return c.execute(text("SELECT status::text FROM sop_parse_jobs WHERE id = :i"), {"i": str(job_id)}).scalar()


def _reset(engine, *job_ids):
    with engine.begin() as c:
        for j in job_ids:
            c.execute(text("UPDATE sop_parse_jobs SET status = 'pending', result = NULL, error_message = NULL "
                           "WHERE id = :i"), {"i": str(j)})


def _parse(Factory, job_id, user_id, client_id):
    resp = MagicMock()
    resp.content = [MagicMock(text=RESULT)]
    with patch("app.services.sop_parse_service.ANTHROPIC_API_KEY", "fake-key"), \
         patch("anthropic.Anthropic") as cls:
        cls.return_value.messages.create.return_value = resp
        SOPParseService.run_extraction_background(
            job_id=job_id, sop_text="SOP", instrument_text="a,b\n1,2",
            user_id=user_id, client_id=client_id, session_factory=Factory)


def test_parse_writes_its_own_clients_job(rls):
    Factory, ids, su = rls
    _reset(su, ids["ja"])
    _parse(Factory, ids["ja"], ids["ua"], ids["ca"])
    assert _status(su, ids["ja"]) == "complete"


def test_parse_cannot_read_or_write_another_clients_job(rls):
    Factory, ids, su = rls
    _reset(su, ids["jb"])
    # User A's context aimed at client B's job: RLS hides it, nothing changes.
    _parse(Factory, ids["jb"], ids["ua"], ids["ca"])
    assert _status(su, ids["jb"]) == "pending"
    with background_session(ids["ua"], ids["ca"], Factory) as db:
        seen = {r[0] for r in db.execute(text("SELECT id FROM sop_parse_jobs WHERE id IN (:a, :b)"),
                                         {"a": str(ids["ja"]), "b": str(ids["jb"])})}
        assert seen == {ids["ja"]}
        n = db.execute(text("UPDATE sop_parse_jobs SET error_message = 'x' WHERE id = :b"),
                       {"b": str(ids["jb"])}).rowcount
        db.commit()
        assert n == 0


def test_context_survives_commit_inside_the_background_session(rls):
    Factory, ids, _ = rls
    with background_session(ids["ua"], ids["ca"], Factory) as db:
        db.commit()
        assert db.execute(text("SELECT current_setting('app.current_user_id', true)")).scalar() == str(ids["ua"])
        assert db.execute(text("SELECT current_setting('app.client_id', true)")).scalar() == str(ids["ca"])


def test_parse_without_a_user_fails_closed(rls):
    Factory, ids, su = rls
    _reset(su, ids["ja"])
    _parse(Factory, ids["ja"], None, None)
    assert _status(su, ids["ja"]) == "pending"
    with pytest.raises(MissingRlsContext):
        with background_session(None, None, Factory):
            pass


def test_router_passes_the_request_user_and_client(client, db_session, test_admin_user, monkeypatch):
    seen = {}
    monkeypatch.setattr(SOPParseService, "run_extraction_background",
                        staticmethod(lambda **kw: seen.update(kw)))
    token = client.post("/auth/login", json={"username": "admin", "password": "adminpassword"}).json()["access_token"]
    r = client.post("/v1/sop-parse", headers={"Authorization": f"Bearer {token}"},
                    files={"sop_file": ("s.txt", b"SOP"), "instrument_file": ("i.csv", b"a,b\n1,2")})
    assert r.status_code == 202, r.text
    assert seen["user_id"] == test_admin_user.id and seen["client_id"] == test_admin_user.client_id


def test_configuring_agent_background_run_sets_context_on_injected_sessions(db_session, test_admin_user, monkeypatch):
    """The agent's background run applied RLS only on its own SessionLocal;
    an injected session factory ran without context. Now always."""
    from types import SimpleNamespace
    from app.services import configuring_agent_service as svc

    uid, cid = test_admin_user.id, test_admin_user.client_id
    seen = {}

    def fake_finish(db, user, pending, raise_errors=True):
        seen["user"] = db.execute(text("SELECT current_setting('app.current_user_id', true)")).scalar()
        seen["client"] = db.execute(text("SELECT current_setting('app.client_id', true)")).scalar()

    monkeypatch.setattr(svc, "finish_run", fake_finish)
    pending = SimpleNamespace(run_id=uuid.uuid4(), user_id=uid, client_id=cid)
    svc.run_in_background(pending, session_factory=lambda: db_session)
    assert seen == {"user": str(uid), "client": str(cid)}
    assert "rls_user_id" not in db_session.info  # restored for the shared test session
