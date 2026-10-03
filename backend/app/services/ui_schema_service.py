"""UI schema registries + Hybrid apply (Brief OQ-4–13)."""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, Iterable, List, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services import ui_schema_catalog as catalog
from models.sample import Sample
from models.ui_schema import (
    SchemaChange,
    SchemaColumn,
    SchemaLayout,
    SchemaLayoutField,
    SchemaPrivilege,
    SchemaRelation,
    SchemaTable,
    UiSchemaDdlLog,
)
from models.user import Role, User

logger = logging.getLogger(__name__)

CARDINALITIES = ("one_to_many", "one_to_one")
SYSTEM_COLUMN_COPY = {
    "system_table": "System reference tables are read-only in the Schema screen.",
    "platform": "Platform fields (id, timestamps, created-by, active) are managed by the engine.",
    "identity": "Identity/lineage fields cannot be removed from the UI.",
    "relationship_key": "Relationship keys are real foreign keys. Change them with a migration, not here.",
}
REFLECTED_COLUMN_COPY = "Built-in fields are owned by migrations. The Schema screen only describes them."

TABLE_SLUG_RE = re.compile(r"^(x|lab)_[a-z][a-z0-9_]{0,47}$")
COL_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
KNOWN_SCREENS = ("receive", "samples.detail", "samples.list")
P1_TYPES = {
    "text": "text",
    "numeric": "numeric",
    "integer": "integer",
    "boolean": "boolean",
    "date": "date",
    "timestamptz": "timestamptz",
    "list": "uuid",
}
IDENTITY_SAMPLE_COLS = {
    "name",
    "parent_sample_id",
    "sample_type",
    "status",
    "matrix",
    "project_id",
    "client_sample_id",
}
PLATFORM_COLS = (
    ("id", "text", True),
    ("client_id", "text", True),
    ("created_at", "timestamptz", True),
    ("created_by", "text", False),
    ("modified_at", "timestamptz", True),
    ("modified_by", "text", False),
    ("active", "boolean", True),
)
ADD_COLUMN_OUT = {
    "asked_for",
    "tests",
    "results",
    "containers",
    "contents",
    "routing_map",
    "work_orders",
}


def _slug(display: str, prefix: Optional[str] = None) -> str:
    raw = re.sub(r"[^a-z0-9]+", "_", display.strip().lower()).strip("_")
    if not raw:
        raw = "field"
    if raw[0].isdigit():
        raw = "f_" + raw
    if prefix:
        return f"{prefix}_{raw}"[:63]
    return raw[:63]


class UiSchemaService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.client_id: UUID = user.client_id

    def _audit(
        self,
        op: str,
        table_physical: str,
        column_physical: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        definition: Optional[str] = None,
    ) -> SchemaChange:
        row = SchemaChange(
            id=uuid.uuid4(),
            client_id=self.client_id,
            actor_id=self.user.id,
            op=op,
            table_physical=table_physical,
            column_physical=column_physical,
            before_status=before,
            after_status=after,
            definition_text=definition,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _log_ddl(
        self,
        change: SchemaChange,
        op: str,
        table_physical: str,
        column_physical: Optional[str] = None,
        pg_type: Optional[str] = None,
        nullable: Optional[bool] = None,
        list_fk: Optional[bool] = None,
    ) -> None:
        self.db.add(
            UiSchemaDdlLog(
                id=uuid.uuid4(),
                client_id=self.client_id,
                change_id=change.id,
                op=op,
                table_physical=table_physical,
                column_physical=column_physical,
                pg_type=pg_type,
                nullable=nullable,
                list_fk=list_fk,
            )
        )

    def ensure_core_catalog(self) -> SchemaTable:
        """Cheap path used by runtime screens: Samples must be registered."""
        row = (
            self.db.query(SchemaTable)
            .filter(
                SchemaTable.client_id == self.client_id,
                SchemaTable.physical_name == "samples",
            )
            .first()
        )
        if row:
            return row
        self.ensure_catalog(only=("samples",))
        return (
            self.db.query(SchemaTable)
            .filter(
                SchemaTable.client_id == self.client_id,
                SchemaTable.physical_name == "samples",
            )
            .one()
        )

    def ensure_catalog(self, only: Optional[Sequence[str]] = None) -> None:
        """Register allow-listed tables and describe their columns from Postgres.

        Lazy registration on view (OQ-3 B). Only tables that really exist are
        registered; engine internals are never allow-listed. Reflection fills
        type / nullability / FK / UNIQUE facts. Nothing here issues DDL.
        """
        wanted = list(catalog.LAB_TABLES) + list(catalog.SYSTEM_TABLES)
        if only is not None:
            wanted = [n for n in wanted if n in set(only)]
        registered = {
            t.physical_name: t
            for t in self.db.query(SchemaTable)
            .filter(SchemaTable.client_id == self.client_id)
            .all()
        }
        # UI-created tables are registered already; they still get reflection facts.
        present = catalog.existing_tables(
            self.db,
            wanted + [n for n in registered if only is None or n in set(only)],
        )
        changed = False
        for name in wanted:
            if name not in present or name in registered:
                continue
            kind = catalog.kind_for(name)
            if not kind:
                continue
            row = SchemaTable(
                id=uuid.uuid4(),
                client_id=self.client_id,
                display_name=catalog.display_name_for(name),
                physical_name=name,
                kind=kind,
                status="active",
                created_by=self.user.id,
                modified_by=self.user.id,
            )
            self.db.add(row)
            self.db.flush()
            registered[name] = row
            self._seed_default_table_privileges(row.id)
            changed = True
        to_sync = [
            t
            for t in registered.values()
            if catalog.shown_in_schema(t.physical_name, t.kind)
            and (only is None or t.physical_name in set(only))
            and t.physical_name in present
        ]
        if to_sync:
            changed = self._sync_columns(to_sync) or changed
        if changed:
            self.db.commit()

    def _sync_columns(self, tables: Sequence[SchemaTable]) -> bool:
        """Describe real columns in the registry. Admin-chosen facts on UI
        columns (display name, type, list binding) are left alone; reflection
        facts (FK / UNIQUE / pg type / nullability) are refreshed everywhere."""
        reflected = catalog.reflect_columns(self.db, [t.physical_name for t in tables])
        existing = (
            self.db.query(SchemaColumn)
            .filter(SchemaColumn.table_id.in_([t.id for t in tables]))
            .all()
        )
        by_key = {(c.table_id, c.physical_name): c for c in existing}
        changed = False
        for table in tables:
            for col in reflected.get(table.physical_name, []):
                row = by_key.get((table.id, col.name))
                is_platform = col.name in catalog.PLATFORM_COLUMN_NAMES
                is_identity = table.physical_name == "samples" and col.name in IDENTITY_SAMPLE_COLS
                mapped = catalog.map_pg_type(col.udt_name, col.is_fk, col.fk_table)
                if row is None:
                    self.db.add(
                        SchemaColumn(
                            id=uuid.uuid4(),
                            client_id=self.client_id,
                            table_id=table.id,
                            display_name=catalog.column_display_name(col.name, col.is_fk),
                            physical_name=col.name,
                            data_type=mapped,
                            nullable=col.nullable,
                            sort_order=col.ordinal,
                            is_platform=is_platform,
                            is_identity=is_identity,
                            is_fk=col.is_fk,
                            fk_table=col.fk_table,
                            is_unique=col.is_unique,
                            pg_type=col.udt_name,
                            origin="reflected",
                            created_by=self.user.id,
                            modified_by=self.user.id,
                        )
                    )
                    changed = True
                    continue
                updates = {
                    "is_fk": col.is_fk,
                    "fk_table": col.fk_table,
                    "is_unique": col.is_unique,
                    "pg_type": col.udt_name,
                    "nullable": col.nullable,
                }
                if row.origin == "reflected":
                    updates["data_type"] = mapped
                    updates["is_platform"] = is_platform or row.is_platform
                for attr, value in updates.items():
                    if getattr(row, attr) != value:
                        setattr(row, attr, value)
                        changed = True
        if changed:
            self.db.flush()
        return changed

    def _seed_default_table_privileges(self, table_id: UUID) -> None:
        mapping = {
            "Administrator": "write",
            "Lab Manager": "write",
            "Lab Technician": "write",
            "Client": "read",
        }
        roles = {r.name: r for r in self.db.query(Role).filter(Role.name.in_(mapping)).all()}
        for name, access in mapping.items():
            role = roles.get(name)
            if not role:
                continue
            exists = (
                self.db.query(SchemaPrivilege)
                .filter(
                    SchemaPrivilege.client_id == self.client_id,
                    SchemaPrivilege.role_id == role.id,
                    SchemaPrivilege.table_id == table_id,
                    SchemaPrivilege.column_id.is_(None),
                )
                .first()
            )
            if exists:
                continue
            self.db.add(
                SchemaPrivilege(
                    id=uuid.uuid4(),
                    client_id=self.client_id,
                    role_id=role.id,
                    table_id=table_id,
                    access=access,
                    created_by=self.user.id,
                    modified_by=self.user.id,
                )
            )
        self.db.flush()

    def list_tables(self) -> List[SchemaTable]:
        self.ensure_catalog()
        rows = (
            self.db.query(SchemaTable)
            .filter(SchemaTable.client_id == self.client_id)
            .order_by(SchemaTable.kind == "system", SchemaTable.display_name)
            .all()
        )
        return [row for row in rows if catalog.shown_in_schema(row.physical_name, row.kind)]

    def _can_add_columns(self, row: SchemaTable) -> bool:
        if row.kind == "system" or row.physical_name in ADD_COLUMN_OUT:
            return False
        if row.kind == "core":
            return row.physical_name == "samples"
        return True

    def table_read(self, row: SchemaTable) -> Dict[str, Any]:
        count = (
            self.db.query(SchemaColumn)
            .filter(SchemaColumn.table_id == row.id)
            .count()
        )
        relation_count = (
            self.db.query(SchemaRelation)
            .filter(
                SchemaRelation.client_id == self.client_id,
                (SchemaRelation.from_table_id == row.id) | (SchemaRelation.to_table_id == row.id),
            )
            .count()
        )
        return {
            "id": row.id,
            "client_id": row.client_id,
            "display_name": row.display_name,
            "physical_name": row.physical_name,
            "kind": row.kind,
            "category": catalog.category_for_kind(row.kind),
            "status": row.status,
            "column_count": count,
            "relation_count": relation_count,
            "can_add_columns": self._can_add_columns(row),
            "can_remove": row.kind == "ui",
            "created_at": row.created_at,
        }

    def column_read(self, col: SchemaColumn, table: Optional[SchemaTable] = None) -> Dict[str, Any]:
        table = table or col.table
        reason = catalog.is_system_column(
            col.physical_name,
            is_platform=col.is_platform,
            is_identity=col.is_identity,
            is_fk=col.is_fk,
            fk_table=col.fk_table,
            table_kind=table.kind if table else "core",
        )
        editable = reason is None and col.origin == "ui"
        return {
            "id": col.id,
            "table_id": col.table_id,
            "display_name": col.display_name,
            "physical_name": col.physical_name,
            "data_type": col.data_type,
            "pg_type": col.pg_type,
            "nullable": col.nullable,
            "list_id": col.list_id,
            "sop_hint": col.sop_hint,
            "sort_order": col.sort_order,
            "status": col.status,
            "is_platform": col.is_platform,
            "is_identity": col.is_identity,
            "is_fk": col.is_fk,
            "fk_table": col.fk_table,
            "is_unique": col.is_unique,
            "origin": col.origin,
            "is_system": reason is not None,
            "system_reason": reason,
            "editable": editable,
        }

    def _refuse_if_locked(self, col: SchemaColumn, verb: str) -> None:
        table = col.table
        reason = catalog.is_system_column(
            col.physical_name,
            is_platform=col.is_platform,
            is_identity=col.is_identity,
            is_fk=col.is_fk,
            fk_table=col.fk_table,
            table_kind=table.kind if table else "core",
        )
        if reason:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, SYSTEM_COLUMN_COPY[reason])
        if col.origin != "ui":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, REFLECTED_COLUMN_COPY)

    def _get_table(self, table_id: UUID) -> SchemaTable:
        row = (
            self.db.query(SchemaTable)
            .filter(SchemaTable.id == table_id, SchemaTable.client_id == self.client_id)
            .first()
        )
        if not row or not catalog.shown_in_schema(row.physical_name, row.kind):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")
        return row

    def create_table(self, display_name: str, physical_name: Optional[str]) -> SchemaTable:
        slug = physical_name or _slug(display_name, "x")
        if not TABLE_SLUG_RE.match(slug):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Physical name must be x_<slug> or lab_<slug>",
            )
        exists = (
            self.db.query(SchemaTable)
            .filter(
                SchemaTable.client_id == self.client_id,
                SchemaTable.physical_name == slug,
            )
            .first()
        )
        if exists:
            raise HTTPException(status.HTTP_409_CONFLICT, "A table with that database name already exists.")
        row = SchemaTable(
            id=uuid.uuid4(),
            client_id=self.client_id,
            display_name=display_name.strip(),
            physical_name=slug,
            kind="ui",
            status="active",
            created_by=self.user.id,
            modified_by=self.user.id,
        )
        self.db.add(row)
        self.db.flush()
        for i, (pname, dtype, required) in enumerate(PLATFORM_COLS):
            self.db.add(
                SchemaColumn(
                    id=uuid.uuid4(),
                    client_id=self.client_id,
                    table_id=row.id,
                    display_name=pname.replace("_", " ").title(),
                    physical_name=pname,
                    data_type=dtype if dtype != "text" else "text",
                    nullable=not required,
                    sort_order=i,
                    is_platform=True,
                    is_identity=pname == "id",
                    origin="reflected",
                    created_by=self.user.id,
                    modified_by=self.user.id,
                )
            )
        self._seed_default_table_privileges(row.id)
        try:
            self.db.execute(text("SELECT ui_schema_create_table(:n)"), {"n": slug})
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Could not create table: {exc}",
            ) from exc
        change = self._audit(
            "create_table",
            slug,
            after="active",
            definition=f"CREATE TABLE {slug} platform columns",
        )
        self._log_ddl(change, "create_table", slug)
        self.db.commit()
        self.db.refresh(row)
        return row

    def deprecate_table(self, table_id: UUID) -> SchemaTable:
        row = self._get_table(table_id)
        if row.kind != "ui":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Only tables created from the Schema screen can be deprecated.",
            )
        row.status = "deprecated"
        row.modified_by = self.user.id
        self._audit("deprecate_table", row.physical_name, before="active", after="deprecated")
        self.db.commit()
        self.db.refresh(row)
        return row

    def drop_table(self, table_id: UUID, confirm: bool) -> None:
        row = self._get_table(table_id)
        if row.kind != "ui":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Only tables created from the Schema screen can be dropped.",
            )
        if not confirm:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "DROP requires confirm=true plus impact review",
            )
        count = 0
        try:
            count = self.db.execute(
                text(f"SELECT count(*) FROM {row.physical_name}")
            ).scalar() or 0
        except Exception:
            count = 0
        layout_refs = (
            self.db.query(SchemaLayoutField)
            .join(SchemaColumn, SchemaColumn.id == SchemaLayoutField.column_id)
            .filter(SchemaColumn.table_id == row.id)
            .count()
        )
        try:
            self.db.execute(text("SELECT ui_schema_drop_table(:n)"), {"n": row.physical_name})
        except Exception as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        change = self._audit(
            "drop_table",
            row.physical_name,
            before=row.status,
            after="dropped",
            definition=f"rows={count} layout_refs={layout_refs}",
        )
        self._log_ddl(change, "drop_table", row.physical_name)
        self.db.query(SchemaRelation).filter(
            (SchemaRelation.from_table_id == row.id) | (SchemaRelation.to_table_id == row.id)
        ).delete(synchronize_session=False)
        self.db.query(SchemaLayoutField).filter(
            SchemaLayoutField.column_id.in_(
                self.db.query(SchemaColumn.id).filter(SchemaColumn.table_id == row.id)
            )
        ).delete(synchronize_session=False)
        self.db.query(SchemaPrivilege).filter(SchemaPrivilege.table_id == row.id).delete(
            synchronize_session=False
        )
        self.db.query(SchemaColumn).filter(SchemaColumn.table_id == row.id).delete(
            synchronize_session=False
        )
        self.db.delete(row)
        self.db.commit()

    def list_columns(self, table_id: UUID) -> List[Dict[str, Any]]:
        table = self._get_table(table_id)
        self.ensure_catalog(only=(table.physical_name,))
        rows = (
            self.db.query(SchemaColumn)
            .filter(SchemaColumn.table_id == table_id)
            .order_by(SchemaColumn.sort_order, SchemaColumn.physical_name)
            .all()
        )
        return [self.column_read(c, table) for c in rows]

    def add_column(
        self,
        table_id: UUID,
        display_name: str,
        data_type: str,
        nullable: bool,
        list_id: Optional[UUID],
        sop_hint: Optional[str],
        sort_order: int,
        physical_name: Optional[str],
    ) -> SchemaColumn:
        table = self._get_table(table_id)
        if not self._can_add_columns(table):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "This table can't get new fields from the UI.",
            )
        if data_type not in P1_TYPES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Type not allow-listed")
        if data_type == "list" and not list_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "List type requires a list source")
        slug = physical_name or _slug(display_name)
        if not COL_SLUG_RE.match(slug):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid field database name")
        if table.physical_name == "samples" and slug in IDENTITY_SAMPLE_COLS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Identity/lineage fields cannot be added or replaced from the UI.",
            )
        dup = (
            self.db.query(SchemaColumn)
            .filter(SchemaColumn.table_id == table.id, SchemaColumn.physical_name == slug)
            .first()
        )
        if dup:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A field with that database name already exists.",
            )
        col = SchemaColumn(
            id=uuid.uuid4(),
            client_id=self.client_id,
            table_id=table.id,
            display_name=display_name.strip(),
            physical_name=slug,
            data_type=data_type,
            nullable=nullable,
            list_id=list_id if data_type == "list" else None,
            sop_hint=sop_hint,
            sort_order=sort_order,
            is_fk=data_type == "list",
            fk_table=catalog.LIST_ENTRIES_TABLE if data_type == "list" else None,
            pg_type=P1_TYPES[data_type],
            origin="ui",
            created_by=self.user.id,
            modified_by=self.user.id,
        )
        self.db.add(col)
        self.db.flush()
        try:
            self.db.execute(
                text(
                    "SELECT ui_schema_add_column(:t, :c, :ty, :n, :fk)"
                ),
                {
                    "t": table.physical_name,
                    "c": slug,
                    "ty": P1_TYPES[data_type],
                    "n": nullable,
                    "fk": data_type == "list",
                },
            )
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Could not add field: {exc}",
            ) from exc
        change = self._audit(
            "add_column",
            table.physical_name,
            slug,
            after="active",
            definition=f"{data_type} nullable={nullable}",
        )
        self._log_ddl(
            change,
            "add_column",
            table.physical_name,
            slug,
            pg_type=P1_TYPES[data_type],
            nullable=nullable,
            list_fk=data_type == "list",
        )
        self.db.commit()
        self.db.refresh(col)
        return self.column_read(col, table)

    def _get_column(self, column_id: UUID) -> SchemaColumn:
        col = (
            self.db.query(SchemaColumn)
            .filter(SchemaColumn.id == column_id, SchemaColumn.client_id == self.client_id)
            .first()
        )
        if not col:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
        return col

    def deprecate_column(self, column_id: UUID) -> Dict[str, Any]:
        col = self._get_column(column_id)
        self._refuse_if_locked(col, "deprecate")
        col.status = "deprecated"
        col.modified_by = self.user.id
        self._audit(
            "deprecate_column",
            col.table.physical_name if col.table else "",
            col.physical_name,
            before="active",
            after="deprecated",
        )
        self.db.commit()
        self.db.refresh(col)
        return self.column_read(col)

    def drop_column(self, column_id: UUID, confirm: bool) -> None:
        col = self._get_column(column_id)
        self._refuse_if_locked(col, "drop")
        if col.physical_name in IDENTITY_SAMPLE_COLS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Identity/lineage fields cannot be dropped.",
            )
        if not confirm:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "DROP requires confirm=true plus impact review",
            )
        table = self._get_table(col.table_id)
        layout_refs = (
            self.db.query(SchemaLayoutField)
            .filter(SchemaLayoutField.column_id == col.id)
            .count()
        )
        try:
            self.db.execute(
                text("SELECT ui_schema_drop_column(:t, :c)"),
                {"t": table.physical_name, "c": col.physical_name},
            )
        except Exception as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        change = self._audit(
            "drop_column",
            table.physical_name,
            col.physical_name,
            before=col.status,
            after="dropped",
            definition=f"layout_refs={layout_refs}",
        )
        self._log_ddl(change, "drop_column", table.physical_name, col.physical_name)
        self.db.query(SchemaRelation).filter(SchemaRelation.fk_column_id == col.id).delete(
            synchronize_session=False
        )
        self.db.query(SchemaLayoutField).filter(SchemaLayoutField.column_id == col.id).delete(
            synchronize_session=False
        )
        self.db.query(SchemaPrivilege).filter(SchemaPrivilege.column_id == col.id).delete(
            synchronize_session=False
        )
        self.db.delete(col)
        self.db.commit()

    def get_layout(self, role_id: UUID, screen_key: str) -> Optional[SchemaLayout]:
        if screen_key not in KNOWN_SCREENS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown screen key")
        return (
            self.db.query(SchemaLayout)
            .filter(
                SchemaLayout.client_id == self.client_id,
                SchemaLayout.role_id == role_id,
                SchemaLayout.screen_key == screen_key,
            )
            .first()
        )

    def put_layout(self, role_id: UUID, screen_key: str, fields: List[Dict[str, Any]]) -> SchemaLayout:
        if screen_key not in KNOWN_SCREENS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown screen key")
        layout = self.get_layout(role_id, screen_key)
        if not layout:
            layout = SchemaLayout(
                id=uuid.uuid4(),
                client_id=self.client_id,
                role_id=role_id,
                screen_key=screen_key,
                created_by=self.user.id,
                modified_by=self.user.id,
            )
            self.db.add(layout)
            self.db.flush()
        self.db.query(SchemaLayoutField).filter(SchemaLayoutField.layout_id == layout.id).delete(
            synchronize_session=False
        )
        seen = set()
        for item in fields:
            cid = item["column_id"] if isinstance(item, dict) else item.column_id
            if cid in seen:
                continue
            col = (
                self.db.query(SchemaColumn)
                .filter(SchemaColumn.id == cid, SchemaColumn.client_id == self.client_id)
                .first()
            )
            if not col:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown column on layout")
            if not self._role_can_read(role_id, col.table_id, col.id):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Layout editor must not offer a field with neither read nor write",
                )
            seen.add(cid)
            self.db.add(
                SchemaLayoutField(
                    id=uuid.uuid4(),
                    client_id=self.client_id,
                    layout_id=layout.id,
                    column_id=cid,
                    section=(item.get("section") if isinstance(item, dict) else item.section),
                    sort_order=(item.get("sort_order", 0) if isinstance(item, dict) else item.sort_order),
                )
            )
        layout.modified_by = self.user.id
        self.db.commit()
        self.db.refresh(layout)
        return layout

    def layout_read(self, layout: SchemaLayout) -> Dict[str, Any]:
        fields = (
            self.db.query(SchemaLayoutField)
            .filter(SchemaLayoutField.layout_id == layout.id)
            .order_by(SchemaLayoutField.sort_order)
            .all()
        )
        return {
            "id": layout.id,
            "role_id": layout.role_id,
            "screen_key": layout.screen_key,
            "fields": [
                {
                    "column_id": f.column_id,
                    "section": f.section,
                    "sort_order": f.sort_order,
                    "physical_name": f.column.physical_name if f.column else None,
                    "display_name": f.column.display_name if f.column else None,
                }
                for f in fields
            ],
        }

    def list_privileges(self, role_id: Optional[UUID], table_id: Optional[UUID]) -> List[SchemaPrivilege]:
        q = self.db.query(SchemaPrivilege).filter(SchemaPrivilege.client_id == self.client_id)
        if role_id:
            q = q.filter(SchemaPrivilege.role_id == role_id)
        if table_id:
            q = q.filter(SchemaPrivilege.table_id == table_id)
        return q.all()

    def put_privileges(self, items: Sequence[Dict[str, Any]]) -> List[SchemaPrivilege]:
        out: List[SchemaPrivilege] = []
        for item in items:
            role_id = item["role_id"] if isinstance(item, dict) else item.role_id
            table_id = item["table_id"] if isinstance(item, dict) else item.table_id
            column_id = item.get("column_id") if isinstance(item, dict) else item.column_id
            access = item["access"] if isinstance(item, dict) else item.access
            if column_id is None and access == "inherit":
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Table privilege cannot be inherit",
                )
            if column_id is not None and access not in ("read", "write", "inherit", "none"):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid access")
            existing = (
                self.db.query(SchemaPrivilege)
                .filter(
                    SchemaPrivilege.client_id == self.client_id,
                    SchemaPrivilege.role_id == role_id,
                    SchemaPrivilege.table_id == table_id,
                    SchemaPrivilege.column_id == column_id
                    if column_id is not None
                    else SchemaPrivilege.column_id.is_(None),
                )
                .first()
            )
            if existing:
                existing.access = access
                existing.modified_by = self.user.id
                out.append(existing)
            else:
                row = SchemaPrivilege(
                    id=uuid.uuid4(),
                    client_id=self.client_id,
                    role_id=role_id,
                    table_id=table_id,
                    column_id=column_id,
                    access=access,
                    created_by=self.user.id,
                    modified_by=self.user.id,
                )
                self.db.add(row)
                out.append(row)
        self.db.commit()
        return out

    def _table_access(self, role_id: UUID, table_id: UUID) -> str:
        row = (
            self.db.query(SchemaPrivilege)
            .filter(
                SchemaPrivilege.client_id == self.client_id,
                SchemaPrivilege.role_id == role_id,
                SchemaPrivilege.table_id == table_id,
                SchemaPrivilege.column_id.is_(None),
            )
            .first()
        )
        return row.access if row else "none"

    def _column_access(self, role_id: UUID, table_id: UUID, column_id: UUID) -> str:
        table_acc = self._table_access(role_id, table_id)
        col = (
            self.db.query(SchemaPrivilege)
            .filter(
                SchemaPrivilege.client_id == self.client_id,
                SchemaPrivilege.role_id == role_id,
                SchemaPrivilege.table_id == table_id,
                SchemaPrivilege.column_id == column_id,
            )
            .first()
        )
        if not col or col.access == "inherit":
            return table_acc
        rank = {"none": 0, "read": 1, "write": 2}
        return col.access if rank.get(col.access, 0) <= rank.get(table_acc, 0) else table_acc

    def _role_can_read(self, role_id: UUID, table_id: UUID, column_id: UUID) -> bool:
        acc = self._column_access(role_id, table_id, column_id)
        return acc in ("read", "write")

    def _role_can_write(self, role_id: UUID, table_id: UUID, column_id: UUID) -> bool:
        return self._column_access(role_id, table_id, column_id) == "write"

    def runtime_columns(self, screen_key: str) -> List[Dict[str, Any]]:
        if screen_key not in KNOWN_SCREENS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown screen key")
        self.ensure_core_catalog()
        role_id = self.user.role_id
        layout = self.get_layout(role_id, screen_key)
        cols = (
            self.db.query(SchemaColumn)
            .join(SchemaTable, SchemaTable.id == SchemaColumn.table_id)
            .filter(
                SchemaColumn.client_id == self.client_id,
                SchemaColumn.status == "active",
                SchemaTable.physical_name == "samples",
            )
            .order_by(SchemaColumn.sort_order)
            .all()
        )
        membership = {}
        if layout:
            for f in layout.fields:
                membership[f.column_id] = f
        out = []
        for col in cols:
            can_read = self._role_can_read(role_id, col.table_id, col.id)
            can_write = self._role_can_write(role_id, col.table_id, col.id)
            on_layout = col.id in membership if layout else can_read
            if layout is None:
                on_layout = can_read
            out.append(
                {
                    "id": col.id,
                    "physical_name": col.physical_name,
                    "display_name": col.display_name,
                    "data_type": col.data_type,
                    "on_layout": on_layout,
                    "can_read": can_read,
                    "can_write": can_write,
                    "sort_order": membership[col.id].sort_order if col.id in membership else col.sort_order,
                    "section": membership[col.id].section if col.id in membership else None,
                }
            )
        return out

    def extra_sample_columns(self) -> List[SchemaColumn]:
        table = (
            self.db.query(SchemaTable)
            .filter(
                SchemaTable.client_id == self.client_id,
                SchemaTable.physical_name == "samples",
            )
            .first()
        )
        if not table:
            return []
        return (
            self.db.query(SchemaColumn)
            .filter(
                SchemaColumn.table_id == table.id,
                SchemaColumn.status == "active",
                SchemaColumn.origin == "ui",
                SchemaColumn.is_identity.is_(False),
                SchemaColumn.is_platform.is_(False),
                SchemaColumn.physical_name.notin_(list(IDENTITY_SAMPLE_COLS)),
            )
            .all()
        )

    # ------------------------------------------------------------------ relations

    def _relation_read(self, rel: SchemaRelation) -> Dict[str, Any]:
        col = rel.fk_column
        return {
            "id": rel.id,
            "display_name": rel.display_name,
            "from_table_id": rel.from_table_id,
            "from_table_name": rel.from_table.display_name if rel.from_table else None,
            "from_physical_name": rel.from_table.physical_name if rel.from_table else None,
            "to_table_id": rel.to_table_id,
            "to_table_name": rel.to_table.display_name if rel.to_table else None,
            "to_physical_name": rel.to_table.physical_name if rel.to_table else None,
            "fk_column_id": rel.fk_column_id,
            "fk_column_name": col.display_name if col else None,
            "fk_physical_name": col.physical_name if col else None,
            "cardinality": rel.cardinality,
            "status": rel.status,
            "created_at": rel.created_at,
        }

    def list_relations(self, table_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        q = self.db.query(SchemaRelation).filter(SchemaRelation.client_id == self.client_id)
        if table_id:
            q = q.filter(
                (SchemaRelation.from_table_id == table_id) | (SchemaRelation.to_table_id == table_id)
            )
        return [self._relation_read(r) for r in q.order_by(SchemaRelation.display_name).all()]

    def create_relation(
        self,
        display_name: str,
        from_table_id: UUID,
        to_table_id: UUID,
        fk_column_id: UUID,
        cardinality: str,
    ) -> Dict[str, Any]:
        """Declare a side link over an existing real FK column on the child.

        Registry only. Refuses when the column is not a FOREIGN KEY to the
        parent, or when one-to-one is asked of a key that Postgres does not
        hold UNIQUE. Never mutates the database.
        """
        if cardinality not in CARDINALITIES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cardinality must be one-to-many or one-to-one")
        parent = self._get_table(from_table_id)
        child = self._get_table(to_table_id)
        col = self._get_column(fk_column_id)
        if col.table_id != child.id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "The key column must belong to the child table.",
            )
        if not col.is_fk or col.fk_table != parent.physical_name:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"{col.display_name} is not a foreign key to {parent.display_name}. "
                "The key must be a real FK column on the child.",
            )
        if cardinality == "one_to_one" and not col.is_unique:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"One-to-one needs a UNIQUE key. {col.display_name} is not unique in Postgres.",
            )
        dup = (
            self.db.query(SchemaRelation)
            .filter(
                SchemaRelation.client_id == self.client_id,
                SchemaRelation.fk_column_id == col.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status.HTTP_409_CONFLICT, "That key already carries a relation.")
        rel = SchemaRelation(
            id=uuid.uuid4(),
            client_id=self.client_id,
            display_name=display_name.strip(),
            from_table_id=parent.id,
            to_table_id=child.id,
            fk_column_id=col.id,
            cardinality=cardinality,
            created_by=self.user.id,
            modified_by=self.user.id,
        )
        self.db.add(rel)
        self._audit(
            "create_relation",
            child.physical_name,
            col.physical_name,
            after="active",
            definition=f"{cardinality} {parent.physical_name} -> {child.physical_name}.{col.physical_name}",
        )
        self.db.commit()
        self.db.refresh(rel)
        return self._relation_read(rel)

    def delete_relation(self, relation_id: UUID) -> None:
        rel = (
            self.db.query(SchemaRelation)
            .filter(SchemaRelation.id == relation_id, SchemaRelation.client_id == self.client_id)
            .first()
        )
        if not rel:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Relation not found")
        self._audit(
            "delete_relation",
            rel.to_table.physical_name if rel.to_table else "",
            rel.fk_column.physical_name if rel.fk_column else None,
            before="active",
            after="removed",
        )
        self.db.delete(rel)
        self.db.commit()

    def table_links(self, table_id: UUID) -> Dict[str, Any]:
        """Read-only link summary for the table browser.

        ``keys``: FK columns on this table (this table is the child).
        ``children``: declared relations where this table is the parent.
        ``parents``: declared relations where this table is the child.
        """
        table = self._get_table(table_id)
        self.ensure_catalog(only=(table.physical_name,))
        registry = {
            t.physical_name: t
            for t in self.db.query(SchemaTable).filter(SchemaTable.client_id == self.client_id).all()
        }
        keys = []
        for col in (
            self.db.query(SchemaColumn)
            .filter(SchemaColumn.table_id == table.id, SchemaColumn.is_fk.is_(True))
            .order_by(SchemaColumn.sort_order)
            .all()
        ):
            if col.fk_table == catalog.LIST_ENTRIES_TABLE:
                continue
            target = registry.get(col.fk_table or "")
            keys.append(
                {
                    "column_id": col.id,
                    "column_name": col.display_name,
                    "physical_name": col.physical_name,
                    "fk_table": col.fk_table,
                    "fk_table_id": target.id if target else None,
                    "fk_table_name": target.display_name if target else None,
                    "is_unique": col.is_unique,
                }
            )
        rels = (
            self.db.query(SchemaRelation)
            .filter(
                SchemaRelation.client_id == self.client_id,
                (SchemaRelation.from_table_id == table.id) | (SchemaRelation.to_table_id == table.id),
            )
            .all()
        )
        return {
            "table_id": table.id,
            "keys": keys,
            "children": [self._relation_read(r) for r in rels if r.from_table_id == table.id],
            "parents": [self._relation_read(r) for r in rels if r.to_table_id == table.id],
        }

    def attach_extra_fields(self, samples: Sequence[Sample]) -> List[Dict[str, Any]]:
        cols = self.extra_sample_columns()
        readable = [c for c in cols if self._role_can_read(self.user.role_id, c.table_id, c.id)]
        payloads: List[Dict[str, Any]] = []
        names = [c.physical_name for c in readable if COL_SLUG_RE.match(c.physical_name)]
        by_id: Dict[Any, Dict[str, Any]] = {}
        if names and samples:
            ids = [s.id for s in samples]
            col_sql = ", ".join(n for n in names)
            stmt = text(f"SELECT id, {col_sql} FROM samples WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            try:
                rows = self.db.execute(stmt, {"ids": ids}).mappings().all()
            except Exception:
                logger.warning("extra sample columns not physically present yet")
                return [{} for _ in samples]
            for r in rows:
                extra = {n: r.get(n) for n in names}
                by_id[r["id"]] = extra
        for sample in samples:
            extra = by_id.get(sample.id, {})
            payloads.append(extra)
        return payloads

    def write_extra_fields(self, sample: Sample, extra_fields: Dict[str, Any]) -> None:
        if not extra_fields:
            return
        cols = {c.physical_name: c for c in self.extra_sample_columns()}
        assignments = []
        params: Dict[str, Any] = {"id": sample.id}
        for name, value in extra_fields.items():
            col = cols.get(name)
            if not col:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"Unknown extra field {name}",
                )
            if not self._role_can_write(self.user.role_id, col.table_id, col.id):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    f"You don't have permission to change {col.display_name}.",
                )
            if not COL_SLUG_RE.match(name):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid field")
            assignments.append(f"{name} = :{name}")
            params[name] = value
        if assignments:
            self.db.execute(
                text(f"UPDATE samples SET {', '.join(assignments)} WHERE id = :id"),
                params,
            )
