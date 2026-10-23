"""Bind imported rows to samples using the parser sample-identifier column.

A row links only when the sample is on this run. Unmatched rows are kept.
The note says why they did not link, including a sample that exists but is
not on the run, and a key that matches a client sample ID and a sample name
pointing at different samples.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.flexible_experiment import LimsRun
from models.sample import Sample

SAMPLE_KEY_MAX = 255
NOT_ON_RUN = "Not on this run"
DIFFERENT_SAMPLES = "Client sample ID and sample name match different samples"
MATCHED_BOTH = "Matched by client sample ID and sample name"


def sample_key_from_config(row_data: Dict[str, Any], parser_config: Optional[dict]) -> Optional[str]:
    """Value of sample_col when that source column is also a mapped field."""
    if not parser_config:
        return None
    sample_col = parser_config.get("sample_col")
    if not sample_col:
        return None
    for col in parser_config.get("columns") or []:
        if col.get("source_col") == sample_col:
            raw = row_data.get(col.get("field_name"))
            if raw is None:
                return None
            text = str(raw).strip()
            return text or None
    return None


def cohort_sample_ids(run: LimsRun) -> Set[uuid.UUID]:
    """Sample ids on the run. Strings in the cohort JSON are accepted."""
    raw = (run.cohort or {}).get("sample_ids") or []
    found: Set[uuid.UUID] = set()
    for sid in raw:
        parsed = _uuid(sid)
        if parsed is not None:
            found.add(parsed)
    return found


def link_rows(
    db: Session,
    rows: Sequence[dict],
    *,
    parser_config: Optional[dict],
    on_run: Set[uuid.UUID],
) -> List[dict]:
    """Set sample_id, sample_key, and link_note on each row dict.

    A row links only to a sample on ``on_run``. When the parser has no
    sample_col and no key, rows are not marked unmatched. Returns the
    unmatched reports (the rows themselves stay in ``rows``). A linked row
    whose key matches both the client sample ID and the name keeps
    ``link_note`` and is not in this list.
    """
    sample_col = (parser_config or {}).get("sample_col") if parser_config else None
    pending: List[tuple[int, dict, Optional[str], Optional[uuid.UUID]]] = []
    keys: List[str] = []
    for index, row in enumerate(rows):
        explicit_key = row.get("sample_key")
        if explicit_key is not None and str(explicit_key).strip() == "":
            explicit_key = None
        elif explicit_key is not None:
            explicit_key = str(explicit_key).strip()
        key = explicit_key if explicit_key is not None else sample_key_from_config(
            row.get("row_data") or {}, parser_config
        )
        if key is not None and len(key) > SAMPLE_KEY_MAX:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "sample_key_too_long",
                    "message": f"sample_key must be at most {SAMPLE_KEY_MAX} characters",
                },
            )
        row["sample_key"] = key
        explicit_id = _uuid(row.get("sample_id"))
        if explicit_id is not None and explicit_id in on_run:
            row["sample_id"] = explicit_id
            row["link_note"] = None
            continue
        row["sample_id"] = None
        if not sample_col and key is None:
            if explicit_id is not None:
                row["link_note"] = NOT_ON_RUN
                pending.append((index, row, None, explicit_id))
            else:
                row["link_note"] = None
            continue
        pending.append((index, row, key, explicit_id))
        if key:
            keys.append(key)

    by_client: Dict[str, List[Sample]] = {}
    by_name: Dict[str, List[Sample]] = {}
    if keys:
        unique = list(dict.fromkeys(keys))
        for sample in (
            db.query(Sample)
            .filter(Sample.client_sample_id.in_(unique), Sample.active == True)  # noqa: E712
            .all()
        ):
            by_client.setdefault(sample.client_sample_id, []).append(sample)
        for sample in (
            db.query(Sample)
            .filter(Sample.name.in_(unique), Sample.active == True)  # noqa: E712
            .all()
        ):
            by_name.setdefault(sample.name, []).append(sample)

    unmatched: List[dict] = []
    for index, row, key, explicit_id in pending:
        if key is None and explicit_id is not None:
            sample_id, note = None, NOT_ON_RUN
        else:
            sample_id, note = _resolve(key, by_client, by_name, on_run)
        row["sample_id"] = sample_id
        row["link_note"] = note
        if sample_id is None and note:
            unmatched.append(
                {
                    "row_index": index,
                    "well_position": row.get("well_position"),
                    "sample_key": key,
                    "reason": note,
                }
            )
    return unmatched


def _uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _resolve(
    key: Optional[str],
    by_client: Dict[str, List[Sample]],
    by_name: Dict[str, List[Sample]],
    on_run: Set[uuid.UUID],
) -> tuple[Optional[uuid.UUID], Optional[str]]:
    if not key:
        return None, "Blank sample identifier"
    clients = by_client.get(key) or []
    names = by_name.get(key) or []
    client_ids = {sample.id for sample in clients}
    name_ids = {sample.id for sample in names}
    if client_ids and name_ids and client_ids != name_ids:
        return None, DIFFERENT_SAMPLES
    if len(clients) > 1:
        return None, f"More than one sample has client sample ID {key}"
    if len(names) > 1 and not clients:
        return None, f"More than one sample is named {key}"
    sample: Optional[Sample] = None
    flag: Optional[str] = None
    if len(clients) == 1 and name_ids == client_ids:
        sample = clients[0]
        flag = MATCHED_BOTH
    elif len(clients) == 1:
        sample = clients[0]
    elif len(names) == 1:
        sample = names[0]
    else:
        return None, f"No sample matches {key}"
    if sample.id not in on_run:
        return None, NOT_ON_RUN
    return sample.id, flag
