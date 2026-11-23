"""Activation of a calculation configuration (calculations S8).

Revision ID: 0126_calculation_activation
Revises: 0125_analysis_version_no_change

CALC-REQ-34, 35, 45, 46, 47. OQ-CALC-12, 14, 15, 17.

* ``calculation_activations``: one append-only row per activation. It records
  the Admin who activated (``created_by``), the time, the configuration name
  and version, the pinned catalog-function versions, the R lock hash, the
  validation state, the review document the Admin was shown, and the SHA-256 of
  that document (RFC 8785 JCS). The database refuses a row whose actor is not
  ``current_user_id()`` (SQLSTATE 42501) and a row whose actor does not hold the
  Administrator role. UPDATE and DELETE are refused for ``lims_app`` both by
  privilege and by trigger. Self-activation is allowed (OQ-CALC-15): nothing
  here compares the actor with the proposer.
* ``validation_state`` is a closed list (OQ-CALC-12, decided provisionally in
  this slice): ``no_test_cases``, ``tests_none_passed``, ``tests_some_passed``,
  ``tests_all_passed``. It is recorded, never a gate, and no state value labels
  a configuration as proven (CALC-REQ-46).
* ``calculation_confirm_tokens``: the single-use confirm token. Only the
  SHA-256 of the token is stored. It is bound to the user, the proposal (the
  analysis and analyte), the configuration version, the review hash, and the
  login ``jti``. ``issued_at`` is the database clock. The only change a row
  accepts from ``lims_app`` is ``consumed_at`` going from null to ``now()``;
  the activation transaction makes that change, so a rolled-back activation
  leaves the token unconsumed. No password is stored or asked for (OQ-CALC-17
  default).
* ``calculation_test_cases``: test cases recorded against one configuration
  version. ``expected_source`` is ``independent`` or ``system_output`` (CALC-REQ-45
  item 2). Insert-only for ``lims_app``.
* ``calculation_test_case_results`` and ``calculation_dry_runs``: what the stage
  runner (S9) will record. S8 runs nothing, so ``lims_app`` can read these and
  cannot write them. The activation review counts what is in them.

Row-level security is not enabled on these tables, as for the S7 tables.
No row is seeded.

Downgrade drops the tables, triggers, and functions. Activation records are
lost.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0126_calculation_activation"
down_revision = "0125_analysis_version_no_change"
branch_labels = None
depends_on = None

APP_ROLE = "lims_app"

VALIDATION_STATES = (
    "no_test_cases",
    "tests_none_passed",
    "tests_some_passed",
    "tests_all_passed",
)

_ACTIVATION_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_calculation_activation()
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
        RAISE EXCEPTION 'calculation_activation_append_only'
            USING ERRCODE = '42501',
                  DETAIL = 'An activation record is never updated or deleted.';
    END IF;
    IF NEW.created_by IS DISTINCT FROM public.current_user_id() THEN
        RAISE EXCEPTION 'calculation_activation_actor'
            USING ERRCODE = '42501',
                  DETAIL = 'The activating user is the signed-in user, not a value written by the caller.';
    END IF;
    IF NOT public.is_admin() THEN
        RAISE EXCEPTION 'calculation_activation_admin_only'
            USING ERRCODE = '42501',
                  DETAIL = 'Only a user with the Admin role activates a calculation configuration.';
    END IF;
    RETURN NEW;
END;
$$;
"""

_TOKEN_GUARD_FN = """
CREATE OR REPLACE FUNCTION public.guard_calculation_confirm_token()
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
        IF NEW.user_id IS DISTINCT FROM public.current_user_id() THEN
            RAISE EXCEPTION 'calculation_confirm_token_user'
                USING ERRCODE = '42501',
                      DETAIL = 'A confirm token is issued to the signed-in user only.';
        END IF;
        NEW.issued_at := now();
        NEW.consumed_at := NULL;
        RETURN NEW;
    END IF;
    IF NEW.id IS DISTINCT FROM OLD.id
       OR NEW.token_hash IS DISTINCT FROM OLD.token_hash
       OR NEW.user_id IS DISTINCT FROM OLD.user_id
       OR NEW.analysis_id IS DISTINCT FROM OLD.analysis_id
       OR NEW.analyte_id IS DISTINCT FROM OLD.analyte_id
       OR NEW.configuration_version IS DISTINCT FROM OLD.configuration_version
       OR NEW.review_hash IS DISTINCT FROM OLD.review_hash
       OR NEW.session_jti IS DISTINCT FROM OLD.session_jti
       OR NEW.issued_at IS DISTINCT FROM OLD.issued_at THEN
        RAISE EXCEPTION 'calculation_confirm_token_immutable'
            USING ERRCODE = '42501',
                  DETAIL = 'A confirm token is consumed. No other field changes.';
    END IF;
    IF OLD.consumed_at IS NOT NULL THEN
        RAISE EXCEPTION 'calculation_confirm_token_used'
            USING ERRCODE = '42501',
                  DETAIL = 'A confirm token is single-use.';
    END IF;
    NEW.consumed_at := now();
    RETURN NEW;
END;
$$;
"""


def _function_grants(signature: str) -> None:
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.{signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO {APP_ROLE}")


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def _user_fk(name: str, *, nullable: bool) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=nullable,
    )


def upgrade() -> None:
    states = ", ".join(f"'{state}'" for state in VALIDATION_STATES)

    op.create_table(
        "calculation_activations",
        _uuid_pk(),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analyte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_name", sa.String(100), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("function_versions", postgresql.JSONB(), nullable=False),
        sa.Column("lock_hash", sa.String(64), nullable=False),
        sa.Column("validation_state", sa.String(30), nullable=False),
        sa.Column("review_document", postgresql.JSONB(), nullable=False),
        sa.Column("review_hash", sa.String(64), nullable=False),
        _created_at(),
        _user_fk("created_by", nullable=False),
        sa.CheckConstraint("configuration_version >= 1", name="ck_calculation_activations_version"),
        sa.CheckConstraint(
            "lock_hash ~ '^[0-9a-f]{64}$' AND review_hash ~ '^[0-9a-f]{64}$'",
            name="ck_calculation_activations_hashes",
        ),
        sa.CheckConstraint(
            f"validation_state IN ({states})",
            name="ck_calculation_activations_state",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(review_document) = 'object' AND jsonb_typeof(function_versions) = 'array'",
            name="ck_calculation_activations_json",
        ),
    )
    op.create_index(
        "ix_calculation_activations_pair",
        "calculation_activations",
        ["analysis_id", "analyte_id", "created_at"],
    )

    op.create_table(
        "calculation_confirm_tokens",
        _uuid_pk(),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        _user_fk("user_id", nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analyte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("review_hash", sa.String(64), nullable=False),
        sa.Column("session_jti", sa.String(128), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$' AND review_hash ~ '^[0-9a-f]{64}$'",
            name="ck_calculation_confirm_tokens_hashes",
        ),
        sa.CheckConstraint("configuration_version >= 1", name="ck_calculation_confirm_tokens_version"),
    )

    op.create_table(
        "calculation_test_cases",
        _uuid_pk(),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analyte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("expected", postgresql.JSONB(), nullable=False),
        sa.Column("expected_source", sa.String(20), nullable=False),
        _created_at(),
        _user_fk("created_by", nullable=False),
        sa.CheckConstraint("configuration_version >= 1", name="ck_calculation_test_cases_version"),
        sa.CheckConstraint(
            "expected_source IN ('independent', 'system_output')",
            name="ck_calculation_test_cases_source",
        ),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_calculation_test_cases_name"),
        sa.CheckConstraint(
            "jsonb_typeof(inputs) = 'object' AND jsonb_typeof(expected) = 'object'",
            name="ck_calculation_test_cases_json",
        ),
    )
    op.create_index(
        "ix_calculation_test_cases_pair",
        "calculation_test_cases",
        ["analysis_id", "analyte_id", "configuration_version"],
    )

    op.create_table(
        "calculation_test_case_results",
        _uuid_pk(),
        sa.Column(
            "test_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_test_cases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("lock_hash", sa.String(64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _user_fk("created_by", nullable=True),
        sa.CheckConstraint("lock_hash ~ '^[0-9a-f]{64}$'", name="ck_calculation_test_case_results_hash"),
    )
    op.create_index(
        "ix_calculation_test_case_results_case",
        "calculation_test_case_results",
        ["test_case_id", "run_at"],
    )

    op.create_table(
        "calculation_dry_runs",
        _uuid_pk(),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analyte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("input", postgresql.JSONB(), nullable=False),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _user_fk("created_by", nullable=True),
        sa.CheckConstraint("configuration_version >= 1", name="ck_calculation_dry_runs_version"),
        sa.CheckConstraint("jsonb_typeof(input) = 'object'", name="ck_calculation_dry_runs_input"),
    )
    op.create_index(
        "ix_calculation_dry_runs_pair",
        "calculation_dry_runs",
        ["analysis_id", "analyte_id", "configuration_version", "run_at"],
    )

    op.execute(_ACTIVATION_GUARD_FN)
    _function_grants("guard_calculation_activation()")
    op.execute(
        "CREATE TRIGGER calculation_activations_guard "
        "BEFORE INSERT OR UPDATE OR DELETE ON calculation_activations "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_calculation_activation()"
    )
    op.execute(_TOKEN_GUARD_FN)
    _function_grants("guard_calculation_confirm_token()")
    op.execute(
        "CREATE TRIGGER calculation_confirm_tokens_guard "
        "BEFORE INSERT OR UPDATE ON calculation_confirm_tokens "
        "FOR EACH ROW EXECUTE FUNCTION public.guard_calculation_confirm_token()"
    )

    for table in (
        "calculation_activations",
        "calculation_confirm_tokens",
        "calculation_test_cases",
        "calculation_test_case_results",
        "calculation_dry_runs",
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APP_ROLE}")
    op.execute("REVOKE UPDATE, DELETE ON calculation_activations FROM lims_app")
    op.execute("REVOKE DELETE ON calculation_confirm_tokens FROM lims_app")
    op.execute("REVOKE UPDATE, DELETE ON calculation_test_cases FROM lims_app")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON calculation_test_case_results FROM lims_app")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON calculation_dry_runs FROM lims_app")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS calculation_confirm_tokens_guard ON calculation_confirm_tokens")
    op.execute("DROP FUNCTION IF EXISTS public.guard_calculation_confirm_token()")
    op.execute("DROP TRIGGER IF EXISTS calculation_activations_guard ON calculation_activations")
    op.execute("DROP FUNCTION IF EXISTS public.guard_calculation_activation()")

    op.drop_index("ix_calculation_dry_runs_pair", table_name="calculation_dry_runs")
    op.drop_table("calculation_dry_runs")
    op.drop_index("ix_calculation_test_case_results_case", table_name="calculation_test_case_results")
    op.drop_table("calculation_test_case_results")
    op.drop_index("ix_calculation_test_cases_pair", table_name="calculation_test_cases")
    op.drop_table("calculation_test_cases")
    op.drop_table("calculation_confirm_tokens")
    op.drop_index("ix_calculation_activations_pair", table_name="calculation_activations")
    op.drop_table("calculation_activations")
