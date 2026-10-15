"""UAT RT-7: parallel reagent uses on one lot must not wedge the API.

Root cause at 0a90f6f: the reagent routes were ``async def`` but used the
sync SQLAlchemy session. A request blocked on the lot's FOR UPDATE lock
blocked the event loop, so the lock holder could never send COMMIT (idle in
transaction) and every other request, /health included, hung.

These tests use real committed rows on Postgres and a pool sized like
production (5 + 10) with more callers than connections.
"""
import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import _engine_kwargs
from app.routers import reagents as r
from app.schemas.reagent import ReagentUseCreate
from models.client import Client
from models.flexible_experiment import LimsRun
from models.reagent import Reagent, ReagentLot, ReagentUse
from models.user import Role, User

PARALLEL = 16


def test_reagent_routes_are_sync_so_db_waits_run_in_the_threadpool():
    for route in r.reagent_uses_router.routes + r.reagent_lots_router.routes + r.reagents_router.routes:
        assert not asyncio.iscoroutinefunction(route.endpoint), route.path


def test_engine_bounds_every_wait():
    kw = _engine_kwargs("postgresql://u:p@h/db")
    opts = kw["connect_args"]["options"]
    for guc in ("lock_timeout", "statement_timeout", "idle_in_transaction_session_timeout"):
        assert f"-c {guc}=" in opts
    assert kw["pool_timeout"] > 0


@pytest.fixture
def committed(db_engine):
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, pool_size=5, max_overflow=10, **_engine_kwargs(url))
    Session = sessionmaker(bind=engine, autoflush=False)
    tag = uuid.uuid4().hex[:8]
    with Session() as s:
        org = Client(name=f"RT7 {tag}")
        role = Role(name=f"rt7 {tag}", description="rt7")
        s.add_all([org, role])
        s.flush()
        user = User(name="RT7", username=f"rt7{tag}", email=f"rt7{tag}@x", password_hash="x",
                    role_id=role.id, client_id=org.id, must_change_password=False)
        s.add(user)
        s.flush()
        reagent = Reagent(name=f"RT7 reagent {tag}", unit="uL", created_by=user.id, modified_by=user.id)
        s.add(reagent)
        s.flush()
        lot = ReagentLot(reagent_id=reagent.id, lot_number=f"RT7-{tag}", unit="uL", quantity_received=Decimal(100),
                         quantity_remaining=Decimal(100), qc_status="released", released=True, active=True,
                         created_by=user.id, modified_by=user.id)
        run = LimsRun(name=f"RT7 run {tag}", created_by=user.id)
        s.add_all([lot, run])
        s.commit()
        ids = dict(user=user.id, lot=lot.id, run=run.id, reagent=reagent.id, role=role.id, org=org.id)
    yield Session, ids
    with engine.begin() as c:
        c.execute(text("DELETE FROM reagent_uses WHERE reagent_lot_id = :i"), {"i": ids["lot"]})
        c.execute(text("DELETE FROM reagent_lots WHERE id = :i"), {"i": ids["lot"]})
        c.execute(text("DELETE FROM lims_runs WHERE id = :i"), {"i": ids["run"]})
        c.execute(text("DELETE FROM reagents WHERE id = :i"), {"i": ids["reagent"]})
        c.execute(text("DELETE FROM users WHERE id = :i"), {"i": ids["user"]})
        c.execute(text("DELETE FROM roles WHERE id = :i"), {"i": ids["role"]})
        c.execute(text("DELETE FROM clients WHERE id = :i"), {"i": ids["org"]})
    engine.dispose()


def _use(Session, ids, qty, gate):
    gate.wait()
    with Session() as s:
        user = s.get(User, ids["user"])
        try:
            r.record_reagent_use(
                ReagentUseCreate(reagent_lot_id=ids["lot"], lims_run_id=ids["run"], quantity_used=qty),
                current_user=user, db=s,
            )
            return 201
        except HTTPException as exc:
            return exc.status_code


@pytest.mark.parametrize("qty,expect_ok", [(Decimal(5), PARALLEL), (Decimal(15), 6)])
def test_parallel_uses_complete_without_oversell(committed, qty, expect_ok):
    Session, ids = committed
    gate = threading.Barrier(PARALLEL)
    start = time.monotonic()
    with ThreadPoolExecutor(PARALLEL) as pool:
        codes = list(pool.map(lambda _: _use(Session, ids, qty, gate), range(PARALLEL)))
    elapsed = time.monotonic() - start
    assert elapsed < 20, elapsed
    assert codes.count(201) == expect_ok, codes
    assert set(codes) <= {201, 422}, codes
    with Session() as s:
        left = s.get(ReagentLot, ids["lot"]).quantity_remaining
        used = s.query(ReagentUse).filter(ReagentUse.reagent_lot_id == ids["lot"]).count()
        idle = s.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction' "
                              "AND pid <> pg_backend_pid()")).scalar()
    assert used == expect_ok
    assert left == Decimal(100) - qty * expect_ok and left >= 0
    assert idle == 0
