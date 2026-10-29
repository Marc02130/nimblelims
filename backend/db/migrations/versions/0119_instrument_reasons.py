"""NBSP void reasons, required change reasons, type deactivation ledger.

Revision ID: 0119_instrument_reasons
Revises: 0118_e3_followups

Grant and CHECK behavior changes live here. 0118 is not edited.
Id stays at or under 32 characters. Nothing existing is dropped on
upgrade. No DELETE grants.
"""

from __future__ import annotations

import importlib.util
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.bootstrap_roles import HISTORICAL_ROLE

revision = "0119_instrument_reasons"
down_revision = "0118_e3_followups"
branch_labels = None
depends_on = None

TABLES = (
    ("instrument_type_deactivations", "core", "Instrument type deactivations"),
)
NEW_COLUMNS = (
    ("instrument_maintenance_audits", "reason"),
)

_WS = r"E' \t\r\n' || U&'\00A0' || U&'\2007'"
_REASON_LEN = (
    f"(reason IS NULL OR (reason ~ '\\S' AND "
    f"char_length(btrim(reason, {_WS})) BETWEEN 1 AND 4000))"
)
_REASON_LEN_REQUIRED = (
    f"(reason ~ '\\S' AND char_length(btrim(reason, {_WS})) BETWEEN 1 AND 4000)"
)
_VOID_REASON_LEN = (
    f"(void_reason IS NULL OR (void_reason ~ '\\S' AND "
    f"char_length(btrim(void_reason, {_WS})) BETWEEN 1 AND 1000))"
)

_0118_WS = r"E' \t\r\n'"
_0118_REASON_LEN = (
    f"(reason IS NULL OR (reason ~ '\\S' AND "
    f"char_length(btrim(reason, {_0118_WS})) BETWEEN 1 AND 1000))"
)
_0118_VOID_REASON_LEN = (
    f"(void_reason IS NULL OR (void_reason ~ '\\S' AND "
    f"char_length(btrim(void_reason, {_0118_WS})) BETWEEN 1 AND 1000))"
)
_ACTION_CHECK = (
    "action IN ('first_due', 'schedule_active', 'schedule_interval', "
    "'schedule_kind', 'schedule_vendor', 'event_void', 'event_restore', "
    "'maintenance_tracked')"
)
_0118_ACTION_CHECK = (
    "action IN ('first_due', 'schedule_active', 'schedule_interval', "
    "'schedule_kind', 'schedule_vendor', 'event_void', 'event_restore')"
)

_CATALOG_POLICY = "is_admin() OR has_experiment_access() OR has_config_edit()"
_CREATED_BY = "created_by IS NOT NULL AND created_by = current_user_id()"
_CATALOG_INSERT = f"{_CREATED_BY} AND ({_CATALOG_POLICY})"

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

_0118_VOID_FN = f"""
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
           OR btrim(NEW.void_reason, {_0118_WS}) = '' THEN
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

_SCHEDULE_REASON_FN = f"""
CREATE OR REPLACE FUNCTION public.require_schedule_change_reason()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NEW.action IN (
        'first_due',
        'schedule_active',
        'schedule_interval',
        'schedule_kind',
        'schedule_vendor'
    ) THEN
        IF NEW.reason IS NULL
           OR NEW.reason !~ '\\S'
           OR btrim(NEW.reason, {_WS}) = ''
           OR char_length(btrim(NEW.reason, {_WS})) > 4000 THEN
            RAISE EXCEPTION 'schedule_change_reason_required'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
"""

_TRACKED_REASON_FN = f"""
CREATE OR REPLACE FUNCTION public.require_maintenance_tracked_reason()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NEW.previous_value IS DISTINCT FROM NEW.new_value THEN
        IF NEW.reason IS NULL
           OR NEW.reason !~ '\\S'
           OR btrim(NEW.reason, {_WS}) = ''
           OR char_length(btrim(NEW.reason, {_WS})) > 4000 THEN
            RAISE EXCEPTION 'maintenance_tracked_reason_required'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
"""


def _replace_check(table: str, name: str, expr: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr})")


def _revoke_historical(table: str) -> None:
    has_legacy = op.get_bind().exec_driver_sql(
        f"SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{HISTORICAL_ROLE}'"
    ).scalar()
    if not has_legacy:
        return
    op.execute(f"REVOKE UPDATE ON TABLE {table} FROM {HISTORICAL_ROLE}")
    op.execute(f"REVOKE DELETE ON TABLE {table} FROM {HISTORICAL_ROLE}")


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0119", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _register() -> None:
    conn = op.get_bind()
    m = _m0089()
    cataloged = [
        r[0]
        for r in conn.execute(
            sa.text("SELECT DISTINCT client_id FROM schema_tables ORDER BY 1")
        ).all()
    ]
    if not cataloged:
        return
    admin = m._bind_admin(conn)
    if admin is None:
        return
    roles = {r[1]: r[0] for r in conn.execute(sa.text("SELECT id, name FROM roles")).all()}
    for client in cataloged:
        registered = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT physical_name FROM schema_tables WHERE client_id = :c"),
                {"c": client},
            ).all()
        }
        for physical, kind, display in TABLES:
            if physical in registered:
                continue
            table_id = m._id(client, physical)
            conn.execute(
                sa.text(
                    """
                    INSERT INTO schema_tables (
                        id, client_id, display_name, physical_name, kind, status, active,
                        created_at, created_by, modified_at, modified_by
                    )
                    VALUES (:id, :c, :d, :p, :k, 'active', true, NOW(), :u, NOW(), :u)
                    """
                ),
                {
                    "id": table_id,
                    "c": client,
                    "d": display,
                    "p": physical,
                    "k": kind,
                    "u": admin,
                },
            )
            reflected = m._reflect(conn, [physical]).get(physical, [])
            for col in reflected:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO schema_columns (
                            id, client_id, table_id, display_name, physical_name, data_type,
                            nullable, sort_order, status, is_platform, is_identity, is_fk,
                            fk_table, is_unique, pg_type, origin, active,
                            created_at, created_by, modified_at, modified_by
                        )
                        VALUES (
                            :id, :c, :t, :d, :p, :dt, :n, :o, 'active', :plat, false, :fk,
                            :fkt, :uq, :pg, :origin, true, NOW(), :u, NOW(), :u
                        )
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
                        "origin": "reflected",
                        "u": admin,
                    },
                )
            for role_name, access in m.DEFAULT_PRIVILEGES:
                role_id = roles.get(role_name)
                if role_id is None:
                    continue
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO schema_privileges (
                            id, client_id, role_id, table_id, column_id, access,
                            created_at, created_by, modified_at, modified_by
                        )
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
    conn.execute(
        sa.text(
            "SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"
        )
    )


def _register_new_columns() -> None:
    conn = op.get_bind()
    m = _m0089()
    admin = m._bind_admin(conn)
    if admin is None:
        return
    tables = sorted({table for table, _col in NEW_COLUMNS})
    reflected_by_table = m._reflect(conn, tables)
    for table, column in NEW_COLUMNS:
        reflected = reflected_by_table.get(table, [])
        col = next((c for c in reflected if c["name"] == column), None)
        if col is None:
            continue
        table_rows = conn.execute(
            sa.text(
                "SELECT client_id, id FROM schema_tables WHERE physical_name = :p"
            ),
            {"p": table},
        ).all()
        for client, table_id in table_rows:
            existing = conn.execute(
                sa.text(
                    "SELECT 1 FROM schema_columns "
                    "WHERE table_id = :t AND physical_name = :p"
                ),
                {"t": table_id, "p": column},
            ).scalar()
            if existing:
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO schema_columns (
                        id, client_id, table_id, display_name, physical_name, data_type,
                        nullable, sort_order, status, is_platform, is_identity, is_fk,
                        fk_table, is_unique, pg_type, origin, active,
                        created_at, created_by, modified_at, modified_by
                    )
                    VALUES (
                        :id, :c, :t, :d, :p, :dt, :n, :o, 'active', :plat, false, :fk,
                        :fkt, :uq, :pg, 'reflected', true, NOW(), :u, NOW(), :u
                    )
                    """
                ),
                {
                    "id": m._id(client, table, "col", column),
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
        sa.text(
            "SELECT set_config('app.current_user_id', '00000000-0000-0000-0000-000000000000', false)"
        )
    )


def _unregister() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_privileges
            WHERE table_id IN (
                SELECT id FROM schema_tables
                WHERE physical_name = 'instrument_type_deactivations'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns
            WHERE table_id IN (
                SELECT id FROM schema_tables
                WHERE physical_name = 'instrument_type_deactivations'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM schema_tables WHERE physical_name = 'instrument_type_deactivations'"
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns
            WHERE physical_name = 'reason'
              AND table_id IN (
                  SELECT id FROM schema_tables
                  WHERE physical_name = 'instrument_maintenance_audits'
              )
            """
        )
    )


def upgrade() -> None:
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
        "instrument_schedule_audits",
        "ck_instrument_schedule_audits_action",
        _ACTION_CHECK,
    )
    op.execute(_VOID_FN)
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() SECURITY DEFINER"
    )
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() "
        "SET search_path = pg_catalog, public"
    )

    op.add_column(
        "instrument_maintenance_audits",
        sa.Column("reason", sa.Text(), nullable=True),
    )
    _replace_check(
        "instrument_maintenance_audits",
        "ck_instrument_maintenance_audits_reason",
        _REASON_LEN,
    )
    op.execute(_TRACKED_REASON_FN)
    op.execute(
        "DROP TRIGGER IF EXISTS trg_require_maintenance_tracked_reason "
        "ON public.instrument_maintenance_audits"
    )
    op.execute(
        "CREATE TRIGGER trg_require_maintenance_tracked_reason "
        "BEFORE INSERT ON public.instrument_maintenance_audits "
        "FOR EACH ROW EXECUTE FUNCTION public.require_maintenance_tracked_reason()"
    )

    op.execute(_SCHEDULE_REASON_FN)
    op.execute(
        "DROP TRIGGER IF EXISTS trg_require_schedule_change_reason "
        "ON public.instrument_schedule_audits"
    )
    op.execute(
        "CREATE TRIGGER trg_require_schedule_change_reason "
        "BEFORE INSERT ON public.instrument_schedule_audits "
        "FOR EACH ROW EXECUTE FUNCTION public.require_schedule_change_reason()"
    )

    uuid_t = postgresql.UUID(as_uuid=True)
    op.create_table(
        "instrument_type_deactivations",
        sa.Column(
            "id",
            uuid_t,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "instrument_type_id",
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
        sa.CheckConstraint(
            _REASON_LEN_REQUIRED,
            name="ck_instrument_type_deactivations_reason",
        ),
    )
    op.create_index(
        "ix_instrument_type_deactivations_type_id",
        "instrument_type_deactivations",
        ["instrument_type_id"],
    )
    op.execute("GRANT SELECT, INSERT ON instrument_type_deactivations TO lims_app")
    op.execute("REVOKE UPDATE ON instrument_type_deactivations FROM lims_app")
    op.execute("REVOKE DELETE ON instrument_type_deactivations FROM lims_app")
    _revoke_historical("instrument_type_deactivations")
    op.execute("ALTER TABLE instrument_type_deactivations ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY instrument_type_deactivations_select "
        "ON instrument_type_deactivations FOR SELECT "
        f"USING ({_CATALOG_POLICY})"
    )
    op.execute(
        "CREATE POLICY instrument_type_deactivations_insert "
        "ON instrument_type_deactivations FOR INSERT "
        f"WITH CHECK ({_CATALOG_INSERT})"
    )
    op.execute("ALTER TABLE instrument_type_deactivations FORCE ROW LEVEL SECURITY")
    op.execute(
        "REVOKE EXECUTE ON FUNCTION public.require_schedule_change_reason() FROM PUBLIC"
    )
    op.execute(
        "REVOKE EXECUTE ON FUNCTION public.require_maintenance_tracked_reason() FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.require_schedule_change_reason() TO lims_app"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.require_maintenance_tracked_reason() TO lims_app"
    )
    _register()
    _register_new_columns()


def downgrade() -> None:
    leftover = op.get_bind().exec_driver_sql(
        "SELECT count(*) FROM instrument_schedule_audits "
        "WHERE action = 'maintenance_tracked'"
    ).scalar()
    if leftover:
        raise RuntimeError(
            "0119 downgrade refuses: instrument_schedule_audits "
            "maintenance_tracked rows exist"
        )
    _unregister()
    op.execute(
        "DROP TRIGGER IF EXISTS trg_require_schedule_change_reason "
        "ON public.instrument_schedule_audits"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_require_maintenance_tracked_reason "
        "ON public.instrument_maintenance_audits"
    )
    op.execute("DROP FUNCTION IF EXISTS public.require_schedule_change_reason()")
    op.execute("DROP FUNCTION IF EXISTS public.require_maintenance_tracked_reason()")
    op.execute(
        "DROP POLICY IF EXISTS instrument_type_deactivations_select "
        "ON instrument_type_deactivations"
    )
    op.execute(
        "DROP POLICY IF EXISTS instrument_type_deactivations_insert "
        "ON instrument_type_deactivations"
    )
    op.drop_index(
        "ix_instrument_type_deactivations_type_id",
        table_name="instrument_type_deactivations",
    )
    op.drop_table("instrument_type_deactivations")
    op.execute(
        "ALTER TABLE instrument_maintenance_audits "
        "DROP CONSTRAINT IF EXISTS ck_instrument_maintenance_audits_reason"
    )
    op.drop_column("instrument_maintenance_audits", "reason")
    op.execute(_0118_VOID_FN)
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() SECURITY DEFINER"
    )
    op.execute(
        "ALTER FUNCTION public.refuse_void_only_passing_event() "
        "SET search_path = pg_catalog, public"
    )
    _replace_check(
        "instrument_schedule_audits",
        "ck_instrument_schedule_audits_reason",
        _0118_REASON_LEN,
    )
    _replace_check(
        "instrument_schedule_audits",
        "ck_instrument_schedule_audits_action",
        _0118_ACTION_CHECK,
    )
    _replace_check(
        "instrument_maintenance_events",
        "ck_instrument_events_void_reason",
        _0118_VOID_REASON_LEN,
    )
