"""Saved formulas and analysis version snapshots (calculations S7)."""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.sql import func

from .base import Base


class CalculationFormula(Base):
    """A saved formula, pinned by name and version (CALC-REQ-23, CALC-REQ-40).

    A row is never updated or deleted by the application role. A changed
    formula is a new version row.
    """

    __tablename__ = "calculation_formulas"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False)
    formula_text = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))


class AnalysisVersion(Base):
    """The state of an analysis at one version. Written by a database trigger."""

    __tablename__ = "analysis_versions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
