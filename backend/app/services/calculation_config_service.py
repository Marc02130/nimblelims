"""Saving calculation configurations, saved formulas, and analysis versions (calculations S7).

The rules live in :mod:`app.services.calculation_config` and
:mod:`app.services.calculation_formula`. This module reads the database for the
facts those rules need, writes the row, and turns a refusal into HTTP 400.

Database triggers (migration 0124) back each rule for the application role:
the analysis version is incremented by the database at commit, and an active
configuration cannot be changed or deleted by a plain write.

A refusal returns HTTP 400. A caller without the Admin role that writes a
formula gets 403. No code here runs a calculation, calls R, or writes a result.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.services.calculation_config import (
    STAGE_KIND_SAVED,
    STATE_ACTIVE,
    STATE_DRAFT,
    ConfigContext,
    ConfigRefusal,
    UnitInfo,
    assign_ad_hoc_versions,
    formula_stages_changed,
    parse_config,
    referenced_analytes,
)
from app.services.calculation_formula import (
    KNOCKED_OUT,
    FormulaSyntaxError,
    format_value,
    parse_formula,
    run_formula,
    term_name_error,
)
from models.analysis import Analysis, AnalysisAnalyte
from models.calculation import AnalysisVersion, CalculationFormula
from models.list import ListEntry
from models.unit import Unit
from models.user import User

NEW_VERSION_SETTING = "lims.calculation_new_version"
MAX_FORMULA_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 2000
MAX_EVALUATE_TERMS = 100


def refuse(code: str, message: str, stage: Optional[str] = None) -> HTTPException:
    detail: Dict[str, Any] = {"code": code, "message": message}
    if stage is not None:
        detail["stage"] = stage
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def refuse_config(exc: ConfigRefusal) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail())


def is_lab_admin(user: User) -> bool:
    """A lab admin is anyone with the Admin role (OQ-CALC-52, Marc 2026-11-18)."""
    return bool(user.role is not None and user.role.name == "Administrator")


def _check_body_keys(body: Any, allowed: Sequence[str], where: str) -> Mapping[str, Any]:
    if not isinstance(body, dict):
        raise refuse("config_invalid", f"{where} must be an object.")
    unknown = sorted(str(key) for key in body if key not in allowed)
    if unknown:
        raise refuse("unknown_field", f"{where} has unknown field(s): {', '.join(unknown)}.")
    return body


# ---- reads ------------------------------------------------------------------


def lock_analysis(db: Session, analysis_id: UUID) -> Analysis:
    """Load the analysis and hold its row lock, so two edits to one analysis queue up."""
    analysis = db.execute(
        select(Analysis).where(Analysis.id == analysis_id).with_for_update()
    ).scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


def get_rule(db: Session, analysis_id: UUID, analyte_id: UUID) -> AnalysisAnalyte:
    rule = db.execute(
        select(AnalysisAnalyte).where(
            AnalysisAnalyte.analysis_id == analysis_id,
            AnalysisAnalyte.analyte_id == analyte_id,
        )
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyte is not linked to this analysis",
        )
    return rule


def analysis_rules(db: Session, analysis_id: UUID) -> List[AnalysisAnalyte]:
    return list(
        db.execute(
            select(AnalysisAnalyte).where(AnalysisAnalyte.analysis_id == analysis_id)
        ).scalars()
    )


def current_analysis_version(db: Session, analysis_id: UUID) -> int:
    db.expire_all()
    return int(
        db.execute(select(Analysis.version).where(Analysis.id == analysis_id)).scalar_one()
    )


def configuration_response(
    rule: AnalysisAnalyte, analysis_version: int
) -> Dict[str, Any]:
    return {
        "analysis_id": rule.analysis_id,
        "analyte_id": rule.analyte_id,
        "analysis_version": analysis_version,
        "calculation_order": rule.calculation_order,
        "state": rule.calculation_config_state,
        "name": rule.calculation_config_name,
        "version": rule.calculation_config_version,
        "configuration": rule.calculation_config,
    }


def _collect_unit_ids(raw: Any) -> List[str]:
    found: List[str] = []
    stages = raw.get("stages") if isinstance(raw, dict) else None
    if not isinstance(stages, list):
        return found
    for stage in stages:
        bindings = stage.get("bindings") if isinstance(stage, dict) else None
        if not isinstance(bindings, dict):
            continue
        for binding in bindings.values():
            if isinstance(binding, dict) and isinstance(binding.get("unit_id"), str):
                found.append(binding["unit_id"])
    return found


def _load_units(db: Session, raw_ids: Sequence[str]) -> Dict[str, UnitInfo]:
    ids: List[UUID] = []
    for raw in raw_ids:
        try:
            ids.append(UUID(raw))
        except ValueError:
            continue
    if not ids:
        return {}
    rows = db.execute(
        select(Unit.id, Unit.name, ListEntry.name)
        .join(ListEntry, ListEntry.id == Unit.type)
        .where(Unit.id.in_(ids), Unit.active == True)  # noqa: E712
    ).all()
    return {str(unit_id): UnitInfo(str(unit_id), name, type_name) for unit_id, name, type_name in rows}


def _collect_saved_formulas(raw: Any) -> List[tuple[str, int]]:
    found: List[tuple[str, int]] = []
    stages = raw.get("stages") if isinstance(raw, dict) else None
    if not isinstance(stages, list):
        return found
    for stage in stages:
        if (
            isinstance(stage, dict)
            and stage.get("kind") == STAGE_KIND_SAVED
            and isinstance(stage.get("formula_name"), str)
            and isinstance(stage.get("formula_version"), int)
            and not isinstance(stage.get("formula_version"), bool)
        ):
            found.append((stage["formula_name"].lower(), stage["formula_version"]))
    return found


def _load_saved_formulas(db: Session, keys: Sequence[tuple[str, int]]) -> Dict[tuple[str, int], str]:
    formulas: Dict[tuple[str, int], str] = {}
    for name, version in set(keys):
        row = db.execute(
            select(CalculationFormula).where(
                CalculationFormula.version == version,
                func.lower(CalculationFormula.name) == name,
            )
        ).scalar_one_or_none()
        if row is not None:
            formulas[(name, version)] = row.formula_text
    return formulas


def build_context(
    db: Session,
    rules: Sequence[AnalysisAnalyte],
    analyte_id: UUID,
    calculation_order: int,
    raw_config: Any,
) -> ConfigContext:
    orders = {
        str(rule.analyte_id): int(rule.calculation_order)
        for rule in rules
        if rule.calculation_order is not None and rule.analyte_id != analyte_id
    }
    return ConfigContext(
        analyte_id=str(analyte_id),
        calculation_order=calculation_order,
        analyte_orders=orders,
        units=_load_units(db, _collect_unit_ids(raw_config)),
        saved_formulas=_load_saved_formulas(db, _collect_saved_formulas(raw_config)),
    )


# ---- order checks -----------------------------------------------------------


def _check_order_value(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise refuse(
            "calculation_order_invalid",
            "calculation_order is a whole number from 1. It is separate from display_order.",
        )
    return value


def _check_order_unique(
    rules: Sequence[AnalysisAnalyte], analyte_id: UUID, order: int
) -> None:
    for rule in rules:
        if rule.analyte_id != analyte_id and rule.calculation_order == order:
            raise refuse(
                "calculation_order_duplicate",
                f"Calculation order {order} is already used by another analyte in this analysis.",
            )


def _check_readers_stay_later(
    rules: Sequence[AnalysisAnalyte], analyte_id: UUID, order: int
) -> None:
    """Every other calculation that reads this analyte must come after it."""
    target = str(analyte_id)
    for rule in rules:
        if rule.analyte_id == analyte_id or rule.calculation_config is None:
            continue
        if target in referenced_analytes(rule.calculation_config):
            reader_order = rule.calculation_order
            if reader_order is None or reader_order <= order:
                raise refuse(
                    "calculation_order_violation",
                    f"Analyte {rule.analyte_id} (calculation order {reader_order}) reads this "
                    f"analyte, so this analyte's order must be earlier than {reader_order}.",
                )


def refuse_if_active(
    db: Session, analysis_id: UUID, analyte_ids: Optional[Sequence[UUID]] = None
) -> None:
    """HTTP 400 before a write that the database would refuse (CALC-REQ-40).

    An analyte link that carries an active configuration is not removed or
    replaced in place. The way forward is a new version of the analysis.
    """
    stmt = select(AnalysisAnalyte.analyte_id).where(
        AnalysisAnalyte.analysis_id == analysis_id,
        AnalysisAnalyte.calculation_config_state == STATE_ACTIVE,
    )
    if analyte_ids is not None:
        stmt = stmt.where(AnalysisAnalyte.analyte_id.in_(list(analyte_ids)))
    active = [str(row) for row in db.execute(stmt).scalars()]
    if active:
        raise refuse(
            "calculation_config_active",
            "An active calculation configuration is immutable. Make a new version of the "
            f"analysis first. Analyte(s) with an active configuration: {', '.join(active)}.",
        )


# ---- configuration writes ---------------------------------------------------


def save_configuration(
    db: Session,
    analysis_id: UUID,
    analyte_id: UUID,
    body: Any,
    user: User,
) -> Dict[str, Any]:
    """Save a draft configuration on one analysis-analyte row. Returns the response."""
    body = _check_body_keys(body, ("calculation_order", "configuration"), "The request")
    analysis = lock_analysis(db, analysis_id)
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config_state == STATE_ACTIVE:
        raise refuse(
            "calculation_config_active",
            "This configuration is active and immutable. Make a new version of the analysis, "
            "then save the change there.",
        )
    if "calculation_order" not in body:
        raise refuse("calculation_order_required", "calculation_order is required.")
    if "configuration" not in body:
        raise refuse("config_invalid", "configuration is required.")
    order = _check_order_value(body["calculation_order"])
    rules = analysis_rules(db, analysis_id)
    _check_order_unique(rules, analyte_id, order)
    _check_readers_stay_later(rules, analyte_id, order)

    context = build_context(db, rules, analyte_id, order, body["configuration"])
    try:
        parsed = parse_config(body["configuration"], context)
    except ConfigRefusal as exc:
        raise refuse_config(exc) from exc
    prior_config = rule.calculation_config
    parsed = assign_ad_hoc_versions(parsed, prior_config)
    new_json = parsed.to_json()

    changed_formulas = formula_stages_changed(new_json, prior_config)
    if changed_formulas and not is_lab_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "formula_admin_only",
                "message": "Only a lab admin (a user with the Admin role) may write a formula, "
                "saved or ad hoc.",
                "stage": changed_formulas[0],
            },
        )

    for other in rules:
        if (
            other.analyte_id != analyte_id
            and other.calculation_config_name is not None
            and other.calculation_config_name.lower() == parsed.name.lower()
        ):
            raise refuse(
                "calculation_config_name_exists",
                f"A configuration named {parsed.name!r} already exists in this analysis.",
            )

    unchanged = (
        prior_config == new_json
        and rule.calculation_order == order
        and rule.calculation_config_name == parsed.name
    )
    if not unchanged:
        previous_version = rule.calculation_config_version
        rule.calculation_config_name = parsed.name
        rule.calculation_config = new_json
        rule.calculation_order = order
        rule.calculation_config_state = STATE_DRAFT
        rule.calculation_config_version = (previous_version or 0) + 1
        analysis.modified_by = user.id
        db.flush()
    db.commit()
    db.refresh(rule)
    return configuration_response(rule, current_analysis_version(db, analysis_id))


def set_calculation_order(
    db: Session, analysis_id: UUID, analyte_id: UUID, body: Any, user: User
) -> Dict[str, Any]:
    body = _check_body_keys(body, ("calculation_order",), "The request")
    analysis = lock_analysis(db, analysis_id)
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config is None:
        raise refuse(
            "configuration_missing",
            "This analyte has no calculation configuration, so it has no calculation order.",
        )
    if rule.calculation_config_state == STATE_ACTIVE:
        raise refuse(
            "calculation_config_active",
            "This configuration is active and immutable. Make a new version of the analysis.",
        )
    if "calculation_order" not in body:
        raise refuse("calculation_order_required", "calculation_order is required.")
    order = _check_order_value(body["calculation_order"])
    rules = analysis_rules(db, analysis_id)
    _check_order_unique(rules, analyte_id, order)
    _check_readers_stay_later(rules, analyte_id, order)
    context = build_context(db, rules, analyte_id, order, rule.calculation_config)
    try:
        parse_config(rule.calculation_config, context)
    except ConfigRefusal as exc:
        raise refuse_config(exc) from exc
    if rule.calculation_order != order:
        rule.calculation_order = order
        rule.calculation_config_version = (rule.calculation_config_version or 0) + 1
        analysis.modified_by = user.id
        db.flush()
    db.commit()
    db.refresh(rule)
    return configuration_response(rule, current_analysis_version(db, analysis_id))


def delete_configuration(
    db: Session, analysis_id: UUID, analyte_id: UUID, user: User
) -> None:
    analysis = lock_analysis(db, analysis_id)
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No calculation configuration"
        )
    if rule.calculation_config_state == STATE_ACTIVE:
        raise refuse(
            "calculation_config_active",
            "An active configuration is not removed. Make a new version of the analysis.",
        )
    target = str(analyte_id)
    for other in analysis_rules(db, analysis_id):
        if other.analyte_id != analyte_id and other.calculation_config is not None:
            if target in referenced_analytes(other.calculation_config):
                raise refuse(
                    "configuration_in_use",
                    f"Analyte {other.analyte_id} reads this analyte. Remove that reference first.",
                )
    rule.calculation_config_name = None
    rule.calculation_config = None
    rule.calculation_config_version = None
    rule.calculation_config_state = None
    rule.calculation_order = None
    analysis.modified_by = user.id
    db.flush()
    db.commit()


@contextmanager
def new_version_allowed(db: Session) -> Iterator[None]:
    """Let this transaction take active configurations back to draft.

    The setting is transaction-local and is turned off again when the block
    ends. Only the new-version route uses it.
    """
    db.execute(text("SELECT set_config(:name, 'on', true)"), {"name": NEW_VERSION_SETTING})
    try:
        yield
        db.flush()
    finally:
        db.execute(text("SELECT set_config(:name, 'off', true)"), {"name": NEW_VERSION_SETTING})


def start_new_version(db: Session, analysis_id: UUID, user: User) -> Dict[str, Any]:
    """Take every active configuration of the analysis to draft, as a new analysis version.

    The previous version is not edited and not deleted: its snapshot in
    ``analysis_versions`` keeps the active configuration as it was.
    """
    analysis = lock_analysis(db, analysis_id)
    active = [
        rule
        for rule in analysis_rules(db, analysis_id)
        if rule.calculation_config_state == STATE_ACTIVE
    ]
    if not active:
        raise refuse(
            "no_active_configuration",
            "This analysis has no active calculation configuration. A draft is edited in place.",
        )
    previous = int(analysis.version)
    with new_version_allowed(db):
        for rule in active:
            rule.calculation_config_state = STATE_DRAFT
        analysis.modified_by = user.id
    db.commit()
    return {
        "analysis_id": analysis_id,
        "previous_version": previous,
        "analysis_version": current_analysis_version(db, analysis_id),
        "drafted_analyte_ids": [rule.analyte_id for rule in active],
    }


# ---- analysis versions ------------------------------------------------------


def list_versions(db: Session, analysis_id: UUID) -> List[AnalysisVersion]:
    if db.get(Analysis, analysis_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return list(
        db.execute(
            select(AnalysisVersion)
            .where(AnalysisVersion.analysis_id == analysis_id)
            .order_by(AnalysisVersion.version)
        ).scalars()
    )


def get_version(db: Session, analysis_id: UUID, version: int) -> AnalysisVersion:
    row = db.execute(
        select(AnalysisVersion).where(
            AnalysisVersion.analysis_id == analysis_id, AnalysisVersion.version == version
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis version not found")
    return row


# ---- saved formulas ---------------------------------------------------------


def formula_response(row: CalculationFormula) -> Dict[str, Any]:
    terms: List[str] = []
    try:
        terms = sorted(parse_formula(row.formula_text).names)
    except FormulaSyntaxError:
        terms = []
    return {
        "id": row.id,
        "name": row.name,
        "version": row.version,
        "formula_text": row.formula_text,
        "description": row.description,
        "terms": terms,
        "created_at": row.created_at,
        "created_by": row.created_by,
    }


def _formula_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise refuse("formula_name_invalid", "name must be non-empty text with no leading or trailing space.")
    if len(value) > MAX_FORMULA_NAME_LENGTH:
        raise refuse("formula_name_invalid", f"name is at most {MAX_FORMULA_NAME_LENGTH} characters.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise refuse("formula_name_invalid", "name cannot contain a control character.")
    return value


def create_saved_formula(db: Session, body: Any, user: User) -> CalculationFormula:
    """Save a formula as the next version of its name. Admin only (checked by the route)."""
    body = _check_body_keys(body, ("name", "formula_text", "description"), "The request")
    name = _formula_name(body.get("name"))
    formula_text = body.get("formula_text")
    try:
        parsed = parse_formula(formula_text)
    except FormulaSyntaxError as exc:
        raise refuse(exc.code, exc.message) from exc
    for term in sorted(parsed.names):
        problem = term_name_error(term)
        if problem:
            raise refuse("formula_unknown_name", problem)
    description = body.get("description")
    if description is not None and (
        not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH
    ):
        raise refuse(
            "config_invalid", f"description is text of at most {MAX_DESCRIPTION_LENGTH} characters."
        )

    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"calculation_formula:{name.lower()}"})
    latest = db.execute(
        select(CalculationFormula)
        .where(func.lower(CalculationFormula.name) == name.lower())
        .order_by(CalculationFormula.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest is not None and latest.formula_text == formula_text:
        raise refuse(
            "formula_unchanged",
            f"Saved formula {latest.name!r} version {latest.version} already has this text.",
        )
    row = CalculationFormula(
        name=latest.name if latest is not None else name,
        version=(latest.version + 1) if latest is not None else 1,
        formula_text=formula_text,
        description=description,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_saved_formulas(db: Session) -> List[CalculationFormula]:
    return list(
        db.execute(
            select(CalculationFormula).order_by(
                func.lower(CalculationFormula.name), CalculationFormula.version
            )
        ).scalars()
    )


def get_saved_formula(db: Session, name: str, version: int) -> CalculationFormula:
    row = db.execute(
        select(CalculationFormula).where(
            CalculationFormula.version == version,
            func.lower(CalculationFormula.name) == name.lower(),
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved formula not found")
    return row


def evaluate_formula_text(body: Any) -> Dict[str, Any]:
    """Run formula text on typed terms, for a lab admin trying a formula.

    This is not a calculation attempt: it reads no run, writes nothing, and
    stores nothing. A term is a decimal string, null (missing), or
    ``{"knocked_out": true}``. A formula error is a 200 with the Excel text; a
    formula outside the grammar is a 400.
    """
    body = _check_body_keys(body, ("formula_text", "terms"), "The request")
    try:
        parsed = parse_formula(body.get("formula_text"))
    except FormulaSyntaxError as exc:
        raise refuse(exc.code, exc.message) from exc
    terms_raw = body.get("terms", {})
    if not isinstance(terms_raw, dict) or len(terms_raw) > MAX_EVALUATE_TERMS:
        raise refuse("config_invalid", "terms must be an object of term values.")
    env: Dict[str, Any] = {}
    for name, value in terms_raw.items():
        if name not in parsed.names:
            raise refuse("formula_unknown_name", f"{name!r} is not a term of this formula.")
        if value is None or isinstance(value, str):
            env[name] = value
        elif isinstance(value, dict) and value == {"knocked_out": True}:
            env[name] = KNOCKED_OUT
        else:
            raise refuse(
                "config_invalid",
                f"The value of {name!r} is a decimal string, null, or {{\"knocked_out\": true}}.",
            )
    outcome = run_formula(parsed, env)
    if outcome.stopped:
        return {"value": None, "error": outcome.error, "detail": outcome.detail}
    return {"value": format_value(outcome.value), "error": None, "detail": ""}
