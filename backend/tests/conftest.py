"""
Pytest configuration and fixtures.
Uses testcontainers-python (PostgreSQL 15) to prevent SQLite/JSONB divergence.
"""
import os

# S3: allow tests to import app.core.config before any other imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-for-production")
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.database import get_db
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
        conn.commit()


@pytest.fixture(scope="session")
def db_engine(pg_container):
    """Create engine and schema once per test session."""
    engine = create_engine(pg_container.get_connection_url())
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    _install_access_functions(engine)
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
    """Engine with full Alembic migration chain applied (RLS policies active).

    Unlike db_engine (which uses Base.metadata.create_all and skips migrations),
    this fixture runs the real Alembic upgrade so RLS policies, SECURITY DEFINER
    functions, and FORCE ROW LEVEL SECURITY are all in effect.

    A non-superuser role (app_test_role) is created so that RLS is enforced on
    queries — PostgreSQL superusers bypass RLS regardless of FORCE settings.
    Tests must SET ROLE app_test_role before querying to activate enforcement.
    """
    from alembic import command
    from alembic.config import Config

    url = migrated_pg_container.get_connection_url()
    engine = create_engine(url)

    # Migration 0003 GRANTs privileges to lims_user. Create it in the testcontainer
    # before running migrations so the GRANTs don't fail with "role does not exist".
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE ROLE lims_user NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN PASSWORD 'lims_password'"
        ))
        # start.sh creates this before Alembic. 0083 GRANTs to it with no IF EXISTS.
        conn.execute(text(
            "CREATE ROLE lims_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN PASSWORD 'lims_app_password'"
        ))
        conn.commit()

    # env.py reads DATABASE_URL env var instead of config.get_main_option("sqlalchemy.url").
    # Override it here so Alembic migrations hit the testcontainer, not the Docker DB.
    # Use try/finally so DATABASE_URL is always cleared even if upgrade() raises.
    os.environ["DATABASE_URL"] = url
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(alembic_cfg, "head")
    finally:
        os.environ.pop("DATABASE_URL", None)

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
        conn.commit()

    yield engine

    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()


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

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with DB session override."""
    def override_get_db():
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
