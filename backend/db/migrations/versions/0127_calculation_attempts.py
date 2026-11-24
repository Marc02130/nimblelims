"""Calculation attempts and the stage runner's records (calculations S9).

Revision ID: 0127_calculation_attempts
Revises: 0126_calculation_activation

CALC-REQ-25, 26, 30, 21, 48, 49, 53, 4a, 37, 58. OQ-CALC-25 (Spec default).

* ``calculation_attempts``: one append-only row per accepted calculation of a
  result-entry row. It holds the provenance of CALC-REQ-30 (OQ-CALC-25 default:
  on the attempt, linked from the row, not copied onto row columns): status
  (``completed`` or ``stopped``), the stop code and the stage that stopped, or
  the Excel text of a lab-written formula error; the run summary (``pass``,
  ``fail``, or ``stopped``) and the check that produced it (CALC-REQ-21); the R
  lock hash and the built image digest; the configuration name and version,
  the analysis version, and the version of every catalog function and formula
  stage; the entries, records, and fields read with their values; every value
  used; the knocked-out points; each stage's record; and the calculated and
  reported values written. The actor is ``current_user_id()``; the time is the
  database clock. The row's Test, analyte, run, and analysis must be those of
  its result entry. UPDATE and DELETE are refused for ``lims_app`` by privilege
  and by trigger. Row-level security follows the result entry it belongs to.
* ``result_entries.calculation_attempt_id``: the link from the row to the
  attempt that last wrote it. It changes only on the calculation path
  (``lims.calculation_write``), only to an attempt of that same row, and only
  together with the attempt's calculated and reported values.
* ``calculation_test_case_results`` and ``calculation_dry_runs``: the stage
  runner now writes them. ``lims_app`` gains INSERT on both (UPDATE and DELETE
  stay revoked), and a trigger refuses any other actor than
  ``current_user_id()`` and any update or delete. Each gains the observed
  outcome and the built image digest; a dry run also records its lock hash.

Nothing here writes to ``results``. A stage output is a calculated value until
the experiment is published (S13).

Downgrade drops the attempts table and the link, restores the 0123 result-entry
guard, drops the new columns, and revokes INSERT on the two runner tables
again. Attempts, test-case outcomes, and dry-run outcomes are lost.
"""

from __future__ import annotations

import importlib.util
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0127_calculation_attempts"
down_revision = "0126_calculation_activation"
branch_labels = None
depends_on = None

APP_ROLE = "lims_app"

ATTEMPT_STATUSES = ("completed", "stopped")
RUN_SUMMARIES = ("pass", "fail", "stopped")
FORMULA_ERRORS = ("#DIV/0!", "#VALUE!", "#N/A", "#NUM!")

_ATTEMPT_JSON_ARRAYS = (
    "function_versions",
    "formula_versions",
    "inputs_read",
    "values_used",
    "knocked_out_points",
    "flags",
    "stages",
)

_CATALOG_ADDED = (("result_entries", "calculation_attempt_id"),)

_ATTEMPT_ACCESS_POLICY = """\
    is_admin() OR result_entry_id IN (SELECT r.id FROM result_entries r)\
"""

_ATTEMPT_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_calculation_attempt()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    row_test uuid;
    row_analyte uuid;
    test_run uuid;
    run_analysis uuid;
BEGIN
    IF public.skip_app_row_guard() THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'calculation_attempt_append_only'
            USING ERRCODE = '42501',
                  DETAIL = 'A calculation attempt is never updated or deleted.';
    END IF;
    IF NEW.created_by IS DISTINCT FROM public.current_user_id() THEN
        RAISE EXCEPTION 'calculation_attempt_actor'
            USING ERRCODE = '42501',
                  DETAIL = 'The attempt is recorded for the signed-in user, not a value written by the caller.';
    END IF;
    SELECT r.test_id, r.analyte_id INTO row_test, row_analyte
      FROM public.result_entries r WHERE r.id = NEW.result_entry_id;
    SELECT t.lims_run_id INTO test_run FROM public.tests t WHERE t.id = row_test;
    SELECT lr.analysis_id INTO run_analysis FROM public.lims_runs lr WHERE lr.id = test_run;
    IF row_test IS NULL
       OR NEW.test_id IS DISTINCT FROM row_test
       OR NEW.analyte_id IS DISTINCT FROM row_analyte
       OR NEW.lims_run_id IS DISTINCT FROM test_run
       OR NEW.analysis_id IS DISTINCT FROM run_analysis THEN
        RAISE EXCEPTION 'calculation_attempt_scope'
            USING ERRCODE = '42501',
                  DETAIL = 'An attempt names the Test, analyte, LIMS run, and analysis of its result entry.';
    END IF;
    NEW.created_at := now();
    RETURN NEW;
END;
$$;
"""

_RUN_RECORD_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_calculation_run_record()
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
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'calculation_run_record_append_only'
            USING ERRCODE = '42501',
                  DETAIL = 'A test-case outcome or a dry run is never updated or deleted.';
    END IF;
    IF NEW.created_by IS DISTINCT FROM public.current_user_id() THEN
        RAISE EXCEPTION 'calculation_run_record_actor'
            USING ERRCODE = '42501',
                  DETAIL = 'The run is recorded for the signed-in user, not a value written by the caller.';
    END IF;
    NEW.run_at := now();
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
    attempt_row uuid;
    attempt_calculated text;
    attempt_reported text;
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
        IF NEW.calculation_attempt_id IS NOT NULL
           AND (TG_OP = 'INSERT' OR NEW.calculation_attempt_id IS DISTINCT FROM OLD.calculation_attempt_id) THEN
            SELECT a.result_entry_id, a.calculated_result, a.reported_result
              INTO attempt_row, attempt_calculated, attempt_reported
              FROM public.calculation_attempts a WHERE a.id = NEW.calculation_attempt_id;
            IF attempt_row IS DISTINCT FROM NEW.id
               OR NEW.calculated_result IS DISTINCT FROM attempt_calculated
               OR NEW.reported_result IS DISTINCT FROM attempt_reported THEN
                RAISE EXCEPTION 'calculation_attempt_mismatch'
                    USING ERRCODE = '42501',
                          DETAIL = 'A row links only an attempt of that row, with the values that attempt wrote.';
            END IF;
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
        IF NEW.calculation_attempt_id IS NOT NULL THEN
            RAISE EXCEPTION 'calculation_attempt_locked' USING ERRCODE = '42501';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.calculation_attempt_id IS DISTINCT FROM OLD.calculation_attempt_id THEN
        RAISE EXCEPTION 'calculation_attempt_locked' USING ERRCODE = '42501';
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


def _m0123():
    path = os.path.join(os.path.dirname(__file__), "0123_result_entry_data_model.py")
    spec = importlib.util.spec_from_file_location("_m0123_for_0127", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _function_grants(signature: str) -> None:
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.{signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {APP_ROLE}")


def _in(values: tuple[str, ...]) -> str:
    return ", ".join("'" + value.replace("'", "''") + "'" for value in values)


def _uuid(name: str, *, nullable: bool = False, fk: str | None = None) -> sa.Column:
    args = [sa.ForeignKey(fk, ondelete="RESTRICT")] if fk else []
    return sa.Column(name, postgresql.UUID(as_uuid=True), *args, nullable=nullable)


def upgrade() -> None:
    arrays = " AND ".join(f"jsonb_typeof({name}) = 'array'" for name in _ATTEMPT_JSON_ARRAYS)
    op.create_table(
        "calculation_attempts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        _uuid("result_entry_id", fk="result_entries.id"),
        _uuid("test_id", fk="tests.id"),
        _uuid("analyte_id", fk="analytes.id"),
        _uuid("lims_run_id", fk="lims_runs.id"),
        _uuid("analysis_id", fk="analyses.id"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stop_code", sa.String(64), nullable=True),
        sa.Column("stop_stage", sa.String(40), nullable=True),
        sa.Column("stop_detail", sa.Text(), nullable=True),
        sa.Column("formula_error", sa.String(16), nullable=True),
        sa.Column("run_summary", sa.String(16), nullable=False),
        sa.Column("summary_check", sa.String(40), nullable=True),
        sa.Column("summary_code", sa.String(64), nullable=True),
        sa.Column("lock_hash", sa.String(64), nullable=False),
        sa.Column("built_image_digest", sa.String(71), nullable=False),
        sa.Column("configuration_name", sa.String(100), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        *(
            sa.Column(name, postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"))
            for name in _ATTEMPT_JSON_ARRAYS
        ),
        sa.Column("calculated_result", sa.String(255), nullable=True),
        sa.Column("reported_result", sa.String(255), nullable=True),
        sa.Column("result_note", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _uuid("created_by", fk="users.id"),
        sa.CheckConstraint(f"status IN ({_in(ATTEMPT_STATUSES)})", name="ck_calculation_attempts_status"),
        sa.CheckConstraint(
            f"run_summary IN ({_in(RUN_SUMMARIES)})", name="ck_calculation_attempts_summary"
        ),
        sa.CheckConstraint(
            f"formula_error IS NULL OR formula_error IN ({_in(FORMULA_ERRORS)})",
            name="ck_calculation_attempts_formula_error",
        ),
        sa.CheckConstraint(
            "(status = 'stopped') = (stop_code IS NOT NULL OR formula_error IS NOT NULL)"
            " AND NOT (stop_code IS NOT NULL AND formula_error IS NOT NULL)",
            name="ck_calculation_attempts_stop",
        ),
        sa.CheckConstraint(
            "status <> 'stopped' OR (run_summary = 'stopped' AND stop_stage IS NOT NULL"
            " AND calculated_result IS NULL AND reported_result IS NULL)",
            name="ck_calculation_attempts_stop_clears",
        ),
        sa.CheckConstraint(
            "(run_summary = 'pass') = (summary_check IS NULL AND summary_code IS NULL)",
            name="ck_calculation_attempts_summary_names_check",
        ),
        sa.CheckConstraint(
            "lock_hash ~ '^[0-9a-f]{64}$' AND built_image_digest ~ '^sha256:[0-9a-f]{64}$'",
            name="ck_calculation_attempts_hashes",
        ),
        sa.CheckConstraint(
            "configuration_version >= 1 AND analysis_version >= 1",
            name="ck_calculation_attempts_versions",
        ),
        sa.CheckConstraint(
            f"{arrays} AND (result_note IS NULL OR jsonb_typeof(result_note) = 'object')",
            name="ck_calculation_attempts_json",
        ),
    )
    op.create_index(
        "ix_calculation_attempts_result_entry",
        "calculation_attempts",
        ["result_entry_id", "created_at"],
    )
    op.create_index("ix_calculation_attempts_run", "calculation_attempts", ["lims_run_id"])

    op.execute(_ATTEMPT_GUARD_FN)
    _function_grants("guard_calculation_attempt()")
    op.execute(
        "CREATE TRIGGER calculation_attempts_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON calculation_attempts "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_calculation_attempt()"
    )
    op.execute("ALTER TABLE calculation_attempts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE calculation_attempts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY calculation_attempts_access ON calculation_attempts "
        f"FOR ALL USING ({_ATTEMPT_ACCESS_POLICY})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON calculation_attempts TO {APP_ROLE}")
    op.execute("REVOKE UPDATE, DELETE ON calculation_attempts FROM lims_app")

    op.add_column(
        "result_entries",
        sa.Column(
            "calculation_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "calculation_attempts.id",
                ondelete="RESTRICT",
                name="fk_result_entries_calculation_attempt",
            ),
            nullable=True,
        ),
    )
    op.execute(_RESULT_ENTRY_GUARD_FN)
    # The guard now reads calculation_attempts as its owner (SECURITY DEFINER),
    # so it is owned by the role that just created that table.
    op.execute("ALTER FUNCTION public.guard_result_entry_write() OWNER TO CURRENT_USER")

    op.add_column("calculation_test_case_results", sa.Column("outcome", postgresql.JSONB(), nullable=True))
    op.add_column(
        "calculation_test_case_results",
        sa.Column("built_image_digest", sa.String(71), nullable=True),
    )
    op.create_check_constraint(
        "ck_calculation_test_case_results_outcome",
        "calculation_test_case_results",
        "(outcome IS NULL OR jsonb_typeof(outcome) = 'object') AND "
        "(built_image_digest IS NULL OR built_image_digest ~ '^sha256:[0-9a-f]{64}$')",
    )
    op.add_column("calculation_dry_runs", sa.Column("outcome", postgresql.JSONB(), nullable=True))
    op.add_column("calculation_dry_runs", sa.Column("lock_hash", sa.String(64), nullable=True))
    op.add_column("calculation_dry_runs", sa.Column("built_image_digest", sa.String(71), nullable=True))
    op.create_check_constraint(
        "ck_calculation_dry_runs_outcome",
        "calculation_dry_runs",
        "(outcome IS NULL OR jsonb_typeof(outcome) = 'object') AND "
        "(lock_hash IS NULL OR lock_hash ~ '^[0-9a-f]{64}$') AND "
        "(built_image_digest IS NULL OR built_image_digest ~ '^sha256:[0-9a-f]{64}$')",
    )

    op.execute(_RUN_RECORD_GUARD_FN)
    _function_grants("guard_calculation_run_record()")
    op.execute(
        "CREATE TRIGGER calculation_test_case_results_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON calculation_test_case_results "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_calculation_run_record()"
    )
    op.execute(
        "CREATE TRIGGER calculation_dry_runs_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON calculation_dry_runs "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_calculation_run_record()"
    )
    op.execute(f"GRANT INSERT ON calculation_test_case_results TO {APP_ROLE}")
    op.execute(f"GRANT INSERT ON calculation_dry_runs TO {APP_ROLE}")

    _m0123()._catalog_add(op.get_bind(), _CATALOG_ADDED)


def downgrade() -> None:
    conn = op.get_bind()
    _m0123()._catalog_remove(conn, _CATALOG_ADDED)

    op.execute("REVOKE INSERT ON calculation_dry_runs FROM lims_app")
    op.execute("REVOKE INSERT ON calculation_test_case_results FROM lims_app")
    op.execute("DROP TRIGGER IF EXISTS calculation_dry_runs_guard ON calculation_dry_runs")
    op.execute(
        "DROP TRIGGER IF EXISTS calculation_test_case_results_guard ON calculation_test_case_results"
    )
    op.execute("DROP FUNCTION IF EXISTS public.guard_calculation_run_record()")
    op.drop_constraint("ck_calculation_dry_runs_outcome", "calculation_dry_runs", type_="check")
    op.drop_column("calculation_dry_runs", "built_image_digest")
    op.drop_column("calculation_dry_runs", "lock_hash")
    op.drop_column("calculation_dry_runs", "outcome")
    op.drop_constraint(
        "ck_calculation_test_case_results_outcome", "calculation_test_case_results", type_="check"
    )
    op.drop_column("calculation_test_case_results", "built_image_digest")
    op.drop_column("calculation_test_case_results", "outcome")

    op.execute(_m0123()._RESULT_ENTRY_GUARD_FN)
    op.drop_constraint("fk_result_entries_calculation_attempt", "result_entries", type_="foreignkey")
    op.drop_column("result_entries", "calculation_attempt_id")

    op.execute("DROP POLICY IF EXISTS calculation_attempts_access ON calculation_attempts")
    op.execute("DROP TRIGGER IF EXISTS calculation_attempts_guard ON calculation_attempts")
    op.execute("DROP FUNCTION IF EXISTS public.guard_calculation_attempt()")
    op.drop_index("ix_calculation_attempts_run", table_name="calculation_attempts")
    op.drop_index("ix_calculation_attempts_result_entry", table_name="calculation_attempts")
    op.drop_table("calculation_attempts")
