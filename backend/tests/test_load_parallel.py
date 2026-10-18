"""Basic load test: parallel requests across several endpoints, including
lock contention on one reagent lot, while /health is polled.

Real committed rows on Postgres and a pool sized like production (5 + 10).
The TestClient drives one event loop, as uvicorn does, so a handler that
blocked the loop would stall /health here.
"""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.database import _engine_kwargs, get_db
from app.main import app
from models.client import Client
from models.flexible_experiment import LimsRun
from models.reagent import Reagent, ReagentLot, Vendor
from models.user import Permission, Role, User, role_permissions

PERMS = ["experiment:manage", "config:edit"]
LOCK_HOLD_S = 2.0


@pytest.fixture
def world(db_engine):
    url = db_engine.url.render_as_string(hide_password=False)
    engine = create_engine(url, pool_size=5, max_overflow=10, **_engine_kwargs(url))
    Session = sessionmaker(bind=engine, autoflush=False)
    tag = uuid.uuid4().hex[:8]
    made_perms = []
    with Session() as s:
        perms = []
        for name in PERMS:
            p = s.query(Permission).filter(Permission.name == name).one_or_none()
            if p is None:
                p = Permission(name=name, description=name)
                s.add(p)
                s.flush()
                made_perms.append(p.id)
            perms.append(p)
        org = Client(name=f"Load {tag}")
        role = Role(name=f"load {tag}", description="load")
        s.add_all([org, role])
        s.flush()
        for p in perms:
            s.execute(role_permissions.insert().values(role_id=role.id, permission_id=p.id))
        user = User(name="Load", username=f"load{tag}", email=f"load{tag}@x", password_hash="x",
                    role_id=role.id, client_id=org.id, must_change_password=False)
        s.add(user)
        s.flush()
        vendor = Vendor(name=f"Load vendor {tag}", created_by=user.id, modified_by=user.id)
        reagent = Reagent(name=f"Load reagent {tag}", unit="uL", created_by=user.id, modified_by=user.id)
        s.add_all([vendor, reagent])
        s.flush()
        lot = ReagentLot(reagent_id=reagent.id, lot_number=f"LOAD-{tag}", unit="uL", quantity_received=Decimal(1000),
                         quantity_remaining=Decimal(1000), qc_status="released", released=True, active=True,
                         created_by=user.id, modified_by=user.id)
        run = LimsRun(name=f"Load run {tag}", created_by=user.id)
        s.add_all([lot, run])
        s.commit()
        ids = dict(user=user.id, lot=lot.id, run=run.id, reagent=reagent.id, vendor=vendor.id,
                   role=role.id, org=org.id)
        token = create_access_token({"sub": str(user.id), "username": user.username,
                                     "role": role.name, "permissions": PERMS})

    def per_request_db():
        from app.core.lab_time import publish_lab_zone

        db = Session()
        try:
            publish_lab_zone(db)
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = per_request_db
    try:
        with TestClient(app) as client:
            yield client, {"Authorization": f"Bearer {token}"}, ids, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        with engine.begin() as c:
            for sql, key in (
                ("DELETE FROM reagent_uses WHERE reagent_lot_id = :i", "lot"),
                ("DELETE FROM reagent_lots WHERE id = :i", "lot"),
                ("DELETE FROM lims_runs WHERE id = :i", "run"),
                ("DELETE FROM reagents WHERE id = :i", "reagent"),
                ("DELETE FROM vendors WHERE id = :i", "vendor"),
                ("DELETE FROM users WHERE id = :i", "user"),
                ("DELETE FROM role_permissions WHERE role_id = :i", "role"),
                ("DELETE FROM roles WHERE id = :i", "role"),
                ("DELETE FROM clients WHERE id = :i", "org"),
            ):
                c.execute(text(sql), {"i": ids[key]})
            for pid in made_perms:
                c.execute(text("DELETE FROM permissions WHERE id = :i"), {"i": pid})
            c.execute(text(
                "DELETE FROM lab_settings WHERE id = 'b1a16ae0-0000-4000-8000-000000000001'"
            ))
        engine.dispose()


def test_parallel_load_with_lock_contention_keeps_health_responsive(world):
    client, h, ids, engine = world
    uses, reads = 12, 24
    lot = str(ids["lot"])
    health = []
    stop = threading.Event()

    def poll_health():
        while not stop.is_set():
            t = time.monotonic()
            r = client.get("/health")
            health.append((r.status_code, time.monotonic() - t))
            time.sleep(0.1)

    def use(_):
        return client.post("/v1/reagent-uses", headers=h, json={
            "reagent_lot_id": lot, "lims_run_id": str(ids["run"]), "quantity_used": 5}).status_code

    def read(i):
        path = ("/v1/reagents", "/v1/reagent-lots", "/v1/vendors", f"/v1/reagent-uses?reagent_lot_id={lot}")[i % 4]
        return client.get(path, headers=h).status_code

    poller = threading.Thread(target=poll_health)
    poller.start()
    start = time.monotonic()
    # Hold the lot's row lock in another connection so every use has to wait.
    with engine.connect() as holder:
        tx = holder.begin()
        holder.execute(text("SELECT 1 FROM reagent_lots WHERE id = :i FOR UPDATE"), {"i": ids["lot"]})
        with ThreadPoolExecutor(uses + reads) as pool:
            use_f = [pool.submit(use, i) for i in range(uses)]
            read_f = [pool.submit(read, i) for i in range(reads)]
            time.sleep(LOCK_HOLD_S)
            during = list(health)
            tx.rollback()
            use_codes = [f.result(timeout=30) for f in use_f]
            read_codes = [f.result(timeout=30) for f in read_f]
    elapsed = time.monotonic() - start
    stop.set()
    poller.join(timeout=5)

    assert elapsed < 30, elapsed
    assert use_codes == [201] * uses, use_codes
    assert read_codes == [200] * reads, read_codes
    # /health kept answering while the uses waited on the lock.
    assert len(during) >= 5, during
    assert all(code == 200 and dt < 1.0 for code, dt in health), max(dt for _, dt in health)
    with engine.connect() as c:
        left = c.execute(text("SELECT quantity_remaining FROM reagent_lots WHERE id = :i"), {"i": ids["lot"]}).scalar()
        idle = c.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction' "
                              "AND pid <> pg_backend_pid()")).scalar()
    assert left == Decimal(1000) - 5 * uses
    assert idle == 0
