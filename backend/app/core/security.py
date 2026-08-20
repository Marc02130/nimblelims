"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import hashlib
import re
import bcrypt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from app.database import get_db
from models.user import User, Role, Permission
from app.schemas.auth import TokenData
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Paths allowed while must_change_password is set (Q7)
_PASSWORD_CHANGE_ALLOWLIST = frozenset(
    {
        "/auth/change-password",
        "/auth/me",
        "/auth/logout",
    }
)

_PASSWORD_MIN_LENGTH = 12


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _is_bcrypt_hash(hashed_password: str) -> bool:
    return hashed_password.startswith(("$2a$", "$2b$", "$2y$"))


def _is_legacy_sha256_hash(hashed_password: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", hashed_password or ""))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against bcrypt or legacy unsalted SHA256."""
    if not hashed_password:
        return False
    if _is_bcrypt_hash(hashed_password):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False
    if _is_legacy_sha256_hash(hashed_password):
        digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return digest == hashed_password
    return False


def needs_rehash(hashed_password: str) -> bool:
    """True when stored hash should be upgraded to bcrypt on next successful login."""
    return _is_legacy_sha256_hash(hashed_password)


def validate_password_complexity(
    password: str,
    *,
    username: str,
    current_password: Optional[str] = None,
) -> List[str]:
    """
    Return a list of failed rule messages; empty list means OK (Q7).
    """
    errors: List[str] = []
    if len(password) < _PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {_PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must include an uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must include a lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("Password must include a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include a symbol")
    if username and password.lower() == username.lower():
        errors.append("Password must not match the username")
    if current_password is not None and password == current_password:
        errors.append("Password must not match the current password")
    return errors


# JWT Bearer token
security = HTTPBearer()

# Define the core permissions for NimbleLims
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
    "config:edit",
    "workflow:execute",
    "experiment:manage",
    "experiment:publish",
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
        must_change = bool(payload.get("pwd_change") or payload.get("must_change_password"))

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
            permissions=permissions,
            must_change_password=must_change,
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _path_allowed_during_password_change(path: str) -> bool:
    normalized = path.rstrip("/") or "/"
    if normalized in _PASSWORD_CHANGE_ALLOWLIST:
        return True
    # Tolerate optional API prefixes
    for allowed in _PASSWORD_CHANGE_ALLOWLIST:
        if normalized.endswith(allowed):
            return True
    return False


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user; enforce must-change-password gate."""
    token = credentials.credentials
    token_data = verify_token(token)

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == token_data.user_id)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    set_current_user_id(str(user.id), db)

    must_change = bool(getattr(user, "must_change_password", False)) or token_data.must_change_password
    if must_change and not _path_allowed_during_password_change(request.url.path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "password_change_required",
                "message": "Password change required before continuing",
            },
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
        db: Session = Depends(get_db),
    ):
        user_permissions = get_user_permissions(current_user, db)
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user

    return permission_checker


def set_current_user_id(user_id: str, db: Session):
    """Set current user ID in database session for RLS"""
    # Use SET (session-level) not SET LOCAL (transaction-level)
    db.execute(text(f"SET app.current_user_id = '{user_id}'"))
    db.flush()
