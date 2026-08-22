"""S15: login failure / lockout tracking."""
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from .base import Base


class LoginThrottle(Base):
    __tablename__ = "login_throttle"

    username_normalized = Column(String(255), primary_key=True, nullable=False)
    failure_count = Column(Integer, nullable=False, default=0, server_default="0")
    window_started_at = Column(DateTime(timezone=True), nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
