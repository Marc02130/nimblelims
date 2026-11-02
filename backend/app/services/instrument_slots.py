"""Instrument slots on experiment templates and the per-run type snapshot.

A slot is ``{key, label, instrument_type_id, required, run_import?}``.
``instrument_type_id`` must be an active ``instrument_types`` list entry when
set. Only the ``run_import`` slot must carry a type. At most one ``run_import``
slot per template.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.instrument import INSTRUMENT_TYPES_LIST_ID, Instrument
from models.list import List, ListEntry

INSTRUMENT_ENTRY_INVALID = "instrument_entry_invalid"
INSTRUMENT_TYPE_MISMATCH = "instrument_type_mismatch"
INSTRUMENT_SLOT_NOT_FOUND = "instrument_slot_not_found"
RUN_IMPORT_TYPE_LOCKED = "run_import_type_locked"
RUN_TEMPLATE_TYPE_REQUIRED = "run_template_type_required"
RUN_TYPE_REQUIRED = "run_type_required"
CRO_IMPORT_REQUIRES_CRO_RUN = "cro_import_requires_cro_run"
RUN_TYPE_LOCKED = "run_type_locked"
RUN_TERMINAL = "run_terminal"
INACTIVE_INSTRUMENT_TYPE = "instrument_type_inactive"


def _stop(code: str, message: str, http_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY) -> None:
    raise HTTPException(
        status_code=http_status,
        detail={"code": code, "message": message},
    )


def is_instrument_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    return entry.get("entry_type") == "instrument" or entry.get("predefined_entry_key") == "instruments"


def template_entries(template_definition: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(template_definition, dict):
        return []
    raw = template_definition.get("entries") or []
    if not isinstance(raw, list):
        return []
    return [e for e in raw if isinstance(e, dict)]


def slots_from_config(config: Any) -> List[Dict[str, Any]]:
    if not isinstance(config, dict):
        return []
    raw = config.get("slots") or []
    if not isinstance(raw, list):
        return []
    return [s for s in raw if isinstance(s, dict)]


def slots_from_template(template_definition: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in template_entries(template_definition):
        if is_instrument_entry(entry):
            out.extend(slots_from_config(entry.get("config")))
    return out


def run_import_slot(template_definition: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for slot in slots_from_template(template_definition):
        if slot.get("run_import") is True:
            return slot
    return None


def typed_run_import_type_id(template_definition: Optional[Dict[str, Any]]) -> Optional[UUID]:
    slot = run_import_slot(template_definition)
    if slot is None:
        return None
    raw = slot.get("instrument_type_id")
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        return None


def _truthy_run_import(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
        return True
    return False


def _parse_optional_uuid(raw: Any, message: str) -> Optional[UUID]:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        _stop(INSTRUMENT_ENTRY_INVALID, message)
    return None


def active_instrument_type(db: Session, type_id: UUID) -> Optional[ListEntry]:
    row = (
        db.query(ListEntry)
        .join(List, List.id == ListEntry.list_id)
        .filter(
            ListEntry.id == type_id,
            List.id == INSTRUMENT_TYPES_LIST_ID,
        )
        .first()
    )
    if row is None or row.active is not True:
        return None
    return row


def require_active_instrument_type(db: Session, type_id: UUID) -> ListEntry:
    row = active_instrument_type(db, type_id)
    if row is None:
        _stop(
            INACTIVE_INSTRUMENT_TYPE,
            "instrument_type_id must be an active instrument_types list entry.",
        )
    return row


def reject_invalid_instrument_slots(
    db: Session, template_definition: Optional[Dict[str, Any]]
) -> None:
    """Validate slots on every Instruments entry. 422 instrument_entry_invalid."""
    if template_definition is None:
        return
    run_import_count = 0
    seen_keys: set[str] = set()
    for entry in template_entries(template_definition):
        if not is_instrument_entry(entry):
            continue
        for slot in slots_from_config(entry.get("config")):
            key = slot.get("key")
            if not isinstance(key, str) or not key.strip():
                _stop(
                    INSTRUMENT_ENTRY_INVALID,
                    "Each instrument slot needs a key.",
                )
            key = key.strip()
            if key in seen_keys:
                _stop(
                    INSTRUMENT_ENTRY_INVALID,
                    f"Instrument slot key '{key}' is used more than once.",
                )
            seen_keys.add(key)
            label = slot.get("label")
            if label is not None and not isinstance(label, str):
                _stop(
                    INSTRUMENT_ENTRY_INVALID,
                    "An instrument slot label must be text.",
                )
            is_run_import = _truthy_run_import(slot.get("run_import"))
            type_id = _parse_optional_uuid(
                slot.get("instrument_type_id"),
                "An instrument slot lists a value that is not an instrument type id.",
            )
            if is_run_import:
                run_import_count += 1
                if type_id is None:
                    _stop(
                        INSTRUMENT_ENTRY_INVALID,
                        "The run_import slot must name an active instrument type.",
                    )
            if type_id is not None and active_instrument_type(db, type_id) is None:
                _stop(
                    INSTRUMENT_ENTRY_INVALID,
                    "An instrument slot names a type that is not an active instrument_types entry.",
                )
    if run_import_count > 1:
        _stop(
            INSTRUMENT_ENTRY_INVALID,
            "A template may have at most one run_import instrument slot.",
        )


def reject_run_import_type_lock(
    db: Session,
    template_id: UUID,
    old_definition: Optional[Dict[str, Any]],
    new_definition: Optional[Dict[str, Any]],
) -> None:
    """Refuse changing an existing run_import type once any lims_runs row references the template.

    Setting a type on a template that has none is allowed. API only — no DB trigger
    (the type lives in JSONB and a trigger would be fragile).
    """
    from models.flexible_experiment import LimsRun

    referenced = (
        db.query(LimsRun.id)
        .filter(LimsRun.experiment_template_id == template_id)
        .first()
    )
    if referenced is None:
        return
    old_type = typed_run_import_type_id(old_definition)
    new_type = typed_run_import_type_id(new_definition)
    if old_type is not None and new_type != old_type:
        _stop(
            RUN_IMPORT_TYPE_LOCKED,
            "The run_import slot type is locked because a LIMS run already uses this template.",
        )


def require_typed_run_import(template_definition: Optional[Dict[str, Any]]) -> UUID:
    type_id = typed_run_import_type_id(template_definition)
    if type_id is None:
        _stop(
            RUN_TEMPLATE_TYPE_REQUIRED,
            "A LIMS run template must have a typed run_import instrument slot.",
        )
    return type_id


def slot_by_key(
    template_definition: Optional[Dict[str, Any]], slot_key: str
) -> Optional[Dict[str, Any]]:
    for slot in slots_from_template(template_definition):
        if str(slot.get("key") or "") == slot_key:
            return slot
    return None


def assert_slot_type_matches_instrument(
    db: Session,
    *,
    slot: Dict[str, Any],
    instrument_id: UUID,
) -> Instrument:
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    raw = slot.get("instrument_type_id")
    if raw is None or str(raw).strip() == "":
        return row
    try:
        slot_type = UUID(str(raw))
    except (ValueError, TypeError):
        _stop(INSTRUMENT_ENTRY_INVALID, "An instrument slot type id is not a UUID.")
    if row.instrument_type_id != slot_type:
        _stop(
            INSTRUMENT_TYPE_MISMATCH,
            "This instrument's type does not match the slot type.",
        )
    return row


def assert_run_instrument_type(
    db: Session,
    *,
    run_type_id: Optional[UUID],
    instrument_id: UUID,
) -> None:
    """Every new LIMS run has a type. A leftover null snapshot is 422."""
    if run_type_id is None:
        _stop(
            RUN_TYPE_REQUIRED,
            "A LIMS run must have an instrument type before import.",
        )
    row = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    if row.instrument_type_id != run_type_id:
        _stop(
            INSTRUMENT_TYPE_MISMATCH,
            "This instrument's type does not match the run's instrument type.",
        )


def run_is_cro(run) -> bool:
    template = getattr(run, "experiment_template", None)
    if template is None:
        return False
    return (getattr(template, "lifecycle_type", None) or "standard") == "cro"
