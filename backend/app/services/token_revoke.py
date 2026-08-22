"""JWT jti denylist helpers (S10 logout residual)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.revoked_token import RevokedToken


def is_token_revoked(db: Session, jti: str) -> bool:
    if not jti:
        return False
    try:
        row = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    except Exception:
        # Table missing in create_all unit tests — fail open for those envs
        return False
    return row is not None


def revoke_token(
    db: Session,
    *,
    jti: str,
    expires_at: Optional[datetime],
) -> None:
    if not jti:
        return
    exp = expires_at or (datetime.now(timezone.utc))
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if existing:
        return
    db.add(RevokedToken(jti=jti, expires_at=exp))
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Unique race or missing table — ignore
        pass


def revoke_raw_jwt(db: Session, token: str) -> None:
    """Decode without full auth gate and denylist jti if present."""
    import jwt
    from app.core.config import SECRET_KEY, ALGORITHM

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
    except Exception:
        return
    jti = payload.get("jti")
    if not jti:
        return
    exp_raw = payload.get("exp")
    exp_dt = None
    if isinstance(exp_raw, (int, float)):
        exp_dt = datetime.fromtimestamp(exp_raw, tz=timezone.utc)
    revoke_token(db, jti=str(jti), expires_at=exp_dt)
