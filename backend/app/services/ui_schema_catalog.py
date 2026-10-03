"""Allow-listed table catalog for the Schema table browser.

The Schema screen is a browser over *real* Postgres tables. What appears is
decided here, not by a hardcoded filter on the registry query:

* **Lab** tables (``kind='core'``) — the sample-centric data spine.
* **System** reference tables (``kind='system'``) — ``lists`` and peers.
* **UI-created** tables (``kind='ui'``) — whatever CREATE TABLE made (``x_`` / ``lab_``).
* **Engine internals** are never registered: migrations, sessions, audit and
  registry plumbing.

Column facts (type, nullability, FOREIGN KEY, UNIQUE) are *reflected* from
Postgres catalogs. Reflection only describes; it never issues DDL (OQ-16).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

LAB_TABLES: tuple[str, ...] = (
    "samples",
    "containers",
    "contents",
    "tests",
    "results",
    "batches",
    "projects",
    "client_projects",
    "experiments",
    "lims_runs",
    "work_orders",
    "asked_for",
    "routing_map",
    "analyses",
    "analytes",
    "test_batteries",
    "instruments",
    "locations",
    "eln_processes",
)

SYSTEM_TABLES: tuple[str, ...] = (
    "lists",
    "list_entries",
    "units",
    "container_types",
    "instrument_types",
    "sample_type_transitions",
    "clients",
    "users",
    "roles",
)

# Never shown. Documented so the list filter is testable, not exhaustive —
# anything not allow-listed above is hidden regardless.
ENGINE_INTERNAL: tuple[str, ...] = (
    "alembic_version",
    "revoked_tokens",
    "login_throttle",
    "permissions",
    "role_permissions",
    "schema_tables",
    "schema_columns",
    "schema_layouts",
    "schema_layout_fields",
    "schema_privileges",
    "schema_relations",
    "schema_changes",
    "ui_schema_ddl_log",
    "custom_attributes_config",
    "field_definitions",
    "name_templates",
)

PLATFORM_COLUMN_NAMES: frozenset[str] = frozenset(
    {"id", "client_id", "created_at", "created_by", "modified_at", "modified_by", "active"}
)

LIST_ENTRIES_TABLE = "list_entries"

DISPLAY_NAMES: Mapping[str, str] = {
    "samples": "Samples",
    "containers": "Containers",
    "contents": "Contents",
    "tests": "Tests",
    "results": "Results",
    "batches": "Batches",
    "projects": "Projects",
    "client_projects": "Client projects",
    "experiments": "Experiments",
    "lims_runs": "LIMS runs",
    "work_orders": "Work orders",
    "asked_for": "Asked for",
    "routing_map": "Routing map",
    "analyses": "Analyses",
    "analytes": "Analytes",
    "test_batteries": "Test batteries",
    "instruments": "Instruments",
    "locations": "Locations",
    "eln_processes": "Processes",
    "lists": "Lists",
    "list_entries": "List entries",
    "units": "Units",
    "container_types": "Container types",
    "instrument_types": "Instrument types",
    "sample_type_transitions": "Sample type transitions",
    "clients": "Clients",
    "users": "Users",
    "roles": "Roles",
}


def kind_for(physical_name: str) -> Optional[str]:
    """``core`` / ``system`` for allow-listed tables, ``None`` when hidden."""
    if physical_name in LAB_TABLES:
        return "core"
    if physical_name in SYSTEM_TABLES:
        return "system"
    return None


def category_for_kind(kind: str) -> str:
    """Badge: every registered table is Lab unless it is a system reference table."""
    return "system" if kind == "system" else "lab"


def display_name_for(physical_name: str) -> str:
    return DISPLAY_NAMES.get(physical_name) or physical_name.replace("_", " ").capitalize()


def column_display_name(physical_name: str, is_fk: bool) -> str:
    base = physical_name
    if is_fk and base.endswith("_id") and len(base) > 3:
        base = base[:-3]
    return base.replace("_", " ").strip().title()


def map_pg_type(udt_name: str, is_fk: bool, fk_table: Optional[str]) -> str:
    """Postgres ``udt_name`` → registry ``data_type``.

    A uuid FK to ``list_entries`` is a *list binding* (lab-editable); any other
    FK is a relationship key.
    """
    if is_fk and fk_table == LIST_ENTRIES_TABLE:
        return "list"
    name = (udt_name or "").lower()
    if name in {"text", "varchar", "bpchar", "char", "citext", "name"}:
        return "text"
    if name in {"numeric", "float4", "float8", "money"}:
        return "numeric"
    if name in {"int2", "int4", "int8"}:
        return "integer"
    if name == "bool":
        return "boolean"
    if name == "date":
        return "date"
    if name in {"timestamp", "timestamptz"}:
        return "timestamptz"
    if name == "uuid":
        return "uuid"
    if name in {"jsonb", "json"}:
        return "jsonb"
    return "other"


def is_system_column(
    physical_name: str,
    *,
    is_platform: bool,
    is_identity: bool,
    is_fk: bool,
    fk_table: Optional[str],
    table_kind: str,
) -> Optional[str]:
    """Reason a column is locked in the UI, or ``None`` when it is a lab column.

    Lock set (product lock): id, timestamps, created-by/modified-by, relationship
    foreign keys (including ``list_id`` on list entries), and every column of a
    System reference table. A ``list_entries`` FK is a list binding, not a
    relationship key, so it stays a lab column.
    """
    if table_kind == "system":
        return "system_table"
    if is_platform or physical_name in PLATFORM_COLUMN_NAMES:
        return "platform"
    if is_identity:
        return "identity"
    if is_fk and fk_table != LIST_ENTRIES_TABLE:
        return "relationship_key"
    return None


@dataclass(frozen=True)
class ReflectedColumn:
    table: str
    name: str
    ordinal: int
    udt_name: str
    nullable: bool
    is_fk: bool
    fk_table: Optional[str]
    is_unique: bool


def existing_tables(db: Session, names: Iterable[str]) -> Set[str]:
    wanted = list(dict.fromkeys(names))
    if not wanted:
        return set()
    stmt = text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name IN :names"
    ).bindparams(bindparam("names", expanding=True))
    return {r[0] for r in db.execute(stmt, {"names": wanted}).all()}


def reflect_columns(db: Session, tables: Sequence[str]) -> Dict[str, List[ReflectedColumn]]:
    """Columns + single-column FK / UNIQUE facts for the given public tables."""
    if not tables:
        return {}
    names = list(dict.fromkeys(tables))
    col_stmt = text(
        "SELECT table_name, column_name, ordinal_position, udt_name, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name IN :names "
        "ORDER BY table_name, ordinal_position"
    ).bindparams(bindparam("names", expanding=True))
    fk_stmt = text(
        """
        SELECT c.conrelid::regclass::text AS table_name,
               a.attname AS column_name,
               c.confrelid::regclass::text AS ref_table
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f'
          AND n.nspname = 'public'
          AND array_length(c.conkey, 1) = 1
          AND c.conrelid::regclass::text IN :names
        """
    ).bindparams(bindparam("names", expanding=True))
    uq_stmt = text(
        """
        SELECT i.indrelid::regclass::text AS table_name, a.attname AS column_name
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
        WHERE n.nspname = 'public'
          AND i.indisunique
          AND i.indnkeyatts = 1
          AND i.indpred IS NULL
          AND i.indrelid::regclass::text IN :names
        """
    ).bindparams(bindparam("names", expanding=True))
    params = {"names": names}
    fks: Dict[tuple[str, str], str] = {}
    for r in db.execute(fk_stmt, params).mappings().all():
        ref = r["ref_table"].split(".")[-1].strip('"')
        fks[(r["table_name"].split(".")[-1].strip('"'), r["column_name"])] = ref
    uniques: Set[tuple[str, str]] = {
        (r["table_name"].split(".")[-1].strip('"'), r["column_name"])
        for r in db.execute(uq_stmt, params).mappings().all()
    }
    out: Dict[str, List[ReflectedColumn]] = {n: [] for n in names}
    for r in db.execute(col_stmt, params).mappings().all():
        key = (r["table_name"], r["column_name"])
        out[r["table_name"]].append(
            ReflectedColumn(
                table=r["table_name"],
                name=r["column_name"],
                ordinal=int(r["ordinal_position"]),
                udt_name=r["udt_name"],
                nullable=(r["is_nullable"] == "YES"),
                is_fk=key in fks,
                fk_table=fks.get(key),
                is_unique=key in uniques,
            )
        )
    return out
