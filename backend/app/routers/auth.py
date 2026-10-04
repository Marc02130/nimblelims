"""
Authentication router for NimbleLims
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetConfirmRequest,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    needs_rehash,
    validate_password_complexity,
    bump_password_epoch,
    create_access_token,
    get_user_permissions,
    set_current_user_id,
    get_current_user,
    require_csrf_for_cookie_auth,
)
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.auth_cookies import (
    set_auth_cookies,
    clear_auth_cookies,
    get_access_token_from_cookie,
)

router = APIRouter()


def _issue_token(user: User, permissions: list, *, must_change: bool) -> str:
    return create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.name,
            "permissions": permissions,
            "pwd_change": must_change,
            "pwd_epoch": int(getattr(user, "password_epoch", 0) or 0),
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT token with permissions.
    May set must_change_password and issue a constrained token (Q7).
    S15: Postgres-backed lockout after repeated failures.
    """
    import logging
    from app.services.login_throttle import LoginThrottleService

    logger = logging.getLogger(__name__)
    throttle = LoginThrottleService(db)

    # Fail closed if locked (before password check)
    throttle.check_allowed(login_data.username)

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
        locked = throttle.record_failure(login_data.username)
        db.commit()
        if locked:
            throttle.check_allowed(login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_data.password, user.password_hash):
        logger.warning("Password verification failed for user: %s", login_data.username)
        locked = throttle.record_failure(login_data.username)
        db.commit()
        if locked:
            throttle.check_allowed(login_data.username)
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

    throttle.record_success(login_data.username)

    permissions = get_user_permissions(user, db)
    must_change = bool(getattr(user, "must_change_password", False))
    access_token = _issue_token(user, permissions, must_change=must_change)

    user.last_login = func.now()
    db.commit()

    set_current_user_id(
        str(user.id),
        db,
        client_id=str(user.client_id) if user.client_id else None,
    )

    # P4 / S10: httpOnly access + double-submit CSRF cookies for SPA
    set_auth_cookies(response, access_token)

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
    request: Request,
    response: Response,
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

    # Revoke the presenting token so prior Bearer/cookie JWT cannot linger
    from app.services.token_revoke import revoke_raw_jwt
    from fastapi.security.utils import get_authorization_scheme_param

    presenting = get_access_token_from_cookie(request)
    if not presenting:
        auth = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth)
        if scheme.lower() == "bearer" and param:
            presenting = param
    if presenting:
        revoke_raw_jwt(db, presenting)

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.must_change_password = False
    bump_password_epoch(current_user)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    permissions = get_user_permissions(current_user, db)
    token = _issue_token(current_user, permissions, must_change=False)
    set_auth_cookies(response, token)

    return ChangePasswordResponse(
        access_token=token,
        must_change_password=False,
        message="Password updated",
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Revoke current JWT (jti denylist) and clear auth cookies.
    Cookie sessions require CSRF; Bearer logout skips CSRF.
    """
    from app.services.token_revoke import revoke_raw_jwt
    from fastapi.security.utils import get_authorization_scheme_param

    cookie_token = get_access_token_from_cookie(request)
    bearer_token = None
    auth = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(auth)
    if scheme.lower() == "bearer" and param:
        bearer_token = param

    if cookie_token and not bearer_token:
        require_csrf_for_cookie_auth(request, "cookie")

    for tok in (cookie_token, bearer_token):
        if tok:
            revoke_raw_jwt(db, tok)

    clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information (cookie or Bearer).
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
    Verify user email address (stub).

    S13: do not leak whether the email exists. Production disables the stub.
    """
    from app.core.config import ENVIRONMENT

    if ENVIRONMENT in ("production", "prod"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Email verification is not configured",
        )

    # Always same response shape — no user-existence oracle
    _ = db.query(User).filter(User.email == verify_data.email).first()
    return VerifyEmailResponse(
        message="If an account exists for that email, verification instructions apply",
        verified=True,
    )


@router.post("/password-reset", response_model=PasswordResetResponse)
def password_reset_request(
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Email a one-time reset link. No login required.

    The response is the same whether or not an account exists. When mail is not
    configured, every caller gets the same unavailable response and no lookup.
    """
    from app.services import password_reset as reset_service

    if not reset_service.email_reset_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=reset_service.NOT_CONFIGURED_MESSAGE,
        )
    reset_service.request_password_reset(db, str(body.email))
    return PasswordResetResponse(message=reset_service.generic_message())


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def password_reset_confirm(
    body: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
):
    """Set a new password from the emailed token. Does not start a session."""
    from app.services import password_reset as reset_service

    reset_service.confirm_password_reset(db, body.token, body.new_password)
    db.commit()
    return PasswordResetResponse(message=reset_service.CONFIRM_MESSAGE)
