"""Email a one-time password reset link. Production, not the demo-password button.

The same response is returned whether or not the address belongs to an account.
Only a hash of the token is stored. The email contains the link, never a password.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import config
from app.core.security import (
    bump_password_epoch,
    get_password_hash,
    validate_password_complexity,
    verify_password,
)
from app.services.login_throttle import LoginThrottleService
from models.password_reset_token import PasswordResetToken
from models.user import User

logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE = (
    "Password reset email is not available. Ask an administrator to set a new password."
)
INVALID_LINK_MESSAGE = "This reset link is invalid or has expired."
CONFIRM_MESSAGE = "Password updated. Sign in with your new password."


def generic_message() -> str:
    minutes = _ttl_minutes()
    return (
        "If an account exists for that email, we sent a reset link. "
        f"The link expires in {minutes} minutes and works once."
    )


def public_app_url() -> str:
    configured = (config.PUBLIC_APP_URL or "").strip().rstrip("/")
    if configured:
        return configured
    if config.ENVIRONMENT in ("development", "dev", "test"):
        return "http://localhost:3000"
    return ""


def email_reset_configured() -> bool:
    """True when a message can actually be sent. Does not look at any account."""
    host = (config.SMTP_HOST or "").strip()
    sender = (config.SMTP_FROM or "").strip()
    return bool(host and sender and public_app_url())


def reset_email_body(link: str, ttl_minutes: int) -> str:
    return (
        "Someone asked to reset the NimbleLIMS password for this address.\n\n"
        "Open this link to choose a new password. "
        f"It expires in {ttl_minutes} minutes and works once.\n\n"
        f"{link}\n\n"
        "If you did not ask for this, ignore this email. Your password stays the same.\n"
    )


def deliver_reset_email(to_address: str, link: str, ttl_minutes: int) -> None:
    """Send the link. Raises on failure. Does not log the link or the message."""
    host = (config.SMTP_HOST or "").strip()
    sender = (config.SMTP_FROM or "").strip()
    if not host or not sender:
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your NimbleLIMS password"
    message["From"] = sender
    message["To"] = to_address
    message.set_content(reset_email_body(link, ttl_minutes))

    port = int(config.SMTP_PORT or 587)
    if config.SMTP_SSL:
        client = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        client = smtplib.SMTP(host, port, timeout=20)
    try:
        if config.SMTP_TLS and not config.SMTP_SSL:
            client.starttls()
        user = (config.SMTP_USER or "").strip()
        if user:
            client.login(user, config.SMTP_PASSWORD or "")
        client.send_message(message)
    finally:
        try:
            client.quit()
        except Exception:
            pass


def request_password_reset(db: Session, email: str) -> None:
    """Create a token and send it when the address belongs to an active user.

    Unknown addresses, inactive accounts, and the hourly cap all finish quietly.
    A send failure removes the token so a down mail server does not use up the cap.
    """
    user = _active_user_for_email(db, email)
    if user is None:
        return

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=1)
    recent = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= since,
        )
        .count()
    )
    if recent >= _max_per_hour():
        logger.info("Password reset rate limited for user_id=%s", user.id)
        return

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    raw = secrets.token_urlsafe(32)
    row = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=now + timedelta(minutes=_ttl_minutes()),
        created_at=now,
    )
    db.add(row)
    db.commit()

    link = f"{public_app_url()}/reset-password#token={quote(raw, safe='')}"
    try:
        deliver_reset_email(user.email, link, _ttl_minutes())
    except Exception as exc:
        db.delete(row)
        db.commit()
        logger.warning(
            "Password reset email failed for user_id=%s (%s)",
            user.id,
            type(exc).__name__,
        )


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    """Set the password when the token is unused and unexpired. Does not sign in."""
    raw = (token or "").strip()
    if not raw or len(raw) > 512:
        _invalid()

    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash_token(raw))
        .first()
    )
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or _as_utc(row.expires_at) <= now:
        _invalid()

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None or user.active is not True:
        _invalid()

    errors = validate_password_complexity(new_password, username=user.username)
    if verify_password(new_password, user.password_hash):
        errors.append("Password must not match the current password")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "password_complexity", "errors": errors},
        )

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    bump_password_epoch(user)
    row.used_at = now
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.id != row.id,
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
    LoginThrottleService(db).record_success(user.username)
    db.add(user)
    db.add(row)
    db.flush()


def _active_user_for_email(db: Session, email: str) -> User | None:
    raw = (email or "").strip()
    if not raw:
        return None
    exact = db.query(User).filter(User.email == raw).first()
    if exact is not None:
        return exact if exact.active is True else None
    matches = (
        db.query(User)
        .filter(func.lower(User.email) == raw.lower())
        .all()
    )
    if len(matches) != 1:
        return None
    user = matches[0]
    return user if user.active is True else None


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _ttl_minutes() -> int:
    try:
        minutes = int(config.PASSWORD_RESET_TTL_MINUTES)
    except (TypeError, ValueError):
        return 60
    return minutes if minutes > 0 else 60


def _max_per_hour() -> int:
    try:
        cap = int(config.PASSWORD_RESET_MAX_PER_HOUR)
    except (TypeError, ValueError):
        return 3
    return cap if cap > 0 else 3


def _invalid() -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=INVALID_LINK_MESSAGE,
    )
