"""The activation review document (calculations S8, CALC-REQ-45).

The server builds one JSON document for the configuration version an Admin is
about to activate. The review dialog renders only from it, the export is its
canonical bytes, the review-screen hash is the SHA-256 of its RFC 8785 JCS
encoding, and the activation row stores both.

The document holds no render time, no nonce, no countdown, and no PII or
secret: no person name, email, user id, token, password, key, or SOP body. The
person who activates is ``created_by`` on the activation row, not a field here.
Building it twice from the same data gives the same bytes.

Words used here, and why. A stage output is a *calculated value*. It becomes a
*result* only when the experiment is published (S13). ``result`` in the stored
configuration is a pointer to the output that will be published as the
analyte's result; this module says so in the plain-language text and writes
nothing to a result table. The document never labels a configuration or a
calculation as proven (CALC-REQ-46).

Nothing here runs a calculation, calls R, or writes a row.
"""
from __future__ import annotations

from datetime import timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services.calculation_config import (
    BINDING_DIRECT,
    BINDING_REFERENCE,
    BINDING_RUN_FIELD,
    BINDING_STAGE_OUTPUT,
    LIMIT_INPUTS,
    STAGE_KIND_AD_HOC,
    STAGE_KIND_CATALOG,
    STAGE_KIND_SAVED,
    STATE_ACTIVE,
    STATE_DRAFT,
    catalog_entries,
)
from app.services.calculation_config_service import get_rule, refuse
from app.services.calculation_runtime import CalculationCallRefused, expected_lock_from_commit
from app.services.jcs import CanonicalizationError, canonical_sha256
from models.analysis import Analysis, Analyte
from models.calculation import (
    AnalysisVersion,
    CalculationDryRun,
    CalculationFormula,
    CalculationTestCase,
    CalculationTestCaseResult,
)
from models.unit import Unit

REVIEW_SCHEMA = "calculation_activation_review/1"

STATE_NO_TESTS = "no_test_cases"
STATE_NONE_PASSED = "tests_none_passed"
STATE_SOME_PASSED = "tests_some_passed"
STATE_ALL_PASSED = "tests_all_passed"
VALIDATION_STATES = (STATE_NO_TESTS, STATE_NONE_PASSED, STATE_SOME_PASSED, STATE_ALL_PASSED)

SOURCE_INDEPENDENT = "independent"
SOURCE_SYSTEM_OUTPUT = "system_output"
EXPECTED_SOURCES = (SOURCE_INDEPENDENT, SOURCE_SYSTEM_OUTPUT)

CONFIRM_LABEL = "Activate"
CONFIRM_LABEL_NO_TESTS = "Activate with no test cases recorded"
NO_TESTS_TEXT = "No test cases recorded"
NO_PREVIOUS_TEXT = "no previous version"

RESULT_POINTER_NOTE = (
    "Stage {stage} output {output} is the calculated value that will be published as the "
    "analyte's result when the experiment is published. Nothing is written to a result "
    "when the configuration is activated or run."
)

ENTRY_TYPE_TEXT = {
    "experiment_data": "experiment data entry",
    "experiment_sample_data": "experiment sample data entry",
}


# ---- the facts the document is built from ------------------------------------


def lock_hash_now() -> str:
    """The R lock hash the runtime serves, recomputed from the commit (Spec §2)."""
    try:
        return expected_lock_from_commit().lock_hash
    except CalculationCallRefused as exc:
        raise refuse(
            "lock_hash_unavailable",
            "The lock hash of the R service cannot be recomputed here, so a review cannot be built.",
        ) from exc


def _jsonable(value: Any) -> Any:
    """A stored JSON value as the canonical form takes it: no float, only text numbers."""
    if isinstance(value, float):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _instant(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def classify_state(total: int, passed: int) -> str:
    if total == 0:
        return STATE_NO_TESTS
    if passed == 0:
        return STATE_NONE_PASSED
    if passed == total:
        return STATE_ALL_PASSED
    return STATE_SOME_PASSED


def list_case_rows(
    db: Session, analysis_id: UUID, analyte_id: UUID, config_version: int
) -> List[CalculationTestCase]:
    return list(
        db.execute(
            select(CalculationTestCase)
            .where(
                CalculationTestCase.analysis_id == analysis_id,
                CalculationTestCase.analyte_id == analyte_id,
                CalculationTestCase.configuration_version == config_version,
            )
            .order_by(CalculationTestCase.created_at, CalculationTestCase.id)
        ).scalars()
    )


def passed_on_lock(db: Session, case_id: UUID, lock_hash: str) -> Optional[bool]:
    """Did the case's latest outcome on this lock hash pass? None when none is recorded."""
    row = db.execute(
        select(CalculationTestCaseResult.passed)
        .where(
            CalculationTestCaseResult.test_case_id == case_id,
            CalculationTestCaseResult.lock_hash == lock_hash,
        )
        .order_by(CalculationTestCaseResult.run_at.desc(), CalculationTestCaseResult.id.desc())
        .limit(1)
    ).first()
    return None if row is None else bool(row[0])


def _headline(total: int, passed: int, from_system: int, dry_run: Optional[Mapping[str, Any]]) -> str:
    dry = "no dry run" if dry_run is None else f"dry run done {dry_run['run_at']}"
    if total == 0:
        return f"{NO_TESTS_TEXT}, {dry}"
    noun = "test case" if total == 1 else "test cases"
    return f"{total} {noun}, {passed} passed, {from_system} from system output, {dry}"


def _test_case_section(
    db: Session, analysis_id: UUID, analyte_id: UUID, config_version: int, lock_hash: str
) -> Dict[str, Any]:
    cases = []
    passed = 0
    from_system = 0
    for row in list_case_rows(db, analysis_id, analyte_id, config_version):
        outcome = passed_on_lock(db, row.id, lock_hash)
        if outcome is True:
            passed += 1
        if row.expected_source == SOURCE_SYSTEM_OUTPUT:
            from_system += 1
        cases.append(
            {
                "name": row.name,
                "expected_source": row.expected_source,
                "from_system_output": row.expected_source == SOURCE_SYSTEM_OUTPUT,
                "passed_on_current_lock": outcome,
            }
        )
    total = len(cases)

    dry = db.execute(
        select(CalculationDryRun)
        .where(
            CalculationDryRun.analysis_id == analysis_id,
            CalculationDryRun.analyte_id == analyte_id,
            CalculationDryRun.configuration_version == config_version,
        )
        .order_by(CalculationDryRun.run_at.desc(), CalculationDryRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    dry_run: Dict[str, Any] = (
        {"done": False, "run_at": None, "input": None}
        if dry is None
        else {"done": True, "run_at": _instant(dry.run_at), "input": _jsonable(dry.input)}
    )
    return {
        "state": classify_state(total, passed),
        "section": {
            "total": total,
            "passed_on_current_lock": passed,
            "from_system_output": from_system,
            "none_recorded": total == 0,
            "notice": NO_TESTS_TEXT if total == 0 else None,
            "cases": cases,
            "summary": _headline(total, passed, from_system, dry_run if dry is not None else None),
        },
        "dry_run": dry_run,
    }


# ---- plain language ----------------------------------------------------------


def _catalog_lookup() -> Dict[tuple, Dict[str, Any]]:
    return {(entry["name"], entry["version"]): entry for entry in catalog_entries()}


def _unit_names(db: Session, raw: Mapping[str, Any]) -> Dict[str, str]:
    ids: List[UUID] = []
    for stage in raw.get("stages", []):
        for binding in stage.get("bindings", {}).values():
            unit = binding.get("unit_id")
            if isinstance(unit, str):
                try:
                    ids.append(UUID(unit))
                except ValueError:
                    continue
    if not ids:
        return {}
    rows = db.execute(select(Unit.id, Unit.name).where(Unit.id.in_(ids))).all()
    return {str(unit_id): name for unit_id, name in rows}


def _analyte_names(db: Session, raw: Mapping[str, Any]) -> Dict[str, str]:
    ids: List[UUID] = []
    for stage in raw.get("stages", []):
        for binding in stage.get("bindings", {}).values():
            if binding.get("kind") == BINDING_REFERENCE:
                try:
                    ids.append(UUID(binding["analyte_id"]))
                except (KeyError, ValueError):
                    continue
    if not ids:
        return {}
    rows = db.execute(select(Analyte.id, Analyte.name).where(Analyte.id.in_(ids))).all()
    return {str(analyte_id): name for analyte_id, name in rows}


def binding_text(
    binding: Optional[Mapping[str, Any]],
    units: Mapping[str, str],
    analytes: Mapping[str, str],
) -> Optional[str]:
    """One binding in plain words. A direct value is a value the lab bound."""
    if binding is None:
        return None
    kind = binding.get("kind")
    if kind == BINDING_RUN_FIELD:
        entry = ENTRY_TYPE_TEXT.get(binding.get("entry_type"), str(binding.get("entry_type")))
        text = f"field {binding.get('field_name')} of the {entry} in the same run"
        if binding.get("match_field") is not None:
            text += f", matched on {binding['match_field']}"
    elif kind == BINDING_STAGE_OUTPUT:
        text = f"output {binding.get('output')} of stage {binding.get('stage')}"
    elif kind == BINDING_REFERENCE:
        analyte_id = str(binding.get("analyte_id"))
        name = analytes.get(analyte_id, analyte_id)
        text = f"the {binding.get('value')} value of analyte {name} in the same run"
    elif kind == BINDING_DIRECT:
        text = f"the value {binding.get('value')} bound directly in the configuration"
    else:
        text = f"a binding of kind {kind}"
    unit = binding.get("unit_id")
    if unit is not None:
        text += f", in unit {units.get(str(unit), str(unit))}"
    return text


def _stage_text(
    stage: Mapping[str, Any],
    catalog: Mapping[tuple, Mapping[str, Any]],
    units: Mapping[str, str],
    analytes: Mapping[str, str],
) -> str:
    kind = stage.get("kind")
    if kind == STAGE_KIND_CATALOG:
        entry = catalog.get((stage.get("function"), stage.get("function_version")))
        head = (
            f"Stage {stage['id']} calls catalog function {stage.get('function')} version "
            f"{stage.get('function_version')}"
        )
        if entry is not None:
            head += f": {entry['description']}"
    elif kind == STAGE_KIND_SAVED:
        head = (
            f"Stage {stage['id']} computes with saved formula {stage.get('formula_name')} "
            f"version {stage.get('formula_version')} (the formula text is listed under formulas)"
        )
    else:
        head = (
            f"Stage {stage['id']} computes with an ad hoc formula, version "
            f"{stage.get('formula_version')} (the formula text is listed under formulas)"
        )
    parts = [
        f"{name} is {binding_text(binding, units, analytes)}"
        for name, binding in sorted(stage.get("bindings", {}).items())
    ]
    inputs = "; ".join(parts) if parts else "it binds no input"
    return f"{head}. Inputs: {inputs}."


# ---- formulas and stage declarations ----------------------------------------


def _saved_formula_texts(db: Session, keys: Sequence[tuple]) -> Dict[tuple, str]:
    texts: Dict[tuple, str] = {}
    for name, version in set(keys):
        row = db.execute(
            select(CalculationFormula).where(
                CalculationFormula.version == version,
                func.lower(CalculationFormula.name) == str(name).lower(),
            )
        ).scalar_one_or_none()
        if row is not None:
            texts[(str(name).lower(), version)] = row.formula_text
    return texts


def _saved_keys(raw: Optional[Mapping[str, Any]]) -> List[tuple]:
    keys: List[tuple] = []
    for stage in (raw or {}).get("stages", []):
        if stage.get("kind") == STAGE_KIND_SAVED:
            keys.append((stage["formula_name"], stage["formula_version"]))
    return keys


def _formula_rows(
    raw: Mapping[str, Any], saved_texts: Mapping[tuple, str]
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for stage in raw.get("stages", []):
        kind = stage.get("kind")
        if kind == STAGE_KIND_SAVED:
            rows.append(
                {
                    "stage": stage["id"],
                    "kind": kind,
                    "name": stage["formula_name"],
                    "version": stage["formula_version"],
                    "text": saved_texts.get((stage["formula_name"].lower(), stage["formula_version"])),
                }
            )
        elif kind == STAGE_KIND_AD_HOC:
            rows.append(
                {
                    "stage": stage["id"],
                    "kind": kind,
                    "name": None,
                    "version": stage.get("formula_version"),
                    "text": stage["formula_text"],
                }
            )
    return rows


def _formula_text_for_diff(
    stage: Mapping[str, Any], saved_texts: Mapping[tuple, str]
) -> Optional[str]:
    kind = stage.get("kind")
    if kind == STAGE_KIND_SAVED:
        text = saved_texts.get((stage["formula_name"].lower(), stage["formula_version"]))
        return f"saved formula {stage['formula_name']} version {stage['formula_version']}: {text}"
    if kind == STAGE_KIND_AD_HOC:
        return f"ad hoc formula version {stage.get('formula_version')}: {stage['formula_text']}"
    return None


def _declarations(raw: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for stage in raw.get("stages", []):
        on_fail = stage.get("on_fail", {})
        reads_limit = stage.get("kind") == STAGE_KIND_CATALOG and any(
            name in LIMIT_INPUTS for name in stage.get("bindings", {})
        )
        rows.append(
            {
                "stage": stage["id"],
                "outcome": on_fail.get("outcome"),
                "verdict": on_fail.get("verdict"),
                "flag": on_fail.get("flag"),
                "missing_limit_flag": on_fail.get("missing_limit_flag"),
                "gates": list(on_fail.get("gates", [])),
                "precedence_place": on_fail.get("precedence_place"),
                "reads_limit": reads_limit,
            }
        )
    return rows


# ---- the diff ----------------------------------------------------------------


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _function_text(stage: Mapping[str, Any]) -> Optional[str]:
    if stage.get("kind") != STAGE_KIND_CATALOG:
        return None
    return f"{stage.get('function')} version {stage.get('function_version')}"


def diff_configurations(
    old: Optional[Mapping[str, Any]],
    new: Mapping[str, Any],
    *,
    old_order: Optional[int],
    new_order: Optional[int],
    old_saved_texts: Mapping[tuple, str],
    new_saved_texts: Mapping[tuple, str],
    units: Mapping[str, str],
    analytes: Mapping[str, str],
) -> List[Dict[str, Any]]:
    """Each change from ``old`` to ``new``: function versions, bindings, stage
    on-fail declarations, and formula text (CALC-REQ-45 item 6).

    Formula text is the saved formula's text with its name and version, or the
    ad hoc formula's text with its version. A change that touches a formula
    always lists the text, old and new.
    """
    changes: List[Dict[str, Any]] = []

    def add(stage: Optional[str], category: str, field: str, before: Any, after: Any) -> None:
        changes.append(
            {"stage": stage, "category": category, "field": field, "old": before, "new": after}
        )

    if old is None:
        return changes
    if old.get("name") != new.get("name"):
        add(None, "configuration", "name", old.get("name"), new.get("name"))
    if old_order != new_order:
        add(None, "configuration", "calculation_order", _text(old_order), _text(new_order))
    if old.get("result") != new.get("result"):
        before = old.get("result") or {}
        after = new.get("result") or {}
        add(
            None,
            "configuration",
            "result_pointer",
            f"stage {before.get('stage')} output {before.get('output')}",
            f"stage {after.get('stage')} output {after.get('output')}",
        )

    old_stages = {stage["id"]: stage for stage in old.get("stages", [])}
    new_stages = {stage["id"]: stage for stage in new.get("stages", [])}
    for stage_id in old_stages:
        if stage_id not in new_stages:
            stage = old_stages[stage_id]
            add(stage_id, "stage", "removed", _function_text(stage) or _formula_text_for_diff(stage, old_saved_texts), None)
    for stage_id, stage in new_stages.items():
        before = old_stages.get(stage_id)
        if before is None:
            add(stage_id, "stage", "added", None, _function_text(stage) or _formula_text_for_diff(stage, new_saved_texts))
            continue
        if before.get("kind") != stage.get("kind"):
            add(stage_id, "stage", "kind", before.get("kind"), stage.get("kind"))
        if _function_text(before) != _function_text(stage):
            add(stage_id, "function_version", "function", _function_text(before), _function_text(stage))

        before_formula = _formula_text_for_diff(before, old_saved_texts)
        after_formula = _formula_text_for_diff(stage, new_saved_texts)
        if before_formula != after_formula:
            add(stage_id, "formula_text", "formula", before_formula, after_formula)

        names = sorted(set(before.get("bindings", {})) | set(stage.get("bindings", {})))
        for name in names:
            old_binding = before.get("bindings", {}).get(name)
            new_binding = stage.get("bindings", {}).get(name)
            if old_binding != new_binding:
                add(
                    stage_id,
                    "binding",
                    name,
                    binding_text(old_binding, units, analytes),
                    binding_text(new_binding, units, analytes),
                )
        old_fail = before.get("on_fail", {})
        new_fail = stage.get("on_fail", {})
        for key in ("outcome", "verdict", "flag", "missing_limit_flag", "gates", "precedence_place"):
            if old_fail.get(key) != new_fail.get(key):
                add(stage_id, "on_fail", key, _text(old_fail.get(key)), _text(new_fail.get(key)))
    return changes


def previous_snapshot_config(
    db: Session, analysis_id: UUID, analyte_id: UUID, previous_version: int
) -> Optional[Dict[str, Any]]:
    """The configuration, order and name as they were at ``previous_version``.

    Read from the newest analysis snapshot that holds that configuration
    version for this analyte. Returns None when no snapshot has it.
    """
    snapshots = db.execute(
        select(AnalysisVersion.snapshot)
        .where(AnalysisVersion.analysis_id == analysis_id)
        .order_by(AnalysisVersion.version.desc())
    ).scalars()
    for snapshot in snapshots:
        for row in (snapshot or {}).get("analytes", []):
            if (
                row.get("analyte_id") == str(analyte_id)
                and row.get("calculation_config") is not None
                and row.get("calculation_config_version") == previous_version
            ):
                return {
                    "config": row["calculation_config"],
                    "order": row.get("calculation_order"),
                }
    return None


def _diff_section(
    db: Session,
    analysis_id: UUID,
    analyte_id: UUID,
    version: int,
    order: int,
    current: Mapping[str, Any],
    units: Mapping[str, str],
    analytes: Mapping[str, str],
) -> Dict[str, Any]:
    if version <= 1:
        return {"previous_version": None, "summary": NO_PREVIOUS_TEXT, "changes": []}
    previous = previous_snapshot_config(db, analysis_id, analyte_id, version - 1)
    if previous is None:
        return {
            "previous_version": version - 1,
            "summary": f"version {version - 1} is not in the analysis version history",
            "changes": [],
        }
    old_config = previous["config"]
    old_units = _unit_names(db, old_config)
    old_analytes = _analyte_names(db, old_config)
    saved_keys = _saved_keys(old_config) + _saved_keys(current)
    texts = _saved_formula_texts(db, saved_keys)
    changes = diff_configurations(
        old_config,
        current,
        old_order=previous["order"],
        new_order=order,
        old_saved_texts=texts,
        new_saved_texts=texts,
        units={**old_units, **units},
        analytes={**old_analytes, **analytes},
    )
    count = len(changes)
    if count == 0:
        summary = f"no changes from version {version - 1}"
    else:
        summary = f"{count} {'change' if count == 1 else 'changes'} from version {version - 1}"
    return {"previous_version": version - 1, "summary": summary, "changes": changes}


# ---- the document ------------------------------------------------------------


def build_review_document(db: Session, analysis_id: UUID, analyte_id: UUID) -> Dict[str, Any]:
    """The review document for the draft configuration on this analysis-analyte row."""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    rule = get_rule(db, analysis_id, analyte_id)
    if rule.calculation_config is None:
        raise refuse(
            "configuration_missing",
            "This analyte has no calculation configuration to activate.",
        )
    if rule.calculation_config_state == STATE_ACTIVE:
        raise refuse("already_active", "This configuration version is already active.")
    if rule.calculation_config_state != STATE_DRAFT:
        raise refuse("configuration_not_draft", "Only a draft configuration is activated.")

    analyte = db.get(Analyte, analyte_id)
    config = _jsonable(rule.calculation_config)
    version = int(rule.calculation_config_version)
    order = int(rule.calculation_order)
    lock = lock_hash_now()
    catalog = _catalog_lookup()
    units = _unit_names(db, config)
    analytes = _analyte_names(db, config)
    saved_texts = _saved_formula_texts(db, _saved_keys(config))
    tests = _test_case_section(db, analysis_id, analyte_id, version, lock)

    function_versions = sorted(
        {
            (stage["function"], stage["function_version"])
            for stage in config.get("stages", [])
            if stage.get("kind") == STAGE_KIND_CATALOG
        }
    )
    pointer = config.get("result") or {}
    no_tests = tests["section"]["none_recorded"]

    document: Dict[str, Any] = {
        "schema": REVIEW_SCHEMA,
        "analysis": {"id": str(analysis_id), "name": analysis.name},
        "analyte": {"id": str(analyte_id), "name": analyte.name if analyte is not None else None},
        "configuration": {
            "name": rule.calculation_config_name,
            "version": version,
            "calculation_order": order,
            "body": config,
        },
        "lock_hash": lock,
        "function_versions": [
            {"function": name, "version": number} for name, number in function_versions
        ],
        "validation_state": tests["state"],
        "test_cases": tests["section"],
        "dry_run": tests["dry_run"],
        "plain_language": {
            "stages": [
                {"stage": stage["id"], "text": _stage_text(stage, catalog, units, analytes)}
                for stage in config.get("stages", [])
            ],
            "result_pointer": RESULT_POINTER_NOTE.format(
                stage=pointer.get("stage"), output=pointer.get("output")
            ),
        },
        "formulas": _formula_rows(config, saved_texts),
        "stage_declarations": _declarations(config),
        "diff": _diff_section(db, analysis_id, analyte_id, version, order, config, units, analytes),
        "confirm_label": CONFIRM_LABEL_NO_TESTS if no_tests else CONFIRM_LABEL,
    }
    return document


def review_hash(document: Mapping[str, Any]) -> str:
    """SHA-256 of the document's RFC 8785 JCS encoding (CALC-REQ-34)."""
    try:
        return canonical_sha256(document)
    except CanonicalizationError as exc:
        raise refuse("review_not_canonical", str(exc)) from exc


def build_review(db: Session, analysis_id: UUID, analyte_id: UUID) -> tuple[Dict[str, Any], str]:
    document = build_review_document(db, analysis_id, analyte_id)
    return document, review_hash(document)
