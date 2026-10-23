"""ELISA follow-ups: revoke DELETE, record a failed-run override, cap volume.

Revision ID: 0108_elisa_followups
Revises: 0107_elisa_run_gaps

0107 granted DELETE on result_acceptances, and 0103's default privileges
grant DELETE on tables created by lims_migrate. This revision revokes that
DELETE from lims_app. It grants nothing and drops no table.

``result_acceptances.override_failed`` records that the reviewer accepted a
value from a failed run. The catalog column is added only for clients that
already have the table registered.

``samples.volume_ul`` gains an upper bound of 10000000 µL (10 L). The
existing non-negative check stays.
"""
from __future__ import annotations

import importlib.util
import os

import sqlalchemy as sa
from alembic import op

revision = "0108_elisa_followups"
down_revision = "0107_elisa_run_gaps"
branch_labels = None
depends_on = None

_COLUMN = "override_failed"
_TABLE = "result_acceptances"


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0108", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_check_constraint(
        "ck_samples_volume_ul_max",
        "samples",
        "volume_ul IS NULL OR volume_ul <= 10000000",
    )
    op.execute("REVOKE DELETE ON TABLE result_acceptances FROM lims_app")
    _sync_override_column(op.get_bind())


def _sync_override_column(conn) -> None:
    """Catalog the new column for clients that already register the table."""
    m = _m0089()
    admin = m._bind_admin(conn)
    reflected = m._reflect(conn, [_TABLE])
    by_name = {col["name"]: col for col in reflected.get(_TABLE, [])}
    col = by_name.get(_COLUMN)
    if col is None:
        return
    clients = [
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT client_id FROM schema_tables WHERE physical_name = :p"
            ),
            {"p": _TABLE},
        ).all()
    ]
    for client in clients:
        table_id = conn.execute(
            sa.text(
                "SELECT id FROM schema_tables WHERE client_id = :c AND physical_name = :p"
            ),
            {"c": client, "p": _TABLE},
        ).scalar()
        if table_id is None:
            continue
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
                VALUES (:id, :c, :t, :d, :p, :dt, :n, :o, 'active', false, false, false, NULL, false,
                    :pg, 'reflected', true, NOW(), :u, NOW(), :u)
                """
            ),
            {
                "id": m._id(client, _TABLE, "col", _COLUMN),
                "c": client,
                "t": table_id,
                "d": "Override failed",
                "p": _COLUMN,
                "dt": m._map_type(col["udt"], False, None),
                "n": col["nullable"],
                "o": col["ordinal"],
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
    op.drop_constraint("ck_samples_volume_ul_max", "samples", type_="check")
    op.drop_column(_TABLE, _COLUMN)
