"""Saved formulas, analysis version snapshots (S7), activation records (S8), and
calculation attempts (S9)."""
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
    """A test case's outcome on one lock hash, written by the stage runner (S9).

    ``outcome`` holds what the run produced and each expected key that did not
    match. The database refuses an update, a delete, and an actor that is not
    the signed-in user.
    """

    __tablename__ = "calculation_test_case_results"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_case_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("calculation_test_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lock_hash = Column(String(64), nullable=False)
    passed = Column(Boolean, nullable=False)
    outcome = Column(JSONB(none_as_null=True), nullable=True)
    built_image_digest = Column(String(71), nullable=True)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))


class CalculationDryRun(Base):
    """A dry run of a configuration on example data, written by the stage runner (S9).

    It writes nothing to a result entry or a result table. ``outcome`` is what
    the stages produced on ``input``.
    """

    __tablename__ = "calculation_dry_runs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    analyte_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    configuration_version = Column(Integer, nullable=False)
    input = Column(JSONB, nullable=False)
    outcome = Column(JSONB(none_as_null=True), nullable=True)
    lock_hash = Column(String(64), nullable=True)
    built_image_digest = Column(String(71), nullable=True)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))


class CalculationAttempt(Base):
    """One accepted calculation of a result-entry row (CALC-REQ-30, OQ-CALC-25 default).

    The provenance lives here and is linked from the row
    (``result_entries.calculation_attempt_id``); it is not copied onto row
    columns. ``status`` is ``completed`` or ``stopped``. A stop has a
    ``stop_code`` (a stage stop, CALC-REQ-25) or the Excel text of a
    lab-written formula error (``formula_error``), never both, and clears
    calculated and reported. ``run_summary`` is ``pass``, ``fail``, or
    ``stopped`` with the check that produced it (CALC-REQ-21). The database
    refuses an update, a delete, an actor that is not the signed-in user, and
    a Test, analyte, run, or analysis that is not the row's.
    """

    __tablename__ = "calculation_attempts"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_entry_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("result_entries.id", ondelete="RESTRICT"), nullable=False
    )
    test_id = Column(PostgresUUID(as_uuid=True), ForeignKey("tests.id", ondelete="RESTRICT"), nullable=False)
    analyte_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analytes.id", ondelete="RESTRICT"), nullable=False
    )
    lims_run_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("lims_runs.id", ondelete="RESTRICT"), nullable=False
    )
    analysis_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analyses.id", ondelete="RESTRICT"), nullable=False
    )
    status = Column(String(16), nullable=False)
    stop_code = Column(String(64), nullable=True)
    stop_stage = Column(String(40), nullable=True)
    stop_detail = Column(Text, nullable=True)
    formula_error = Column(String(16), nullable=True)
    run_summary = Column(String(16), nullable=False)
    summary_check = Column(String(40), nullable=True)
    summary_code = Column(String(64), nullable=True)
    lock_hash = Column(String(64), nullable=False)
    built_image_digest = Column(String(71), nullable=False)
    configuration_name = Column(String(100), nullable=False)
    configuration_version = Column(Integer, nullable=False)
    analysis_version = Column(Integer, nullable=False)
    function_versions = Column(JSONB, nullable=False, default=list)
    formula_versions = Column(JSONB, nullable=False, default=list)
    inputs_read = Column(JSONB, nullable=False, default=list)
    values_used = Column(JSONB, nullable=False, default=list)
    knocked_out_points = Column(JSONB, nullable=False, default=list)
    flags = Column(JSONB, nullable=False, default=list)
    stages = Column(JSONB, nullable=False, default=list)
    calculated_result = Column(String(255), nullable=True)
    reported_result = Column(String(255), nullable=True)
    result_note = Column(JSONB(none_as_null=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
