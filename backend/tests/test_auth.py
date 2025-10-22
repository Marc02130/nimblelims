"""
Tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import create_access_token, verify_token, get_password_hash
from app.schemas.auth import TokenData

class TestLogin:
    """Test login endpoint"""
    
    def test_login_success(self, client: TestClient, test_user):
        """Test successful login"""
        response = client.post(
            "/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "test_role"
        assert "sample:create" in data["permissions"]
        assert "sample:read" in data["permissions"]
        assert "result:enter" in data["permissions"]
    
    def test_login_invalid_username(self, client: TestClient):
        """Test login with invalid username"""
        response = client.post(
            "/auth/login",
            json={
                "username": "nonexistent",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, client: TestClient, test_user):
        """Test login with invalid password"""
        response = client.post(
            "/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, db_session: Session, test_user):
        """Test login with inactive user"""
        # Deactivate user
        test_user.active = False
        db_session.commit()
        
        response = client.post(
            "/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 401
        assert "User account is inactive" in response.json()["detail"]

class TestEmailVerification:
    """Test email verification endpoint"""
    
    def test_verify_email_success(self, client: TestClient, test_user):
        """Test successful email verification"""
        response = client.post(
            "/auth/verify-email",
            json={
                "email": "test@example.com",
                "token": "dummy_token"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email verification successful"
        assert data["verified"] is True
    
    def test_verify_email_user_not_found(self, client: TestClient):
        """Test email verification with non-existent user"""
        response = client.post(
            "/auth/verify-email",
            json={
                "email": "nonexistent@example.com",
                "token": "dummy_token"
            }
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

class TestJWTToken:
    """Test JWT token functionality"""
    
    def test_create_and_verify_token(self):
        """Test token creation and verification"""
        # Create token
        token_data = {
            "sub": "test_user_id",
            "username": "testuser",
            "role": "test_role",
            "permissions": ["sample:create", "sample:read"]
        }
        
        token = create_access_token(data=token_data)
        assert token is not None
        
        # Verify token
        verified_data = verify_token(token)
        assert verified_data.user_id == "test_user_id"
        assert verified_data.username == "testuser"
        assert verified_data.role == "test_role"
        assert "sample:create" in verified_data.permissions
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        with pytest.raises(Exception):  # Should raise HTTPException
            verify_token("invalid_token")
    
    def test_verify_expired_token(self):
        """Test verification of expired token"""
        from datetime import datetime, timedelta
        import jwt
        from app.core.config import SECRET_KEY, ALGORITHM
        
        # Create expired token
        expired_data = {
            "sub": "test_user_id",
            "username": "testuser",
            "role": "test_role",
            "permissions": ["sample:create"],
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        
        expired_token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)
        
        with pytest.raises(Exception):  # Should raise HTTPException
            verify_token(expired_token)

class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_password_hash(self):
        """Test password hashing"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format
    
    def test_password_verification(self):
        """Test password verification"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        from app.core.security import verify_password
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

class TestPermissions:
    """Test permission system"""
    
    def test_admin_user_permissions(self, client: TestClient, test_admin_user):
        """Test admin user has all permissions"""
        response = client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "adminpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that admin has all core permissions
        permissions = data["permissions"]
        expected_permissions = [
            "sample:create", "sample:read", "sample:update", "sample:delete",
            "test:assign", "test:update", "result:enter", "result:review", "result:read",
            "batch:manage", "batch:read", "project:manage", "project:read",
            "user:manage", "config:edit"
        ]
        
        for perm in expected_permissions:
            assert perm in permissions
