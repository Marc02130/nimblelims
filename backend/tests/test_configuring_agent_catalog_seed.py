"""D-3/L-4 (Marc's ruling): configurable existing tables are registered up front
by migration 0089, and starting a run writes nothing before confirm.

Pass bar (Tobias): a fresh seed DB already has the schema_tables /
schema_columns / schema_privileges rows before any run, matching the Schema
display rule, and run start makes zero catalog/configuration writes.
"""

import importlib.util
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.services import configuring_agent_service as svc
from app.services import ui_schema_catalog as catalog
from models.configuring_agent import Configuration
from tests.test_configuring_agent_locks import _no_live_provider, _propose, _user  # noqa: F401

SEED_CLIENT = "00000000-0000-0000-0000-000000000001"
MIGRATION = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0089_register_schema_catalog.py")


MIGRATION_0090 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0090_reagent_tracking.py")
MIGRATION_0111 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0111_instrument_tracking.py")
MIGRATION_0107 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0107_elisa_run_gaps.py")
MIGRATION_0113 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0113_maintenance_tracked.py")
MIGRATION_0115 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0115_instrument_type_slots.py")
MIGRATION_0116 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0116_e2_review_fixes.py")
MIGRATION_0117 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0117_e3_hardening.py")
MIGRATION_0119 = os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "versions", "0119_instrument_reasons.py")


def _migration(path=MIGRATION):
    spec = importlib.util.spec_from_file_location("m" + os.path.basename(path)[:4], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _display_set(conn):
    wanted = list(catalog.LAB_TABLES) + list(catalog.SYSTEM_TABLES)
    present = {r[0] for r in conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
        "AND table_type='BASE TABLE' AND table_name = ANY(:n)"), {"n": wanted}).all()}
    return {n for n in present if catalog.shown_in_schema(n, catalog.kind_for(n))}


def test_frozen_migration_list_matches_the_live_display_rule():
    module = _migration()
    m0111 = _migration(MIGRATION_0111)
    frozen = {
        t[0]: (t[1], t[2])
        for t in module.TABLES
        + _migration(MIGRATION_0090).TABLES
        + _migration(MIGRATION_0107).TABLES
        + _migration(MIGRATION_0113).TABLES
        + _migration(MIGRATION_0115).TABLES
        + _migration(MIGRATION_0116).TABLES
        + _migration(MIGRATION_0117).TABLES
        + _migration(MIGRATION_0119).TABLES
    }
    for name in getattr(m0111, "REMOVED", ()):
        frozen.pop(name, None)
    for t in m0111.TABLES:
        frozen[t[0]] = (t[1], t[2])
    live = {
        n: (catalog.kind_for(n), catalog.display_name_for(n))
        for n in list(catalog.LAB_TABLES) + list(catalog.SYSTEM_TABLES)
        if catalog.shown_in_schema(n, catalog.kind_for(n))
    }
    assert frozen == live
    assert not set(frozen) & set(catalog.NOT_SCHEMA_TABLES)
    assert len(_migration(MIGRATION_0113).revision) <= 32
    assert len(_migration(MIGRATION_0115).revision) <= 32
    assert len(_migration(MIGRATION_0116).revision) <= 32
    assert len(_migration(MIGRATION_0117).revision) <= 32
    assert len(_migration(MIGRATION_0119).revision) <= 32


def test_fresh_seed_db_has_catalog_rows_before_any_run(migrated_engine):
    with migrated_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM configuration_runs")).scalar() == 0
        expected = _display_set(conn)
        clients = [r[0] for r in conn.execute(text("SELECT id FROM clients")).all()]
        assert clients
        for client in clients:
            tables = dict(conn.execute(text(
                "SELECT physical_name, id FROM schema_tables WHERE client_id = :c"), {"c": client}).all())
            assert set(tables) == expected, client
            assert not {"lists", "list_entries", "units"} & set(tables)
            for physical, table_id in tables.items():
                cols = {r[0] for r in conn.execute(text(
                    "SELECT physical_name FROM schema_columns WHERE table_id = :t"), {"t": table_id}).all()}
                real = {r[0] for r in conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
                    "AND table_name = :n"), {"n": physical}).all()}
                assert cols == real, physical
            privs = dict(conn.execute(text(
                "SELECT r.name, p.access FROM schema_privileges p JOIN roles r ON r.id = p.role_id "
                "WHERE p.table_id = :t AND p.column_id IS NULL"), {"t": tables["samples"]}).all())
            for role, access in (("Administrator", "write"), ("Lab Manager", "write"),
                                 ("Lab Technician", "write"), ("Client", "read")):
                assert privs.get(role) == access


@pytest.fixture
def seed(migrated_engine):
    """The seed client, as migrated, in a savepoint-isolated session."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")()
    from models.client import Client

    org = session.get(Client, uuid.UUID(SEED_CLIENT))
    user = _user(session, org, "seedadmin", ["config:edit", "schema:edit", "layout:edit"])
    cfg = Configuration(id=uuid.uuid4(), client_id=org.id, name=f"S {uuid.uuid4().hex[:6]}", created_by=user.id)
    session.add(cfg)
    session.commit()
    yield session, user, cfg, connection
    session.close()
    transaction.rollback()
    connection.close()


def test_ensure_catalog_finds_nothing_left_to_register(seed):
    """The migration wrote what the Schema screen's lazy path would have."""
    session, user, _cfg, _conn = seed
    from app.services.ui_schema_service import UiSchemaService

    def counts():
        return tuple(session.execute(text(f"SELECT count(*) FROM {t} WHERE client_id = :c"),
                                     {"c": SEED_CLIENT}).scalar()
                     for t in ("schema_tables", "schema_columns", "schema_privileges"))

    before = counts()
    UiSchemaService(session, user).ensure_catalog()
    assert counts() == before


def _row_counts(session):
    tables = [r[0] for r in session.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"))]
    return {t: session.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in tables}


def test_run_start_writes_nothing_but_the_run_itself(seed, monkeypatch):
    session, user, cfg, _conn = seed
    before = _row_counts(session)
    _propose(monkeypatch, [
        {"group": "schema_columns", "target": "Note", "action": "Add", "why": "SOP",
         "call": {"method": "POST", "path": "/v1/schema/columns",
                  "body": {"name": f"Note {uuid.uuid4().hex[:4]}", "table": "samples", "data_type": "text"}}},
    ])
    run = svc.start_run(session, user, cfg.id, "goal")
    # The catalog already had samples, so the row resolves to a real id.
    assert uuid.UUID(run.steps[0].call_body["table_id"])
    after = _row_counts(session)
    changed = {t for t in after if after[t] != before[t]}
    assert changed == {"configuration_runs", "configuration_steps"}, changed


def test_downgrade_removes_only_its_rows_and_upgrade_restores_them(migrated_engine):
    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    module = _migration()
    # 0090, 0107, 0111, 0113, 0115, and 0116 register later tables with the same
    # helpers; include them so the round trip covers every catalog row on a
    # fresh DB.
    module.TABLES = (
        module.TABLES
        + _migration(MIGRATION_0090).TABLES
        + _migration(MIGRATION_0107).TABLES
        + _migration(MIGRATION_0111).TABLES
        + _migration(MIGRATION_0113).TABLES
        + _migration(MIGRATION_0115).TABLES
        + _migration(MIGRATION_0116).TABLES
        + _migration(MIGRATION_0117).TABLES
        + _migration(MIGRATION_0119).TABLES
    )
    with migrated_engine.connect() as conn:
        transaction = conn.begin()
        try:
            ctx = MigrationContext.configure(conn)
            def total():
                return tuple(conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                             for t in ("schema_tables", "schema_columns", "schema_privileges"))
            seeded = total()
            assert all(seeded)
            with Operations.context(ctx):
                module.downgrade()
            assert total() == (0, 0, 0)
            with Operations.context(ctx):
                module.upgrade()
            assert total() == seeded
        finally:
            transaction.rollback()
