"""Bind imported rows to samples using the parser sample-identifier column.

Unmatched rows are kept. The note says why they did not link.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from models.sample import Sample


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


def link_rows(
    db: Session,
    rows: Sequence[dict],
    *,
    parser_config: Optional[dict],
) -> List[dict]:
    """Set sample_id, sample_key, and link_note on each row dict.

    A row that already has sample_id is left linked. When the parser has no
    sample_col, rows are not marked unmatched. Returns the unmatched reports
    (the rows themselves stay in ``rows``).
    """
    sample_col = (parser_config or {}).get("sample_col") if parser_config else None
    pending: List[tuple[int, dict, Optional[str]]] = []
    keys: List[str] = []
    for index, row in enumerate(rows):
        explicit = row.get("sample_key")
        if explicit is not None and str(explicit).strip() == "":
            explicit = None
        elif explicit is not None:
            explicit = str(explicit).strip()
        key = explicit if explicit is not None else sample_key_from_config(row.get("row_data") or {}, parser_config)
        row["sample_key"] = key
        if row.get("sample_id"):
            row["link_note"] = None
            continue
        if not sample_col and key is None:
            row["link_note"] = None
            continue
        pending.append((index, row, key))
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
    for index, row, key in pending:
        sample_id, note = _resolve(key, by_client, by_name)
        row["sample_id"] = sample_id
        row["link_note"] = note
        if note:
            unmatched.append(
                {
                    "row_index": index,
                    "well_position": row.get("well_position"),
                    "sample_key": key,
                    "reason": note,
                }
            )
    return unmatched


def _resolve(
    key: Optional[str],
    by_client: Dict[str, List[Sample]],
    by_name: Dict[str, List[Sample]],
) -> tuple[Optional[uuid.UUID], Optional[str]]:
    if not key:
        return None, "Blank sample identifier"
    clients = by_client.get(key) or []
    if len(clients) == 1:
        return clients[0].id, None
    if len(clients) > 1:
        return None, f"More than one sample has client sample ID {key}"
    names = by_name.get(key) or []
    if len(names) == 1:
        return names[0].id, None
    if len(names) > 1:
        return None, f"More than one sample is named {key}"
    return None, f"No sample matches {key}"
