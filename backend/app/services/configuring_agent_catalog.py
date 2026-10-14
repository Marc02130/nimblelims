"""What the model is told, and how its bodies are turned into real requests.

UAT on 145f6b3 (D-4, D-5, D-7, G5): the model had no catalog ids and no request
formats, so it sent ``{"name": ..., "table": "blood"}`` to POST /v1/schema/columns,
called routes that don't exist (/v1/layouts, /v1/container-types, /v1/relations),
proposed new tables for sample types that are already list entries, and on rerun
proposed everything again. This module:

* ``route_formats``: the request format for every allowed route, generated from
  ``configuring_agent_allow._ALLOWED`` and the routers' own Pydantic schemas.
* ``catalog_snapshot`` / ``catalog_text``: the confirmer's client's tables (with
  ids), lists (with ids and entries), roles, container types, and screen keys.
* ``resolve_body``: names -> ids and the model's usual key mistakes -> the real
  field names, at proposal time and again at apply time (so a table created by an
  earlier row in the same apply resolves).
* ``reuse_gap``: a new table for a sample type / matrix / container type, or a list
  of per-run values (lot numbers), is a stop with the reason.
* ``describe_change``: before/after for a row; ``changed`` False means a rerun
  no-op.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func

from models.user import User

SEED_LISTS = ("sample_types", "matrix_types")
# Per-run values are recorded when the work happens. They are never list values
# or configuration (UAT: the model invented kit lot numbers).
_RUN_VALUE_RE = re.compile(r"\b(lot|lots|lot[_ ]?(no|number|numbers)|expiry|expiration|serial)\b", re.I)
_SEED_KINDS = {
    "sample_type": "sample_types",
    "sample_types": "sample_types",
    "sample type": "sample_types",
    "specimen": "sample_types",
    "specimen_type": "sample_types",
    "matrix": "matrix_types",
    "matrix_type": "matrix_types",
    "matrix_types": "matrix_types",
    "container_type": "/containers/types",
    "container": "/containers/types",
}


# ---------------------------------------------------------------- formats ---


def _schema_for(method: str, kind: str):
    from app.schemas.container import ContainerTypeCreate, ContentsUpdate
    from app.schemas.experiment import ExperimentTemplateCreate, ExperimentTemplateUpdate
    from app.schemas.list import ListCreate, ListEntryCreate, ListEntryUpdate, ListUpdate
    from app.schemas.sample_type_transition import SampleTypeTransitionCreate
    from app.schemas.ui_schema import (
        PrivilegeIn,
        SchemaColumnCreate,
        SchemaLayoutPut,
        SchemaRelationCreate,
        SchemaTableCreate,
    )
    from app.schemas.user import RolePermissionsUpdate

    table = {
        ("POST", "table"): SchemaTableCreate,
        ("POST", "column"): SchemaColumnCreate,
        ("PUT", "layout"): SchemaLayoutPut,
        ("PUT", "privilege"): PrivilegeIn,
        ("POST", "relationship"): SchemaRelationCreate,
        ("POST", "list"): ListCreate,
        ("PATCH", "list"): ListUpdate,
        ("POST", "list_entry"): ListEntryCreate,
        ("PATCH", "list_entry"): ListEntryUpdate,
        ("POST", "experiment_template"): ExperimentTemplateCreate,
        ("PATCH", "experiment_template"): ExperimentTemplateUpdate,
        ("POST", "container_type"): ContainerTypeCreate,
        ("POST", "sample_type_transition"): SampleTypeTransitionCreate,
        ("PUT", "role_permissions"): RolePermissionsUpdate,
        ("PATCH", "contents_amount"): ContentsUpdate,
    }
    return table.get((method, kind))


_PATH_NAMES = {
    r"^/v1/schema/tables/[^/]+/deprecate$": "/v1/schema/tables/{table_id}/deprecate",
    r"^/v1/schema/columns/[^/]+/deprecate$": "/v1/schema/columns/{column_id}/deprecate",
    r"^/lists/[^/]+$": "/lists/{list_id}",
    r"^/lists/[^/]+/entries$": "/lists/{list_name}/entries",
    r"^/lists/[^/]+/entries/[^/]+$": "/lists/{list_name}/entries/{entry_id}",
    r"^/v1/experiment-templates/[^/]+$": "/v1/experiment-templates/{template_id}",
    r"^/users/[^/]+$": "/users/{user_id}",
    r"^/roles/[^/]+/permissions$": "/roles/{role_id}/permissions",
    r"^/containers/[^/]+/contents/[^/]+$": "/containers/{container_id}/contents/{sample_id}",
}


def _readable_path(pattern: str) -> str:
    if pattern in _PATH_NAMES:
        return _PATH_NAMES[pattern]
    return pattern.strip("^$")


def _type_of(prop: dict, defs: dict) -> str:
    if "$ref" in prop:
        name = prop["$ref"].split("/")[-1]
        return _fields_text(defs.get(name, {}), defs)
    if "enum" in prop:
        return "|".join(str(v) for v in prop["enum"])
    if "anyOf" in prop:
        kinds = [_type_of(p, defs) for p in prop["anyOf"] if p.get("type") != "null"]
        return (kinds[0] if len(kinds) == 1 else "|".join(kinds)) + " or null"
    kind = prop.get("type") or "any"
    if prop.get("format") == "uuid":
        return "uuid"
    if kind == "array":
        return "[" + _type_of(prop.get("items") or {}, defs) + "]"
    return kind


def _fields_text(schema: dict, defs: dict) -> str:
    required = set(schema.get("required") or [])
    parts = []
    for name, prop in (schema.get("properties") or {}).items():
        mark = "" if name in required else "?"
        parts.append(f"{name}{mark}: {_type_of(prop, defs)}")
    return "{" + ", ".join(parts) + "}"


def route_formats() -> list[dict[str, str]]:
    """Every route the agent may call, with its body format, from the real schemas."""
    from app.services.configuring_agent_allow import _ALLOWED

    rows = []
    for method, pattern, group, permission, kind in _ALLOWED:
        path = _readable_path(pattern.pattern)
        schema = _schema_for(method, kind)
        if path.endswith("/deprecate"):
            body = "{} (no body)"
        elif path == "/users/{user_id}":
            body = "{role_id: uuid} (role only)"
        elif path == "/v1/schema/privileges":
            body = "[" + _fields_text(schema.model_json_schema(), {}) + "] (a JSON array of rows)"
        elif path.startswith("/containers/") and "contents" in path:
            body = "{amount: 0} (exactly this)"
        elif schema is not None:
            full = schema.model_json_schema()
            body = _fields_text(full, full.get("$defs") or {})
        else:
            body = "{}"
        rows.append({"method": method, "path": path, "body": body, "group": group, "permission": permission})
    return rows


def route_formats_text() -> str:
    lines = [f"{row['method']} {row['path']} body {row['body']}" for row in route_formats()]
    return "\n".join(lines)


# ---------------------------------------------------------------- catalog ---


def catalog_snapshot(db, user: User) -> dict[str, Any]:
    """The confirmer's client's catalog with ids. Registers the Schema catalog on
    view (same as the Schema screen), never DDL."""
    from models.container import ContainerType
    from models.list import List as ListModel, ListEntry
    from models.ui_schema import SchemaColumn
    from models.user import Role
    from app.schemas.ui_schema import SCREEN_KEYS
    from app.services.ui_schema_service import UiSchemaService

    tables = []
    try:
        rows = UiSchemaService(db, user).list_tables()
    except Exception:  # noqa: BLE001 - the prompt still works without tables
        rows = []
    for table in rows:
        columns = (
            db.query(SchemaColumn)
            .filter(SchemaColumn.table_id == table.id)
            .order_by(SchemaColumn.sort_order, SchemaColumn.physical_name)
            .all()
        )
        tables.append(
            {
                "id": str(table.id),
                "physical_name": table.physical_name,
                "display_name": table.display_name,
                "kind": table.kind,
                "columns": [
                    {"id": str(c.id), "physical_name": c.physical_name, "display_name": c.display_name}
                    for c in columns
                ],
            }
        )
    lists = []
    for row in db.query(ListModel).filter(ListModel.active == True).order_by(ListModel.name).all():  # noqa: E712
        entries = (
            db.query(ListEntry)
            .filter(ListEntry.list_id == row.id, ListEntry.active == True)  # noqa: E712
            .order_by(ListEntry.name)
            .all()
        )
        lists.append(
            {"id": str(row.id), "name": row.name, "entries": [{"id": str(e.id), "name": e.name} for e in entries]}
        )
    roles = [
        {"id": str(r.id), "name": r.name}
        for r in db.query(Role).filter(Role.active == True).order_by(Role.name).all()  # noqa: E712
    ]
    containers = [
        {"id": str(c.id), "name": c.name}
        for c in db.query(ContainerType).filter(ContainerType.active == True).order_by(ContainerType.name).all()  # noqa: E712
    ]
    return {
        "tables": tables,
        "lists": lists,
        "roles": roles,
        "container_types": containers,
        "screen_keys": list(SCREEN_KEYS),
    }


def catalog_text(snapshot: dict[str, Any]) -> str:
    lines = ["Schema tables (id physical_name \"display\" kind: columns):"]
    for t in snapshot.get("tables") or []:
        cols = ", ".join(f"{c['physical_name']}={c['id']}" for c in t["columns"])
        lines.append(f"- {t['id']} {t['physical_name']} \"{t['display_name']}\" {t['kind']}: {cols}")
    lines.append("Lists (id name: entries):")
    for item in snapshot.get("lists") or []:
        entries = ", ".join(f"{e['name']}={e['id']}" for e in item["entries"])
        lines.append(f"- {item['id']} {item['name']}: {entries}")
    lines.append("Roles: " + ", ".join(f"{r['name']}={r['id']}" for r in snapshot.get("roles") or []))
    lines.append(
        "Container types: " + (", ".join(f"{c['name']}={c['id']}" for c in snapshot.get("container_types") or []) or "none")
    )
    lines.append("Layout screen_key values: " + ", ".join(snapshot.get("screen_keys") or []))
    return "\n".join(lines)


# ------------------------------------------------------------- resolution ---


def _uuid(value) -> Optional[UUID]:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).strip().lower()).strip("_")


def find_table(db, user: User, ref) -> Optional[Any]:
    from models.ui_schema import SchemaTable

    if ref in (None, ""):
        return None
    query = db.query(SchemaTable).filter(SchemaTable.client_id == user.client_id)
    as_id = _uuid(ref)
    if as_id:
        return query.filter(SchemaTable.id == as_id).first()
    text = str(ref).strip()
    slug = _slug(text)
    names = {text, slug, f"x_{slug}", f"lab_{slug}"}
    row = query.filter(SchemaTable.physical_name.in_(names)).first()
    if row is None:
        row = query.filter(func.lower(SchemaTable.display_name) == text.lower()).first()
    if row is None and slug.endswith("s"):
        row = query.filter(SchemaTable.physical_name.in_({slug[:-1], f"x_{slug[:-1]}"})).first()
    if row is None:
        row = query.filter(SchemaTable.physical_name.in_({slug + "s", f"x_{slug}s"})).first()
    return row


def find_column(db, table_id, ref) -> Optional[Any]:
    from models.ui_schema import SchemaColumn

    if ref in (None, "") or table_id is None:
        return None
    query = db.query(SchemaColumn).filter(SchemaColumn.table_id == table_id)
    as_id = _uuid(ref)
    if as_id:
        return query.filter(SchemaColumn.id == as_id).first()
    text = str(ref).strip()
    slug = _slug(text)
    row = query.filter(SchemaColumn.physical_name.in_({text, slug, f"x_{slug}", f"{slug}_id"})).first()
    if row is None:
        row = query.filter(func.lower(SchemaColumn.display_name) == text.lower()).first()
    return row


def find_list(db, ref) -> Optional[Any]:
    from models.list import List as ListModel
    from app.routers.lists import _LIST_NAME_ALIASES

    if ref in (None, ""):
        return None
    as_id = _uuid(ref)
    if as_id:
        return db.query(ListModel).filter(ListModel.id == as_id).first()
    text = str(ref).strip()
    names = {text, _slug(text), _LIST_NAME_ALIASES.get(_slug(text), _slug(text))}
    row = db.query(ListModel).filter(ListModel.name.in_(names)).first()
    if row is None:
        row = db.query(ListModel).filter(func.lower(ListModel.name) == text.lower()).first()
    return row


def find_entry(db, list_name: str, ref) -> Optional[Any]:
    from models.list import ListEntry

    as_id = _uuid(ref)
    lst = find_list(db, list_name)
    if lst is None or ref in (None, ""):
        return None
    query = db.query(ListEntry).filter(ListEntry.list_id == lst.id)
    if as_id:
        return query.filter(ListEntry.id == as_id).first()
    return query.filter(func.lower(ListEntry.name) == str(ref).strip().lower()).first()


def find_role(db, ref) -> Optional[Any]:
    from models.user import Role

    if ref in (None, ""):
        return None
    as_id = _uuid(ref)
    if as_id:
        return db.query(Role).filter(Role.id == as_id).first()
    return db.query(Role).filter(func.lower(Role.name) == str(ref).strip().lower()).first()


def _first(data: dict, *keys):
    for key in keys:
        if data.get(key) not in (None, ""):
            return data.get(key)
    return None


def _id_or_ref(row, ref):
    return str(row.id) if row is not None else ref


def resolve_body(db, user: User, method: str, path: str, body: Any) -> Any:
    """The model's body as the real API expects it. Never invents a value:
    a name that doesn't resolve is left as is, so the API's own 422 stops the row."""
    method = (method or "").upper()
    path = (path or "").split("?", 1)[0].rstrip("/")
    if isinstance(body, list):
        if path == "/v1/schema/privileges":
            return [_privilege_row(db, user, row) for row in body]
        return body
    if not isinstance(body, dict):
        return body
    data = dict(body)

    if method == "POST" and path == "/v1/schema/tables":
        out = {"display_name": _first(data, "display_name", "name", "label", "title")}
        if data.get("physical_name"):
            out["physical_name"] = data["physical_name"]
        return out

    if method == "POST" and path == "/v1/schema/columns":
        table_ref = _first(data, "table_id", "table", "table_name", "table_physical_name")
        table = find_table(db, user, table_ref)
        out: dict[str, Any] = {
            "table_id": _id_or_ref(table, table_ref),
            "display_name": _first(data, "display_name", "name", "label", "title"),
            "data_type": _first(data, "data_type", "type") or "text",
        }
        for key in ("physical_name", "sop_hint", "sort_order"):
            if data.get(key) is not None:
                out[key] = data[key]
        if "nullable" in data:
            out["nullable"] = bool(data["nullable"])
        elif _first(data, "required", "is_required") is not None:
            out["nullable"] = not bool(_first(data, "required", "is_required"))
        list_ref = _first(data, "list_id", "list_name", "list")
        if list_ref is not None:
            found = find_list(db, list_ref)
            out["list_id"] = _id_or_ref(found, list_ref)
            out["data_type"] = "list"
        return out

    if method == "POST" and path == "/v1/schema/relations":
        from_ref = _first(data, "from_table_id", "from_table", "parent_table", "from")
        to_ref = _first(data, "to_table_id", "to_table", "child_table", "to")
        from_table = find_table(db, user, from_ref)
        to_table = find_table(db, user, to_ref)
        fk_ref = _first(data, "fk_column_id", "fk_column", "foreign_key", "foreign_key_column", "column")
        fk = find_column(db, to_table.id if to_table else None, fk_ref)
        cardinality = _first(data, "cardinality", "relation_type", "type") or "one_to_many"
        out = {
            "display_name": _first(data, "display_name", "name", "label")
            or f"{from_ref} to {to_ref}",
            "from_table_id": _id_or_ref(from_table, from_ref),
            "to_table_id": _id_or_ref(to_table, to_ref),
            "fk_column_id": _id_or_ref(fk, fk_ref),
            "cardinality": str(cardinality).replace("-", "_").lower(),
        }
        return out

    if method == "PUT" and path == "/v1/schema/layouts":
        role_ref = _first(data, "role_id", "role", "role_name")
        role = find_role(db, role_ref)
        screen = _first(data, "screen_key", "screen") or ""
        samples = find_table(db, user, data.get("table") or "samples")
        fields = []
        for index, item in enumerate(data.get("fields") or []):
            if isinstance(item, dict):
                col_ref = _first(item, "column_id", "column", "name", "physical_name")
                section = item.get("section")
                order = item.get("sort_order", index)
            else:
                col_ref, section, order = item, None, index
            column = find_column(db, samples.id if samples else None, col_ref)
            fields.append({"column_id": _id_or_ref(column, col_ref), "section": section, "sort_order": order})
        return {"role_id": _id_or_ref(role, role_ref), "screen_key": screen, "fields": fields}

    if method == "PUT" and path == "/v1/schema/privileges":
        rows = data.get("privileges") or data.get("items") or [data]
        return [_privilege_row(db, user, row) for row in rows]

    if path == "/lists" and method == "POST":
        out = {"name": _first(data, "name", "display_name", "label")}
        if data.get("description"):
            out["description"] = data["description"]
        return out

    if re.match(r"^/lists/[^/]+/entries$", path) and method == "POST":
        out = {"name": _first(data, "name", "value", "label", "display_name")}
        if data.get("description"):
            out["description"] = data["description"]
        if "active" in data:
            out["active"] = data["active"]
        return out

    if path == "/containers/types" and method == "POST":
        if "name" not in data and _first(data, "display_name", "label"):
            data["name"] = _first(data, "display_name", "label")
        for key in ("display_name", "label"):
            data.pop(key, None)
        return data

    if path == "/v1/sample-type-transitions" and method == "POST":
        out = dict(data)
        for key, aliases in (
            ("source_sample_type", ("source_sample_type", "source", "from", "source_sample_type_name")),
            ("allowed_dest_sample_type", ("allowed_dest_sample_type", "dest", "to", "destination", "allowed_dest_sample_type_name")),
        ):
            ref = _first(data, *aliases)
            entry = find_entry(db, "sample_types", ref)
            out[key] = _id_or_ref(entry, ref)
            for alias in aliases:
                if alias != key:
                    out.pop(alias, None)
        if out.get("operation"):
            out["operation"] = str(out["operation"]).lower()
        return out

    return data


def _privilege_row(db, user: User, row) -> Any:
    if not isinstance(row, dict):
        return row
    role_ref = _first(row, "role_id", "role", "role_name")
    table_ref = _first(row, "table_id", "table", "table_name")
    role = find_role(db, role_ref)
    table = find_table(db, user, table_ref)
    out = {
        "role_id": _id_or_ref(role, role_ref),
        "table_id": _id_or_ref(table, table_ref),
        "access": row.get("access"),
    }
    col_ref = _first(row, "column_id", "column", "column_name")
    if col_ref is not None:
        out["column_id"] = _id_or_ref(find_column(db, table.id if table else None, col_ref), col_ref)
    return out


# ------------------------------------------------------------ reuse rules ---


def reuse_gap(method: str, path: str, body: Any) -> Optional[str]:
    """Stop rows that duplicate a seed list as a table, or configure per-run values."""
    method = (method or "").upper()
    path = (path or "").split("?", 1)[0].rstrip("/")
    data = body if isinstance(body, dict) else {}
    if method == "POST" and path == "/v1/schema/tables":
        hint = str(_first(data, "table_type", "entity_type", "category", "kind", "type") or "").strip().lower()
        name = _slug(_first(data, "display_name", "name", "label", "physical_name") or "")
        target = _SEED_KINDS.get(hint) or _SEED_KINDS.get(hint.replace(" ", "_"))
        if not target:
            for key, value in _SEED_KINDS.items():
                if name in (_slug(key), _slug(key) + "s", "x_" + _slug(key), "x_" + _slug(key) + "s"):
                    target = value
                    break
        if target == "/containers/types":
            return (
                "Container types are created with POST /containers/types, not as a new Schema table."
            )
        if target:
            return (
                f"Sample types and matrices already exist as entries in the {target} list. "
                f"Add a value with POST /lists/{target}/entries instead of a new table."
            )
    if method == "POST" and path == "/lists":
        name = str(_first(data, "name", "display_name") or "")
        if _RUN_VALUE_RE.search(name.replace("_", " ")):
            return (
                "Lot numbers, expiry dates and serials are recorded when the work is done. "
                "They are not configuration values."
            )
    entry = re.match(r"^/lists/([^/]+)/entries$", path)
    if method == "POST" and entry and _RUN_VALUE_RE.search(entry.group(1).replace("_", " ")):
        return (
            "Lot numbers, expiry dates and serials are recorded when the work is done. "
            "They are not configuration values."
        )
    return None


# ----------------------------------------------------------- before/after ---


def _clean(value):
    if isinstance(value, UUID):
        return str(value)
    return value


def describe_change(db, user: User, method: str, path: str, body: Any) -> dict[str, Any]:
    """{before, after, changed} for a row against the live configuration.

    ``changed`` False: applying the row would change nothing (a rerun no-op).
    ``before`` None: the object does not exist yet.
    """
    from app.services.configuring_agent_rerun import existing_change

    method = (method or "").upper()
    path = (path or "").split("?", 1)[0].rstrip("/")
    resolved = resolve_body(db, user, method, path, body)
    data = resolved if isinstance(resolved, dict) else {}
    after = resolved

    if method == "POST" and not path.endswith("/deprecate"):
        present = existing_change(db, user, method, path, resolved)
        if present is not None:
            return {"before": {"id": str(present.target_id), "name": present.name}, "after": after, "changed": False}
        return {"before": None, "after": after, "changed": True}

    if path.endswith("/deprecate"):
        from models.ui_schema import SchemaColumn, SchemaTable

        model = SchemaTable if "/tables/" in path else SchemaColumn
        row = db.query(model).filter(model.id == _uuid(path.split("/")[-2])).first() if _uuid(path.split("/")[-2]) else None
        before = {"status": row.status} if row is not None else None
        return {"before": before, "after": {"status": "deprecated"}, "changed": not (row is not None and row.status == "deprecated")}

    current: Optional[dict] = None
    try:
        current = _current_values(db, user, method, path, resolved)
    except Exception:  # noqa: BLE001 - a diff is advisory; apply re-checks through the API
        current = None
    if current is None:
        return {"before": None, "after": after, "changed": True}
    if isinstance(after, dict):
        compare = {key: _clean(current.get(key)) for key in data}
        changed = any(_norm(compare.get(k)) != _norm(v) for k, v in data.items())
        return {"before": compare, "after": after, "changed": changed}
    return {"before": current.get("_rows"), "after": after, "changed": _norm(current.get("_rows")) != _norm(after)}


def _norm(value):
    if isinstance(value, list):
        return sorted((_norm(v) for v in value), key=repr)
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items() if v is not None}
    if isinstance(value, UUID):
        return str(value)
    return value


def _current_values(db, user: User, method: str, path: str, body: Any) -> Optional[dict]:
    from models.list import List as ListModel, ListEntry

    match = re.match(r"^/lists/([^/]+)$", path)
    if method == "PATCH" and match:
        row = find_list(db, match.group(1))
        return None if row is None else {"name": row.name, "description": row.description, "active": row.active}
    match = re.match(r"^/lists/([^/]+)/entries/([^/]+)$", path)
    if method == "PATCH" and match:
        row = db.query(ListEntry).filter(ListEntry.id == _uuid(match.group(2))).first() if _uuid(match.group(2)) else None
        return None if row is None else {"name": row.name, "description": row.description, "active": row.active}
    match = re.match(r"^/users/([^/]+)$", path)
    if method == "PATCH" and match:
        target = db.query(User).filter(User.id == _uuid(match.group(1))).first() if _uuid(match.group(1)) else None
        return None if target is None else {"role_id": str(target.role_id) if target.role_id else None}
    match = re.match(r"^/roles/([^/]+)/permissions$", path)
    if method == "PUT" and match:
        from models.user import role_permissions

        role_id = _uuid(match.group(1))
        if role_id is None:
            return None
        ids = [str(r[0]) for r in db.query(role_permissions.c.permission_id).filter(role_permissions.c.role_id == role_id).all()]
        return {"permission_ids": ids}
    match = re.match(r"^/v1/experiment-templates/([^/]+)$", path)
    if method == "PATCH" and match:
        from models.experiment import ExperimentTemplate

        row = db.query(ExperimentTemplate).filter(ExperimentTemplate.id == _uuid(match.group(1))).first()
        return None if row is None else {"name": row.name, "description": row.description, "active": row.active}
    match = re.match(r"^/containers/([^/]+)/contents/([^/]+)$", path)
    if method == "PATCH" and match:
        from models.container import Contents

        row = (
            db.query(Contents)
            .filter(Contents.container_id == _uuid(match.group(1)), Contents.sample_id == _uuid(match.group(2)))
            .first()
        )
        if row is None:
            return None
        amount = float(row.amount) if row.amount is not None else None
        return {"amount": 0 if amount == 0 else amount}
    if method == "PUT" and path == "/v1/schema/layouts":
        from models.ui_schema import SchemaLayout, SchemaLayoutField

        data = body if isinstance(body, dict) else {}
        role_id, screen = _uuid(data.get("role_id")), data.get("screen_key")
        if role_id is None:
            return None
        layout = (
            db.query(SchemaLayout)
            .filter(SchemaLayout.client_id == user.client_id, SchemaLayout.role_id == role_id, SchemaLayout.screen_key == screen)
            .first()
        )
        if layout is None:
            return None
        fields = [
            {"column_id": str(f.column_id), "section": f.section, "sort_order": f.sort_order}
            for f in db.query(SchemaLayoutField).filter(SchemaLayoutField.layout_id == layout.id).all()
        ]
        return {"role_id": str(role_id), "screen_key": screen, "fields": fields}
    if method == "PUT" and path == "/v1/schema/privileges":
        from models.ui_schema import SchemaPrivilege

        rows = body if isinstance(body, list) else []
        current = []
        for row in rows:
            if not isinstance(row, dict):
                return None
            role_id, table_id = _uuid(row.get("role_id")), _uuid(row.get("table_id"))
            if role_id is None or table_id is None:
                return None
            column_id = _uuid(row.get("column_id")) if row.get("column_id") else None
            found = (
                db.query(SchemaPrivilege)
                .filter(
                    SchemaPrivilege.client_id == user.client_id,
                    SchemaPrivilege.role_id == role_id,
                    SchemaPrivilege.table_id == table_id,
                    SchemaPrivilege.column_id == column_id if column_id else SchemaPrivilege.column_id.is_(None),
                )
                .first()
            )
            entry = {"role_id": str(role_id), "table_id": str(table_id), "access": found.access if found else None}
            if column_id:
                entry["column_id"] = str(column_id)
            current.append(entry)
        return {"_rows": current}
    return None
