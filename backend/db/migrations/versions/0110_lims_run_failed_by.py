"""Record who failed a LIMS run.

Revision ID: 0110_lims_run_failed_by
Revises: 0109_revoke_reagent_delete

``lims_runs.failed_by`` is the user who failed the run. It is NULL on runs
failed before this revision; ``modified_by`` on those rows may name a later
editor, so it is not copied over. The FK is ON DELETE RESTRICT, like the
other identity columns. The catalog column is added only for clients that
already register ``lims_runs``. No privilege is granted and nothing is dropped.
"""
from __future__ import annotations

import importlib.util
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0110_lims_run_failed_by"
down_revision = "0109_revoke_reagent_delete"
branch_labels = None
depends_on = None

_TABLE = "lims_runs"
_COLUMN = "failed_by"
_FK = "fk_lims_runs_failed_by_users"


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0110", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(_FK, _TABLE, "users", [_COLUMN], ["id"], ondelete="RESTRICT")
    _sync_column(op.get_bind())


def _sync_column(conn) -> None:
    """Catalog the new column for clients that already register the table."""
    m = _m0089()
    admin = m._bind_admin(conn)
    col = {c["name"]: c for c in m._reflect(conn, [_TABLE]).get(_TABLE, [])}.get(_COLUMN)
    if col is None:
        return
    tables = conn.execute(
        sa.text("SELECT client_id, id FROM schema_tables WHERE physical_name = :p"),
        {"p": _TABLE},
    ).all()
    for client, table_id in tables:
        have = conn.execute(
            sa.text(
                "SELECT 1 FROM schema_columns WHERE table_id = :t AND physical_name = :n"
            ),
            {"t": table_id, "n": _COLUMN},
        ).scalar()
        if have:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO schema_columns (id, client_id, table_id, display_name, physical_name, data_type,
                    nullable, sort_order, status, is_platform, is_identity, is_fk, fk_table, is_unique,
                    pg_type, origin, active, created_at, created_by, modified_at, modified_by)
                VALUES (:id, :c, :t, :d, :p, :dt, :n, :o, 'active', false, false, :fk, :fkt, :uq,
                    :pg, 'reflected', true, NOW(), :u, NOW(), :u)
                """
            ),
            {
                "id": m._id(client, _TABLE, "col", _COLUMN),
                "c": client,
                "t": table_id,
                "d": "Failed by",
                "p": _COLUMN,
                "dt": m._map_type(col["udt"], col["is_fk"], col["fk_table"]),
                "n": col["nullable"],
                "o": col["ordinal"],
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
    m = _m0089()
    m._bind_admin(conn)
    clients = [row[0] for row in conn.execute(sa.text("SELECT id FROM clients")).all()]
    col_ids = [m._id(client, _TABLE, "col", _COLUMN) for client in clients]
    if col_ids:
        conn.execute(
            sa.text("DELETE FROM schema_layout_fields WHERE column_id = ANY(CAST(:c AS uuid[]))"),
            {"c": col_ids},
        )
        conn.execute(
            sa.text("DELETE FROM schema_privileges WHERE column_id = ANY(CAST(:c AS uuid[]))"),
            {"c": col_ids},
        )
        conn.execute(
            sa.text("DELETE FROM schema_columns WHERE id = ANY(CAST(:c AS uuid[]))"),
            {"c": col_ids},
        )
    conn.execute(
        sa.text(
            "SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"
        )
    )
    op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    op.drop_column(_TABLE, _COLUMN)
