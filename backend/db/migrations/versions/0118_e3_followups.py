"""E3 follow-ups: lab_settings no-delete, whitespace reasons, legacy grants.

Revision ID: 0118_e3_followups
Revises: 0117_e3_hardening

Grant/behavior changes live here. 0117 only inlined maintenance role
names (no behavior change). Id stays at or under 32 characters.
Nothing is dropped. No DELETE grants.
"""

from __future__ import annotations

from alembic import op

from db.append_only_tables import APPEND_ONLY_REVOKES

# Historical NOLOGIN grant target from early migrations. Not a secret.
_HISTORICAL_ROLE = "lims_user"  # pragma: allowlist secret

revision = "0118_e3_followups"
down_revision = "0117_e3_hardening"
branch_labels = None
depends_on = None

_WS = r"E' \t\r\n'"
_REASON_LEN = (
    f"(reason IS NULL OR (reason ~ '\\S' AND "
    f"char_length(btrim(reason, {_WS})) BETWEEN 1 AND 1000))"
)
_REASON_LEN_REQUIRED = (
    f"(reason ~ '\\S' AND char_length(btrim(reason, {_WS})) BETWEEN 1 AND 1000)"
)
_VOID_REASON_LEN = (
    f"(void_reason IS NULL OR (void_reason ~ '\\S' AND "
    f"char_length(btrim(void_reason, {_WS})) BETWEEN 1 AND 1000))"
)
_0117_REASON_LEN = (
    "(reason IS NULL OR (char_length(btrim(reason)) BETWEEN 1 AND 1000))"
)
_0117_REASON_LEN_REQUIRED = "(char_length(btrim(reason)) BETWEEN 1 AND 1000)"
_0117_VOID_REASON_LEN = (
    "(void_reason IS NULL OR (char_length(btrim(void_reason)) BETWEEN 1 AND 1000))"
)

_VOID_FN = f"""
CREATE OR REPLACE FUNCTION public.refuse_void_only_passing_event()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT public.is_lab_manager_or_admin() THEN
        RAISE EXCEPTION 'maintenance_event_update_forbidden'
            USING ERRCODE = '42501';
    END IF;
    IF NEW.active IS FALSE AND OLD.active IS TRUE THEN
        IF NEW.void_reason IS NULL
           OR NEW.void_reason !~ '\\S'
           OR btrim(NEW.void_reason, {_WS}) = '' THEN
            RAISE EXCEPTION 'void_reason_required'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    IF OLD.schedule_id IS NOT NULL THEN
        PERFORM 1
           FROM public.instrument_maintenance_schedules s
          WHERE s.id = OLD.schedule_id
          FOR UPDATE;
    END IF;
    RETURN NEW;
END;
$$;
"""

_0117_VOID_FN = """
CREATE OR REPLACE FUNCTION public.refuse_void_only_passing_event()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT public.is_lab_manager_or_admin() THEN
        RAISE EXCEPTION 'maintenance_event_update_forbidden'
            USING ERRCODE = '42501';
    END IF;
    IF NEW.active IS FALSE AND OLD.active IS TRUE THEN
        IF NEW.void_reason IS NULL OR btrim(NEW.void_reason) = '' THEN
            RAISE EXCEPTION 'void_reason_required'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    IF OLD.schedule_id IS NOT NULL THEN
        PERFORM 1
           FROM public.instrument_maintenance_schedules s
          WHERE s.id = OLD.schedule_id
          FOR UPDATE;
    END IF;
    RETURN NEW;
END;
$$;
"""


def _refuse_bad_reasons(conn) -> None:
    checks = (
        (
            "instrument_maintenance_events",
            "void_reason",
            f"void_reason IS NOT NULL AND NOT (void_reason ~ '\\S' AND "
            f"char_length(btrim(void_reason, {_WS})) BETWEEN 1 AND 1000)",
        ),
        (
            "instrument_schedule_audits",
            "reason",
            f"reason IS NOT NULL AND NOT (reason ~ '\\S' AND "
            f"char_length(btrim(reason, {_WS})) BETWEEN 1 AND 1000)",
        ),
        (
            "lims_run_type_substitutions",
            "reason",
            f"NOT (reason ~ '\\S' AND char_length(btrim(reason, {_WS})) "
            "BETWEEN 1 AND 1000)",
        ),
        (
            "instrument_template_inactivations",
            "reason",
            f"NOT (reason ~ '\\S' AND char_length(btrim(reason, {_WS})) "
            "BETWEEN 1 AND 1000)",
        ),
    )
    bad = []
    for table, column, where in checks:
        present = conn.exec_driver_sql(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            f"AND table_name = '{table}' AND column_name = '{column}'"
        ).scalar()
        if not present:
            continue
        count = conn.exec_driver_sql(
            f"SELECT count(*) FROM {table} WHERE {where}"
        ).scalar()
        if count:
            bad.append(f"{table}.{column}={count}")
    if bad:
        raise RuntimeError("0118 refuses CHECK: " + ", ".join(bad))


def _replace_check(table: str, name: str, expr: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr})")


def upgrade() -> None:
    _refuse_bad_reasons(op.get_bind())
    op.execute("REVOKE DELETE ON TABLE lab_settings FROM lims_app")
    existing = {
        r[0]
        for r in op.get_bind().exec_driver_sql(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        ).all()
    }
    has_legacy = op.get_bind().exec_driver_sql(
        f"SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{_HISTORICAL_ROLE}'"
    ).scalar()
    if has_legacy:
        for table, privileges in APPEND_ONLY_REVOKES.items():
            if table not in existing:
                continue
            for privilege in sorted(privileges):
                op.execute(
                    f"REVOKE {privilege} ON TABLE {table} FROM {_HISTORICAL_ROLE}"
                )
    _replace_check(
        "instrument_maintenance_events",
        "ck_instrument_events_void_reason",
        _VOID_REASON_LEN,
    )
    _replace_check(
        "instrument_schedule_audits",
        "ck_instrument_schedule_audits_reason",
        _REASON_LEN,
    )
    _replace_check(
        "lims_run_type_substitutions",
        "ck_lims_run_type_substitutions_reason",
        _REASON_LEN_REQUIRED,
    )
    _replace_check(
        "instrument_template_inactivations",
        "ck_instrument_template_inactivations_reason",
        _REASON_LEN_REQUIRED,
    )
    op.execute(_VOID_FN)
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() SECURITY DEFINER"
    )
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() "
        "SET search_path = pg_catalog, public"
    )


def downgrade() -> None:
    op.execute(_0117_VOID_FN)
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() SECURITY DEFINER"
    )
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() "
        "SET search_path = pg_catalog, public"
    )
    _replace_check(
        "instrument_template_inactivations",
        "ck_instrument_template_inactivations_reason",
        _0117_REASON_LEN_REQUIRED,
    )
    _replace_check(
        "lims_run_type_substitutions",
        "ck_lims_run_type_substitutions_reason",
        _0117_REASON_LEN_REQUIRED,
    )
    _replace_check(
        "instrument_schedule_audits",
        "ck_instrument_schedule_audits_reason",
        _0117_REASON_LEN,
    )
    _replace_check(
        "instrument_maintenance_events",
        "ck_instrument_events_void_reason",
        _0117_VOID_REASON_LEN,
    )
