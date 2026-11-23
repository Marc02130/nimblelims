"""Saved formulas, analysis version snapshots (S7), and activation records (S8)."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
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


class CalculationActivation(Base):
    """One append-only record of an Admin activating a configuration (CALC-REQ-35).

    ``review_document`` is the JSON the Admin was shown and ``review_hash`` is
    the SHA-256 of its RFC 8785 JCS encoding (CALC-REQ-34, CALC-REQ-45). The
    database refuses an update, a delete, and an actor that is not the
    signed-in Admin.
    """

    __tablename__ = "calculation_activations"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    configuration_name = Column(String(100), nullable=False)
    configuration_version = Column(Integer, nullable=False)
    function_versions = Column(JSONB, nullable=False)
    lock_hash = Column(String(64), nullable=False)
    validation_state = Column(String(30), nullable=False)
    review_document = Column(JSONB, nullable=False)
    review_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class CalculationConfirmToken(Base):
    """A single-use confirm token. Only the SHA-256 of the token is stored (CALC-REQ-34)."""

    __tablename__ = "calculation_confirm_tokens"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), nullable=False, unique=True)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    analysis_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    configuration_version = Column(Integer, nullable=False)
    review_hash = Column(String(64), nullable=False)
    session_jti = Column(String(128), nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)


class CalculationTestCase(Base):
    """A test case recorded against one configuration version (CALC-REQ-45 items 1 and 2)."""

    __tablename__ = "calculation_test_cases"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    configuration_version = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    inputs = Column(JSONB, nullable=False)
    expected = Column(JSONB, nullable=False)
    expected_source = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class CalculationTestCaseResult(Base):
    """A test case's outcome on one lock hash. Written by the stage runner (S9); S8 only reads it."""

    __tablename__ = "calculation_test_case_results"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("calculation_test_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lock_hash = Column(String(64), nullable=False)
    passed = Column(Boolean, nullable=False)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))


class CalculationDryRun(Base):
    """A dry run of a configuration on example data. Stores no result. Written by S9; S8 only reads it."""

    __tablename__ = "calculation_dry_runs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    configuration_version = Column(Integer, nullable=False)
    input = Column(JSONB, nullable=False)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
