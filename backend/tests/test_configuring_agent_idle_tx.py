"""UAT 67481e9 blocker: the propose step held a DB transaction open through
the model call (120-300 s), so idle_in_transaction_session_timeout (60 s,
#162) killed the connection and every run failed with OperationalError.

Real committed rows and a real session whose idle timeout (1 s) is shorter
than the mocked model call (2.5 s).
"""
import time
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.services import configuring_agent_service as svc
from models.client import Client
from models.configuring_agent import Configuration, ConfigurationRun
from models.user import Permission, Role, User, role_permissions
from tests.test_configuring_agent_locks import _no_live_provider  # noqa: F401  (autouse fixture)

IDLE_MS = 1000
MODEL_S = 2.5
PERMS = ["config:edit", "schema:edit", "layout:edit"]


def _slow_model(*_a, **_k):
    time.sleep(MODEL_S)
    return {"steps": [{"group": "other", "target": "Slow list", "action": "Create list", "why": "SOP",
                       "call": {"method": "POST", "path": "/lists", "body": {"name": f"Slow_{uuid.uuid4().hex[:6]}"}}}]}


@pytest.fixture
def world(db_engine):
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, connect_args={"options": f"-c idle_in_transaction_session_timeout={IDLE_MS}"})
    Session = sessionmaker(bind=engine, autoflush=False)
    tag = uuid.uuid4().hex[:8]
    made = []
    with Session() as s:
        org = Client(name=f"Idle {tag}")
        role = Role(name=f"idle {tag}", description="idle")
        s.add_all([org, role])
        s.flush()
        for name in PERMS:
            p = s.query(Permission).filter(Permission.name == name).one_or_none()
            if p is None:
                p = Permission(name=name, description=name)
                s.add(p)
                s.flush()
                made.append(p.id)
            s.execute(role_permissions.insert().values(role_id=role.id, permission_id=p.id))
        user = User(name="Idle", username=f"idle{tag}", email=f"idle{tag}@x", password_hash="x",
                    role_id=role.id, client_id=org.id, must_change_password=False)
        s.add(user)
        s.flush()
        cfg = Configuration(id=uuid.uuid4(), client_id=org.id, name=f"Idle cfg {tag}", created_by=user.id)
        s.add(cfg)
        s.commit()
        ids = dict(user=user.id, org=org.id, role=role.id, cfg=cfg.id)
    yield Session, ids
    with engine.begin() as c:
        c.execute(text("DELETE FROM configuration_steps WHERE run_id IN "
                       "(SELECT id FROM configuration_runs WHERE configuration_id = :i)"), {"i": ids["cfg"]})
        c.execute(text("DELETE FROM configuration_runs WHERE configuration_id = :i"), {"i": ids["cfg"]})
        c.execute(text("DELETE FROM configurations WHERE id = :i"), {"i": ids["cfg"]})
        c.execute(text("DELETE FROM users WHERE id = :i"), {"i": ids["user"]})
        c.execute(text("DELETE FROM role_permissions WHERE role_id = :i"), {"i": ids["role"]})
        c.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
        c.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
        for pid in made:
            c.execute(text("DELETE FROM permissions WHERE id = :i"), {"i": pid})
    engine.dispose()


def test_background_propose_outlives_a_short_idle_timeout(world, monkeypatch):
    Session, ids = world
    monkeypatch.setattr(svc, "propose", _slow_model)
    with Session() as s:
        user = s.get(User, ids["user"])
        run, pending = svc.begin_run(s, user, ids["cfg"], "goal")
        run_id = run.id
    svc.run_in_background(pending, session_factory=Session)
    with Session() as s:
        run = s.get(ConfigurationRun, run_id)
        assert run.status == "proposing", run.error_message
        assert len(run.steps) == 1


def test_inline_start_and_redo_outlive_a_short_idle_timeout(world, monkeypatch):
    Session, ids = world
    monkeypatch.setattr(svc, "propose", _slow_model)
    with Session() as s:
        user = s.get(User, ids["user"])
        run = svc.start_run(s, user, ids["cfg"], "goal")  # same session as the request
        assert run.status == "proposing", run.error_message
        step_id = run.steps[0].id
        redone = svc.redo_step(s, user, run.id, step_id, "use a different name")
        assert redone.status == "proposing" and len(redone.steps) == 1


def test_no_transaction_is_open_during_the_model_call(world, monkeypatch):
    Session, ids = world
    seen = {}
    with Session() as s:
        def check(*a, **k):
            seen["in_tx"] = s.in_transaction()
            return {"steps": []}

        monkeypatch.setattr(svc, "propose", check)
        svc.start_run(s, s.get(User, ids["user"]), ids["cfg"], "goal")
    assert seen == {"in_tx": False}
