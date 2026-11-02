"""Optional per-instrument maintenance tracking.

Revision ID: 0113_maintenance_tracked
Revises: 0112_instrument_legacy_lock

Marc (2026-10-22): maintenance is optional. Some labs use their own metrology
system. ``instruments.maintenance_tracked`` is NOT NULL default false
(Postgres ``DEFAULT false`` stays, so an INSERT that omits the column is
false). Existing rows stay false. The type default lives on
``instrument_type_defaults`` (side table, registered in Schema) so
``list_entries`` is not widened for every list.

Revision id stays at or under 32 characters because
``alembic_version.version_num`` is varchar(32).

Revokes only. No new GRANTs. Nothing is dropped.
"""

from __future__ import annotations

import importlib.util
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0113_maintenance_tracked"
down_revision = "0112_instrument_legacy_lock"
branch_labels = None
depends_on = None

_CONFIG_EDIT = """EXISTS (
    SELECT 1 FROM users u
    JOIN role_permissions rp ON rp.role_id = u.role_id
    JOIN permissions p ON p.id = rp.permission_id
    WHERE u.id = current_user_id() AND p.name = 'config:edit' AND p.active = true
)"""
_CATALOG_POLICY = f"is_admin() OR has_experiment_access() OR {_CONFIG_EDIT}"

TABLES = (
    ("instrument_type_defaults", "core", "Instrument type defaults"),
)


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0113", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lock(table: str, policy: str) -> None:
    op.execute(f"REVOKE DELETE ON {table} FROM lims_app")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table}")
    op.execute(
        f"CREATE POLICY {table}_access ON {table} FOR ALL "
        f"USING ({policy}) WITH CHECK ({policy})"
    )
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    uuid_t = postgresql.UUID(as_uuid=True)
    op.add_column(
        "instruments",
        sa.Column(
            "maintenance_tracked",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    op.create_table(
        "instrument_type_defaults",
        sa.Column(
            "instrument_type_id",
            uuid_t,
            sa.ForeignKey("list_entries.id"),
            primary_key=True,
        ),
        sa.Column(
            "maintenance_tracked",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "modified_by",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.execute(
        "DROP TRIGGER IF EXISTS instrument_type_defaults_update_modified_at "
        "ON instrument_type_defaults"
    )
    op.execute(
        "CREATE TRIGGER instrument_type_defaults_update_modified_at "
        "BEFORE UPDATE ON instrument_type_defaults "
        "FOR EACH ROW EXECUTE FUNCTION update_modified_at_column()"
    )

    op.create_table(
        "instrument_maintenance_audits",
        sa.Column(
            "id",
            uuid_t,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "instrument_id",
            uuid_t,
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("previous_value", sa.Boolean(), nullable=False),
        sa.Column("new_value", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            uuid_t,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_instrument_maintenance_audits_instrument_id",
        "instrument_maintenance_audits",
        ["instrument_id"],
    )

    _lock("instrument_type_defaults", _CATALOG_POLICY)
    _lock("instrument_maintenance_audits", _CATALOG_POLICY)
    _register()
    _sync_maintenance_column()


def _register() -> None:
    conn = op.get_bind()
    m = _m0089()
    cataloged = [
        r[0]
        for r in conn.execute(
            sa.text("SELECT DISTINCT client_id FROM schema_tables ORDER BY 1")
        ).all()
    ]
    if not cataloged:
        return
    admin = m._bind_admin(conn)
    roles = {r[1]: r[0] for r in conn.execute(sa.text("SELECT id, name FROM roles")).all()}
    for client in cataloged:
        registered = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT physical_name FROM schema_tables WHERE client_id = :c"),
                {"c": client},
            ).all()
        }
        for physical, kind, display in TABLES:
            if physical in registered:
                continue
            table_id = m._id(client, physical)
            conn.execute(
                sa.text(
                    """
                    INSERT INTO schema_tables (
                        id, client_id, display_name, physical_name, kind, status, active,
                        created_at, created_by, modified_at, modified_by
                    )
                    VALUES (:id, :c, :d, :p, :k, 'active', true, NOW(), :u, NOW(), :u)
                    """
                ),
                {
                    "id": table_id,
                    "c": client,
                    "d": display,
                    "p": physical,
                    "k": kind,
                    "u": admin,
                },
            )
            reflected = m._reflect(conn, [physical]).get(physical, [])
            for col in reflected:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO schema_columns (
                            id, client_id, table_id, display_name, physical_name, data_type,
                            nullable, sort_order, status, is_platform, is_identity, is_fk,
                            fk_table, is_unique, pg_type, origin, active,
                            created_at, created_by, modified_at, modified_by
                        )
                        VALUES (
                            :id, :c, :t, :d, :p, :dt, :n, :o, 'active', :plat, false, :fk,
                            :fkt, :uq, :pg, 'reflected', true, NOW(), :u, NOW(), :u
                        )
                        """
                    ),
                    {
                        "id": m._id(client, physical, "col", col["name"]),
                        "c": client,
                        "t": table_id,
                        "d": m._column_display(col["name"], col["is_fk"]),
                        "p": col["name"],
                        "dt": m._map_type(col["udt"], col["is_fk"], col["fk_table"]),
                        "n": col["nullable"],
                        "o": col["ordinal"],
                        "plat": col["name"] in m.PLATFORM_COLUMNS,
                        "fk": col["is_fk"],
                        "fkt": col["fk_table"],
                        "uq": col["is_unique"],
                        "pg": col["udt"],
                        "u": admin,
                    },
                )
            for role_name, access in m.DEFAULT_PRIVILEGES:
                role_id = roles.get(role_name)
                if role_id is None:
                    continue
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO schema_privileges (
                            id, client_id, role_id, table_id, column_id, access,
                            created_at, created_by, modified_at, modified_by
                        )
                        VALUES (:id, :c, :r, :t, NULL, :a, NOW(), :u, NOW(), :u)
                        """
                    ),
                    {
                        "id": m._id(client, physical, "priv", role_id),
                        "c": client,
                        "r": role_id,
                        "t": table_id,
                        "a": access,
                        "u": admin,
                    },
                )
    conn.execute(
        sa.text(
            "SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"
        )
    )


def _sync_maintenance_column() -> None:
    conn = op.get_bind()
    m = _m0089()
    admin = m._bind_admin(conn)
    reflected = m._reflect(conn, ["instruments"]).get("instruments", [])
    col = next((c for c in reflected if c["name"] == "maintenance_tracked"), None)
    if col is None:
        return
    table_rows = conn.execute(
        sa.text(
            "SELECT client_id, id FROM schema_tables WHERE physical_name = 'instruments'"
        )
    ).all()
    for client, table_id in table_rows:
        existing = conn.execute(
            sa.text(
                "SELECT 1 FROM schema_columns "
                "WHERE table_id = :t AND physical_name = 'maintenance_tracked'"
            ),
            {"t": table_id},
        ).scalar()
        if existing:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO schema_columns (
                    id, client_id, table_id, display_name, physical_name, data_type,
                    nullable, sort_order, status, is_platform, is_identity, is_fk,
                    fk_table, is_unique, pg_type, origin, active,
                    created_at, created_by, modified_at, modified_by
                )
                VALUES (
                    :id, :c, :t, :d, :p, :dt, :n, :o, 'active', :plat, false, :fk,
                    :fkt, :uq, :pg, 'reflected', true, NOW(), :u, NOW(), :u
                )
                """
            ),
            {
                "id": m._id(client, "instruments", "col", "maintenance_tracked"),
                "c": client,
                "t": table_id,
                "d": m._column_display(col["name"], col["is_fk"]),
                "p": col["name"],
                "dt": m._map_type(col["udt"], col["is_fk"], col["fk_table"]),
                "n": col["nullable"],
                "o": col["ordinal"],
                "plat": col["name"] in m.PLATFORM_COLUMNS,
                "fk": col["is_fk"],
                "fkt": col["fk_table"],
                "uq": col["is_unique"],
                "pg": col["udt"],
                "u": admin,
            },
        )
    conn.execute(
        sa.text(
            "SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    leftover = conn.execute(sa.text("SELECT count(*) FROM instrument_maintenance_audits")).scalar()
    if leftover:
        raise RuntimeError(
            "0113 downgrade refuses: instrument_maintenance_audits has rows"
        )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_privileges
            WHERE table_id IN (
                SELECT id FROM schema_tables
                WHERE physical_name = 'instrument_type_defaults'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns
            WHERE table_id IN (
                SELECT id FROM schema_tables
                WHERE physical_name = 'instrument_type_defaults'
            )
            """
        )
    )
    conn.execute(
        sa.text("DELETE FROM schema_tables WHERE physical_name = 'instrument_type_defaults'")
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns
            WHERE physical_name = 'maintenance_tracked'
              AND table_id IN (
                  SELECT id FROM schema_tables WHERE physical_name = 'instruments'
              )
            """
        )
    )
    op.execute("DROP TRIGGER IF EXISTS instrument_type_defaults_update_modified_at ON instrument_type_defaults")
    op.execute("DROP POLICY IF EXISTS instrument_type_defaults_access ON instrument_type_defaults")
    op.execute("DROP POLICY IF EXISTS instrument_maintenance_audits_access ON instrument_maintenance_audits")
    op.drop_index(
        "ix_instrument_maintenance_audits_instrument_id",
        table_name="instrument_maintenance_audits",
    )
    op.drop_table("instrument_maintenance_audits")
    op.drop_table("instrument_type_defaults")
    op.drop_column("instruments", "maintenance_tracked")
