"""
Pytest configuration and fixtures.
Uses testcontainers-python (PostgreSQL 15) to prevent SQLite/JSONB divergence.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.main import app
from app.database import get_db
from models.base import Base
from models.user import User, Role, Permission, RolePermission
from app.core.security import get_password_hash

# Import all models so Base.metadata is fully populated
import models  # noqa: F401


POSTGRES_IMAGE = "postgres:15"


@pytest.fixture(scope="session")
def pg_container():
    """Start a PostgreSQL 15 container once per test session."""
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        yield pg


@pytest.fixture(scope="session")
def db_engine(pg_container):
    """Create engine and schema once per test session."""
    engine = create_engine(pg_container.get_connection_url())
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Wrap each test in a transaction that is rolled back on teardown."""
    connection = db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
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


@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user with role and permissions."""
    test_role = Role(name="test_role", description="Test role for authentication")
    db_session.add(test_role)
    db_session.flush()

    permissions = [
        Permission(name="sample:create", description="Create samples"),
        Permission(name="sample:read", description="Read samples"),
        Permission(name="result:enter", description="Enter results"),
    ]
    for perm in permissions:
        db_session.add(perm)
    db_session.flush()

    for perm in permissions:
        db_session.add(RolePermission(role_id=test_role.id, permission_id=perm.id))

    user = User(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        role_id=test_role.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session):
    """Create a test admin user with all permissions."""
    admin_role = Role(name="Administrator", description="Administrator role")
    db_session.add(admin_role)
    db_session.flush()

    all_permissions = [
        "sample:create", "sample:read", "sample:update", "sample:delete",
        "test:assign", "test:update", "result:enter", "result:review", "result:read",
        "batch:manage", "batch:read", "project:manage", "project:read",
        "user:manage", "config:edit", "workflow:execute", "experiment:manage",
        "experiment:publish",
    ]
    permissions = []
    for perm_name in all_permissions:
        perm = Permission(name=perm_name, description=f"Permission: {perm_name}")
        db_session.add(perm)
        permissions.append(perm)
    db_session.flush()

    for perm in permissions:
        db_session.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

    admin_user = User(
        name="Admin User",
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword"),
        role_id=admin_role.id,
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
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .filter(RolePermission.role_id == test_admin_user.role_id)
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
def client_user_token(db_session):
    """Create a JWT token for a client user."""
    from app.core.security import create_access_token

    client_role = Role(name="Client", description="Client user role")
    db_session.add(client_role)
    db_session.flush()

    client_permissions = [
        Permission(name="sample:read", description="Read samples"),
        Permission(name="result:read", description="Read results"),
        Permission(name="project:read", description="Read projects"),
    ]
    for perm in client_permissions:
        db_session.add(perm)
    db_session.flush()

    for perm in client_permissions:
        db_session.add(RolePermission(role_id=client_role.id, permission_id=perm.id))

    client_user = User(
        name="Client User",
        username="client_user",
        email="client@example.com",
        password_hash=get_password_hash("clientpass123"),
        role_id=client_role.id,
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
