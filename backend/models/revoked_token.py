"""JWT jti denylist (P4 / S10 residual — logout revocation)."""
from datetime import datetime

from sqlalchemy import Column, DateTime, String, func

from models.base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True, nullable=False)
    revoked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
