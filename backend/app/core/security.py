"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from uuid import UUID, uuid4
import jwt
import hashlib
import re
import secrets
import bcrypt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
from app.database import get_db, set_rls_context
from models.user import User, Role, Permission
from app.schemas.auth import TokenData
from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    CSRF_HEADER_NAME,
)
from app.core.auth_cookies import (
    get_access_token_from_cookie,
    get_csrf_from_cookie,
)

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


# JWT Bearer optional — cookie AuthN is preferred for SPA (P4 / S10)
security = HTTPBearer(auto_error=False)

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

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
    """Create a JWT access token (includes unique jti for logout denylist)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "jti": to_encode.get("jti") or str(uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, db: Optional[Session] = None) -> TokenData:
    """Verify and decode a JWT token; reject revoked jti when db is provided."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        permissions: List[str] = payload.get("permissions", [])
        must_change = bool(payload.get("pwd_change") or payload.get("must_change_password"))
        jti = payload.get("jti")
        exp_raw = payload.get("exp")
        exp_dt = None
        if isinstance(exp_raw, (int, float)):
            exp_dt = datetime.fromtimestamp(exp_raw, tz=timezone.utc)
        elif isinstance(exp_raw, datetime):
            exp_dt = exp_raw

        if user_id is None or username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if db is not None and jti:
            from app.services.token_revoke import is_token_revoked

            if is_token_revoked(db, str(jti)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions,
            must_change_password=must_change,
            jti=str(jti) if jti else None,
            exp=exp_dt,
        )
    except HTTPException:
        raise
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


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Tuple[str, str]:
    """
    Resolve JWT from Authorization Bearer (scripts/API) or httpOnly cookie (SPA).
    Returns (token, auth_via) where auth_via is "bearer" or "cookie".
    """
    if credentials and credentials.credentials:
        return credentials.credentials, "bearer"
    cookie_token = get_access_token_from_cookie(request)
    if cookie_token:
        return cookie_token, "cookie"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_csrf_for_cookie_auth(request: Request, auth_via: str) -> None:
    """
    Double-submit CSRF: cookie auth + unsafe method requires X-CSRF-Token == nimble_csrf.
    Bearer-authenticated clients skip CSRF (pytest / UAT scripts).
    """
    if auth_via != "cookie":
        return
    if request.method.upper() not in _UNSAFE_METHODS:
        return
    csrf_cookie = get_csrf_from_cookie(request)
    csrf_header = request.headers.get(CSRF_HEADER_NAME) or request.headers.get(
        CSRF_HEADER_NAME.lower()
    )
    if (
        not csrf_cookie
        or not csrf_header
        or not secrets.compare_digest(str(csrf_cookie), str(csrf_header))
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "csrf_failed",
                "message": "CSRF token missing or invalid",
            },
        )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user; enforce must-change-password gate."""
    token, auth_via = _extract_token(request, credentials)
    require_csrf_for_cookie_auth(request, auth_via)
    token_data = verify_token(token, db=db)

    # Invalid sub must be 401 (not 500 from DB UUID cast)
    try:
        user_uuid = UUID(str(token_data.user_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_uuid)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    set_current_user_id(
        str(user.id),
        db,
        client_id=str(user.client_id) if getattr(user, "client_id", None) else None,
    )

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


def set_current_user_id(user_id: str, db: Session, client_id: Optional[str] = None):
    """Set RLS GUCs for the current request (P0d — transaction-local via set_config)."""
    set_rls_context(db, user_id=user_id, client_id=client_id)
