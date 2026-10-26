"""E2 instrument type slots, run snapshot, substitution audit.

Revision ID: 0115_instrument_type_slots
Revises: 0114_instrument_hardening

Revision id stays at or under 32 characters because
``alembic_version.version_num`` is varchar(32).

Nothing is dropped. No DELETE grants. Lab rows are never deleted.
Untyped LIMS run templates are set inactive (status flag only).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0115_instrument_type_slots"
down_revision = "0114_instrument_hardening"
branch_labels = None
depends_on = None

_CATALOG_POLICY = "is_admin() OR has_experiment_access() OR has_config_edit()"
_CREATED_BY = "created_by IS NOT NULL AND created_by = current_user_id()"
_AUDIT_INSERT = f"{_CREATED_BY} AND (is_admin() OR has_config_edit())"
_CATALOG_INSERT = f"{_CREATED_BY} AND ({_CATALOG_POLICY})"


def upgrade() -> None:
    uuid_t = postgresql.UUID(as_uuid=True)

    op.add_column(
        "instrument_uses",
        sa.Column("entry_id", uuid_t, sa.ForeignKey("entries.id"), nullable=True),
    )
    op.add_column(
        "instrument_uses",
        sa.Column("slot_key", sa.String(64), nullable=True),
    )
    op.create_index(
        "uq_instrument_uses_entry_slot_active",
        "instrument_uses",
        ["entry_id", "slot_key"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE"),
    )
    op.create_index(
        "ix_instrument_uses_entry_id",
        "instrument_uses",
        ["entry_id"],
    )

    op.add_column(
        "lims_runs",
        sa.Column(
            "instrument_type_id",
            uuid_t,
            sa.ForeignKey("list_entries.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_lims_runs_instrument_type_id",
        "lims_runs",
        ["instrument_type_id"],
    )

    op.add_column(
        "lims_run_imports",
        sa.Column("note", sa.Text(), nullable=True),
    )

    op.add_column(
        "instrument_schedule_audits",
        sa.Column("reason", sa.Text(), nullable=True),
    )

    op.create_table(
        "lims_run_type_substitutions",
        sa.Column(
            "id",
            uuid_t,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "lims_run_id",
            uuid_t,
            sa.ForeignKey("lims_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "from_instrument_type_id",
            uuid_t,
            sa.ForeignKey("list_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "to_instrument_type_id",
            uuid_t,
            sa.ForeignKey("list_entries.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
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
            nullable=False,
        ),
    )
    op.create_index(
        "ix_lims_run_type_substitutions_run_id",
        "lims_run_type_substitutions",
        ["lims_run_id"],
    )
    # 0103 default privileges also grant UPDATE/DELETE. Nothing is deleted.
    op.execute("GRANT SELECT, INSERT ON lims_run_type_substitutions TO lims_app")
    op.execute("REVOKE UPDATE ON lims_run_type_substitutions FROM lims_app")
    op.execute("REVOKE DELETE ON lims_run_type_substitutions FROM lims_app")
    op.execute("ALTER TABLE lims_run_type_substitutions ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY lims_run_type_substitutions_select "
        "ON lims_run_type_substitutions FOR SELECT "
        f"USING ({_CATALOG_POLICY})"
    )
    op.execute(
        "CREATE POLICY lims_run_type_substitutions_insert "
        "ON lims_run_type_substitutions FOR INSERT "
        f"WITH CHECK ({_CATALOG_INSERT})"
    )
    op.execute("ALTER TABLE lims_run_type_substitutions FORCE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS instrument_maintenance_audits_insert ON instrument_maintenance_audits")
    op.execute(
        "CREATE POLICY instrument_maintenance_audits_insert "
        "ON instrument_maintenance_audits FOR INSERT "
        f"WITH CHECK ({_AUDIT_INSERT})"
    )
    op.execute("DROP POLICY IF EXISTS instrument_schedule_audits_insert ON instrument_schedule_audits")
    op.execute(
        "CREATE POLICY instrument_schedule_audits_insert "
        "ON instrument_schedule_audits FOR INSERT "
        f"WITH CHECK ({_CATALOG_INSERT})"
    )

    # LIMS run templates = referenced by lims_runs OR carrying a run_import slot.
    # Untyped ones (no slot with run_import true AND a non-null instrument_type_id)
    # are set inactive. Rows are never deleted. Runs that reference them keep
    # their FK.
    op.execute(
        """
        UPDATE experiment_templates t
           SET active = false,
               modified_at = NOW()
         WHERE t.active IS TRUE
           AND (
                EXISTS (
                    SELECT 1 FROM lims_runs r
                     WHERE r.experiment_template_id = t.id
                )
                OR EXISTS (
                    SELECT 1
                      FROM jsonb_array_elements(
                               COALESCE(t.template_definition->'entries', '[]'::jsonb)
                           ) e
                      CROSS JOIN LATERAL jsonb_array_elements(
                               COALESCE(e->'config'->'slots', '[]'::jsonb)
                           ) s
                     WHERE (e->>'entry_type' = 'instrument'
                            OR e->>'predefined_entry_key' = 'instruments')
                       AND COALESCE((s->>'run_import')::boolean, false) IS TRUE
                )
           )
           AND NOT EXISTS (
                SELECT 1
                  FROM jsonb_array_elements(
                           COALESCE(t.template_definition->'entries', '[]'::jsonb)
                       ) e
                  CROSS JOIN LATERAL jsonb_array_elements(
                           COALESCE(e->'config'->'slots', '[]'::jsonb)
                       ) s
                 WHERE (e->>'entry_type' = 'instrument'
                        OR e->>'predefined_entry_key' = 'instruments')
                   AND COALESCE((s->>'run_import')::boolean, false) IS TRUE
                   AND NULLIF(btrim(s->>'instrument_type_id'), '') IS NOT NULL
           )
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    leftover = conn.exec_driver_sql(
        "SELECT count(*) FROM lims_run_type_substitutions"
    ).scalar()
    if leftover:
        raise RuntimeError(
            "0115 downgrade refuses: lims_run_type_substitutions has rows"
        )
    op.execute(
        "DROP POLICY IF EXISTS lims_run_type_substitutions_select "
        "ON lims_run_type_substitutions"
    )
    op.execute(
        "DROP POLICY IF EXISTS lims_run_type_substitutions_insert "
        "ON lims_run_type_substitutions"
    )
    op.drop_index(
        "ix_lims_run_type_substitutions_run_id",
        table_name="lims_run_type_substitutions",
    )
    op.drop_table("lims_run_type_substitutions")

    op.execute("DROP POLICY IF EXISTS instrument_maintenance_audits_insert ON instrument_maintenance_audits")
    op.execute(
        "CREATE POLICY instrument_maintenance_audits_insert "
        "ON instrument_maintenance_audits FOR INSERT "
        "WITH CHECK (is_admin() OR has_config_edit())"
    )
    op.execute("DROP POLICY IF EXISTS instrument_schedule_audits_insert ON instrument_schedule_audits")
    op.execute(
        "CREATE POLICY instrument_schedule_audits_insert "
        "ON instrument_schedule_audits FOR INSERT "
        "WITH CHECK (is_admin() OR has_experiment_access() OR has_config_edit())"
    )

    op.drop_column("instrument_schedule_audits", "reason")
    op.drop_column("lims_run_imports", "note")
    op.drop_index("ix_lims_runs_instrument_type_id", table_name="lims_runs")
    op.drop_column("lims_runs", "instrument_type_id")
    op.drop_index("ix_instrument_uses_entry_id", table_name="instrument_uses")
    op.drop_index("uq_instrument_uses_entry_slot_active", table_name="instrument_uses")
    op.drop_column("instrument_uses", "slot_key")
    op.drop_column("instrument_uses", "entry_id")
    # Templates inactivated in upgrade stay inactive. Re-activating them would
    # also flip rows a lab later retired for another reason.
