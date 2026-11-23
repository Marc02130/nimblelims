"""Activating a calculation configuration (calculations S8).

CALC-REQ-34 (confirm token), CALC-REQ-35 (Admin only, append-only record),
CALC-REQ-45 (review), CALC-REQ-46 (wording), CALC-REQ-47 (the agent proposes).

The flow, all on the interactive path of a signed-in Admin:

1. ``GET .../activation-review`` returns the review document and its hash.
2. ``POST .../activation-token`` with that hash issues a single-use confirm
   token, valid for 300 seconds on the database clock.
3. ``POST .../activate`` with the token activates. The token is consumed in
   the same transaction. Any failure rolls the transaction back, so the token
   stays unconsumed.

A configuring-agent run cannot do any of this (:mod:`app.core.agent_context`).
No password is asked for (OQ-CALC-17, Spec default). The validation state is
recorded, never a gate.

This module writes no result and no calculation attempt, and runs nothing.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any, Dict, List, Mapping, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.core.agent_context import in_agent_context, refuse_in_agent_context
from app.services.calculation_config import STATE_ACTIVE, STATE_DRAFT
from app.services.calculation_config_service import (
    get_rule,
    is_lab_admin,
    lock_analysis,
    refuse,
)
from app.services.calculation_review import (
    EXPECTED_SOURCES,
    SOURCE_INDEPENDENT,
    SOURCE_SYSTEM_OUTPUT,
    build_review,
    list_case_rows,
    lock_hash_now,
    passed_on_lock,
)
from app.services.jcs import CanonicalizationError, canonical_bytes, canonical_json
from models.analysis import Analysis
from models.calculation import (
    CalculationActivation,
    CalculationConfirmToken,
    CalculationTestCase,
)
from models.user import User

ACTIVATE_SETTING = "lims.calculation_activate"
TOKEN_LIFETIME_SECONDS = 300
MAX_TEST_CASE_NAME = 200
MAX_TEST_CASE_JSON = 20000


def _check_keys(body: Any, allowed: Sequence[str], where: str) -> Mapping[str, Any]:
    if not isinstance(body, dict):
        raise refuse("request_invalid", f"{where} must be an object.")
    unknown = sorted(str(key) for key in body if key not in allowed)
    if unknown:
        raise refuse(
            "unknown_field",
            f"{where} has unknown field(s): {', '.join(unknown)}. "
            "Activation takes no password and no reason.",
        )
    return body


def _require_admin(user: User) -> None:
    """Only the Admin role activates (CALC-REQ-35). The route checks it too."""
    if not is_lab_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "admin_required",
                "message": "Only a user with the Admin role can review and activate a calculation configuration.",
            },
        )


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---- the review --------------------------------------------------------------


def read_review(db: Session, user: User, analysis_id: UUID, analyte_id: UUID) -> Dict[str, Any]:
    refuse_in_agent_context("The activation review")
    _require_admin(user)
    document, digest = build_review(db, analysis_id, analyte_id)
    return {"document": document, "review_hash": digest}


def export_review(
    db: Session, user: User, analysis_id: UUID, analyte_id: UUID
) -> tuple[bytes, str]:
    """Exactly the document the dialog shows, as canonical bytes. Runs nothing, writes nothing."""
    refuse_in_agent_context("The activation review export")
    _require_admin(user)
    document, digest = build_review(db, analysis_id, analyte_id)
    return canonical_bytes(document), digest


# ---- the confirm token -------------------------------------------------------


def issue_token(
    db: Session,
    user: User,
    session_jti: str,
    analysis_id: UUID,
    analyte_id: UUID,
    body: Any,
) -> Dict[str, Any]:
    """Issue a single-use confirm token for the review the Admin was shown."""
    refuse_in_agent_context("Issuing a confirm token")
    _require_admin(user)
    body = _check_keys(body, ("review_hash",), "The request")
    shown = body.get("review_hash")
    if not isinstance(shown, str) or not shown:
        raise refuse("review_hash_required", "review_hash is required: the hash of the review the Admin was shown.")
    rule = get_rule(db, analysis_id, analyte_id)
    document, digest = build_review(db, analysis_id, analyte_id)
    if shown != digest:
        raise refuse(
            "review_changed",
            "The configuration or its review changed after it was shown. Open the review again.",
        )
    token = secrets.token_urlsafe(32)
    db.add(
        CalculationConfirmToken(
            token_hash=token_digest(token),
            user_id=user.id,
            analysis_id=analysis_id,
            analyte_id=analyte_id,
            configuration_version=int(rule.calculation_config_version),
            review_hash=digest,
            session_jti=session_jti,
        )
    )
    db.commit()
    return {
        "confirm_token": token,
        "review_hash": digest,
        "expires_in_seconds": TOKEN_LIFETIME_SECONDS,
    }


# ---- activation --------------------------------------------------------------


def _token_row(db: Session, token: str) -> Optional[CalculationConfirmToken]:
    return db.execute(
        select(CalculationConfirmToken)
        .where(CalculationConfirmToken.token_hash == token_digest(token))
        .with_for_update()
    ).scalar_one_or_none()


def _in_window(db: Session, row: CalculationConfirmToken) -> bool:
    """Seconds since issue are counted on the database clock: 300 is accepted, 301 is not."""
    return bool(
        db.execute(
            text(
                "SELECT now() - issued_at <= make_interval(secs => :secs) "
                "FROM calculation_confirm_tokens WHERE id = :id"
            ),
            {"secs": TOKEN_LIFETIME_SECONDS, "id": row.id},
        ).scalar_one()
    )


def _check_token(
    db: Session,
    row: CalculationConfirmToken,
    user: User,
    session_jti: str,
    analysis_id: UUID,
    analyte_id: UUID,
    config_version: int,
) -> None:
    if row.user_id != user.id:
        raise refuse("confirm_token_wrong_user", "This confirm token was issued to another user.")
    if row.consumed_at is not None:
        raise refuse("confirm_token_used", "This confirm token was already used.")
    if row.analysis_id != analysis_id or row.analyte_id != analyte_id:
        raise refuse(
            "confirm_token_wrong_proposal",
            "This confirm token was issued for a different proposal.",
        )
    if row.session_jti != session_jti:
        raise refuse(
            "confirm_token_wrong_session",
            "This confirm token was issued in a different sign-in. Open the review again.",
        )
    if row.configuration_version != config_version:
        raise refuse(
            "confirm_token_version_changed",
            "The configuration version changed after the token was issued. Open the review again.",
        )
    if not _in_window(db, row):
        raise refuse(
            "confirm_token_expired",
            f"This confirm token is older than {TOKEN_LIFETIME_SECONDS} seconds. Open the review again.",
        )


def _activation_response(row: CalculationActivation) -> Dict[str, Any]:
    return {
        "id": row.id,
        "analysis_id": row.analysis_id,
        "analyte_id": row.analyte_id,
        "configuration_name": row.configuration_name,
        "configuration_version": row.configuration_version,
        "function_versions": row.function_versions,
        "lock_hash": row.lock_hash,
        "validation_state": row.validation_state,
        "review_document": row.review_document,
        "review_hash": row.review_hash,
        "created_at": row.created_at,
        "created_by": row.created_by,
    }


def activate(
    db: Session,
    user: User,
    session_jti: str,
    analysis_id: UUID,
    analyte_id: UUID,
    body: Any,
) -> Dict[str, Any]:
    """Activate the draft configuration. One transaction: token, state, record.

    Every refusal, and any database error, rolls the transaction back, so a
    token is consumed only by an activation that happened.
    """
    refuse_in_agent_context("Activation")
    _require_admin(user)
    body = _check_keys(body, ("confirm_token",), "The request")
    token = body.get("confirm_token")
    if not isinstance(token, str) or not token:
        raise refuse("confirm_token_required", "confirm_token is required.")
    try:
        return _activate(db, user, session_jti, analysis_id, analyte_id, token)
    except BaseException:
        db.rollback()
        raise


def _activate(
    db: Session,
    user: User,
    session_jti: str,
    analysis_id: UUID,
    analyte_id: UUID,
    token: str,
) -> Dict[str, Any]:
    analysis = lock_analysis(db, analysis_id)
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config is None:
        raise refuse("configuration_missing", "This analyte has no calculation configuration to activate.")
    if rule.calculation_config_state == STATE_ACTIVE:
        raise refuse("already_active", "This configuration version is already active.")
    if rule.calculation_config_state != STATE_DRAFT:
        raise refuse("configuration_not_draft", "Only a draft configuration is activated.")

    row = _token_row(db, token)
    if row is None:
        raise refuse("confirm_token_invalid", "This confirm token is not recognised.")
    _check_token(
        db, row, user, session_jti, analysis_id, analyte_id, int(rule.calculation_config_version)
    )
    document, digest = build_review(db, analysis_id, analyte_id)
    if digest != row.review_hash:
        raise refuse(
            "confirm_token_review_changed",
            "The review changed after the token was issued (a test case, dry run, or the "
            "configuration changed). Open the review again.",
        )

    consumed = db.execute(
        update(CalculationConfirmToken)
        .where(CalculationConfirmToken.id == row.id, CalculationConfirmToken.consumed_at.is_(None))
        .values(consumed_at=func.now())
    )
    if consumed.rowcount != 1:
        raise refuse("confirm_token_used", "This confirm token was already used.")

    db.execute(text("SELECT set_config(:name, 'on', true)"), {"name": ACTIVATE_SETTING})
    try:
        rule.calculation_config_state = STATE_ACTIVE
        analysis.modified_by = user.id
        db.flush()
    finally:
        db.execute(text("SELECT set_config(:name, 'off', true)"), {"name": ACTIVATE_SETTING})

    record = CalculationActivation(
        analysis_id=analysis_id,
        analyte_id=analyte_id,
        configuration_name=document["configuration"]["name"],
        configuration_version=document["configuration"]["version"],
        function_versions=document["function_versions"],
        lock_hash=document["lock_hash"],
        validation_state=document["validation_state"],
        review_document=document,
        review_hash=digest,
        created_by=user.id,
    )
    db.add(record)
    db.flush()
    db.commit()
    db.refresh(record)
    return _activation_response(record)


def list_activations(
    db: Session, analysis_id: UUID, analyte_id: UUID
) -> List[Dict[str, Any]]:
    if db.get(Analysis, analysis_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    get_rule(db, analysis_id, analyte_id)
    rows = db.execute(
        select(CalculationActivation)
        .where(
            CalculationActivation.analysis_id == analysis_id,
            CalculationActivation.analyte_id == analyte_id,
        )
        .order_by(CalculationActivation.created_at.desc(), CalculationActivation.id.desc())
    ).scalars()
    return [_activation_response(row) for row in rows]


# ---- test cases --------------------------------------------------------------


def _refuse_floats(value: Any, where: str) -> None:
    if isinstance(value, float):
        raise refuse(
            "test_case_number_invalid",
            f"{where} holds a JSON number with a fraction. Write values as decimal strings.",
        )
    if isinstance(value, dict):
        for item in value.values():
            _refuse_floats(item, where)
    elif isinstance(value, list):
        for item in value:
            _refuse_floats(item, where)


def _test_case_object(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise refuse("test_case_invalid", f"{field} must be an object.")
    _refuse_floats(value, field)
    try:
        size = len(canonical_json(value))
    except CanonicalizationError as exc:
        raise refuse("test_case_invalid", f"{field} cannot be stored: {exc}") from exc
    if size > MAX_TEST_CASE_JSON:
        raise refuse("test_case_invalid", f"{field} is larger than {MAX_TEST_CASE_JSON} characters.")
    return value


def _test_case_response(row: CalculationTestCase, lock_hash: str, db: Session) -> Dict[str, Any]:
    return {
        "id": row.id,
        "analysis_id": row.analysis_id,
        "analyte_id": row.analyte_id,
        "configuration_version": row.configuration_version,
        "name": row.name,
        "inputs": row.inputs,
        "expected": row.expected,
        "expected_source": row.expected_source,
        "from_system_output": row.expected_source == SOURCE_SYSTEM_OUTPUT,
        "passed_on_current_lock": passed_on_lock(db, row.id, lock_hash),
        "created_at": row.created_at,
        "created_by": row.created_by,
    }


def create_test_case(
    db: Session,
    user: User,
    analysis_id: UUID,
    analyte_id: UUID,
    body: Any,
) -> Dict[str, Any]:
    """Record a test case against the draft configuration version.

    A person says where the expected value came from. The configuring agent
    can only know the system's own output, so its test case is recorded as
    ``system_output`` and an agent that claims ``independent`` is refused
    (CALC-REQ-45 item 2). S8 stores the case; it does not run it (S9).
    """
    body = _check_keys(body, ("name", "inputs", "expected", "expected_source"), "The request")
    lock_analysis(db, analysis_id)
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config is None:
        raise refuse("configuration_missing", "This analyte has no calculation configuration.")
    if rule.calculation_config_state == STATE_ACTIVE:
        raise refuse(
            "calculation_config_active",
            "This configuration is active and immutable. Test cases are recorded against a draft.",
        )

    name = body.get("name")
    if not isinstance(name, str) or not name.strip() or name != name.strip():
        raise refuse("test_case_invalid", "name must be non-empty text with no leading or trailing space.")
    if len(name) > MAX_TEST_CASE_NAME or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise refuse("test_case_invalid", f"name is text of at most {MAX_TEST_CASE_NAME} characters, with no control character.")
    inputs = _test_case_object(body.get("inputs"), "inputs")
    expected = _test_case_object(body.get("expected"), "expected")

    source = body.get("expected_source")
    if in_agent_context():
        if source is not None and source != SOURCE_SYSTEM_OUTPUT:
            raise refuse(
                "agent_expected_source",
                "The configuring agent records only system output as the expected value. "
                "It cannot claim an independent source.",
            )
        source = SOURCE_SYSTEM_OUTPUT
    elif source not in EXPECTED_SOURCES:
        raise refuse(
            "expected_source_required",
            f"expected_source is required: {SOURCE_INDEPENDENT} or {SOURCE_SYSTEM_OUTPUT}.",
        )

    version = int(rule.calculation_config_version)
    for existing in list_case_rows(db, analysis_id, analyte_id, version):
        if existing.name.lower() == name.lower():
            raise refuse(
                "test_case_name_exists",
                f"A test case named {name!r} already exists for configuration version {version}.",
            )
    row = CalculationTestCase(
        analysis_id=analysis_id,
        analyte_id=analyte_id,
        configuration_version=version,
        name=name,
        inputs=inputs,
        expected=expected,
        expected_source=source,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    db.commit()
    db.refresh(row)
    return _test_case_response(row, lock_hash_now(), db)


def list_test_cases(
    db: Session,
    analysis_id: UUID,
    analyte_id: UUID,
    version: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rule = get_rule(db, analysis_id, analyte_id)
    target = version if version is not None else rule.calculation_config_version
    if target is None:
        return []
    lock = lock_hash_now()
    return [
        _test_case_response(row, lock, db)
        for row in list_case_rows(db, analysis_id, analyte_id, int(target))
    ]
