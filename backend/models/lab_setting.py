"""One row for the lab's clock. There is no per-client timezone."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.sql import func

from .base import Base

# Fixed id so the migration and the app share one row.
LAB_SETTINGS_ID = uuid.UUID("b1a16ae0-0000-4000-8000-000000000001")


class LabSetting(Base):
    __tablename__ = "lab_settings"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timezone = Column(String(64), nullable=True)
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modified_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
