"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import hashlib
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from models.user import User, Role, Permission
from app.schemas.auth import TokenData
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Simple password hashing using SHA256 (for development only)
def get_password_hash(password: str) -> str:
    """Hash a password using SHA256 (development only)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return get_password_hash(plain_password) == hashed_password

# JWT Bearer token
security = HTTPBearer()

# Define the 15 core permissions for NimbleLims
CORE_PERMISSIONS = [
    "sample:create",
    "sample:read", 
    "sample:update",
    "sample:delete",
    "test:assign",
    "test:update",
    "result:enter",
    "result:review",
    "result:read",
    "batch:manage",
    "batch:read",
    "project:manage",
    "project:read",
    "user:manage",
    "config:edit"
]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        permissions: List[str] = payload.get("permissions", [])
        
        if user_id is None or username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    token = credentials.credentials
    token_data = verify_token(token)
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def get_user_permissions(user: User, db: Session) -> List[str]:
    """Get user permissions from their role"""
    permissions = db.query(Permission.name).join(
        Role, Permission.roles
    ).filter(Role.id == user.role_id).all()
    
    return [perm.name for perm in permissions]

def require_permission(permission: str):
    """Dependency factory for permission-based authorization"""
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        user_permissions = get_user_permissions(current_user, db)
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker

def set_current_user_id(user_id: str, db: Session):
    """Set current user ID in database session for RLS"""
    # This would be used to set the current_user_id for Row Level Security
    # Implementation depends on your RLS setup
    pass
