"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import tempfile

from app.main import app
from app.database import get_db, Base
from app.models.user import User, Role, Permission, RolePermission
from app.core.security import get_password_hash

# Test database URL (in-memory SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database session"""
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
    """Create a test user with role and permissions"""
    # Create test role
    test_role = Role(
        name="test_role",
        description="Test role for authentication"
    )
    db_session.add(test_role)
    db_session.flush()
    
    # Create test permissions
    permissions = [
        Permission(name="sample:create", description="Create samples"),
        Permission(name="sample:read", description="Read samples"),
        Permission(name="result:enter", description="Enter results"),
    ]
    
    for perm in permissions:
        db_session.add(perm)
    db_session.flush()
    
    # Assign permissions to role
    for perm in permissions:
        role_perm = RolePermission(role_id=test_role.id, permission_id=perm.id)
        db_session.add(role_perm)
    
    # Create test user
    test_user = User(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        role_id=test_role.id
    )
    db_session.add(test_user)
    db_session.commit()
    
    return test_user

@pytest.fixture(scope="function")
def test_admin_user(db_session):
    """Create a test admin user with all permissions"""
    # Create admin role
    admin_role = Role(
        name="admin",
        description="Administrator role"
    )
    db_session.add(admin_role)
    db_session.flush()
    
    # Create all permissions
    all_permissions = [
        "sample:create", "sample:read", "sample:update", "sample:delete",
        "test:assign", "test:update", "result:enter", "result:review", "result:read",
        "batch:manage", "batch:read", "project:manage", "project:read",
        "user:manage", "config:edit"
    ]
    
    permissions = []
    for perm_name in all_permissions:
        perm = Permission(name=perm_name, description=f"Permission: {perm_name}")
        db_session.add(perm)
        permissions.append(perm)
    db_session.flush()
    
    # Assign all permissions to admin role
    for perm in permissions:
        role_perm = RolePermission(role_id=admin_role.id, permission_id=perm.id)
        db_session.add(role_perm)
    
    # Create admin user
    admin_user = User(
        name="Admin User",
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword"),
        role_id=admin_role.id
    )
    db_session.add(admin_user)
    db_session.commit()
    
    return admin_user
