"""ELISA run gaps: sample link notes, plate reject, rerun, receipt fields.

Revision ID: 0107_elisa_run_gaps
Revises: 0105_lab_timezone_required

Additive only. Nothing is dropped.

* samples.volume_ul, receipt_condition, thaw_count — receipt facts. Collection
  day stays on samples.date_sampled.
* lims_runs.status_reason, rejected_at, replaces_run_id — reject keeps the run
  (status failed) and a rerun points at the run it replaces.
* lims_run_data.sample_key, link_note — unmatched import rows stay, with why.
* result_acceptances — the reviewer's pick of which value is accepted. An
  older pick is inactive. Rows are not deleted.

result_acceptances is registered in the Schema catalog the same way 0089
registers a lab table. New columns on samples and lims_runs are added to the
existing catalog rows so the column list matches Postgres.

This revision revises 0105. After merge, 0108_elisa_followups revises this
revision, then 0109_instrument_tracking, so the chain is a single head.
"""
from __future__ import annotations

import importlib.util
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0107_elisa_run_gaps"
down_revision = "0105_lab_timezone_required"
branch_labels = None
depends_on = None

TABLES = (("result_acceptances", "core", "Result acceptances"),)

_ACCEPT_POLICY = """is_admin() OR EXISTS (
    SELECT 1 FROM samples s
    WHERE s.id = result_acceptances.sample_id
    AND has_project_access(s.project_id)
)"""

_NEW_COLUMNS = {
    "samples": ("volume_ul", "receipt_condition", "thaw_count"),
    "lims_runs": ("status_reason", "replaces_run_id", "rejected_at"),
}

_DISPLAY = {
    "volume_ul": "Volume (µL)",
    "receipt_condition": "Condition",
    "thaw_count": "Thaw count",
    "status_reason": "Status reason",
    "replaces_run_id": "Replaces run",
    "rejected_at": "Rejected at",
}


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0107", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_cols():
    return [
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
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
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.add_column("samples", sa.Column("volume_ul", sa.Numeric(12, 2), nullable=True))
    op.add_column("samples", sa.Column("receipt_condition", sa.String(255), nullable=True))
    op.add_column("samples", sa.Column("thaw_count", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_samples_volume_ul_nonneg",
        "samples",
        "volume_ul IS NULL OR volume_ul >= 0",
    )
    op.create_check_constraint(
        "ck_samples_thaw_count_nonneg",
        "samples",
        "thaw_count IS NULL OR thaw_count >= 0",
    )

    op.add_column("lims_runs", sa.Column("status_reason", sa.Text(), nullable=True))
    op.add_column(
        "lims_runs",
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "lims_runs",
        sa.Column("replaces_run_id", uuid, sa.ForeignKey("lims_runs.id"), nullable=True),
    )
    op.create_index("ix_lims_runs_replaces_run_id", "lims_runs", ["replaces_run_id"])
    op.create_check_constraint(
        "ck_lims_runs_replaces_not_self",
        "lims_runs",
        "replaces_run_id IS NULL OR replaces_run_id <> id",
    )

    op.add_column("lims_run_data", sa.Column("sample_key", sa.String(255), nullable=True))
    op.add_column("lims_run_data", sa.Column("link_note", sa.Text(), nullable=True))

    op.create_table(
        "result_acceptances",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "sample_id",
            uuid,
            sa.ForeignKey("samples.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "analyte_id",
            uuid,
            sa.ForeignKey("analytes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("replicate", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "accepted_lims_run_id",
            uuid,
            sa.ForeignKey("lims_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("accepted_value", sa.Text(), nullable=False),
        sa.Column(
            "other_lims_run_id",
            uuid,
            sa.ForeignKey("lims_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("other_value", sa.Text(), nullable=True),
        sa.Column(
            "previous_lims_run_id",
            uuid,
            sa.ForeignKey("lims_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        *_audit_cols(),
    )
    op.create_index("ix_result_acceptances_sample_id", "result_acceptances", ["sample_id"])
    op.create_index("ix_result_acceptances_analyte_id", "result_acceptances", ["analyte_id"])
    op.create_index(
        "ix_result_acceptances_accepted_lims_run_id",
        "result_acceptances",
        ["accepted_lims_run_id"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_result_acceptances_live ON result_acceptances "
        "(sample_id, analyte_id, replicate) WHERE active = true"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON result_acceptances TO lims_app")
    op.execute("ALTER TABLE result_acceptances ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY result_acceptances_access ON result_acceptances "
        f"FOR ALL USING ({_ACCEPT_POLICY}) WITH CHECK ({_ACCEPT_POLICY})"
    )
    op.execute("ALTER TABLE result_acceptances FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE TRIGGER result_acceptances_update_modified_at BEFORE UPDATE ON result_acceptances "
        "FOR EACH ROW EXECUTE FUNCTION update_modified_at_column()"
    )

    _register(op.get_bind())
    _sync_columns(op.get_bind())


def _register(conn) -> None:
    """Register result_acceptances for clients that already have a schema catalog.

    0089's upgrade walks every client. A later upgrade-to-head, after a test has
    inserted a client, would attach a catalog row to that client and block
    deleting it. Only clients that already have ``samples`` registered are in
    the catalog.
    """
    m = _m0089()
    admin = m._bind_admin(conn)
    reflected = m._reflect(conn, ["result_acceptances"])
    roles = {r[1]: r[0] for r in conn.execute(sa.text("SELECT id, name FROM roles")).all()}
    clients = [
        r[0]
        for r in conn.execute(
            sa.text(
                "SELECT DISTINCT client_id FROM schema_tables WHERE physical_name = 'samples'"
            )
        ).all()
    ]
    physical, kind, display = TABLES[0]
    for client in clients:
        already = conn.execute(
            sa.text(
                "SELECT 1 FROM schema_tables WHERE client_id = :c AND physical_name = :p"
            ),
            {"c": client, "p": physical},
        ).scalar()
        if already:
            continue
        table_id = m._id(client, physical)
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
        for role_name, access in m.DEFAULT_PRIVILEGES:
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
                {
                    "id": m._id(client, physical, "priv", role_id),
                    "c": client,
                    "r": role_id,
                    "t": table_id,
                    "a": access,
                    "u": admin,
                },
            )
        for col in reflected.get(physical, []):
            conn.execute(
                sa.text(
                    """
                    INSERT INTO schema_columns (id, client_id, table_id, display_name, physical_name, data_type,
                        nullable, sort_order, status, is_platform, is_identity, is_fk, fk_table, is_unique,
                        pg_type, origin, active, created_at, created_by, modified_at, modified_by)
                    VALUES (:id, :c, :t, :d, :p, :dt, :n, :o, 'active', :plat, false, :fk, :fkt, :uq,
                        :pg, 'reflected', true, NOW(), :u, NOW(), :u)
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
    conn.execute(
        sa.text("SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)")
    )


def _sync_columns(conn) -> None:
    """Add catalog rows for columns this revision added to tables 0089 already registered."""
    m = _m0089()
    admin = m._bind_admin(conn)
    names = list(_NEW_COLUMNS)
    reflected = m._reflect(conn, names)
    clients = [r[0] for r in conn.execute(sa.text("SELECT id FROM clients")).all()]
    for client in clients:
        for physical, wanted in _NEW_COLUMNS.items():
            table_id = conn.execute(
                sa.text(
                    "SELECT id FROM schema_tables WHERE client_id = :c AND physical_name = :p"
                ),
                {"c": client, "p": physical},
            ).scalar()
            if table_id is None:
                continue
            have = {
                r[0]
                for r in conn.execute(
                    sa.text("SELECT physical_name FROM schema_columns WHERE table_id = :t"),
                    {"t": table_id},
                ).all()
            }
            by_name = {c["name"]: c for c in reflected.get(physical, [])}
            for name in wanted:
                if name in have or name not in by_name:
                    continue
                col = by_name[name]
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
                        "id": m._id(client, physical, "col", name),
                        "c": client,
                        "t": table_id,
                        "d": _DISPLAY.get(name, m._column_display(name, col["is_fk"])),
                        "p": name,
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
        sa.text("SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)")
    )


def downgrade() -> None:
    conn = op.get_bind()
    m = _m0089()
    m._bind_admin(conn)
    col_ids = []
    clients = [r[0] for r in conn.execute(sa.text("SELECT id FROM clients")).all()]
    for client in clients:
        for physical, names in _NEW_COLUMNS.items():
            for name in names:
                col_ids.append(m._id(client, physical, "col", name))
    if col_ids:
        conn.execute(
            sa.text("DELETE FROM schema_columns WHERE id = ANY(CAST(:c AS uuid[]))"),
            {"c": col_ids},
        )
    original = m.TABLES
    try:
        m.TABLES = TABLES
        m.downgrade()
    finally:
        m.TABLES = original
    names = [t[0] for t in TABLES]
    conn.execute(
        sa.text(
            "DELETE FROM schema_layout_fields WHERE column_id IN (SELECT c.id FROM schema_columns c "
            "JOIN schema_tables t ON t.id = c.table_id WHERE t.physical_name = ANY(:n))"
        ),
        {"n": names},
    )
    conn.execute(
        sa.text(
            "DELETE FROM schema_relations WHERE from_table_id IN "
            "(SELECT id FROM schema_tables WHERE physical_name = ANY(:n)) "
            "OR to_table_id IN (SELECT id FROM schema_tables WHERE physical_name = ANY(:n))"
        ),
        {"n": names},
    )
    conn.execute(
        sa.text(
            "DELETE FROM schema_privileges WHERE table_id IN "
            "(SELECT id FROM schema_tables WHERE physical_name = ANY(:n)) "
            "OR column_id IN (SELECT c.id FROM schema_columns c JOIN schema_tables t ON t.id = c.table_id "
            "WHERE t.physical_name = ANY(:n))"
        ),
        {"n": names},
    )
    conn.execute(
        sa.text(
            "DELETE FROM schema_columns WHERE table_id IN "
            "(SELECT id FROM schema_tables WHERE physical_name = ANY(:n))"
        ),
        {"n": names},
    )
    conn.execute(sa.text("DELETE FROM schema_tables WHERE physical_name = ANY(:n)"), {"n": names})
    conn.execute(
        sa.text("SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)")
    )

    op.execute("DROP TRIGGER IF EXISTS result_acceptances_update_modified_at ON result_acceptances")
    op.execute("DROP POLICY IF EXISTS result_acceptances_access ON result_acceptances")
    op.drop_index("uq_result_acceptances_live", table_name="result_acceptances")
    op.drop_table("result_acceptances")

    op.drop_constraint("ck_lims_runs_replaces_not_self", "lims_runs", type_="check")
    op.drop_index("ix_lims_runs_replaces_run_id", table_name="lims_runs")
    op.drop_column("lims_runs", "replaces_run_id")
    op.drop_column("lims_runs", "rejected_at")
    op.drop_column("lims_runs", "status_reason")

    op.drop_column("lims_run_data", "link_note")
    op.drop_column("lims_run_data", "sample_key")

    op.drop_constraint("ck_samples_thaw_count_nonneg", "samples", type_="check")
    op.drop_constraint("ck_samples_volume_ul_nonneg", "samples", type_="check")
    op.drop_column("samples", "thaw_count")
    op.drop_column("samples", "receipt_condition")
    op.drop_column("samples", "volume_ul")
