"""Apply accepted steps through existing APIs, as one transaction.

Services commit on the session they are given. AtomicSession turns those commits
into flushes. The caller commits once at the end, or rolls back so nothing remains.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import get_user_permissions
from app.services.configuring_agent_allow import Classified, classify_call
from models.user import Permission, Role, User, role_permissions


class CannotExpress(Exception):
    def __init__(self, gap: str):
        self.gap = gap
        super().__init__(gap)


class PermissionDenied(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


@dataclass
class AppliedChange:
    kind: str
    name: str
    target_id: Optional[UUID]


class AtomicSession:
    """Flush instead of commit. Rollback still rolls the real transaction back."""

    def __init__(self, session):
        object.__setattr__(self, "_session", session)

    def commit(self):
        self._session.flush()

    def rollback(self):
        self._session.rollback()

    def __getattr__(self, name):
        return getattr(self._session, name)


def error_text(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("detail") or detail)
    return str(detail)


def _uuid_from_path(path: str) -> UUID:
    return UUID(path.rstrip("/").split("/")[-1])


def _permission_names(db, role_id: UUID) -> set[str]:
    rows = (
        db.query(Permission.name)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .filter(role_permissions.c.role_id == role_id, Permission.active == True)  # noqa: E712
        .all()
    )
    return {row[0] for row in rows}


def _require(user: User, db, classified: Classified) -> None:
    held = set(get_user_permissions(user, db))
    needed = classified.permission or ""
    if needed == "layout:edit":
        if "layout:edit" in held or "schema:edit" in held:
            return
        raise PermissionDenied("Permission 'layout:edit' required")
    if needed and needed not in held:
        raise PermissionDenied(f"Permission '{needed}' required")


async def execute_step(db, user: User, method: str, path: str, body: Any) -> list[AppliedChange]:
    payload = body if isinstance(body, dict) else {}
    classified = classify_call(method, path, payload)
    if not classified.ok:
        raise CannotExpress(classified.gap or "This change cannot be applied through configuration APIs.")
    _require(user, db, classified)
    try:
        return await _dispatch(db, user, method.upper(), path, body, classified.kind or "other")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _dispatch(db, user: User, method: str, path: str, body: dict, kind: str) -> list[AppliedChange]:
    if path == "/roles" or path.startswith("/roles/"):
        return await _roles(db, user, method, path, body)
    if path.startswith("/v1/schema/"):
        return _schema(db, user, method, path, body, kind)
    if path == "/lists" or path.startswith("/lists/"):
        return await _lists(db, user, method, path, body, kind)
    if path.startswith("/v1/experiment-templates"):
        return _templates(db, user, method, path, body)
    if path == "/containers/types":
        return await _container_type(db, user, body)
    if path == "/v1/sample-type-transitions":
        return _transition(db, user, body)
    if path.startswith("/users/"):
        return await _user_role(db, user, path, body)
    raise CannotExpress(f"No configuration API matches {method} {path}.")


def _schema(db, user: User, method: str, path: str, body: dict, kind: str) -> list[AppliedChange]:
    from app.schemas.ui_schema import (
        ConfirmBody,
        PrivilegeIn,
        SchemaColumnCreate,
        SchemaLayoutPut,
        SchemaRelationCreate,
        SchemaTableCreate,
    )
    from app.services.ui_schema_service import UiSchemaService

    svc = UiSchemaService(db, user)
    if method == "POST" and path == "/v1/schema/tables":
        data = SchemaTableCreate.model_validate(body)
        row = svc.create_table(data.display_name, data.physical_name)
        read = svc.table_read(row)
        return [AppliedChange("table", read["display_name"], read["id"])]
    if path.endswith("/deprecate") and "/tables/" in path:
        row = svc.deprecate_table(_uuid_from_path(path.replace("/deprecate", "")))
        read = svc.table_read(row)
        return [AppliedChange("table", read["display_name"], read["id"])]
    if path.endswith("/drop") and "/tables/" in path:
        svc.drop_table(_uuid_from_path(path.replace("/drop", "")), ConfirmBody.model_validate(body).confirm)
        return [AppliedChange("table", path, _uuid_from_path(path.replace("/drop", "")))]
    if method == "POST" and path == "/v1/schema/columns":
        data = SchemaColumnCreate.model_validate(body)
        column = svc.add_column(
            table_id=data.table_id,
            display_name=data.display_name,
            data_type=data.data_type,
            nullable=data.nullable,
            list_id=data.list_id,
            sop_hint=data.sop_hint,
            sort_order=data.sort_order,
            physical_name=data.physical_name,
        )
        return [AppliedChange("column", column.display_name, column.id)]
    if path.endswith("/deprecate") and "/columns/" in path:
        read = svc.deprecate_column(_uuid_from_path(path.replace("/deprecate", "")))
        return [AppliedChange("column", read["display_name"], read["id"])]
    if path.endswith("/drop") and "/columns/" in path:
        column_id = _uuid_from_path(path.replace("/drop", ""))
        svc.drop_column(column_id, ConfirmBody.model_validate(body).confirm)
        return [AppliedChange("column", str(column_id), column_id)]
    if method == "PUT" and path == "/v1/schema/layouts":
        data = SchemaLayoutPut.model_validate(body)
        layout = svc.put_layout(data.role_id, data.screen_key, [field.model_dump() for field in data.fields])
        read = svc.layout_read(layout)
        return [AppliedChange("layout", read.get("screen_key") or "layout", read.get("id"))]
    if method == "PUT" and path == "/v1/schema/privileges":
        rows = body if isinstance(body, list) else body.get("privileges") or body.get("items") or []
        read = svc.put_privileges([PrivilegeIn.model_validate(item).model_dump() for item in rows])
        return [AppliedChange("privilege", row.access, row.id) for row in read] or [
            AppliedChange("privilege", "privileges", None)
        ]
    if method == "POST" and path == "/v1/schema/relations":
        data = SchemaRelationCreate.model_validate(body)
        read = svc.create_relation(
            display_name=data.display_name,
            from_table_id=data.from_table_id,
            to_table_id=data.to_table_id,
            fk_column_id=data.fk_column_id,
            cardinality=data.cardinality,
        )
        return [AppliedChange("relationship", read["display_name"], read["id"])]
    if method == "DELETE" and path.startswith("/v1/schema/relations/"):
        relation_id = _uuid_from_path(path)
        svc.delete_relation(relation_id)
        return [AppliedChange("relationship", str(relation_id), relation_id)]
    raise CannotExpress(f"No configuration API matches {method} {path}.")


async def _lists(db, user, method: str, path: str, body: dict, kind: str) -> list[AppliedChange]:
    from app.routers.lists import create_list, create_list_entry, delete_list, delete_list_entry, update_list, update_list_entry
    from app.schemas.list import ListCreate, ListEntryCreate, ListEntryUpdate, ListUpdate

    if method == "POST" and path == "/lists":
        created = await create_list(ListCreate.model_validate(body), user, db)
        return [AppliedChange("list", created.name, created.id)]
    entry = re.match(r"^/lists/([^/]+)/entries$", path)
    if method == "POST" and entry:
        created = await create_list_entry(entry.group(1), ListEntryCreate.model_validate(body), user, db)
        return [AppliedChange("list_entry", created.name, created.id)]
    if method == "PATCH" and re.match(r"^/lists/[^/]+$", path):
        updated = await update_list(_uuid_from_path(path), ListUpdate.model_validate(body), user, db)
        return [AppliedChange("list", updated.name, updated.id)]
    if method == "DELETE" and re.match(r"^/lists/[^/]+$", path):
        list_id = _uuid_from_path(path)
        await delete_list(list_id, user, db)
        return [AppliedChange("list", str(list_id), list_id)]
    entry_one = re.match(r"^/lists/([^/]+)/entries/([^/]+)$", path)
    if entry_one and method == "PATCH":
        updated = await update_list_entry(
            entry_one.group(1), UUID(entry_one.group(2)), ListEntryUpdate.model_validate(body), user, db
        )
        return [AppliedChange("list_entry", updated.name, updated.id)]
    if entry_one and method == "DELETE":
        entry_id = UUID(entry_one.group(2))
        await delete_list_entry(entry_one.group(1), entry_id, user, db)
        return [AppliedChange("list_entry", str(entry_id), entry_id)]
    raise CannotExpress(f"No configuration API matches {method} {path}.")


def _templates(db, user, method: str, path: str, body: dict) -> list[AppliedChange]:
    from app.schemas.experiment import ExperimentTemplateCreate, ExperimentTemplateUpdate
    from app.services.experiment_service import ExperimentService

    svc = ExperimentService(db, user, auto_commit=False)
    if method == "POST":
        created = svc.create_template(ExperimentTemplateCreate.model_validate(body))
        return [AppliedChange("experiment_template", created.name, created.id)]
    updated = svc.update_template(_uuid_from_path(path), ExperimentTemplateUpdate.model_validate(body))
    return [AppliedChange("experiment_template", updated.name, updated.id)]


async def _container_type(db, user, body: dict) -> list[AppliedChange]:
    from app.routers.containers import create_container_type
    from app.schemas.container import ContainerTypeCreate

    created = await create_container_type(ContainerTypeCreate.model_validate(body), user, db)
    return [AppliedChange("container_type", created.name, created.id)]


def _transition(db, user, body: dict) -> list[AppliedChange]:
    from app.schemas.sample_type_transition import SampleTypeTransitionCreate
    from app.services.sample_type_transition_service import SampleTypeTransitionService

    created = SampleTypeTransitionService(db, user).create(SampleTypeTransitionCreate.model_validate(body))
    name = created.source_sample_type_name or str(created.id)
    return [AppliedChange("sample_type_transition", name, created.id)]


async def _user_role(db, user, path: str, body: dict) -> list[AppliedChange]:
    from app.routers.users import update_user
    from app.schemas.user import UserUpdate

    updated = await update_user(_uuid_from_path(path), UserUpdate.model_validate(body), user, db)
    return [AppliedChange("user_role", updated.name, updated.id)]


async def _roles(db, user, method: str, path: str, body: dict) -> list[AppliedChange]:
    from app.routers.roles import update_role_permissions
    from app.schemas.user import RolePermissionsUpdate

    role_id = UUID(path.split("/")[2])
    data = RolePermissionsUpdate.model_validate(body)
    names = (
        db.query(Permission.name)
        .filter(Permission.id.in_(data.permission_ids), Permission.active == True)  # noqa: E712
        .all()
    )
    proposed = {row[0] for row in names}
    if "schema:edit" in proposed and "schema:edit" not in _permission_names(db, role_id):
        raise CannotExpress("Lab personnel input does not grant schema:edit.")
    role = db.query(Role).filter(Role.id == role_id).first()
    label = role.name if role else str(role_id)
    await update_role_permissions(role_id, data, user, db)
    return [AppliedChange("role_permissions", label, role_id)]
