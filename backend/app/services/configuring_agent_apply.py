"""Apply included steps through existing APIs, as one transaction.

Never a drop or a delete: ``execute_step`` refuses them before dispatch, and the
dispatcher has no code path for them (L-B, L-3, FB-11).

The agent acts as the confirming user (L-2): every call is checked against that
user's own permissions, and a call that would give anyone (including that user)
a permission the user does not already hold is a stop, never an apply.

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
from app.services.configuring_agent_allow import Classified, classify_call, is_drop_or_delete
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
    # True when the object is already exactly as proposed: nothing was written.
    noop: bool = False


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


def missing_permission(user: User, db, classified: Classified) -> Optional[str]:
    """The permission this user lacks for the call, or None."""
    try:
        _require(user, db, classified)
    except PermissionDenied:
        return classified.permission
    return None


def _role_permission_names(db, role_id) -> set[str]:
    return _permission_names(db, role_id) if role_id else set()


def escalation_gap(db, user: User, method: str, path: str, body: Any) -> Optional[str]:
    """A stop reason when the call would grant a privilege the user lacks.

    The agent never grants privileges (Marc 2026-10-07). Self-escalation is a
    stop: changing your own role, adding permissions to your own role, or
    granting anyone a permission you don't hold yourself.
    """
    method = (method or "").upper()
    path = (path or "").split("?", 1)[0].rstrip("/")
    data = body if isinstance(body, dict) else {}
    held = set(get_user_permissions(user, db))
    role_match = re.match(r"^/roles/([^/]+)/permissions$", path)
    if method == "PUT" and role_match:
        try:
            role_id = UUID(role_match.group(1))
            ids = [UUID(str(item)) for item in data.get("permission_ids") or []]
        except ValueError:
            return None
        proposed = {
            row[0]
            for row in db.query(Permission.name)
            .filter(Permission.id.in_(ids), Permission.active == True)  # noqa: E712
            .all()
        } if ids else set()
        current = _role_permission_names(db, role_id)
        added = proposed - current
        if "schema:edit" in added:
            return "Lab personnel input does not grant schema:edit."
        if role_id == getattr(user, "role_id", None) and added:
            return (
                "This would add permissions to your own role ("
                + ", ".join(sorted(added))
                + "). The agent never grants you new privileges."
            )
        beyond = added - held
        if beyond:
            return (
                "This would grant permissions you don't hold ("
                + ", ".join(sorted(beyond))
                + "). The agent never grants privileges beyond yours."
            )
        return None
    user_match = re.match(r"^/users/([^/]+)$", path)
    if method == "PATCH" and user_match and "role_id" in data:
        try:
            target_user = UUID(user_match.group(1))
            new_role = UUID(str(data.get("role_id")))
        except ValueError:
            return None
        if target_user == getattr(user, "id", None):
            return "This would change your own role. The agent never changes its confirming user's privileges."
        beyond = _role_permission_names(db, new_role) - held
        if beyond:
            return (
                "That role has permissions you don't hold ("
                + ", ".join(sorted(beyond))
                + "). The agent never grants privileges beyond yours."
            )
        return None
    if method == "PUT" and path == "/v1/schema/privileges":
        rows = body if isinstance(body, list) else data.get("privileges") or data.get("items") or []
        own = str(getattr(user, "role_id", "") or "")
        if own and any(isinstance(row, dict) and str(row.get("role_id")) == own for row in rows):
            return "This would change your own role's table privileges. The agent never grants you new privileges."
        # G7: granting another role more access than your own role has on that
        # table/column is granting a privilege you don't hold.
        if own:
            from app.services.ui_schema_service import UiSchemaService

            svc = UiSchemaService(db, user)
            rank = {"none": 0, "read": 1, "write": 2}
            # Table-level rows in the same body set the target's table access that
            # a column 'inherit' row resolves to.
            body_table = {
                (str(row.get("role_id")), str(row.get("table_id"))): row.get("access")
                for row in rows
                if isinstance(row, dict) and not row.get("column_id")
            }
            for row in rows:
                if not isinstance(row, dict):
                    continue
                table_id = _safe_uuid(row.get("table_id"))
                role_id = _safe_uuid(row.get("role_id"))
                if table_id is None or role_id is None:
                    continue
                column_id = _safe_uuid(row.get("column_id"))
                access = row.get("access")
                if access == "inherit" and column_id:
                    # 'inherit' is not 'none': the column gets the target role's table access.
                    access = body_table.get((str(role_id), str(table_id))) or svc._table_access(role_id, table_id)
                if access not in ("read", "write"):
                    continue
                mine = (
                    svc._column_access(UUID(own), table_id, column_id)
                    if column_id
                    else svc._table_access(UUID(own), table_id)
                )
                if rank[access] > rank.get(mine, 0):
                    label = access if access == row.get("access") else f"{access} (inherited)"
                    return (
                        f"This would grant {label} access where your own role has {mine}. "
                        "The agent never grants privileges beyond yours."
                    )
    return None


def _safe_uuid(value) -> Optional[UUID]:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None


def register_catalog(db, user: User) -> None:
    """Idempotent safety net. Migration 0089 registers every configurable
    existing table up front (D-3/L-4); this only catches tables or clients
    created after it, inside the apply transaction, once per apply. Never at
    run start, and a rolled-back apply leaves nothing."""
    if isinstance(db, AtomicSession):
        if db.__dict__.get("_catalog_ready"):
            return
        object.__setattr__(db, "_catalog_ready", True)
    from app.services.ui_schema_service import UiSchemaService

    UiSchemaService(db, user).ensure_catalog()


def execute_step(db, user: User, method: str, path: str, body: Any) -> list[AppliedChange]:
    if is_drop_or_delete(method, path):
        raise CannotExpress("Drop and delete are never applied by the configuring agent.")
    from app.services.configuring_agent_catalog import (
        column_home_gap,
        transition_gap,
        describe_change,
        resolve_body,
        resolve_path,
        reuse_gap,
    )

    original = body if isinstance(body, dict) else {}
    early = classify_call(method, path, original)
    if not early.ok:
        raise CannotExpress(early.gap or "This change cannot be applied through configuration APIs.")
    reuse = reuse_gap(method, path, body)
    if reuse:
        raise CannotExpress(reuse)
    if (path or "").startswith("/v1/schema/"):
        register_catalog(db, user)
    # Names -> ids again at apply: a table created by an earlier row in this same
    # apply (flushed) now resolves.
    path = resolve_path(db, user, method, path)
    body = resolve_body(db, user, method, path, body)
    payload = body if isinstance(body, dict) else {}
    classified = classify_call(method, path, payload)
    if not classified.ok:
        raise CannotExpress(classified.gap or "This change cannot be applied through configuration APIs.")
    _require(user, db, classified)
    gap = escalation_gap(db, user, method, path, body)
    if gap:
        raise CannotExpress(gap)
    from app.services.configuring_agent_rerun import existing_change

    present = existing_change(db, user, method, path, body)
    if present is not None:
        # Safe rerun (D-7): the object is already there, so this is a no-op.
        present.noop = True
        return [present]
    home = column_home_gap(db, user, method, path, body) or transition_gap(method, path, body)
    if home:
        raise CannotExpress(home)
    if (method or "").upper() in ("PUT", "PATCH") or path.endswith("/deprecate"):
        diff = describe_change(db, user, method, path, body)
        if not diff["changed"]:
            # G5: the target already has these values. No call, no write.
            return [AppliedChange(classified.kind or "other", str(path), None, noop=True)]
    try:
        return _dispatch(db, user, method.upper(), path, body, classified.kind or "other")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _dispatch(db, user: User, method: str, path: str, body: dict, kind: str) -> list[AppliedChange]:
    if path == "/roles" or path.startswith("/roles/"):
        return _roles(db, user, method, path, body)
    if path.startswith("/v1/schema/"):
        return _schema(db, user, method, path, body, kind)
    if path == "/lists" or path.startswith("/lists/"):
        return _lists(db, user, method, path, body, kind)
    if path.startswith("/v1/experiment-templates"):
        return _templates(db, user, method, path, body)
    if path == "/containers/types":
        return _container_type(db, user, body)
    if path == "/analyses" or path == "/analytes" or re.match(r"^/analyses/[^/]+/analytes$", path):
        return _analyses(db, user, path, body)
    if path == "/v1/sample-type-transitions":
        return _transition(db, user, body)
    if path in ("/v1/vendors", "/v1/reagents", "/v1/reagent-vendors"):
        return _reagent_catalog(db, user, path, body)
    if path == "/v1/instruments" or path.startswith("/v1/instruments/"):
        return _instrument_catalog(db, user, method, path, body)
    if path == "/v1/instrument-maintenance-schedules" or path.startswith(
        "/v1/instrument-maintenance-schedules/"
    ):
        return _instrument_schedule(db, user, method, path, body)
    if path.startswith("/users/"):
        return _user_role(db, user, path, body)
    if re.match(r"^/containers/[^/]+/contents/[^/]+$", path):
        return _contents_amount_zero(db, user, path, body)
    raise CannotExpress(f"No configuration API matches {method} {path}.")


def _schema(db, user: User, method: str, path: str, body: dict, kind: str) -> list[AppliedChange]:
    from app.schemas.ui_schema import (
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
        # add_column returns the read dict (UAT: this raised, so no column ever applied).
        if isinstance(column, dict):
            return [AppliedChange("column", column["display_name"], column["id"])]
        return [AppliedChange("column", column.display_name, column.id)]
    if path.endswith("/deprecate") and "/columns/" in path:
        read = svc.deprecate_column(_uuid_from_path(path.replace("/deprecate", "")))
        return [AppliedChange("column", read["display_name"], read["id"])]
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
    raise CannotExpress(f"No configuration API matches {method} {path}.")


def _lists(db, user, method: str, path: str, body: dict, kind: str) -> list[AppliedChange]:
    from app.routers.lists import create_list, create_list_entry, update_list, update_list_entry
    from app.schemas.list import ListCreate, ListEntryCreate, ListEntryUpdate, ListUpdate

    if method == "POST" and path == "/lists":
        created = create_list(ListCreate.model_validate(body), user, db)
        return [AppliedChange("list", created.name, created.id)]
    entry = re.match(r"^/lists/([^/]+)/entries$", path)
    if method == "POST" and entry:
        created = create_list_entry(entry.group(1), ListEntryCreate.model_validate(body), user, db)
        return [AppliedChange("list_entry", created.name, created.id)]
    if method == "PATCH" and re.match(r"^/lists/[^/]+$", path):
        updated = update_list(_uuid_from_path(path), ListUpdate.model_validate(body), user, db)
        return [AppliedChange("list", updated.name, updated.id)]
    entry_one = re.match(r"^/lists/([^/]+)/entries/([^/]+)$", path)
    if entry_one and method == "PATCH":
        updated = update_list_entry(
            entry_one.group(1), UUID(entry_one.group(2)), ListEntryUpdate.model_validate(body), user, db
        )
        return [AppliedChange("list_entry", updated.name, updated.id)]
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


def _analyses(db, user, path: str, body: dict) -> list[AppliedChange]:
    """Analysis, analyte, and the analysis-analyte link, through their routers."""
    from app.routers.analyses import create_analysis, link_analytes_to_analysis
    from app.routers.analytes import create_analyte
    from app.schemas.analysis import AnalysisCreate, AnalyteLinkRequest
    from app.schemas.analyte import AnalyteCreate

    if path == "/analyses":
        created = create_analysis(AnalysisCreate.model_validate(body), user, db)
        return [AppliedChange("analysis", created.name, created.id)]
    if path == "/analytes":
        created = create_analyte(AnalyteCreate.model_validate(body), user, db)
        return [AppliedChange("analyte", created.name, created.id)]
    try:
        analysis_id = UUID(path.split("/")[2])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Analysis not found") from exc
    linked = link_analytes_to_analysis(analysis_id, AnalyteLinkRequest.model_validate(body), user, db)
    return [AppliedChange("analysis_analytes", ", ".join(a.name for a in linked) or "analytes", analysis_id)]


def _container_type(db, user, body: dict) -> list[AppliedChange]:
    from app.routers.containers import create_container_type
    from app.schemas.container import ContainerTypeCreate

    created = create_container_type(ContainerTypeCreate.model_validate(body), user, db)
    return [AppliedChange("container_type", created.name, created.id)]


def _reagent_catalog(db, user, path: str, body: dict) -> list[AppliedChange]:
    from app.routers.reagents import create_reagent, create_reagent_vendor, create_vendor
    from app.schemas.reagent import ReagentCreate, ReagentVendorCreate, VendorCreate

    if path == "/v1/reagent-vendors":
        created = create_reagent_vendor(ReagentVendorCreate.model_validate(body), user, db)
        return [AppliedChange("reagent_vendor", created.catalog_number or created.vendor_name or "source", created.id)]
    if path == "/v1/vendors":
        created = create_vendor(VendorCreate.model_validate(body), user, db)
        return [AppliedChange("vendor", created.name, created.id)]
    created = create_reagent(ReagentCreate.model_validate(body), user, db)
    return [AppliedChange("reagent", created.name, created.id)]


def _instrument_catalog(db, user, method: str, path: str, body: dict) -> list[AppliedChange]:
    from app.routers.instrument_catalog import create_instrument, update_instrument
    from app.schemas.instrument_catalog import InstrumentCreate, InstrumentUpdate

    if method == "POST" and path == "/v1/instruments":
        created = create_instrument(InstrumentCreate.model_validate(body), user, db)
        return [AppliedChange("instrument", created.name, created.id)]
    instrument_id = _uuid_from_path(path)
    updated = update_instrument(instrument_id, InstrumentUpdate.model_validate(body), user, db)
    return [AppliedChange("instrument", updated.name, updated.id)]


def _instrument_schedule(db, user, method: str, path: str, body: dict) -> list[AppliedChange]:
    from app.routers.instrument_ops import create_schedule, update_schedule
    from app.schemas.instrument_ops import MaintenanceScheduleCreate, MaintenanceScheduleUpdate

    if method == "POST" and path == "/v1/instrument-maintenance-schedules":
        created = create_schedule(MaintenanceScheduleCreate.model_validate(body), user, db)
        return [AppliedChange("instrument_schedule", created.kind_name or str(created.id), created.id)]
    schedule_id = _uuid_from_path(path)
    updated = update_schedule(schedule_id, MaintenanceScheduleUpdate.model_validate(body), user, db)
    return [AppliedChange("instrument_schedule", updated.kind_name or str(updated.id), updated.id)]


def _transition(db, user, body: dict) -> list[AppliedChange]:
    from app.schemas.sample_type_transition import SampleTypeTransitionCreate
    from app.services.sample_type_transition_service import SampleTypeTransitionService

    created = SampleTypeTransitionService(db, user).create(SampleTypeTransitionCreate.model_validate(body))
    name = created.source_sample_type_name or str(created.id)
    return [AppliedChange("sample_type_transition", name, created.id)]


def _user_role(db, user, path: str, body: dict) -> list[AppliedChange]:
    from app.routers.users import update_user
    from app.schemas.user import UserUpdate

    updated = update_user(_uuid_from_path(path), UserUpdate.model_validate(body), user, db)
    return [AppliedChange("user_role", updated.name, updated.id)]


def _contents_amount_zero(db, user, path: str, body: dict) -> list[AppliedChange]:
    """Container retire: PATCH contents amount to 0. Nothing is deleted."""
    from app.routers.containers import update_container_contents
    from app.schemas.container import ContentsUpdate

    parts = path.strip("/").split("/")
    container_id, sample_id = UUID(parts[1]), UUID(parts[3])
    if (body or {}).get("amount") not in (0, 0.0) or set(body or {}) != {"amount"}:
        raise CannotExpress("The only container change this run makes is Amount \u2192 0.")
    update_container_contents(container_id, sample_id, ContentsUpdate(amount=0), user, db)
    return [AppliedChange("contents_amount", f"{container_id}/{sample_id}", container_id)]


def _roles(db, user, method: str, path: str, body: dict) -> list[AppliedChange]:
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
    update_role_permissions(role_id, data, user, db)
    return [AppliedChange("role_permissions", label, role_id)]
