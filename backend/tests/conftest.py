"""
Pytest configuration and fixtures.
Uses testcontainers-python (PostgreSQL 15) to prevent SQLite/JSONB divergence.
"""
import os

# S3: allow tests to import app.core.config before any other imports.
# Assign, do not setdefault: a developer shell often exports ENVIRONMENT=development,
# and the API startup check must not open that database from the test client.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-for-production")
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")
# The lab timezone is required and stored in lab_settings.timezone. Tests that
# need a lab zone set that row. There is no environment fallback.
# Import builds an engine immediately. Tests do not query that engine.
# Fixtures pass the testcontainer URL through the environment. No password.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://lims_app@127.0.0.1:5432/lims_db",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.database import get_db
from app.core.bootstrap_roles import (
    TEST_APP_PASSWORD,
    TEST_MIGRATE_PASSWORD,
    apply_init_extensions,
    apply_zz_roles,
    migrate_database_url,
    run_privilege_snapshot,
)
from models.base import Base
from models.user import User, Role, Permission, role_permissions
from models.client import Client
from app.core.security import get_password_hash

# Import all models so Base.metadata is fully populated
import models  # noqa: F401


POSTGRES_IMAGE = "pgvector/pgvector:pg15"


@pytest.fixture(scope="session")
def pg_container():
    """Start a PostgreSQL 15 container once per test session."""
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        yield pg


def _install_access_functions(engine):
    """Install the SQL access helpers that routers call directly.

    create_all() builds tables only; batches/samples routers run
    ``SELECT has_project_access(...)`` and fail with UndefinedFunction without
    it. current_user_id()/is_admin() match migration 0003 and
    has_project_access() is loaded from migration 0065 (current definition),
    so the test DB uses the same logic as production. RLS policies themselves
    are NOT installed here; RLS tests use migrated_engine.
    """
    import importlib.util
    from pathlib import Path

    mig = Path(__file__).resolve().parents[1] / "db" / "migrations" / "versions" / "0065_has_project_access_project_users.py"
    spec = importlib.util.spec_from_file_location("_mig_0065", mig)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION current_user_id()
            RETURNS UUID AS $$
            BEGIN
                RETURN COALESCE(
                    NULLIF(current_setting('app.current_user_id', true), '')::UUID,
                    '00000000-0000-0000-0000-000000000000'::UUID
                );
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """))
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION is_admin()
            RETURNS BOOLEAN AS $$
            DECLARE
                user_role_name TEXT;
            BEGIN
                SELECT r.name INTO user_role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = current_user_id();
                RETURN user_role_name = 'Administrator';
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """))
        conn.execute(text(mod.NEW_FUNCTION))
        status_path = (
            Path(__file__).resolve().parents[1]
            / "db"
            / "migrations"
            / "versions"
            / "0098_batch_access_status.py"
        )
        status_spec = importlib.util.spec_from_file_location(
            "_mig_0098_batch_access_status", status_path
        )
        status_mod = importlib.util.module_from_spec(status_spec)
        status_spec.loader.exec_module(status_mod)
        conn.execute(text(status_mod.CREATE_FUNCTION))
        conn.execute(
            text(
                "REVOKE ALL ON FUNCTION public.batch_access_status(uuid) FROM PUBLIC"
            )
        )
        conn.commit()


def _seed_instrument_tracking_lists(engine) -> None:
    """Seed the lists 0106 would insert so create_all tests match a migrated DB."""
    from models.instrument import (
        DOWNTIME_REASONS_LIST_ID,
        INSTRUMENT_TYPES_LIST_ID,
        MAINTENANCE_TYPES_LIST_ID,
    )

    types = [
        (INSTRUMENT_TYPES_LIST_ID, "instrument_types", "Instrument kinds",
         [
             ("a1000001-0002-4001-8001-000000000001", "Plate reader", "plate_reader"),
             ("a1000001-0002-4001-8001-000000000002", "qPCR", "qpcr"),
             ("a1000001-0002-4001-8001-000000000003", "LC-MS", "lc_ms"),
             ("a1000001-0002-4001-8001-000000000004", "Liquid handler", "liquid_handler"),
             ("a1000001-0002-4001-8001-000000000005", "Balance", "balance"),
             ("a1000001-0002-4001-8001-000000000006", "Centrifuge", "centrifuge"),
         ]),
        (MAINTENANCE_TYPES_LIST_ID, "maintenance_types", "Instrument maintenance kinds",
         [
             ("a1000001-0003-4001-8001-000000000001", "PM", "pm"),
             ("a1000001-0003-4001-8001-000000000002", "calibration", "calibration"),
             ("a1000001-0003-4001-8001-000000000003", "qualification", "qualification"),
         ]),
        (DOWNTIME_REASONS_LIST_ID, "downtime_reasons", "Why an instrument is down",
         [
             ("a1000001-0004-4001-8001-000000000001", "Breakdown", "breakdown"),
             ("a1000001-0004-4001-8001-000000000002", "Preventive maintenance", "preventive_maintenance"),
             ("a1000001-0004-4001-8001-000000000003", "Calibration", "calibration_downtime"),
             ("a1000001-0004-4001-8001-000000000004", "Qualification", "qualification_downtime"),
             ("a1000001-0004-4001-8001-000000000005", "Facility", "facility"),
             ("a1000001-0004-4001-8001-000000000006", "Other", "other"),
         ]),
    ]
    with engine.begin() as conn:
        for list_id, name, description, entries in types:
            conn.execute(
                text(
                    "INSERT INTO lists (id, name, description, active, created_at, modified_at) "
                    "VALUES (:id, :name, :description, true, NOW(), NOW()) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": list_id, "name": name, "description": description},
            )
            for entry_id, entry_name, _code in entries:
                conn.execute(
                    text(
                        "INSERT INTO list_entries "
                        "(id, name, description, code, active, created_at, modified_at, list_id) "
                        "VALUES (:id, :name, :name, NULL, true, NOW(), NOW(), :list_id) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": entry_id,
                        "name": entry_name,
                        "list_id": list_id,
                    },
                )


def _install_lab_day_function(engine) -> None:
    """results.entry_date defaults to current_lab_day(), which must exist first."""
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "db"
        / "migrations"
        / "versions"
        / "0105_lab_timezone_required.py"
    )
    spec = importlib.util.spec_from_file_location("_mig_0105_lab_timezone_required", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with engine.connect() as conn:
        conn.execute(text(mod.CREATE_FUNCTION))
        conn.commit()


@pytest.fixture(scope="session")
def db_engine(pg_container):
    """Create engine and schema once per test session."""
    engine = create_engine(pg_container.get_connection_url())
    apply_init_extensions(engine)
    apply_zz_roles(engine)
    _install_lab_day_function(engine)
    Base.metadata.create_all(bind=engine)
    _install_access_functions(engine)
    _seed_instrument_tracking_lists(engine)
    # Commit UTC so parallel connections see it. db_session also upserts
    # UTC inside the test transaction because some tests commit a delete
    # of this row (test_load_parallel) and later tests must still have a zone.
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO lab_settings (id, timezone) "
                "VALUES ('b1a16ae0-0000-4000-8000-000000000001', 'UTC') "
                "ON CONFLICT (id) DO UPDATE SET timezone = 'UTC'"
            )
        )
    yield engine
    # Drop via raw SQL to avoid CircularDependencyError from clients↔roles↔users FKs
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()


@pytest.fixture(scope="session")
def migrated_pg_container():
    """Dedicated PostgreSQL 15 container for migration-based RLS tests.

    A separate container from pg_container is required because db_engine uses
    Base.metadata.create_all() (no migrations) while migrated_engine needs the
    real Alembic chain. Sharing one container would create schema conflicts.
    """
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        yield pg


@pytest.fixture(scope="session")
def migrated_engine(migrated_pg_container):
    """Engine with the Alembic chain run as non-superuser ``lims_migrate``.

    Roles match ``db/zz-roles.sh``. The privilege snapshot runs after upgrade
    and fails the session if ``lims_app`` is a superuser or bypasses RLS.

    ``app_test_role`` is created so tests can enforce RLS. Superusers and
    ``BYPASSRLS`` roles skip policies even with FORCE ROW LEVEL SECURITY.
    """
    from alembic import command
    from alembic.config import Config

    engine = create_engine(migrated_pg_container.get_connection_url())

    # Same order as Compose: init.sql extensions, zz-roles.sh, then Alembic
    # as non-superuser lims_migrate. CI uses this fixture; no extra job.
    apply_init_extensions(engine)
    apply_zz_roles(
        engine,
        migrate_password=TEST_MIGRATE_PASSWORD,
        app_password=TEST_APP_PASSWORD,
    )
    migrate_url = migrate_database_url(engine, TEST_MIGRATE_PASSWORD)

    # env.py reads MIGRATE_DATABASE_URL. Alembic must use lims_migrate, not
    # the bootstrap superuser. DATABASE_URL is pointed at the same URL so a
    # migration that also reads it stays on this testcontainer.
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = migrate_url
    os.environ["MIGRATE_DATABASE_URL"] = migrate_url
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", migrate_url)
        command.upgrade(alembic_cfg, "head")
    finally:
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate

    run_privilege_snapshot(engine)

    # Create a non-superuser role so RLS is actually enforced.
    # Superusers and roles with BYPASSRLS skip RLS even with FORCE ROW LEVEL SECURITY.
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE ROLE app_test_role NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN PASSWORD 'test'"
        ))
        conn.execute(text("GRANT CONNECT ON DATABASE postgres TO app_test_role"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO app_test_role"))
        conn.execute(text(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_test_role"
        ))
        conn.execute(text(
            "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_test_role"
        ))
        conn.execute(text(
            "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_test_role"
        ))
        conn.execute(text(
            "ALTER DEFAULT PRIVILEGES FOR ROLE lims_migrate IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_test_role"
        ))
        conn.commit()

    yield engine

    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()


@pytest.fixture(autouse=True)
def _reset_published_lab_zone():
    """Date validators read a process-wide zone. Each test starts without one."""
    from app.core.lab_time import clear_published_lab_zone

    clear_published_lab_zone()
    yield
    clear_published_lab_zone()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Wrap each test in a transaction that is rolled back on teardown."""
    connection = db_engine.connect()
    transaction = connection.begin()
    # create_savepoint: app/fixture session.commit() only releases a SAVEPOINT,
    # so nothing a test does can escape the outer transaction rolled back below.
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection,
        join_transaction_mode="create_savepoint",
    )
    session = TestingSessionLocal()
    _ensure_test_lab_timezone(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def _ensure_test_lab_timezone(session) -> None:
    """Tests that use the API client set UTC explicitly. There is no fallback.

    A SELECT here begins the fixture transaction. Tests that check
    idle-in-transaction must not request db_session or client.
    """
    from models.lab_setting import LAB_SETTINGS_ID, LabSetting

    row = session.query(LabSetting).filter(LabSetting.id == LAB_SETTINGS_ID).first()
    if row is None:
        session.add(LabSetting(id=LAB_SETTINGS_ID, timezone="UTC"))
    elif not (row.timezone or "").strip():
        row.timezone = "UTC"
    session.flush()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with DB session override."""
    def override_get_db():
        from app.core.lab_time import publish_lab_zone

        publish_lab_zone(db_session)
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _get_or_create(session, model, name, description):
    """Fetch a Role/Permission by unique name or create it.

    Several fixtures (test_user, test_admin_user, client_user_token) share
    permission names; requesting more than one in a test used to raise
    UniqueViolation on permissions_name_key.
    """
    obj = session.query(model).filter(model.name == name).one_or_none()
    if obj is None:
        obj = model(name=name, description=description)
        session.add(obj)
        session.flush()
    return obj


def _grant(session, role, perms):
    for perm in perms:
        exists = session.execute(
            role_permissions.select().where(
                role_permissions.c.role_id == role.id,
                role_permissions.c.permission_id == perm.id,
            )
        ).first()
        if not exists:
            session.execute(role_permissions.insert().values(role_id=role.id, permission_id=perm.id))


@pytest.fixture(scope="function")
def test_org(db_session):
    """Create a test client org (required FK on User.client_id)."""
    org = Client(name="Test Lab")
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture(scope="function")
def test_user(db_session, test_org):
    """Create a test user with role and permissions."""
    test_role = _get_or_create(db_session, Role, "test_role", "Test role for authentication")
    permissions = [
        _get_or_create(db_session, Permission, "sample:create", "Create samples"),
        _get_or_create(db_session, Permission, "sample:read", "Read samples"),
        _get_or_create(db_session, Permission, "result:enter", "Enter results"),
    ]
    _grant(db_session, test_role, permissions)

    user = User(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        role_id=test_role.id,
        client_id=test_org.id,
        must_change_password=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session, test_org):
    """Create a test admin user with all permissions."""
    admin_role = _get_or_create(db_session, Role, "Administrator", "Administrator role")

    all_permissions = [
        "sample:create", "sample:read", "sample:update", "sample:delete",
        "test:assign", "test:update", "result:enter", "result:review", "result:read",
        "batch:manage", "batch:read", "batch:update", "batch:delete",
        "result:update", "result:delete",
        "project:manage", "project:read",
        "user:manage", "config:edit", "schema:edit", "layout:edit",
        "workflow:execute", "experiment:manage",
        "experiment:publish",
    ]
    permissions = [
        _get_or_create(db_session, Permission, perm_name, f"Permission: {perm_name}")
        for perm_name in all_permissions
    ]
    _grant(db_session, admin_role, permissions)

    admin_user = User(
        name="Admin User",
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword"),
        role_id=admin_role.id,
        client_id=test_org.id,
        must_change_password=False,
    )
    db_session.add(admin_user)
    db_session.commit()
    return admin_user


@pytest.fixture(scope="function")
def admin_token(test_admin_user, db_session):
    """Create a JWT token for admin user."""
    from app.core.security import create_access_token

    permissions = (
        db_session.query(Permission)
        .join(role_permissions, Permission.id == role_permissions.c.permission_id)
        .filter(role_permissions.c.role_id == test_admin_user.role_id)
        .all()
    )
    perm_names = [p.name for p in permissions]
    token_data = {
        "sub": str(test_admin_user.id),
        "username": test_admin_user.username,
        "role": "Administrator",
        "permissions": perm_names,
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
def client_user_token(db_session, test_org):
    """Create a JWT token for a client user."""
    from app.core.security import create_access_token

    client_role = _get_or_create(db_session, Role, "Client", "Client user role")
    client_permissions = [
        _get_or_create(db_session, Permission, "sample:read", "Read samples"),
        _get_or_create(db_session, Permission, "result:read", "Read results"),
        _get_or_create(db_session, Permission, "project:read", "Read projects"),
    ]
    _grant(db_session, client_role, client_permissions)

    client_user = User(
        name="Client User",
        username="client_user",
        email="client@example.com",
        password_hash=get_password_hash("clientpass123"),
        role_id=client_role.id,
        client_id=test_org.id,
    )
    db_session.add(client_user)
    db_session.commit()

    perm_names = [p.name for p in client_permissions]
    token_data = {
        "sub": str(client_user.id),
        "username": client_user.username,
        "role": "Client",
        "permissions": perm_names,
    }
    return create_access_token(token_data)


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for ``db_session`` used by older test modules (e.g. test_help)."""
    return db_session


# ── Shared LimsRun fixtures (LimsRunCreate requires analysis_id; start requires a cohort) ──

@pytest.fixture
def run_analysis_id(db_session, test_admin_user):
    """LimsRunCreate requires analysis_id (import + promote target)."""
    from uuid import uuid4
    from models.analysis import Analysis, Analyte, AnalysisAnalyte

    a = Analysis(
        name=f"An {uuid4().hex[:6]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    # Publish promotes data -> results and refuses an analysis with no active analytes.
    an = Analyte(
        name=f"viability_pct_{uuid4().hex[:4]}",
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add_all([a, an])
    db_session.flush()
    db_session.add(AnalysisAnalyte(analysis_id=a.id, analyte_id=an.id))
    db_session.flush()
    return str(a.id)


@pytest.fixture
def cohort_sample_id(db_session, test_admin_user, test_org):
    """Starting a run requires a sample cohort; create one available sample."""
    from datetime import datetime, timedelta
    from uuid import uuid4
    from models.list import List, ListEntry
    from models.project import Project
    from models.sample import Sample

    lst = List(name=f"fx_{uuid4().hex[:6]}")
    db_session.add(lst)
    db_session.flush()
    avail = ListEntry(list_id=lst.id, name=f"Available {uuid4().hex[:4]}")
    st = ListEntry(list_id=lst.id, name=f"t_{uuid4().hex[:4]}")
    mx = ListEntry(list_id=lst.id, name=f"m_{uuid4().hex[:4]}")
    db_session.add_all([avail, st, mx])
    # Starting a run creates tests for the cohort with an "Assigned/Pending" status.
    if not db_session.query(ListEntry).filter(ListEntry.name == "Assigned/Pending").first():
        ts = List(name=f"Test Status {uuid4().hex[:4]}")
        db_session.add(ts)
        db_session.flush()
        db_session.add(ListEntry(list_id=ts.id, name="Assigned/Pending"))
    db_session.flush()
    project = Project(
        name=f"P {uuid4().hex[:6]}",
        client_id=test_org.id,
        status=avail.id,
        start_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=7),
    )
    db_session.add(project)
    db_session.flush()
    sample = Sample(
        name=f"S {uuid4().hex[:6]}",
        sample_type=st.id,
        status=avail.id,
        matrix=mx.id,
        project_id=project.id,
        created_by=test_admin_user.id,
        modified_by=test_admin_user.id,
    )
    db_session.add(sample)
    db_session.commit()
    return str(sample.id)


@pytest.fixture(scope="function")
def system_org(db_session):
    """The System client (lab employees). Users on it get org-wide project access
    (app.core.rbac.SYSTEM_CLIENT_ID); migrations seed it in a real DB."""
    from app.core.rbac import SYSTEM_CLIENT_ID

    org = db_session.get(Client, SYSTEM_CLIENT_ID)
    if org is None:
        org = Client(id=SYSTEM_CLIENT_ID, name="System")
        db_session.add(org)
        db_session.flush()
    return org
