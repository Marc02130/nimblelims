"""Run and result-entry data model (calculations S6) and the knock-in audit.

Revision ID: 0123_result_entry_data_model
Revises: 0122_calculation_units_seed

CALC-REQ-49, 54, 55, 28, 53, and 27 (knock-in record).

* ``tests.lims_run_id``: the run a Test belongs to. A result on a Test with no
  run is refused by a trigger. The column itself stays nullable, because the
  Spec does not design when Tests are created (#254) and accessioning still
  creates Tests before any run exists. Once set, it does not change.
* ``results.lims_run_id`` is removed. The run a result came from is
  ``tests.lims_run_id``. Existing rows are moved first: a Test whose results
  all came from one run takes that run. A Test with results from more than one
  run, or with run results beside run-less results, is split: each run gets
  its own copy of the Test and that run's results move onto it. Run-less
  results stay on the original Test. Nothing is deleted.
* ``results`` gains ``display_order``, ``raw_units``, ``final_units_id``, and the
  knockout flag (``knocked_out``, ``knocked_out_by``, ``knocked_out_at``).
* ``entries.experiment_id`` becomes nullable and ``entries.lims_run_id`` is
  added. ``ck_entries_experiment_xor_lims_run``: exactly one of the two, and a
  run id only on ``experiment_data`` / ``experiment_sample_data`` entries.
* ``result_entries``: dedicated result-entry columns on a run's experiment
  sample data entry. One row per Test x analyte x replicate, including the
  average analyte. RLS follows the parent entry, as ``entry_field_values`` does.
* ``analysis_analytes`` gains ``pairing_unit_id`` (defaults from
  ``analytes.units_default`` on insert, existing rows backfilled). No replicate
  count column: CALC-REQ-54 forbids one, and the count is a configuration
  value (CALC-REQ-15, #258).
* Calculated is locked. A write to ``calculated_result`` on ``results`` or on
  ``result_entries`` is refused unless the transaction set
  ``lims.calculation_write = 'on'``. Only server code that writes a
  calculation's outputs sets it; no API route does. A reported write on a
  result entry with no calculated value is refused the same way.
* ``lims_run_data_exclusions``: a clear is recorded (``cleared_by``,
  ``cleared_at``) instead of deleting the row. ``lims_app`` loses DELETE and a
  trigger refuses a delete and any update except that one clear. One active
  exclusion per data point.

The guards use ``skip_app_row_guard()`` (0117): the application role is held
to them, the migration and superuser maintenance roles are not.

Downgrade restores ``results.lims_run_id`` from ``tests.lims_run_id``, drops
the new table and columns, deletes run-scoped entries (they cannot exist
without ``experiment_id``), and deletes cleared exclusions, because the old
schema recorded a clear by deleting the row. Split Tests stay split.
"""

from __future__ import annotations

import importlib.util
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0123_result_entry_data_model"
down_revision = "0122_calculation_units_seed"
branch_labels = None
depends_on = None

APP_ROLE = "lims_app"

RESULT_ENTRY_DATA_TYPES = ("experiment_data", "experiment_sample_data")

_ENTRY_CHILD_POLICY = """\
    is_admin() OR (
        has_experiment_access() AND
        entry_id IN (
            SELECT e.id FROM entries e
            WHERE e.created_by IN (
                SELECT u.id FROM users u
                WHERE u.client_id = (
                    SELECT u2.client_id FROM users u2
                    WHERE u2.id = current_user_id()
                )
            )
        )
    )\
"""

_CALCULATION_WRITE_FN = """
CREATE OR REPLACE FUNCTION public.calculation_write_allowed()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(current_setting('lims.calculation_write', true), '') = 'on'
$$;
"""

_RESULTS_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_result_write()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    run_id uuid;
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    SELECT t.lims_run_id INTO run_id FROM public.tests t WHERE t.id = NEW.test_id;
    -- Retiring a legacy run-less result (active -> false, values unchanged)
    -- stays possible; any other write needs a Test with a run.
    IF run_id IS NULL AND TG_OP = 'UPDATE' AND OLD.active AND NOT NEW.active
       AND NEW.test_id = OLD.test_id
       AND NEW.analyte_id = OLD.analyte_id
       AND NEW.replicate = OLD.replicate
       AND NEW.raw_result IS NOT DISTINCT FROM OLD.raw_result
       AND NEW.reported_result IS NOT DISTINCT FROM OLD.reported_result
       AND NEW.calculated_result IS NOT DISTINCT FROM OLD.calculated_result
       AND NEW.qualifiers IS NOT DISTINCT FROM OLD.qualifiers THEN
        RETURN NEW;
    END IF;
    IF run_id IS NULL THEN
        RAISE EXCEPTION 'result_test_has_no_run'
            USING ERRCODE = '23514',
                  DETAIL = 'A result lives on a Test that has a LIMS run (tests.lims_run_id).';
    END IF;
    IF NOT public.calculation_write_allowed() THEN
        IF TG_OP = 'INSERT' AND NEW.calculated_result IS NOT NULL THEN
            RAISE EXCEPTION 'calculated_locked' USING ERRCODE = '42501';
        END IF;
        IF TG_OP = 'UPDATE'
           AND NEW.calculated_result IS DISTINCT FROM OLD.calculated_result THEN
            RAISE EXCEPTION 'calculated_locked' USING ERRCODE = '42501';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
"""

_TEST_RUN_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_test_run_change()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF OLD.lims_run_id IS NOT NULL
       AND NEW.lims_run_id IS DISTINCT FROM OLD.lims_run_id THEN
        RAISE EXCEPTION 'test_run_immutable'
            USING ERRCODE = '42501',
                  DETAIL = 'A Test belongs to one LIMS run. A new generation is a new Test.';
    END IF;
    RETURN NEW;
END;
$$;
"""

_RESULT_ENTRY_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_result_entry_write()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    entry_run uuid;
    entry_kind text;
    test_run uuid;
BEGIN
    SELECT e.lims_run_id, e.entry_type INTO entry_run, entry_kind
      FROM public.entries e WHERE e.id = NEW.entry_id;
    SELECT t.lims_run_id INTO test_run FROM public.tests t WHERE t.id = NEW.test_id;
    IF entry_run IS NULL
       OR entry_kind <> 'experiment_sample_data'
       OR test_run IS DISTINCT FROM entry_run THEN
        RAISE EXCEPTION 'result_entry_scope'
            USING ERRCODE = '23514',
                  DETAIL = 'A result entry is on its run''s experiment sample data entry, for a Test on that run.';
    END IF;
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF public.calculation_write_allowed() THEN
        IF TG_OP = 'UPDATE' AND NEW.raw_result IS DISTINCT FROM OLD.raw_result THEN
            RAISE EXCEPTION 'calculation_changes_raw' USING ERRCODE = '42501';
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.calculated_result IS NOT NULL THEN
            RAISE EXCEPTION 'calculated_locked' USING ERRCODE = '42501';
        END IF;
        IF NEW.reported_result IS NOT NULL THEN
            RAISE EXCEPTION 'reported_before_calculation' USING ERRCODE = '42501';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.calculated_result IS DISTINCT FROM OLD.calculated_result THEN
        RAISE EXCEPTION 'calculated_locked' USING ERRCODE = '42501';
    END IF;
    IF NEW.reported_result IS DISTINCT FROM OLD.reported_result
       AND NEW.calculated_result IS NULL THEN
        RAISE EXCEPTION 'reported_before_calculation' USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$;
"""

_PAIRING_UNIT_DEFAULT_FN = """
CREATE OR REPLACE FUNCTION public.default_pairing_unit()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NEW.pairing_unit_id IS NULL THEN
        SELECT a.units_default INTO NEW.pairing_unit_id
          FROM public.analytes a WHERE a.id = NEW.analyte_id;
    END IF;
    RETURN NEW;
END;
$$;
"""

_EXCLUSION_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_exclusion_record()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'exclusion_record_kept'
            USING ERRCODE = '42501',
                  DETAIL = 'A knockout is cleared by recording cleared_by and cleared_at, not by deleting it.';
    END IF;
    IF OLD.cleared_at IS NOT NULL
       OR NEW.cleared_at IS NULL
       OR NEW.cleared_by IS NULL
       OR NEW.id IS DISTINCT FROM OLD.id
       OR NEW.lims_run_data_id IS DISTINCT FROM OLD.lims_run_data_id
       OR NEW.excluded_by IS DISTINCT FROM OLD.excluded_by
       OR NEW.excluded_at IS DISTINCT FROM OLD.excluded_at
       OR NEW.reason IS DISTINCT FROM OLD.reason
       OR NEW.client_id IS DISTINCT FROM OLD.client_id THEN
        RAISE EXCEPTION 'exclusion_record_kept'
            USING ERRCODE = '42501',
                  DETAIL = 'The only change to a knockout record is its one clear.';
    END IF;
    RETURN NEW;
END;
$$;
"""

_SPLIT_TESTS_BY_RUN = """
DO $$
DECLARE
    t record;
    r record;
    has_runless boolean;
    kept boolean;
    new_id uuid;
BEGIN
    FOR t IN
        SELECT DISTINCT res.test_id
          FROM results res
         WHERE res.lims_run_id IS NOT NULL
    LOOP
        SELECT EXISTS (
            SELECT 1 FROM results x
             WHERE x.test_id = t.test_id AND x.lims_run_id IS NULL
        ) INTO has_runless;
        kept := has_runless;
        FOR r IN
            SELECT lr.id
              FROM lims_runs lr
             WHERE lr.id IN (
                   SELECT DISTINCT x.lims_run_id FROM results x
                    WHERE x.test_id = t.test_id AND x.lims_run_id IS NOT NULL)
             ORDER BY lr.created_at, lr.id
        LOOP
            IF NOT kept THEN
                UPDATE tests SET lims_run_id = r.id WHERE id = t.test_id;
                kept := true;
            ELSE
                new_id := gen_random_uuid();
                INSERT INTO tests
                SELECT (jsonb_populate_record(
                    NULL::tests,
                    to_jsonb(src) || jsonb_build_object(
                        'id', new_id,
                        'name', left(src.name, 220) || '_run_'
                                || left(replace(new_id::text, '-', ''), 12),
                        'lims_run_id', r.id
                    )
                )).*
                  FROM tests src
                 WHERE src.id = t.test_id;
                UPDATE results SET test_id = new_id
                 WHERE test_id = t.test_id AND lims_run_id = r.id;
            END IF;
        END LOOP;
    END LOOP;
END
$$;
"""


# Columns of Schema-registered tables (0089) that this revision adds or removes.
_CATALOG_ADDED = (
    ("tests", "lims_run_id"),
    ("results", "display_order"),
    ("results", "raw_units"),
    ("results", "final_units_id"),
    ("results", "knocked_out"),
    ("results", "knocked_out_by"),
    ("results", "knocked_out_at"),
)
_CATALOG_REMOVED = (("results", "lims_run_id"),)


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0123", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _release_admin(conn) -> None:
    conn.execute(
        sa.text(
            "SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"
        )
    )


def _catalog_add(conn, pairs) -> None:
    """Catalog new columns for clients that already register the table."""
    m = _m0089()
    admin = m._bind_admin(conn)
    reflected = m._reflect(conn, sorted({table for table, _ in pairs}))
    for table, column in pairs:
        col = {c["name"]: c for c in reflected.get(table, [])}.get(column)
        if col is None:
            continue
        registered = conn.execute(
            sa.text("SELECT client_id, id FROM schema_tables WHERE physical_name = :p"),
            {"p": table},
        ).all()
        for client, table_id in registered:
            have = conn.execute(
                sa.text("SELECT 1 FROM schema_columns WHERE table_id = :t AND physical_name = :n"),
                {"t": table_id, "n": column},
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
                    "id": m._id(client, table, "col", column),
                    "c": client,
                    "t": table_id,
                    "d": m._column_display(column, col["is_fk"]),
                    "p": column,
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
    _release_admin(conn)


def _catalog_remove(conn, pairs) -> None:
    """Drop catalog rows (and their privileges and layout fields) for columns that go."""
    m = _m0089()
    m._bind_admin(conn)
    for table, column in pairs:
        col_ids = [
            row[0]
            for row in conn.execute(
                sa.text(
                    "SELECT c.id FROM schema_columns c JOIN schema_tables t ON t.id = c.table_id "
                    "WHERE t.physical_name = :t AND c.physical_name = :n"
                ),
                {"t": table, "n": column},
            ).all()
        ]
        if not col_ids:
            continue
        for sql in (
            "DELETE FROM schema_layout_fields WHERE column_id = ANY(CAST(:c AS uuid[]))",
            "DELETE FROM schema_privileges WHERE column_id = ANY(CAST(:c AS uuid[]))",
            "DELETE FROM schema_columns WHERE id = ANY(CAST(:c AS uuid[]))",
        ):
            conn.execute(sa.text(sql), {"c": [str(i) for i in col_ids]})
    _release_admin(conn)


def _function_grants(signature: str) -> None:
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.{signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {APP_ROLE}")


def upgrade() -> None:
    op.execute(_CALCULATION_WRITE_FN)
    op.execute(
        f"GRANT EXECUTE ON FUNCTION public.calculation_write_allowed() TO {APP_ROLE}"
    )

    # tests.lims_run_id, backfilled from results.lims_run_id before that column goes.
    op.add_column(
        "tests",
        sa.Column("lims_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tests_lims_run_id",
        "tests",
        "lims_runs",
        ["lims_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_tests_lims_run_id", "tests", ["lims_run_id"])
    op.execute(_SPLIT_TESTS_BY_RUN)

    op.drop_index("ix_results_lims_run_id", table_name="results")
    op.drop_constraint("fk_results_lims_run_id", "results", type_="foreignkey")
    op.drop_column("results", "lims_run_id")

    op.add_column("results", sa.Column("display_order", sa.Integer(), nullable=True))
    op.add_column("results", sa.Column("raw_units", sa.String(64), nullable=True))
    op.add_column(
        "results",
        sa.Column(
            "final_units_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id", name="fk_results_final_units_id"),
            nullable=True,
        ),
    )
    op.add_column(
        "results",
        sa.Column("knocked_out", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "results",
        sa.Column(
            "knocked_out_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_results_knocked_out_by", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "results",
        sa.Column("knocked_out_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_results_knockout_fields",
        "results",
        "knocked_out OR (knocked_out_by IS NULL AND knocked_out_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_results_knockout_time",
        "results",
        "NOT knocked_out OR knocked_out_at IS NOT NULL",
    )

    # entries: experiment id XOR LIMS run id.
    op.alter_column("entries", "experiment_id", nullable=True)
    op.add_column(
        "entries",
        sa.Column("lims_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_entries_lims_run_id",
        "entries",
        "lims_runs",
        ["lims_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_entries_lims_run_id", "entries", ["lims_run_id"])
    kinds = ", ".join(f"'{k}'" for k in RESULT_ENTRY_DATA_TYPES)
    op.create_check_constraint(
        "ck_entries_experiment_xor_lims_run",
        "entries",
        f"num_nonnulls(experiment_id, lims_run_id) = 1 "
        f"AND (lims_run_id IS NULL OR entry_type IN ({kinds}))",
    )

    # analysis_analytes: pairing unit.
    op.add_column(
        "analysis_analytes",
        sa.Column(
            "pairing_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id", name="fk_analysis_analytes_pairing_unit_id"),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE analysis_analytes aa SET pairing_unit_id = a.units_default "
        "FROM analytes a WHERE a.id = aa.analyte_id AND aa.pairing_unit_id IS NULL"
    )
    op.execute(_PAIRING_UNIT_DEFAULT_FN)
    _function_grants("default_pairing_unit()")
    op.execute(
        "CREATE TRIGGER analysis_analytes_default_pairing_unit "
        "BEFORE INSERT ON analysis_analytes "
        "FOR EACH ROW EXECUTE FUNCTION public.default_pairing_unit()"
    )

    # result_entries: dedicated result-entry columns.
    op.create_table(
        "result_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "analyte_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analytes.id"),
            nullable=False,
        ),
        sa.Column("replicate", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("raw_result", sa.String(255), nullable=True),
        sa.Column("raw_units", sa.String(64), nullable=True),
        sa.Column("raw_origin", sa.String(16), nullable=True),
        sa.Column(
            "final_units_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id"),
            nullable=True,
        ),
        sa.Column("calculated_result", sa.String(255), nullable=True),
        sa.Column("reported_result", sa.String(255), nullable=True),
        sa.Column(
            "qualifiers",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("list_entries.id"),
            nullable=True,
        ),
        sa.Column("knocked_out", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "knocked_out_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("knocked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=True),
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
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "modified_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "test_id", "analyte_id", "replicate", name="uq_result_entries_test_analyte_replicate"
        ),
        sa.CheckConstraint("replicate >= 1", name="ck_result_entries_replicate"),
        sa.CheckConstraint(
            "raw_origin IS NULL OR raw_origin IN ('upload', 'typed')",
            name="ck_result_entries_raw_origin",
        ),
        sa.CheckConstraint(
            "raw_result IS NULL OR raw_origin IS NOT NULL",
            name="ck_result_entries_raw_has_origin",
        ),
        sa.CheckConstraint(
            "knocked_out OR (knocked_out_by IS NULL AND knocked_out_at IS NULL)",
            name="ck_result_entries_knockout_fields",
        ),
        sa.CheckConstraint(
            "NOT knocked_out OR knocked_out_at IS NOT NULL",
            name="ck_result_entries_knockout_time",
        ),
    )
    op.create_index("ix_result_entries_entry_id", "result_entries", ["entry_id"])
    op.create_index("ix_result_entries_test_id", "result_entries", ["test_id"])
    op.execute("ALTER TABLE result_entries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE result_entries FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY result_entries_access ON result_entries "
        f"FOR ALL USING ({_ENTRY_CHILD_POLICY})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON result_entries TO {APP_ROLE}")

    op.execute(_RESULTS_GUARD_FN)
    _function_grants("guard_result_write()")
    op.execute(
        "CREATE TRIGGER results_guard_write BEFORE INSERT OR UPDATE ON results "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_result_write()"
    )
    op.execute(_TEST_RUN_GUARD_FN)
    _function_grants("guard_test_run_change()")
    op.execute(
        "CREATE TRIGGER tests_guard_run_change BEFORE UPDATE OF lims_run_id ON tests "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_test_run_change()"
    )
    op.execute(_RESULT_ENTRY_GUARD_FN)
    _function_grants("guard_result_entry_write()")
    op.execute(
        "CREATE TRIGGER result_entries_guard_write "
        "BEFORE INSERT OR UPDATE ON result_entries "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_result_entry_write()"
    )

    # Knock-in: record the clear, keep the knockout.
    op.add_column(
        "lims_run_data_exclusions",
        sa.Column(
            "cleared_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_lims_run_data_exclusions_cleared_by",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "lims_run_data_exclusions",
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_lims_run_data_exclusions_cleared",
        "lims_run_data_exclusions",
        "(cleared_at IS NULL) = (cleared_by IS NULL)",
    )
    op.drop_constraint(
        "uq_experiment_data_exclusions_data_id",
        "lims_run_data_exclusions",
        type_="unique",
    )
    op.create_index(
        "uq_lims_run_data_exclusions_active",
        "lims_run_data_exclusions",
        ["lims_run_data_id"],
        unique=True,
        postgresql_where=sa.text("cleared_at IS NULL"),
    )
    op.execute(_EXCLUSION_GUARD_FN)
    _function_grants("guard_exclusion_record()")
    op.execute(
        "CREATE TRIGGER lims_run_data_exclusions_keep_record "
        "BEFORE UPDATE OR DELETE ON lims_run_data_exclusions "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_exclusion_record()"
    )
    op.execute("REVOKE DELETE ON lims_run_data_exclusions FROM lims_app")

    conn = op.get_bind()
    _catalog_remove(conn, _CATALOG_REMOVED)
    _catalog_add(conn, _CATALOG_ADDED)


def downgrade() -> None:
    conn = op.get_bind()
    _catalog_remove(conn, _CATALOG_ADDED)
    op.execute("GRANT DELETE ON lims_run_data_exclusions TO lims_app")
    op.execute(
        "DROP TRIGGER IF EXISTS lims_run_data_exclusions_keep_record "
        "ON lims_run_data_exclusions"
    )
    op.execute("DROP FUNCTION IF EXISTS public.guard_exclusion_record()")
    op.execute("DELETE FROM lims_run_data_exclusions WHERE cleared_at IS NOT NULL")
    op.drop_index("uq_lims_run_data_exclusions_active", table_name="lims_run_data_exclusions")
    op.create_unique_constraint(
        "uq_experiment_data_exclusions_data_id",
        "lims_run_data_exclusions",
        ["lims_run_data_id"],
    )
    op.drop_constraint(
        "ck_lims_run_data_exclusions_cleared", "lims_run_data_exclusions", type_="check"
    )
    op.drop_column("lims_run_data_exclusions", "cleared_at")
    op.drop_constraint(
        "fk_lims_run_data_exclusions_cleared_by",
        "lims_run_data_exclusions",
        type_="foreignkey",
    )
    op.drop_column("lims_run_data_exclusions", "cleared_by")

    op.execute("DROP TRIGGER IF EXISTS result_entries_guard_write ON result_entries")
    op.execute("DROP FUNCTION IF EXISTS public.guard_result_entry_write()")
    op.execute("DROP TRIGGER IF EXISTS tests_guard_run_change ON tests")
    op.execute("DROP FUNCTION IF EXISTS public.guard_test_run_change()")
    op.execute("DROP TRIGGER IF EXISTS results_guard_write ON results")
    op.execute("DROP FUNCTION IF EXISTS public.guard_result_write()")

    op.execute("DROP POLICY IF EXISTS result_entries_access ON result_entries")
    op.drop_table("result_entries")

    op.execute(
        "DROP TRIGGER IF EXISTS analysis_analytes_default_pairing_unit ON analysis_analytes"
    )
    op.execute("DROP FUNCTION IF EXISTS public.default_pairing_unit()")
    op.drop_constraint(
        "fk_analysis_analytes_pairing_unit_id", "analysis_analytes", type_="foreignkey"
    )
    op.drop_column("analysis_analytes", "pairing_unit_id")

    op.drop_constraint("ck_entries_experiment_xor_lims_run", "entries", type_="check")
    op.execute("DELETE FROM entries WHERE experiment_id IS NULL")
    op.drop_index("ix_entries_lims_run_id", table_name="entries")
    op.drop_constraint("fk_entries_lims_run_id", "entries", type_="foreignkey")
    op.drop_column("entries", "lims_run_id")
    op.alter_column("entries", "experiment_id", nullable=False)

    op.drop_constraint("ck_results_knockout_time", "results", type_="check")
    op.drop_constraint("ck_results_knockout_fields", "results", type_="check")
    op.drop_column("results", "knocked_out_at")
    op.drop_constraint("fk_results_knocked_out_by", "results", type_="foreignkey")
    op.drop_column("results", "knocked_out_by")
    op.drop_column("results", "knocked_out")
    op.drop_constraint("fk_results_final_units_id", "results", type_="foreignkey")
    op.drop_column("results", "final_units_id")
    op.drop_column("results", "raw_units")
    op.drop_column("results", "display_order")

    op.add_column(
        "results",
        sa.Column("lims_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_results_lims_run_id",
        "results",
        "lims_runs",
        ["lims_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_results_lims_run_id", "results", ["lims_run_id"])
    op.execute(
        "UPDATE results r SET lims_run_id = t.lims_run_id "
        "FROM tests t WHERE t.id = r.test_id AND t.lims_run_id IS NOT NULL"
    )

    _catalog_add(conn, _CATALOG_REMOVED)

    op.drop_index("ix_tests_lims_run_id", table_name="tests")
    op.drop_constraint("fk_tests_lims_run_id", "tests", type_="foreignkey")
    op.drop_column("tests", "lims_run_id")

    op.execute("DROP FUNCTION IF EXISTS public.calculation_write_allowed()")
