"""
Authentication router for NimbleLims
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    needs_rehash,
    validate_password_complexity,
    create_access_token,
    get_user_permissions,
    set_current_user_id,
    get_current_user,
)
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


def _issue_token(user: User, permissions: list, *, must_change: bool) -> str:
    return create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.name,
            "permissions": permissions,
            "pwd_change": must_change,
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT token with permissions.
    May set must_change_password and issue a constrained token (Q7).
    """
    import logging
    logger = logging.getLogger(__name__)

    user_count = db.query(User).count()
    if user_count == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No users found in database. Run: docker exec lims-backend python run_migrations.py",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.username == login_data.username)
        .first()
    )

    if not user:
        logger.warning("User not found: %s", login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_data.password, user.password_hash):
        logger.warning("Password verification failed for user: %s", login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        logger.warning("Inactive user attempted login: %s", login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    # Upgrade legacy SHA256 hashes to bcrypt on successful login (S2)
    if needs_rehash(user.password_hash):
        user.password_hash = get_password_hash(login_data.password)

    permissions = get_user_permissions(user, db)
    must_change = bool(getattr(user, "must_change_password", False))
    access_token = _issue_token(user, permissions, must_change=must_change)

    user.last_login = func.now()
    db.commit()

    set_current_user_id(str(user.id), db)

    return LoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role.name,
        permissions=permissions,
        must_change_password=must_change,
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password; clears must_change_password when successful (Q7)."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    errors = validate_password_complexity(
        body.new_password,
        username=current_user.username,
        current_password=body.current_password,
    )
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "password_complexity", "errors": errors},
        )

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    permissions = get_user_permissions(current_user, db)
    token = _issue_token(current_user, permissions, must_change=False)

    return ChangePasswordResponse(
        access_token=token,
        must_change_password=False,
        message="Password updated",
    )


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information
    """
    permissions = get_user_permissions(current_user, db)

    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.name,
        "permissions": permissions,
        "client_id": str(current_user.client_id) if current_user.client_id else None,
        "must_change_password": bool(getattr(current_user, "must_change_password", False)),
    }


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """
    Verify user email address (stub implementation)
    """
    user = db.query(User).filter(User.email == verify_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return VerifyEmailResponse(
        message="Email verification successful",
        verified=True,
    )
