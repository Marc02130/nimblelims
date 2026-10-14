"""Reagent tracking: vendors, reagents, reagent_vendors, reagent_lots, reagent_uses.

Revision ID: 0090_reagent_tracking
Revises: 0089_register_schema_catalog

Step 2 (Marc): an out-of-the-box reagent catalog and a per-run record of which
lot was used, so lot and expiry are recorded on the run instead of as columns.

* reagents are vendor-agnostic; reagent_vendors holds each vendor's catalog
  number, unit, unit of sale, reorder point / quantity, lead time and price
  (Marc: a reagent can come from several vendors). A lot names its reagent and,
  optionally, the reagent_vendor it was bought from.
* vendors, reagents, reagent_vendors, reagent_lots: lab-wide catalog (like instruments). Read by
  lab roles and config editors; written through the API with config:edit.
* reagent_uses: a lot used on a LIMS run or an experiment. Lot number and
  expiry are copied at record time. Tenant-scoped like LIMS runs (created_by's
  client).
* Lots carry ``released`` (default true), a lab-set gate separate from
  ``active`` and ``qc_status``: use needs released, active, not expired, not
  QC-rejected.
* No delete: rows carry ``active``; a lot's quantity remaining can go to 0.
* The five tables are configurable (Schema display rule, kind core) and are
  registered in the Schema catalog here for every existing client, with the
  same deterministic ids and default privileges as 0089.
"""

import importlib.util
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0090_reagent_tracking"
down_revision = "0089_register_schema_catalog"
branch_labels = None
depends_on = None

TABLES = (
    ("vendors", "core", "Vendors"),
    ("reagents", "core", "Reagents"),
    ("reagent_vendors", "core", "Reagent vendors"),
    ("reagent_lots", "core", "Reagent lots"),
    ("reagent_uses", "core", "Reagent uses"),
)

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
    spec = importlib.util.spec_from_file_location("_m0089_for_0090", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_cols():
    return [
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("modified_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("modified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
    ]


def _secure(table: str, policy: str) -> None:
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO lims_app")
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {table}_access ON {table} FOR ALL USING ({policy}) WITH CHECK ({policy})")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE TRIGGER {table}_update_modified_at BEFORE UPDATE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION update_modified_at_column()"
    )


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "vendors",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contact", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        *_audit_cols(),
    )
    op.create_table(
        "reagents",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("storage_condition", sa.String(32), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("hazard_class", sa.String(255), nullable=True),
        sa.Column("sds_url", sa.String(1024), nullable=True),
        sa.Column("stability_after_opening_days", sa.Numeric(), nullable=True),
        *_audit_cols(),
    )
    op.create_table(
        "reagent_vendors",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reagent_id", uuid, sa.ForeignKey("reagents.id"), nullable=False),
        sa.Column("vendor_id", uuid, sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("catalog_number", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("unit_of_sale", sa.String(255), nullable=True),
        sa.Column("quantity_per_unit_of_sale", sa.Numeric(), nullable=True),
        sa.Column("reorder_point", sa.Numeric(), nullable=True),
        sa.Column("reorder_quantity", sa.Numeric(), nullable=True),
        sa.Column("lead_time_days", sa.Numeric(), nullable=True),
        sa.Column("price_per_unit", sa.Numeric(), nullable=True),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_cols(),
        sa.UniqueConstraint("reagent_id", "vendor_id", "catalog_number", name="uq_reagent_vendors"),
    )
    op.create_index("ix_reagent_vendors_reagent_id", "reagent_vendors", ["reagent_id"])
    op.create_index("ix_reagent_vendors_vendor_id", "reagent_vendors", ["vendor_id"])
    op.create_table(
        "reagent_lots",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reagent_id", uuid, sa.ForeignKey("reagents.id"), nullable=False),
        sa.Column("reagent_vendor_id", uuid, sa.ForeignKey("reagent_vendors.id"), nullable=True),
        sa.Column("lot_number", sa.String(255), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("purchased_date", sa.Date(), nullable=True),
        sa.Column("quantity_received", sa.Numeric(), nullable=True),
        sa.Column("quantity_remaining", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("received_by", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("opened_date", sa.Date(), nullable=True),
        sa.Column("storage_location", sa.String(255), nullable=True),
        sa.Column("qc_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("released", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("coa_url", sa.String(1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *_audit_cols(),
        sa.UniqueConstraint("reagent_id", "lot_number", name="uq_reagent_lots_reagent_lot"),
        sa.CheckConstraint("quantity_remaining IS NULL OR quantity_remaining >= 0", name="ck_reagent_lots_remaining"),
        sa.CheckConstraint("qc_status IN ('pending', 'released', 'rejected')", name="ck_reagent_lots_qc_status"),
    )
    op.create_index("ix_reagent_lots_reagent_id", "reagent_lots", ["reagent_id"])
    op.create_index("ix_reagent_lots_reagent_vendor_id", "reagent_lots", ["reagent_vendor_id"])
    op.create_table(
        "reagent_uses",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reagent_lot_id", uuid, sa.ForeignKey("reagent_lots.id"), nullable=False),
        sa.Column("lims_run_id", uuid, sa.ForeignKey("lims_runs.id"), nullable=True),
        sa.Column("experiment_id", uuid, sa.ForeignKey("experiments.id"), nullable=True),
        sa.Column("analysis_id", uuid, sa.ForeignKey("analyses.id"), nullable=True),
        sa.Column("lot_number", sa.String(255), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("used_on", sa.Date(), nullable=False),
        sa.Column("quantity_used", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_audit_cols(),
        sa.CheckConstraint("num_nonnulls(lims_run_id, experiment_id) >= 1", name="ck_reagent_uses_target"),
        sa.CheckConstraint("quantity_used >= 0", name="ck_reagent_uses_quantity"),
    )
    for col in ("reagent_lot_id", "lims_run_id", "experiment_id"):
        op.create_index(f"ix_reagent_uses_{col}", "reagent_uses", [col])

    for table in ("vendors", "reagents", "reagent_vendors", "reagent_lots"):
        _secure(table, _CATALOG_POLICY)
    _secure("reagent_uses", _USE_POLICY)

    _register(op.get_bind())


def _register(conn) -> None:
    """Same rows 0089 writes, for the five new tables, for every client."""
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
    m.TABLES = TABLES
    m.downgrade()
    # Anything still pointing at these tables (a layout field, a relation) blocks
    # the table row's removal above; remove the registry rows outright here,
    # since the tables themselves are dropped.
    m._bind_admin(conn)
    names = [t[0] for t in TABLES]
    conn.execute(sa.text(
        "DELETE FROM schema_layout_fields WHERE column_id IN (SELECT c.id FROM schema_columns c "
        "JOIN schema_tables t ON t.id = c.table_id WHERE t.physical_name = ANY(:n))"), {"n": names})
    conn.execute(sa.text(
        "DELETE FROM schema_relations WHERE from_table_id IN (SELECT id FROM schema_tables WHERE physical_name = ANY(:n)) "
        "OR to_table_id IN (SELECT id FROM schema_tables WHERE physical_name = ANY(:n))"), {"n": names})
    conn.execute(sa.text(
        "DELETE FROM schema_privileges WHERE table_id IN (SELECT id FROM schema_tables WHERE physical_name = ANY(:n)) "
        "OR column_id IN (SELECT c.id FROM schema_columns c JOIN schema_tables t ON t.id = c.table_id "
        "WHERE t.physical_name = ANY(:n))"), {"n": names})
    conn.execute(sa.text(
        "DELETE FROM schema_columns WHERE table_id IN (SELECT id FROM schema_tables WHERE physical_name = ANY(:n))"),
        {"n": names})
    conn.execute(sa.text("DELETE FROM schema_tables WHERE physical_name = ANY(:n)"), {"n": names})
    conn.execute(sa.text("SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"))
    for table in ("reagent_uses", "reagent_lots", "reagent_vendors", "reagents", "vendors"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_update_modified_at ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_access ON {table}")
        op.drop_table(table)
