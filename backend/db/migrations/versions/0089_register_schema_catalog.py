"""Register the configurable existing tables in the Schema catalog up front.

Revision ID: 0089_register_schema_catalog
Revises: 0088_seed_config_editor

Marc's D-3/L-4 ruling: the existing tables a change can be made to and used
through configuration (the Schema display rule) are registered by migration,
not lazily when a screen or a configuring-agent run first looks. A fresh seed
DB then already has schema_tables, schema_columns, and table-level
schema_privileges rows, and starting a run writes nothing to the catalog.

The table list, kinds, display names, column facts, and default privileges are
frozen copies of app/services/ui_schema_catalog.py and UiSchemaService
(ensure_catalog, _sync_columns, _seed_default_table_privileges) as of this
revision; a test compares them with the live display rule. Code-owned tables
(lists, list_entries, units) are never registered.

Rows get deterministic ids (uuid5), so downgrade removes exactly what this
migration added. Tables a client already had registered are left alone.
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0089_register_schema_catalog"
down_revision = "0088_seed_config_editor"
branch_labels = None
depends_on = None

NAMESPACE = uuid.UUID("5c7b3f0e-2b51-4d0e-9a51-0089c0a7a10c")

# (physical_name, kind, display_name): LAB_TABLES (core) + SYSTEM_TABLES (system),
# minus NOT_SCHEMA_TABLES (lists, list_entries, units).
TABLES = (
    ("samples", "core", "Samples"),
    ("containers", "core", "Containers"),
    ("contents", "core", "Contents"),
    ("tests", "core", "Tests"),
    ("results", "core", "Results"),
    ("batches", "core", "Batches"),
    ("projects", "core", "Projects"),
    ("client_projects", "core", "Client projects"),
    ("experiments", "core", "Experiments"),
    ("lims_runs", "core", "LIMS runs"),
    ("work_orders", "core", "Work orders"),
    ("asked_for", "core", "Asked for"),
    ("routing_map", "core", "Routing map"),
    ("analyses", "core", "Analyses"),
    ("analytes", "core", "Analytes"),
    ("test_batteries", "core", "Test batteries"),
    ("instruments", "core", "Instruments"),
    ("locations", "core", "Locations"),
    ("eln_processes", "core", "Processes"),
    ("container_types", "system", "Container types"),
    ("instrument_types", "system", "Instrument types"),
    ("sample_type_transitions", "system", "Sample type transitions"),
    ("clients", "system", "Clients"),
    ("users", "system", "Users"),
    ("roles", "system", "Roles"),
)
NEVER = ("lists", "list_entries", "units")
PLATFORM_COLUMNS = {"active", "client_id", "created_at", "created_by", "id", "modified_at", "modified_by"}
IDENTITY_SAMPLE_COLS = {"client_sample_id", "matrix", "name", "parent_sample_id", "project_id", "sample_type", "status"}
DEFAULT_PRIVILEGES = (
    ("Administrator", "write"),
    ("Lab Manager", "write"),
    ("Lab Technician", "write"),
    ("Client", "read"),
)


def _id(*parts) -> str:
    return str(uuid.uuid5(NAMESPACE, ":".join(str(p) for p in parts)))


def _map_type(udt: str, is_fk: bool, fk_table) -> str:
    if is_fk and fk_table == "list_entries":
        return "list"
    name = (udt or "").lower()
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


def _column_display(name: str, is_fk: bool) -> str:
    base = name
    if is_fk and base.endswith("_id") and len(base) > 3:
        base = base[:-3]
    return base.replace("_", " ").strip().title()


def _acting_admin(conn):
    return conn.execute(
        sa.text(
            """
            SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id
            WHERE r.name = 'Administrator'
            ORDER BY (u.id = '00000000-0000-0000-0000-000000000001') DESC, u.created_at
            LIMIT 1
            """
        )
    ).scalar()


def _bind_admin(conn):
    """The schema registries have FORCE RLS; act as an Administrator (is_admin())."""
    admin = _acting_admin(conn)
    if admin is not None:
        conn.execute(sa.text("SELECT set_config('app.current_user_id', :v, false)"), {"v": str(admin)})
    return admin


def _reflect(conn, names):
    cols = conn.execute(
        sa.text(
            "SELECT table_name, column_name, ordinal_position, udt_name, is_nullable "
            "FROM information_schema.columns WHERE table_schema = 'public' AND table_name = ANY(:n) "
            "ORDER BY table_name, ordinal_position"
        ),
        {"n": list(names)},
    ).all()
    fks = {
        (r[0], r[1]): r[2]
        for r in conn.execute(
            sa.text(
                """
                SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text
                FROM pg_constraint c
                JOIN pg_namespace n ON n.oid = c.connamespace
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
                WHERE c.contype = 'f' AND n.nspname = 'public' AND array_length(c.conkey, 1) = 1
                  AND c.conrelid::regclass::text = ANY(:n)
                """
            ),
            {"n": list(names)},
        ).all()
    }
    uniques = {
        (r[0], r[1])
        for r in conn.execute(
            sa.text(
                """
                SELECT i.indrelid::regclass::text, a.attname
                FROM pg_index i
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
                WHERE n.nspname = 'public' AND i.indisunique AND i.indnkeyatts = 1
                  AND i.indrelid::regclass::text = ANY(:n)
                """
            ),
            {"n": list(names)},
        ).all()
    }
    out = {}
    for table, name, ordinal, udt, nullable in cols:
        fk_table = fks.get((table, name))
        out.setdefault(table, []).append(
            {
                "name": name,
                "ordinal": ordinal,
                "udt": udt,
                "nullable": nullable == "YES",
                "is_fk": fk_table is not None,
                "fk_table": fk_table,
                "is_unique": (table, name) in uniques,
            }
        )
    return out


def upgrade() -> None:
    conn = op.get_bind()
    admin = _bind_admin(conn)
    present = {
        r[0]
        for r in conn.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' AND table_name = ANY(:n)"
            ),
            {"n": [t[0] for t in TABLES]},
        ).all()
    }
    tables = [t for t in TABLES if t[0] in present and t[0] not in NEVER]
    reflected = _reflect(conn, [t[0] for t in tables])
    roles = {r[1]: r[0] for r in conn.execute(sa.text("SELECT id, name FROM roles")).all()}
    clients = [r[0] for r in conn.execute(sa.text("SELECT id FROM clients ORDER BY created_at")).all()]
    for client in clients:
        registered = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT physical_name FROM schema_tables WHERE client_id = :c"), {"c": client}
            ).all()
        }
        for physical, kind, display in tables:
            if physical in registered:
                continue
            table_id = _id(client, physical)
            conn.execute(
                sa.text(
                    """
                    INSERT INTO schema_tables (id, client_id, display_name, physical_name, kind, status, active,
                                               created_at, created_by, modified_at, modified_by)
                    VALUES (:id, :c, :d, :p, :k, 'active', true, NOW(), :u, NOW(), :u)
                    """
                ),
                {"id": table_id, "c": client, "d": display, "p": physical, "k": kind, "u": admin},
            )
            for role_name, access in DEFAULT_PRIVILEGES:
                role_id = roles.get(role_name)
                if role_id is None:
                    continue
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO schema_privileges (id, client_id, role_id, table_id, column_id, access,
                                                       created_at, created_by, modified_at, modified_by)
                        VALUES (:id, :c, :r, :t, NULL, :a, NOW(), :u, NOW(), :u)
                        """
                    ),
                    {"id": _id(client, physical, "priv", role_id), "c": client, "r": role_id,
                     "t": table_id, "a": access, "u": admin},
                )
            for col in reflected.get(physical, []):
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO schema_columns (id, client_id, table_id, display_name, physical_name, data_type,
                            nullable, sort_order, status, is_platform, is_identity, is_fk, fk_table, is_unique,
                            pg_type, origin, active, created_at, created_by, modified_at, modified_by)
                        VALUES (:id, :c, :t, :d, :p, :dt, :n, :o, 'active', :plat, :ident, :fk, :fkt, :uq,
                            :pg, 'reflected', true, NOW(), :u, NOW(), :u)
                        """
                    ),
                    {
                        "id": _id(client, physical, "col", col["name"]),
                        "c": client,
                        "t": table_id,
                        "d": _column_display(col["name"], col["is_fk"]),
                        "p": col["name"],
                        "dt": _map_type(col["udt"], col["is_fk"], col["fk_table"]),
                        "n": col["nullable"],
                        "o": col["ordinal"],
                        "plat": col["name"] in PLATFORM_COLUMNS,
                        "ident": physical == "samples" and col["name"] in IDENTITY_SAMPLE_COLS,
                        "fk": col["is_fk"],
                        "fkt": col["fk_table"],
                        "uq": col["is_unique"],
                        "pg": col["udt"],
                        "u": admin,
                    },
                )
    conn.execute(sa.text("SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"))


def downgrade() -> None:
    """Remove exactly the rows this migration added (deterministic ids). A row a
    later change still points at (a layout field, a relation, a column
    privilege, a UI column) is kept, with its table, so nothing else breaks."""
    conn = op.get_bind()
    _bind_admin(conn)
    roles = [r[0] for r in conn.execute(sa.text("SELECT id FROM roles")).all()]
    clients = [r[0] for r in conn.execute(sa.text("SELECT id FROM clients")).all()]
    table_ids, column_ids, privilege_ids = [], [], []
    for client in clients:
        for physical, _kind, _display in TABLES:
            table_ids.append(_id(client, physical))
            privilege_ids.extend(_id(client, physical, "priv", role) for role in roles)
    for row in conn.execute(
        sa.text("SELECT c.client_id, t.physical_name, c.physical_name FROM schema_columns c "
                "JOIN schema_tables t ON t.id = c.table_id WHERE t.id = ANY(CAST(:t AS uuid[]))"),
        {"t": table_ids},
    ).all():
        column_ids.append(_id(row[0], row[1], "col", row[2]))
    conn.execute(sa.text("DELETE FROM schema_privileges WHERE id = ANY(CAST(:p AS uuid[]))"), {"p": privilege_ids})
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns c WHERE c.id = ANY(CAST(:c AS uuid[]))
              AND NOT EXISTS (SELECT 1 FROM schema_layout_fields f WHERE f.column_id = c.id)
              AND NOT EXISTS (SELECT 1 FROM schema_relations r WHERE r.fk_column_id = c.id)
              AND NOT EXISTS (SELECT 1 FROM schema_privileges p WHERE p.column_id = c.id)
            """
        ),
        {"c": column_ids},
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_tables t WHERE t.id = ANY(CAST(:t AS uuid[]))
              AND NOT EXISTS (SELECT 1 FROM schema_columns c WHERE c.table_id = t.id)
              AND NOT EXISTS (SELECT 1 FROM schema_privileges p WHERE p.table_id = t.id)
              AND NOT EXISTS (SELECT 1 FROM schema_relations r WHERE r.from_table_id = t.id OR r.to_table_id = t.id)
              AND NOT EXISTS (SELECT 1 FROM schema_layout_fields f JOIN schema_columns c ON c.id = f.column_id
                              WHERE c.table_id = t.id)
            """
        ),
        {"t": table_ids},
    )
    conn.execute(sa.text("SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"))
