"""Calculation configuration on analysis_analytes and analysis versions (calculations S7).

Revision ID: 0124_calculation_configuration
Revises: 0123_result_entry_data_model

CALC-REQ-40, 23, 48, 22, 28, 50, 46. OQ-CALC-31, 35, 46, 48.

* ``analyses.version`` (OQ-CALC-31): an integer on the analysis itself, 1 at
  creation. Any committed change to the analysis, to one of its
  ``analysis_analytes`` rows, or to a calculation configuration increments it
  by one, once per transaction. The increment is made by a deferred trigger,
  not by the application: the application role cannot write ``version``.
* ``analysis_versions``: one row per analysis version, written by the same
  trigger from the state the transaction commits. It is how a past version
  stays readable, and it is the only place a version's configuration is kept
  (the calculation attempt stores the analysis version and no formula text).
  Append-only for ``lims_app``.
* ``analysis_analytes`` gains the configuration (OQ-CALC-48): a name, an
  integer configuration version, the configuration body as JSON (stages,
  bindings, on-fail declarations), a state (``draft`` or ``active``), and the
  calculation order (OQ-CALC-35). They are all null, or all set. The order is
  a positive integer, unique inside the analysis, and distinct from
  ``display_order``. Which row reads which row is checked on save; an order
  that is missing cannot exist on a configured row.
* ``calculation_formulas``: saved formulas, pinned by name and version. A row
  is never updated or deleted by ``lims_app``; a changed formula is a new
  version. Lab admins write them; the route checks the Admin role.
* An active configuration is immutable (CALC-REQ-40). A trigger refuses an
  update to the configuration columns of an active row, and a delete of it,
  unless the transaction set ``lims.calculation_new_version = 'on'`` (the new
  analysis version route). That flag also allows the one allowed change: the
  active row goes back to ``draft`` with its content unchanged. Moving a row to
  ``active`` needs ``lims.calculation_activate = 'on'``. No route sets that
  flag in this revision: activation is slice S8.

The guards use ``skip_app_row_guard()`` (0117): the application role is held
to them, the migration and superuser maintenance roles are not.

No row is seeded. There is no ELISA or LAL configuration here (OQ-CALC-24).

Downgrade drops the triggers, tables, and columns. Configurations and saved
formulas are lost; analysis versions fall back to nothing.
"""

from __future__ import annotations

import importlib.util
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0124_calculation_configuration"
down_revision = "0123_result_entry_data_model"
branch_labels = None
depends_on = None

APP_ROLE = "lims_app"

_CATALOG_ADDED = (
    ("analyses", "version"),
    ("analysis_analytes", "calculation_order"),
    ("analysis_analytes", "calculation_config_name"),
    ("analysis_analytes", "calculation_config_version"),
    ("analysis_analytes", "calculation_config"),
    ("analysis_analytes", "calculation_config_state"),
)

_FLAG_FNS = """
CREATE OR REPLACE FUNCTION public.calculation_new_version_allowed()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(current_setting('lims.calculation_new_version', true), '') = 'on'
$$;

CREATE OR REPLACE FUNCTION public.calculation_activate_allowed()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(current_setting('lims.calculation_activate', true), '') = 'on'
$$;

CREATE OR REPLACE FUNCTION public.analysis_version_bump_allowed()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(current_setting('lims.analysis_version_bump', true), '') = 'on'
$$;
"""

_ANALYSIS_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_analysis_version()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.version IS DISTINCT FROM 1 THEN
            RAISE EXCEPTION 'analysis_version_locked'
                USING ERRCODE = '42501',
                      DETAIL = 'A new analysis starts at version 1. The version is incremented by the database.';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.version IS DISTINCT FROM OLD.version
       AND NOT public.analysis_version_bump_allowed() THEN
        RAISE EXCEPTION 'analysis_version_locked'
            USING ERRCODE = '42501',
                  DETAIL = 'The analysis version is incremented by the database, not written.';
    END IF;
    RETURN NEW;
END;
$$;
"""

_CONFIG_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_analysis_analyte_calculation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    same_content boolean;
BEGIN
    IF public.skip_app_row_guard() THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'INSERT' THEN
        IF NEW.calculation_config_state = 'active'
           AND NOT public.calculation_activate_allowed() THEN
            RAISE EXCEPTION 'calculation_activation_required'
                USING ERRCODE = '42501',
                      DETAIL = 'A configuration becomes active only through activation, not by a write.';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        IF OLD.calculation_config_state = 'active'
           AND NOT public.calculation_new_version_allowed() THEN
            RAISE EXCEPTION 'calculation_config_active'
                USING ERRCODE = '42501',
                      DETAIL = 'An active configuration is not deleted. Make a new version of the analysis.';
        END IF;
        RETURN OLD;
    END IF;

    IF NEW.calculation_config_state = 'active'
       AND OLD.calculation_config_state IS DISTINCT FROM 'active'
       AND NOT public.calculation_activate_allowed() THEN
        RAISE EXCEPTION 'calculation_activation_required'
            USING ERRCODE = '42501',
                  DETAIL = 'A configuration becomes active only through activation, not by a write.';
    END IF;

    IF OLD.calculation_config_state = 'active' THEN
        same_content :=
            NEW.calculation_config_name IS NOT DISTINCT FROM OLD.calculation_config_name
            AND NEW.calculation_config_version IS NOT DISTINCT FROM OLD.calculation_config_version
            AND NEW.calculation_config IS NOT DISTINCT FROM OLD.calculation_config
            AND NEW.calculation_order IS NOT DISTINCT FROM OLD.calculation_order;
        IF NEW.calculation_config_state IS NOT DISTINCT FROM OLD.calculation_config_state
           AND same_content THEN
            RETURN NEW;
        END IF;
        IF public.calculation_new_version_allowed()
           AND NEW.calculation_config_state = 'draft'
           AND same_content THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'calculation_config_active'
            USING ERRCODE = '42501',
                  DETAIL = 'An active configuration is immutable. Make a new version of the analysis.';
    END IF;
    RETURN NEW;
END;
$$;
"""

_RECORD_VERSION_FN = """
CREATE OR REPLACE FUNCTION public.record_analysis_version()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    aid uuid;
    marker text;
    new_version integer;
    snap jsonb;
BEGIN
    IF TG_TABLE_NAME = 'analyses' THEN
        aid := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        aid := OLD.analysis_id;
    ELSE
        aid := NEW.analysis_id;
    END IF;

    marker := 'lims.av_' || replace(aid::text, '-', '_');
    IF coalesce(current_setting(marker, true), '') <> '' THEN
        RETURN NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.analyses a WHERE a.id = aid) THEN
        RETURN NULL;
    END IF;
    PERFORM set_config(marker, '1', true);

    IF TG_TABLE_NAME = 'analyses' AND TG_OP = 'INSERT' THEN
        SELECT a.version INTO new_version FROM public.analyses a WHERE a.id = aid;
    ELSE
        PERFORM set_config('lims.analysis_version_bump', 'on', true);
        UPDATE public.analyses SET version = version + 1
         WHERE id = aid
        RETURNING version INTO new_version;
        PERFORM set_config('lims.analysis_version_bump', 'off', true);
    END IF;

    SELECT jsonb_build_object(
               'analysis', to_jsonb(a),
               'analytes', coalesce(
                   (SELECT jsonb_agg(to_jsonb(aa) ORDER BY aa.analyte_id)
                      FROM public.analysis_analytes aa
                     WHERE aa.analysis_id = aid),
                   '[]'::jsonb)
           )
      INTO snap
      FROM public.analyses a
     WHERE a.id = aid;

    INSERT INTO public.analysis_versions (analysis_id, version, snapshot, created_by)
    VALUES (
        aid,
        new_version,
        snap,
        (SELECT u.id FROM public.users u WHERE u.id = public.current_user_id())
    );
    RETURN NULL;
END;
$$;
"""


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0124", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _m0123():
    path = os.path.join(os.path.dirname(__file__), "0123_result_entry_data_model.py")
    spec = importlib.util.spec_from_file_location("_m0123_for_0124", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _function_grants(signature: str) -> None:
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.{signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {APP_ROLE}")


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint("ck_analyses_version", "analyses", "version >= 1")

    op.add_column("analysis_analytes", sa.Column("calculation_order", sa.Integer(), nullable=True))
    op.add_column(
        "analysis_analytes",
        sa.Column("calculation_config_name", sa.String(100), nullable=True),
    )
    op.add_column(
        "analysis_analytes",
        sa.Column("calculation_config_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "analysis_analytes",
        sa.Column("calculation_config", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "analysis_analytes",
        sa.Column("calculation_config_state", sa.String(10), nullable=True),
    )
    op.create_check_constraint(
        "ck_analysis_analytes_calc_config_complete",
        "analysis_analytes",
        "(calculation_config IS NULL AND calculation_config_name IS NULL "
        "AND calculation_config_version IS NULL AND calculation_config_state IS NULL "
        "AND calculation_order IS NULL) "
        "OR (calculation_config IS NOT NULL AND calculation_config_name IS NOT NULL "
        "AND calculation_config_version IS NOT NULL AND calculation_config_state IS NOT NULL "
        "AND calculation_order IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_analysis_analytes_calc_config_values",
        "analysis_analytes",
        "(calculation_order IS NULL OR calculation_order >= 1) "
        "AND (calculation_config_version IS NULL OR calculation_config_version >= 1) "
        "AND (calculation_config_state IS NULL "
        "OR calculation_config_state IN ('draft', 'active')) "
        "AND (calculation_config IS NULL OR jsonb_typeof(calculation_config) = 'object') "
        "AND (calculation_config_name IS NULL OR btrim(calculation_config_name) <> '')",
    )
    op.create_index(
        "uq_analysis_analytes_calculation_order",
        "analysis_analytes",
        ["analysis_id", "calculation_order"],
        unique=True,
        postgresql_where=sa.text("calculation_order IS NOT NULL"),
    )
    op.create_index(
        "uq_analysis_analytes_calculation_config_name",
        "analysis_analytes",
        ["analysis_id", sa.text("lower(calculation_config_name)")],
        unique=True,
        postgresql_where=sa.text("calculation_config_name IS NOT NULL"),
    )

    op.create_table(
        "analysis_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.UniqueConstraint("analysis_id", "version", name="uq_analysis_versions_analysis_version"),
        sa.CheckConstraint("version >= 1", name="ck_analysis_versions_version"),
    )

    op.create_table(
        "calculation_formulas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("formula_text", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint("version >= 1", name="ck_calculation_formulas_version"),
        sa.CheckConstraint(
            "btrim(name) <> '' AND btrim(formula_text) <> '' AND char_length(formula_text) <= 2000",
            name="ck_calculation_formulas_text",
        ),
    )
    op.create_index(
        "uq_calculation_formulas_name_version",
        "calculation_formulas",
        [sa.text("lower(name)"), "version"],
        unique=True,
    )

    op.execute(_FLAG_FNS)
    for signature in (
        "calculation_new_version_allowed()",
        "calculation_activate_allowed()",
        "analysis_version_bump_allowed()",
    ):
        _function_grants(signature)

    op.execute(_ANALYSIS_GUARD_FN)
    _function_grants("guard_analysis_version()")
    op.execute(
        "CREATE TRIGGER analyses_guard_version BEFORE INSERT OR UPDATE ON analyses "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_analysis_version()"
    )

    op.execute(_CONFIG_GUARD_FN)
    _function_grants("guard_analysis_analyte_calculation()")
    op.execute(
        "CREATE TRIGGER analysis_analytes_guard_calculation "
        "BEFORE INSERT OR UPDATE OR DELETE ON analysis_analytes "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_analysis_analyte_calculation()"
    )

    op.execute(_RECORD_VERSION_FN)
    _function_grants("record_analysis_version()")
    op.execute(
        "CREATE CONSTRAINT TRIGGER analyses_record_version "
        "AFTER INSERT OR UPDATE ON analyses "
        "DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.record_analysis_version()"
    )
    op.execute(
        "CREATE CONSTRAINT TRIGGER analysis_analytes_record_version "
        "AFTER INSERT OR UPDATE OR DELETE ON analysis_analytes "
        "DEFERRABLE INITIALLY DEFERRED "
        "FOR EACH ROW EXECUTE FUNCTION public.record_analysis_version()"
    )

    # Every analysis that exists now is version 1, with its current state as
    # that version's snapshot.
    op.execute(
        """
        INSERT INTO analysis_versions (analysis_id, version, snapshot)
        SELECT a.id, a.version,
               jsonb_build_object(
                   'analysis', to_jsonb(a),
                   'analytes', coalesce(
                       (SELECT jsonb_agg(to_jsonb(aa) ORDER BY aa.analyte_id)
                          FROM analysis_analytes aa WHERE aa.analysis_id = a.id),
                       '[]'::jsonb)
               )
          FROM analyses a
        """
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON calculation_formulas TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON analysis_versions TO {APP_ROLE}")
    op.execute("REVOKE UPDATE, DELETE ON calculation_formulas FROM lims_app")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON analysis_versions FROM lims_app")

    conn = op.get_bind()
    _m0123()._catalog_add(conn, _CATALOG_ADDED)


def downgrade() -> None:
    conn = op.get_bind()
    _m0123()._catalog_remove(conn, _CATALOG_ADDED)

    op.execute("DROP TRIGGER IF EXISTS analysis_analytes_record_version ON analysis_analytes")
    op.execute("DROP TRIGGER IF EXISTS analyses_record_version ON analyses")
    op.execute("DROP FUNCTION IF EXISTS public.record_analysis_version()")
    op.execute("DROP TRIGGER IF EXISTS analysis_analytes_guard_calculation ON analysis_analytes")
    op.execute("DROP FUNCTION IF EXISTS public.guard_analysis_analyte_calculation()")
    op.execute("DROP TRIGGER IF EXISTS analyses_guard_version ON analyses")
    op.execute("DROP FUNCTION IF EXISTS public.guard_analysis_version()")
    op.execute("DROP FUNCTION IF EXISTS public.analysis_version_bump_allowed()")
    op.execute("DROP FUNCTION IF EXISTS public.calculation_activate_allowed()")
    op.execute("DROP FUNCTION IF EXISTS public.calculation_new_version_allowed()")

    op.drop_index("uq_calculation_formulas_name_version", table_name="calculation_formulas")
    op.drop_table("calculation_formulas")
    op.drop_table("analysis_versions")

    op.drop_index("uq_analysis_analytes_calculation_config_name", table_name="analysis_analytes")
    op.drop_index("uq_analysis_analytes_calculation_order", table_name="analysis_analytes")
    op.drop_constraint(
        "ck_analysis_analytes_calc_config_values", "analysis_analytes", type_="check"
    )
    op.drop_constraint(
        "ck_analysis_analytes_calc_config_complete", "analysis_analytes", type_="check"
    )
    for column in (
        "calculation_config_state",
        "calculation_config",
        "calculation_config_version",
        "calculation_config_name",
        "calculation_order",
    ):
        op.drop_column("analysis_analytes", column)

    op.drop_constraint("ck_analyses_version", "analyses", type_="check")
    op.drop_column("analyses", "version")
