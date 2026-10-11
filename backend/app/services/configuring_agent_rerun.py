"""Safe rerun (D-7): find the object a create step would make, if it already exists.

Running the same input again must be a no-op or a clear diff, never a duplicate
table, column, or row. A create step whose object is already present returns the
existing object instead of calling the API again. Updates (PATCH/PUT) replace
values and are already idempotent.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func

from models.user import User


def _uuid(value) -> Optional[UUID]:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def existing_change(db, user: User, method: str, path: str, body: Any):
    """Return an AppliedChange for an object that already exists, else None."""
    from app.services.configuring_agent_apply import AppliedChange

    method = (method or "").upper()
    path = (path or "").split("?", 1)[0].rstrip("/") or "/"
    data = body if isinstance(body, dict) else {}
    if method != "POST":
        return None
    name = str(data.get("name") or "").strip()

    if path == "/lists" and name:
        from models.list import List as ListModel

        row = db.query(ListModel).filter(func.lower(ListModel.name) == name.lower()).first()
        return AppliedChange("list", row.name, row.id) if row else None

    entry = re.match(r"^/lists/([^/]+)/entries$", path)
    if entry and name:
        from models.list import List as ListModel, ListEntry
        from app.routers.lists import _LIST_NAME_ALIASES

        names = [entry.group(1)]
        if _LIST_NAME_ALIASES.get(entry.group(1)):
            names.append(_LIST_NAME_ALIASES[entry.group(1)])
        row = (
            db.query(ListEntry)
            .join(ListModel, ListModel.id == ListEntry.list_id)
            .filter(ListModel.name.in_(names), func.lower(ListEntry.name) == name.lower())
            .first()
        )
        return AppliedChange("list_entry", row.name, row.id) if row else None

    if path == "/containers/types" and name:
        from models.container import ContainerType

        row = db.query(ContainerType).filter(func.lower(ContainerType.name) == name.lower()).first()
        return AppliedChange("container_type", row.name, row.id) if row else None

    if path == "/v1/experiment-templates" and name:
        from models.experiment import ExperimentTemplate

        row = db.query(ExperimentTemplate).filter(func.lower(ExperimentTemplate.name) == name.lower()).first()
        return AppliedChange("experiment_template", row.name, row.id) if row else None

    if path == "/v1/sample-type-transitions":
        from models.sample import SampleTypeTransition

        source = _uuid(data.get("source_sample_type"))
        dest = _uuid(data.get("allowed_dest_sample_type"))
        operation = data.get("operation")
        if source and dest and operation:
            row = (
                db.query(SampleTypeTransition)
                .filter(
                    SampleTypeTransition.client_id == user.client_id,
                    SampleTypeTransition.source_sample_type == source,
                    SampleTypeTransition.operation == operation,
                    SampleTypeTransition.allowed_dest_sample_type == dest,
                )
                .first()
            )
            return AppliedChange("sample_type_transition", str(row.id), row.id) if row else None
        return None

    if path == "/v1/schema/tables":
        from models.ui_schema import SchemaTable

        physical = str(data.get("physical_name") or "").strip()
        display = str(data.get("display_name") or "").strip()
        query = db.query(SchemaTable).filter(SchemaTable.client_id == user.client_id)
        if physical:
            row = query.filter(SchemaTable.physical_name == physical).first()
        elif display:
            row = query.filter(func.lower(SchemaTable.display_name) == display.lower()).first()
        else:
            row = None
        return AppliedChange("table", row.display_name, row.id) if row else None

    if path == "/v1/schema/columns":
        from models.ui_schema import SchemaColumn

        table_id = _uuid(data.get("table_id"))
        physical = str(data.get("physical_name") or "").strip()
        display = str(data.get("display_name") or "").strip()
        if not table_id:
            return None
        query = db.query(SchemaColumn).filter(SchemaColumn.table_id == table_id)
        if physical:
            row = query.filter(SchemaColumn.physical_name == physical).first()
        elif display:
            row = query.filter(func.lower(SchemaColumn.display_name) == display.lower()).first()
        else:
            row = None
        return AppliedChange("column", row.display_name, row.id) if row else None

    if path == "/v1/schema/relations":
        from models.ui_schema import SchemaRelation

        fk = _uuid(data.get("fk_column_id"))
        if fk:
            row = (
                db.query(SchemaRelation)
                .filter(SchemaRelation.client_id == user.client_id, SchemaRelation.fk_column_id == fk)
                .first()
            )
            return AppliedChange("relationship", row.display_name, row.id) if row else None
    return None
