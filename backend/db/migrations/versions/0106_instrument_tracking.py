"""Instrument tracking: list types, maintenance, downtime, uses.

Revision ID: 0106_instrument_tracking
Revises: 0105_lab_timezone_required

Marc (2026-10-22): replace instrument_types with the instrument_types list,
move vendor/model onto instruments, retire (never drop) the old table, add
maintenance / downtime / instrument_uses, and upgrade catalog RLS to the 0090
pattern. Data on existing type rows is copied onto list entries, vendors, and
instruments. Downgrade remaps instruments back onto the restored table.
"""

from __future__ import annotations

import importlib.util
import os
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0106_instrument_tracking"
down_revision = "0105_lab_timezone_required"
branch_labels = None
depends_on = None

INSTRUMENT_TYPES_LIST_ID = "a1000001-0001-4001-8001-000000000001"
MAINTENANCE_TYPES_LIST_ID = "a1000001-0001-4001-8001-000000000002"
DOWNTIME_REASONS_LIST_ID = "a1000001-0001-4001-8001-000000000003"

SEED_INSTRUMENT_TYPES = (
    ("a1000001-0002-4001-8001-000000000001", "Plate reader", "plate_reader"),
    ("a1000001-0002-4001-8001-000000000002", "qPCR", "qpcr"),
    ("a1000001-0002-4001-8001-000000000003", "LC-MS", "lc_ms"),
    ("a1000001-0002-4001-8001-000000000004", "Liquid handler", "liquid_handler"),
    ("a1000001-0002-4001-8001-000000000005", "Balance", "balance"),
    ("a1000001-0002-4001-8001-000000000006", "Centrifuge", "centrifuge"),
)

SEED_MAINTENANCE_TYPES = (
    ("a1000001-0003-4001-8001-000000000001", "PM", "pm"),
    ("a1000001-0003-4001-8001-000000000002", "calibration", "calibration"),
    ("a1000001-0003-4001-8001-000000000003", "qualification", "qualification"),
)

# Sensible lab-ops defaults. Calibration/qualification overlap maintenance kinds
# on purpose: a downtime can be for that work.
SEED_DOWNTIME_REASONS = (
    ("a1000001-0004-4001-8001-000000000001", "Breakdown", "breakdown"),
    ("a1000001-0004-4001-8001-000000000002", "Preventive maintenance", "preventive_maintenance"),
    ("a1000001-0004-4001-8001-000000000003", "Calibration", "calibration_downtime"),
    ("a1000001-0004-4001-8001-000000000004", "Qualification", "qualification_downtime"),
    ("a1000001-0004-4001-8001-000000000005", "Facility", "facility"),
    ("a1000001-0004-4001-8001-000000000006", "Other", "other"),
)

TABLES = (
    ("instrument_maintenance_schedules", "core", "Instrument maintenance schedules"),
    ("instrument_maintenance_events", "core", "Instrument maintenance events"),
    ("instrument_downtime", "core", "Instrument downtime"),
    ("instrument_uses", "core", "Instrument uses"),
)
REMOVED = ("instrument_types",)

_CONFIG_EDIT = """EXISTS (
    SELECT 1 FROM users u
    JOIN role_permissions rp ON rp.role_id = u.role_id
    JOIN permissions p ON p.id = rp.permission_id
    WHERE u.id = current_user_id() AND p.name = 'config:edit' AND p.active = true
)"""
_CATALOG_POLICY = f"is_admin() OR has_experiment_access() OR {_CONFIG_EDIT}"
_USE_POLICY = """is_admin() OR (
    has_experiment_access() AND created_by IN (
        SELECT u.id FROM users u
        WHERE u.client_id = (SELECT u2.client_id FROM users u2 WHERE u2.id = current_user_id())
    )
)"""


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0106", path)
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


def _secure(table: str, policy: str) -> None:
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_app")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table}")
    op.execute(
        f"CREATE POLICY {table}_access ON {table} FOR ALL "
        f"USING ({policy}) WITH CHECK ({policy})"
    )
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE TRIGGER {table}_update_modified_at BEFORE UPDATE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION update_modified_at_column()"
    )


def _seed_list(conn, list_id: str, name: str, description: str, entries) -> None:
    conn.execute(
        sa.text(
            """
            INSERT INTO lists (id, name, description, active, created_at, modified_at)
            VALUES (:id, :name, :description, true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"id": list_id, "name": name, "description": description},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO lists (id, name, description, active, created_at, modified_at)
            VALUES (:id, :name, :description, true, NOW(), NOW())
            ON CONFLICT (name) DO NOTHING
            """
        ),
        {"id": list_id, "name": name, "description": description},
    )
    resolved = conn.execute(
        sa.text("SELECT id FROM lists WHERE name = :name LIMIT 1"),
        {"name": name},
    ).scalar()
    if resolved is None:
        raise RuntimeError(f"could not seed list {name}")
    resolved = str(resolved)
    for entry_id, entry_name, _code in entries:
        # list_entries.code is only positive/negative (0097). Slugs stay unused.
        conn.execute(
            sa.text(
                """
                INSERT INTO list_entries (
                    id, name, description, code, active, created_at, modified_at, list_id
                )
                VALUES (
                    :id, :name, :name, NULL, true, NOW(), NOW(), :list_id
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": entry_id,
                "name": entry_name,
                "list_id": resolved,
            },
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO list_entries (
                    id, name, description, code, active, created_at, modified_at, list_id
                )
                VALUES (
                    gen_random_uuid(), :name, :name, NULL, true, NOW(), NOW(), :list_id
                )
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": entry_name, "list_id": resolved},
        )


def _carry_types(conn) -> None:
    """Copy every instrument_types row onto list entries, vendors, instruments."""
    list_id = conn.execute(
        sa.text("SELECT id FROM lists WHERE name = 'instrument_types' LIMIT 1")
    ).scalar()
    types = conn.execute(
        sa.text(
            "SELECT id, name, description, vendor, model, active, created_at, "
            "created_by, modified_at, modified_by FROM instrument_types"
        )
    ).mappings().all()
    seed_by_name = {
        name.lower(): entry_id for entry_id, name, _code in SEED_INSTRUMENT_TYPES
    }
    for row in types:
        key = (row["name"] or "").strip()
        mapped = seed_by_name.get(key.lower())
        if mapped is None:
            existing = conn.execute(
                sa.text(
                    "SELECT id FROM list_entries WHERE list_id = :lid AND lower(name) = lower(:n)"
                ),
                {"lid": str(list_id), "n": key},
            ).scalar()
            if existing is None:
                taken = conn.execute(
                    sa.text("SELECT 1 FROM list_entries WHERE id = :id"),
                    {"id": str(row["id"])},
                ).scalar()
                entry_id = str(row["id"]) if taken is None else str(uuid.uuid4())
                insert_name = key
                name_taken = conn.execute(
                    sa.text("SELECT 1 FROM list_entries WHERE name = :n"),
                    {"n": insert_name},
                ).scalar()
                if name_taken is not None:
                    insert_name = f"{key} (instrument type)"
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO list_entries (
                            id, name, description, code, active,
                            created_at, created_by, modified_at, modified_by, list_id
                        )
                        VALUES (
                            :id, :name, :description, NULL, :active,
                            :created_at, :created_by, :modified_at, :modified_by, :list_id
                        )
                        """
                    ),
                    {
                        "id": entry_id,
                        "name": insert_name,
                        "description": row["description"],
                        "active": bool(row["active"]),
                        "created_at": row["created_at"],
                        "created_by": row["created_by"],
                        "modified_at": row["modified_at"],
                        "modified_by": row["modified_by"],
                        "list_id": str(list_id),
                    },
                )
                mapped = entry_id
            else:
                mapped = str(existing)
        conn.execute(
            sa.text(
                "UPDATE instrument_types SET list_entry_id = :eid WHERE id = :id"
            ),
            {"eid": mapped, "id": str(row["id"])},
        )
        vendor_id = None
        vendor_name = (row["vendor"] or "").strip()
        if vendor_name:
            vendor_id = conn.execute(
                sa.text("SELECT id FROM vendors WHERE lower(name) = lower(:n)"),
                {"n": vendor_name},
            ).scalar()
            if vendor_id is None:
                vendor_id = uuid.uuid4()
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO vendors (id, name, description, active, created_at, modified_at)
                        VALUES (:id, :name, NULL, true, NOW(), NOW())
                        """
                    ),
                    {"id": vendor_id, "name": vendor_name},
                )
        conn.execute(
            sa.text(
                """
                UPDATE instruments
                SET vendor_id = COALESCE(vendor_id, :vendor_id),
                    model = COALESCE(model, :model)
                WHERE instrument_type_id = :old
                """
            ),
            {
                "vendor_id": vendor_id,
                "model": (row["model"] or "").strip() or None,
                "old": str(row["id"]),
            },
        )


def upgrade() -> None:
    conn = op.get_bind()
    uuid_t = postgresql.UUID(as_uuid=True)

    op.add_column(
        "instrument_types",
        sa.Column("list_entry_id", uuid_t, nullable=True),
    )

    op.add_column("instruments", sa.Column("vendor_id", uuid_t, nullable=True))
    op.add_column("instruments", sa.Column("model", sa.String(255), nullable=True))
    op.add_column("instruments", sa.Column("asset_tag", sa.String(255), nullable=True))
    op.add_column("instruments", sa.Column("location_id", uuid_t, nullable=True))
    op.add_column(
        "instruments",
        sa.Column("status", sa.String(32), nullable=False, server_default="in_service"),
    )
    op.create_foreign_key(
        "fk_instruments_vendor_id", "instruments", "vendors", ["vendor_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_instruments_location_id",
        "instruments",
        "locations",
        ["location_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_instruments_status",
        "instruments",
        "status IN ('in_service', 'out_of_service', 'retired')",
    )

    _seed_list(
        conn,
        INSTRUMENT_TYPES_LIST_ID,
        "instrument_types",
        "Kinds of laboratory instruments",
        SEED_INSTRUMENT_TYPES,
    )
    _seed_list(
        conn,
        MAINTENANCE_TYPES_LIST_ID,
        "maintenance_types",
        "Instrument maintenance kinds: PM, calibration, qualification",
        SEED_MAINTENANCE_TYPES,
    )
    _seed_list(
        conn,
        DOWNTIME_REASONS_LIST_ID,
        "downtime_reasons",
        "Why an instrument is down: Breakdown, Preventive maintenance, Calibration, Qualification, Facility, Other",
        SEED_DOWNTIME_REASONS,
    )
    _carry_types(conn)

    op.drop_constraint("instruments_instrument_type_id_fkey", "instruments", type_="foreignkey")
    op.execute("DROP INDEX IF EXISTS uq_instruments_type_serial")
    conn.execute(
        sa.text(
            """
            UPDATE instruments i
            SET instrument_type_id = t.list_entry_id
            FROM instrument_types t
            WHERE i.instrument_type_id = t.id AND t.list_entry_id IS NOT NULL
            """
        )
    )
    op.execute("ALTER TABLE instrument_types RENAME TO instrument_types_legacy")
    op.execute(
        "ALTER INDEX IF EXISTS ix_instrument_types_active "
        "RENAME TO ix_instrument_types_legacy_active"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_instrument_types_vendor "
        "RENAME TO ix_instrument_types_legacy_vendor"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_instrument_types_model "
        "RENAME TO ix_instrument_types_legacy_model"
    )
    op.create_foreign_key(
        "fk_instruments_instrument_type_id",
        "instruments",
        "list_entries",
        ["instrument_type_id"],
        ["id"],
    )
    op.create_index(
        "uq_instruments_vendor_model_serial",
        "instruments",
        ["vendor_id", "model", "serial_number"],
        unique=True,
        postgresql_where=sa.text("serial_number IS NOT NULL"),
    )
    op.alter_column("instruments", "status", server_default=None)

    op.create_table(
        "instrument_maintenance_schedules",
        sa.Column("id", uuid_t, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_id", uuid_t, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("kind_id", uuid_t, sa.ForeignKey("list_entries.id"), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("last_done", sa.Date(), nullable=True),
        sa.Column("next_due", sa.Date(), nullable=True),
        sa.Column("service_vendor_id", uuid_t, sa.ForeignKey("vendors.id"), nullable=True),
        sa.CheckConstraint("interval_days > 0", name="ck_instrument_schedules_interval"),
        *_audit_cols(),
    )
    op.create_index(
        "ix_instrument_maintenance_schedules_instrument_id",
        "instrument_maintenance_schedules",
        ["instrument_id"],
    )
    op.create_table(
        "instrument_maintenance_events",
        sa.Column("id", uuid_t, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "schedule_id",
            uuid_t,
            sa.ForeignKey("instrument_maintenance_schedules.id"),
            nullable=True,
        ),
        sa.Column("instrument_id", uuid_t, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("performed_by_user_id", uuid_t, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("performed_by_vendor_id", uuid_t, sa.ForeignKey("vendors.id"), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("certificate_url", sa.String(1024), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "num_nonnulls(performed_by_user_id, performed_by_vendor_id) >= 1",
            name="ck_instrument_events_performer",
        ),
        *_audit_cols(),
    )
    op.create_index(
        "ix_instrument_maintenance_events_instrument_id",
        "instrument_maintenance_events",
        ["instrument_id"],
    )
    op.create_index(
        "ix_instrument_maintenance_events_schedule_id",
        "instrument_maintenance_events",
        ["schedule_id"],
    )
    op.create_table(
        "instrument_downtime",
        sa.Column("id", uuid_t, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_id", uuid_t, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason_id", uuid_t, sa.ForeignKey("list_entries.id"), nullable=False),
        sa.Column(
            "maintenance_event_id",
            uuid_t,
            sa.ForeignKey("instrument_maintenance_events.id"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_instrument_downtime_window",
        ),
        *_audit_cols(),
    )
    op.create_index(
        "ix_instrument_downtime_instrument_id",
        "instrument_downtime",
        ["instrument_id"],
    )
    op.create_table(
        "instrument_uses",
        sa.Column("id", uuid_t, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("instrument_id", uuid_t, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("lims_run_id", uuid_t, sa.ForeignKey("lims_runs.id"), nullable=True),
        sa.Column("experiment_id", uuid_t, sa.ForeignKey("experiments.id"), nullable=True),
        sa.Column("analysis_id", uuid_t, sa.ForeignKey("analyses.id"), nullable=True),
        sa.Column("used_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "num_nonnulls(lims_run_id, experiment_id) >= 1",
            name="ck_instrument_uses_target",
        ),
        *_audit_cols(),
    )
    for col in ("instrument_id", "lims_run_id", "experiment_id"):
        op.create_index(f"ix_instrument_uses_{col}", "instrument_uses", [col])

    op.add_column("data_parsers", sa.Column("instrument_type_id", uuid_t, nullable=True))
    op.create_foreign_key(
        "fk_data_parsers_instrument_type_id",
        "data_parsers",
        "list_entries",
        ["instrument_type_id"],
        ["id"],
    )
    op.drop_constraint("ck_data_parsers_source_xor", "data_parsers", type_="check")
    op.create_check_constraint(
        "ck_data_parsers_source_xor",
        "data_parsers",
        "(num_nonnulls(instrument_id, cro_source_id, instrument_type_id) = 1)",
    )
    op.create_index(
        "ix_data_parsers_instrument_type_id",
        "data_parsers",
        ["instrument_type_id"],
    )

    for table in (
        "instruments",
        "cro_sources",
        "instrument_maintenance_schedules",
        "instrument_maintenance_events",
        "instrument_downtime",
    ):
        _secure(table, _CATALOG_POLICY)
    _secure("instrument_uses", _USE_POLICY)

    _unregister_instrument_types(conn)
    _register(conn)


def _unregister_instrument_types(conn) -> None:
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_privileges
            WHERE table_id IN (
                SELECT id FROM schema_tables WHERE physical_name = 'instrument_types'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns
            WHERE table_id IN (
                SELECT id FROM schema_tables WHERE physical_name = 'instrument_types'
            )
            """
        )
    )
    conn.execute(
        sa.text("DELETE FROM schema_tables WHERE physical_name = 'instrument_types'")
    )


def _register(conn) -> None:
    m = _m0089()
    original = m.TABLES
    try:
        m.TABLES = TABLES
        m.upgrade()
    finally:
        m.TABLES = original


def downgrade() -> None:
    conn = op.get_bind()
    m = _m0089()
    original = m.TABLES
    try:
        m.TABLES = TABLES
        m.downgrade()
    finally:
        m.TABLES = original

    op.drop_index("ix_data_parsers_instrument_type_id", table_name="data_parsers")
    op.drop_constraint("ck_data_parsers_source_xor", "data_parsers", type_="check")
    op.drop_constraint(
        "fk_data_parsers_instrument_type_id", "data_parsers", type_="foreignkey"
    )
    op.drop_column("data_parsers", "instrument_type_id")
    op.create_check_constraint(
        "ck_data_parsers_source_xor",
        "data_parsers",
        "(instrument_id IS NOT NULL AND cro_source_id IS NULL) OR "
        "(instrument_id IS NULL AND cro_source_id IS NOT NULL)",
    )

    for table in (
        "instrument_uses",
        "instrument_downtime",
        "instrument_maintenance_events",
        "instrument_maintenance_schedules",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table}")
        op.drop_table(table)

    op.execute("DROP INDEX IF EXISTS uq_instruments_vendor_model_serial")
    op.drop_constraint("fk_instruments_instrument_type_id", "instruments", type_="foreignkey")
    op.execute("ALTER TABLE instrument_types_legacy RENAME TO instrument_types")
    op.execute(
        "ALTER INDEX IF EXISTS ix_instrument_types_legacy_active "
        "RENAME TO ix_instrument_types_active"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_instrument_types_legacy_vendor "
        "RENAME TO ix_instrument_types_vendor"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_instrument_types_legacy_model "
        "RENAME TO ix_instrument_types_model"
    )
    conn.execute(
        sa.text(
            """
            UPDATE instruments i
            SET instrument_type_id = t.id
            FROM instrument_types t
            WHERE t.list_entry_id = i.instrument_type_id
            """
        )
    )
    op.create_foreign_key(
        "instruments_instrument_type_id_fkey",
        "instruments",
        "instrument_types",
        ["instrument_type_id"],
        ["id"],
    )
    op.create_index(
        "uq_instruments_type_serial",
        "instruments",
        ["instrument_type_id", "serial_number"],
        unique=True,
        postgresql_where=sa.text("serial_number IS NOT NULL"),
    )
    op.drop_constraint("ck_instruments_status", "instruments", type_="check")
    op.drop_constraint("fk_instruments_location_id", "instruments", type_="foreignkey")
    op.drop_constraint("fk_instruments_vendor_id", "instruments", type_="foreignkey")
    op.drop_column("instruments", "status")
    op.drop_column("instruments", "location_id")
    op.drop_column("instruments", "asset_tag")
    op.drop_column("instruments", "model")
    op.drop_column("instruments", "vendor_id")
    op.drop_column("instrument_types", "list_entry_id")

    _restore_instrument_types_catalog(conn)

    for name in ("downtime_reasons", "maintenance_types", "instrument_types"):
        conn.execute(
            sa.text("DELETE FROM list_entries WHERE list_id IN (SELECT id FROM lists WHERE name = :n)"),
            {"n": name},
        )
        conn.execute(sa.text("DELETE FROM lists WHERE name = :n"), {"n": name})


def _restore_instrument_types_catalog(conn) -> None:
    m = _m0089()
    original = m.TABLES
    try:
        m.TABLES = (("instrument_types", "system", "Instrument types"),)
        m.upgrade()
    finally:
        m.TABLES = original
