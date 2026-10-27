"""E3 hardening: void reason, reason length, DB run guards, slot audit.

Revision ID: 0117_e3_hardening
Revises: 0116_e2_review_fixes

Revision id stays at or under 32 characters because
``alembic_version.version_num`` is varchar(32).

Nothing is dropped. No DELETE grants. Lab rows are never deleted.
R5.11 (run status audit/history) is deferred — this revision does not
add a run-status history table or trigger.
"""

from __future__ import annotations

import importlib.util
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from db.append_only_tables import MAINTENANCE_SESSION_ROLES

revision = "0117_e3_hardening"
down_revision = "0116_e2_review_fixes"
branch_labels = None
depends_on = None

TABLES = (
    ("instrument_entry_slot_audits", "core", "Instrument entry slot audits"),
)
NEW_COLUMNS = (
    ("instrument_maintenance_events", "void_reason"),
)

_CATALOG_POLICY = "is_admin() OR has_experiment_access() OR has_config_edit()"
_CREATED_BY = "created_by IS NOT NULL AND created_by = current_user_id()"
_CATALOG_INSERT = f"{_CREATED_BY} AND ({_CATALOG_POLICY})"
_SUBSTITUTION_INSERT = f"{_CATALOG_INSERT} AND can_substitute_run(lims_run_id)"

_REASON_LEN = (
    "(reason IS NULL OR (char_length(btrim(reason)) BETWEEN 1 AND 1000))"
)
_REASON_LEN_REQUIRED = "(char_length(btrim(reason)) BETWEEN 1 AND 1000)"
_VOID_REASON_LEN = (
    "(void_reason IS NULL OR (char_length(btrim(void_reason)) BETWEEN 1 AND 1000))"
)


def _m0089():
    path = os.path.join(os.path.dirname(__file__), "0089_register_schema_catalog.py")
    spec = importlib.util.spec_from_file_location("_m0089_for_0117", path)
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
                WHERE physical_name = 'instrument_entry_slot_audits'
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
                WHERE physical_name = 'instrument_entry_slot_audits'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM schema_tables WHERE physical_name = 'instrument_entry_slot_audits'"
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM schema_columns
            WHERE physical_name = 'void_reason'
              AND table_id IN (
                  SELECT id FROM schema_tables
                  WHERE physical_name = 'instrument_maintenance_events'
              )
            """
        )
    )


# current_setting(..., true) returns '' when unset. 0003's COALESCE never
# saw NULL because the cast threw first. Treat blank like NULL.
_CURRENT_USER_ID_FN = """
CREATE OR REPLACE FUNCTION public.current_user_id()
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN COALESCE(
        NULLIF(current_setting('app.current_user_id', true), '')::UUID,
        '00000000-0000-0000-0000-000000000000'::UUID
    );
END;
$$;
"""

_0003_CURRENT_USER_ID_FN = """
CREATE OR REPLACE FUNCTION public.current_user_id()
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN COALESCE(
        current_setting('app.current_user_id', true)::UUID,
        '00000000-0000-0000-0000-000000000000'::UUID
    );
END;
$$;
"""

# session_user is the login role. SECURITY DEFINER does not change it.
# Production connects as lims_app and never SET ROLE, so current_setting('role')
# is 'none'. Skip only pinned maintenance roles (and superuser logins used
# by tests). Enforce when session_user is lims_app or SET ROLE lims_app.
_SKIP_GUARD_FN = f"""
CREATE OR REPLACE FUNCTION public.skip_app_row_guard()
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF session_user = 'lims_app'
       OR current_setting('role', true) = 'lims_app' THEN
        RETURN FALSE;
    END IF;
    IF session_user = ANY (
        ARRAY[{", ".join(repr(n) for n in MAINTENANCE_SESSION_ROLES)}]::name[]
    ) THEN
        RETURN TRUE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles r
         WHERE r.rolname = session_user AND r.rolsuper
    );
END;
$$;
"""

# 0116 behavior: no skip. Manager check + void_reason always run.
_VOID_FN = """
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

_0116_VOID_FN = """
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

_CAN_SUBSTITUTE_FN = """
CREATE OR REPLACE FUNCTION public.can_substitute_run(run_id uuid)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.is_lab_manager_or_admin() THEN
        RETURN TRUE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM public.lims_runs r
         WHERE r.id = run_id
           AND r.created_by = public.current_user_id()
    );
END;
$$;
"""

_SUBSTITUTE_INSERT_FN = """
CREATE OR REPLACE FUNCTION public.refuse_run_type_substitution()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF public.can_substitute_run(NEW.lims_run_id) THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'substitute_not_own_run'
        USING ERRCODE = '42501';
END;
$$;
"""

_SUBSTITUTE_APPLY_FN = """
CREATE OR REPLACE FUNCTION public.refuse_run_type_apply()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF NEW.instrument_type_id IS NOT DISTINCT FROM OLD.instrument_type_id THEN
        RETURN NEW;
    END IF;
    IF public.is_lab_manager_or_admin() THEN
        RETURN NEW;
    END IF;
    IF OLD.created_by = public.current_user_id() THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'substitute_not_own_run'
        USING ERRCODE = '42501';
END;
$$;
"""

_CANCEL_AFTER_IMPORT_FN = """
CREATE OR REPLACE FUNCTION public.refuse_cancel_after_import()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status
       AND NEW.status = 'canceled'
       AND EXISTS (
            SELECT 1 FROM public.lims_run_imports i
             WHERE i.lims_run_id = NEW.id
       )
    THEN
        RAISE EXCEPTION 'run_has_imported_data'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
"""

_IMPORT_ROW_IMMUTABLE_FN = """
CREATE OR REPLACE FUNCTION public.refuse_imported_row_mutate()
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
    RAISE EXCEPTION 'imported_row_immutable'
        USING ERRCODE = '42501';
END;
$$;
"""

_CREATED_BY_IMMUTABLE_FN = """
CREATE OR REPLACE FUNCTION public.refuse_run_created_by_mutate()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF public.skip_app_row_guard() THEN
        RETURN NEW;
    END IF;
    IF NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION 'run_created_by_immutable'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$;
"""


def _install_fn(sql: str, name: str) -> None:
    op.execute(sql)
    op.execute(f"ALTER FUNCTION public.{name}() SECURITY DEFINER")
    op.execute(f"ALTER FUNCTION public.{name}() SET search_path = pg_catalog, public")
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.{name}() FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION public.{name}() TO lims_app")


def _refuse_bad_reasons(conn) -> None:
    """Abort upgrade with table+count rather than a bare CHECK failure.

    Pre-existing whitespace-only or over-length reasons would otherwise
    fail ADD CONSTRAINT with no row counts. Chosen over NOT VALID: a
    lab row that already violates the rule must be fixed before 0117
    proceeds, not left unvalidated.
    """
    checks = (
        (
            "instrument_maintenance_events",
            "void_reason",
            "void_reason IS NOT NULL AND NOT (char_length(btrim(void_reason)) BETWEEN 1 AND 1000)",
        ),
        (
            "instrument_schedule_audits",
            "reason",
            "reason IS NOT NULL AND NOT (char_length(btrim(reason)) BETWEEN 1 AND 1000)",
        ),
        (
            "lims_run_type_substitutions",
            "reason",
            "NOT (char_length(btrim(reason)) BETWEEN 1 AND 1000)",
        ),
        (
            "instrument_template_inactivations",
            "reason",
            "NOT (char_length(btrim(reason)) BETWEEN 1 AND 1000)",
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
        raise RuntimeError(
            "0117 refuses CHECK: " + ", ".join(bad)
        )


def upgrade() -> None:
    uuid_t = postgresql.UUID(as_uuid=True)
    _refuse_bad_reasons(op.get_bind())

    op.add_column(
        "instrument_maintenance_events",
        sa.Column("void_reason", sa.Text(), nullable=True),
    )
    op.execute(
        "ALTER TABLE instrument_maintenance_events "
        "DROP CONSTRAINT IF EXISTS ck_instrument_events_void_reason"
    )
    op.execute(
        "ALTER TABLE instrument_maintenance_events "
        f"ADD CONSTRAINT ck_instrument_events_void_reason CHECK ({_VOID_REASON_LEN})"
    )
    op.execute(
        "ALTER TABLE instrument_schedule_audits "
        "DROP CONSTRAINT IF EXISTS ck_instrument_schedule_audits_reason"
    )
    op.execute(
        "ALTER TABLE instrument_schedule_audits "
        f"ADD CONSTRAINT ck_instrument_schedule_audits_reason CHECK ({_REASON_LEN})"
    )
    op.execute(
        "ALTER TABLE lims_run_type_substitutions "
        "DROP CONSTRAINT IF EXISTS ck_lims_run_type_substitutions_reason"
    )
    op.execute(
        "ALTER TABLE lims_run_type_substitutions "
        f"ADD CONSTRAINT ck_lims_run_type_substitutions_reason "
        f"CHECK ({_REASON_LEN_REQUIRED})"
    )
    op.execute(
        "ALTER TABLE instrument_template_inactivations "
        "DROP CONSTRAINT IF EXISTS ck_instrument_template_inactivations_reason"
    )
    op.execute(
        "ALTER TABLE instrument_template_inactivations "
        f"ADD CONSTRAINT ck_instrument_template_inactivations_reason "
        f"CHECK ({_REASON_LEN_REQUIRED})"
    )

    op.create_table(
        "instrument_entry_slot_audits",
        sa.Column(
            "id",
            uuid_t,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "entry_id",
            uuid_t,
            sa.ForeignKey("entries.id"),
            nullable=False,
        ),
        sa.Column("slot_key", sa.String(64), nullable=False),
        sa.Column(
            "previous_instrument_type_id",
            uuid_t,
            sa.ForeignKey("list_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "new_instrument_type_id",
            uuid_t,
            sa.ForeignKey("list_entries.id"),
            nullable=True,
        ),
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
        "ix_instrument_entry_slot_audits_entry_id",
        "instrument_entry_slot_audits",
        ["entry_id"],
    )
    op.execute("GRANT SELECT, INSERT ON instrument_entry_slot_audits TO lims_app")
    op.execute("REVOKE UPDATE ON instrument_entry_slot_audits FROM lims_app")
    op.execute("REVOKE DELETE ON instrument_entry_slot_audits FROM lims_app")
    op.execute("ALTER TABLE instrument_entry_slot_audits ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY instrument_entry_slot_audits_select "
        "ON instrument_entry_slot_audits FOR SELECT "
        f"USING ({_CATALOG_POLICY})"
    )
    op.execute(
        "CREATE POLICY instrument_entry_slot_audits_insert "
        "ON instrument_entry_slot_audits FOR INSERT "
        f"WITH CHECK ({_CATALOG_INSERT})"
    )
    op.execute("ALTER TABLE instrument_entry_slot_audits FORCE ROW LEVEL SECURITY")
    _register()
    _register_new_columns()

    op.execute(_CURRENT_USER_ID_FN)
    op.execute("ALTER FUNCTION public.current_user_id() SECURITY DEFINER")
    op.execute(
        "ALTER FUNCTION public.current_user_id() "
        "SET search_path = pg_catalog, public"
    )
    op.execute("GRANT EXECUTE ON FUNCTION public.current_user_id() TO lims_app")
    _install_fn(_SKIP_GUARD_FN, "skip_app_row_guard")
    _install_fn(_VOID_FN, "refuse_void_only_passing_event")
    op.execute(
        "DROP TRIGGER IF EXISTS instrument_events_refuse_only_passing_void "
        "ON instrument_maintenance_events"
    )
    op.execute(
        "CREATE TRIGGER instrument_events_refuse_only_passing_void "
        "BEFORE UPDATE ON instrument_maintenance_events "
        "FOR EACH ROW EXECUTE FUNCTION public.refuse_void_only_passing_event()"
    )

    op.execute(_CAN_SUBSTITUTE_FN)
    op.execute("ALTER FUNCTION public.can_substitute_run(uuid) SECURITY DEFINER")
    op.execute(
        "ALTER FUNCTION public.can_substitute_run(uuid) "
        "SET search_path = pg_catalog, public"
    )
    op.execute("REVOKE EXECUTE ON FUNCTION public.can_substitute_run(uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.can_substitute_run(uuid) TO lims_app")
    _install_fn(_SUBSTITUTE_INSERT_FN, "refuse_run_type_substitution")
    op.execute(
        "DROP TRIGGER IF EXISTS lims_run_type_substitutions_refuse_not_own "
        "ON lims_run_type_substitutions"
    )
    op.execute(
        "CREATE TRIGGER lims_run_type_substitutions_refuse_not_own "
        "BEFORE INSERT ON lims_run_type_substitutions "
        "FOR EACH ROW EXECUTE FUNCTION public.refuse_run_type_substitution()"
    )
    op.execute("DROP POLICY IF EXISTS lims_run_type_substitutions_insert ON lims_run_type_substitutions")
    op.execute(
        "CREATE POLICY lims_run_type_substitutions_insert "
        "ON lims_run_type_substitutions FOR INSERT "
        f"WITH CHECK ({_SUBSTITUTION_INSERT})"
    )

    _install_fn(_SUBSTITUTE_APPLY_FN, "refuse_run_type_apply")
    op.execute("DROP TRIGGER IF EXISTS lims_runs_refuse_type_apply ON lims_runs")
    op.execute(
        "CREATE TRIGGER lims_runs_refuse_type_apply "
        "BEFORE UPDATE ON lims_runs "
        "FOR EACH ROW EXECUTE FUNCTION public.refuse_run_type_apply()"
    )

    _install_fn(_CANCEL_AFTER_IMPORT_FN, "refuse_cancel_after_import")
    op.execute("DROP TRIGGER IF EXISTS lims_runs_refuse_cancel_after_import ON lims_runs")
    op.execute(
        "CREATE TRIGGER lims_runs_refuse_cancel_after_import "
        "BEFORE UPDATE ON lims_runs "
        "FOR EACH ROW EXECUTE FUNCTION public.refuse_cancel_after_import()"
    )
    _install_fn(_CREATED_BY_IMMUTABLE_FN, "refuse_run_created_by_mutate")
    op.execute("DROP TRIGGER IF EXISTS lims_runs_refuse_created_by_mutate ON lims_runs")
    op.execute(
        "CREATE TRIGGER lims_runs_refuse_created_by_mutate "
        "BEFORE UPDATE ON lims_runs "
        "FOR EACH ROW EXECUTE FUNCTION public.refuse_run_created_by_mutate()"
    )

    # Stored import rows stay. fail_run already keeps them; this closes the
    # app-user bypass. No DELETE grants. UPDATE is also refused — there is
    # no legitimate status column on these tables in this slice.
    op.execute("GRANT SELECT, INSERT ON lims_run_imports TO lims_app")
    op.execute("GRANT SELECT, INSERT ON lims_run_data TO lims_app")
    op.execute("REVOKE UPDATE ON lims_run_imports FROM lims_app")
    op.execute("REVOKE DELETE ON lims_run_imports FROM lims_app")
    op.execute("REVOKE UPDATE ON lims_run_data FROM lims_app")
    op.execute("REVOKE DELETE ON lims_run_data FROM lims_app")
    _install_fn(_IMPORT_ROW_IMMUTABLE_FN, "refuse_imported_row_mutate")
    for table in ("lims_run_imports", "lims_run_data"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_refuse_mutate ON {table}")
        op.execute(
            f"CREATE TRIGGER {table}_refuse_mutate "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION public.refuse_imported_row_mutate()"
        )


def downgrade() -> None:
    conn = op.get_bind()
    slots = conn.exec_driver_sql(
        "SELECT count(*) FROM instrument_entry_slot_audits"
    ).scalar()
    if slots:
        raise RuntimeError(
            "0117 downgrade refuses: instrument_entry_slot_audits has rows"
        )
    voids = conn.exec_driver_sql(
        "SELECT count(*) FROM instrument_maintenance_events "
        "WHERE void_reason IS NOT NULL"
    ).scalar()
    if voids:
        raise RuntimeError(
            "0117 downgrade refuses: instrument_maintenance_events.void_reason is set"
        )

    for table in ("lims_run_imports", "lims_run_data"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_refuse_mutate ON {table}")
    op.execute("DROP FUNCTION IF EXISTS public.refuse_imported_row_mutate()")

    op.execute("DROP TRIGGER IF EXISTS lims_runs_refuse_cancel_after_import ON lims_runs")
    op.execute("DROP FUNCTION IF EXISTS public.refuse_cancel_after_import()")
    op.execute("DROP TRIGGER IF EXISTS lims_runs_refuse_created_by_mutate ON lims_runs")
    op.execute("DROP FUNCTION IF EXISTS public.refuse_run_created_by_mutate()")
    op.execute("DROP TRIGGER IF EXISTS lims_runs_refuse_type_apply ON lims_runs")
    op.execute("DROP FUNCTION IF EXISTS public.refuse_run_type_apply()")
    op.execute(
        "DROP TRIGGER IF EXISTS lims_run_type_substitutions_refuse_not_own "
        "ON lims_run_type_substitutions"
    )
    op.execute("DROP FUNCTION IF EXISTS public.refuse_run_type_substitution()")
    op.execute("DROP POLICY IF EXISTS lims_run_type_substitutions_insert ON lims_run_type_substitutions")
    op.execute(
        "CREATE POLICY lims_run_type_substitutions_insert "
        "ON lims_run_type_substitutions FOR INSERT "
        f"WITH CHECK ({_CATALOG_INSERT})"
    )
    op.execute("DROP FUNCTION IF EXISTS public.can_substitute_run(uuid)")

    op.execute(_0116_VOID_FN)
    op.execute("DROP FUNCTION IF EXISTS public.skip_app_row_guard()")
    op.execute(_0003_CURRENT_USER_ID_FN)
    op.execute(
        "DROP TRIGGER IF EXISTS instrument_events_refuse_only_passing_void "
        "ON instrument_maintenance_events"
    )
    op.execute(
        "CREATE TRIGGER instrument_events_refuse_only_passing_void "
        "BEFORE UPDATE ON instrument_maintenance_events "
        "FOR EACH ROW EXECUTE FUNCTION public.refuse_void_only_passing_event()"
    )

    _unregister()
    op.drop_index(
        "ix_instrument_entry_slot_audits_entry_id",
        table_name="instrument_entry_slot_audits",
    )
    op.drop_table("instrument_entry_slot_audits")

    op.execute(
        "ALTER TABLE instrument_template_inactivations "
        "DROP CONSTRAINT IF EXISTS ck_instrument_template_inactivations_reason"
    )
    op.execute(
        "ALTER TABLE lims_run_type_substitutions "
        "DROP CONSTRAINT IF EXISTS ck_lims_run_type_substitutions_reason"
    )
    op.execute(
        "ALTER TABLE instrument_schedule_audits "
        "DROP CONSTRAINT IF EXISTS ck_instrument_schedule_audits_reason"
    )
    op.execute(
        "ALTER TABLE instrument_maintenance_events "
        "DROP CONSTRAINT IF EXISTS ck_instrument_events_void_reason"
    )
    op.drop_column("instrument_maintenance_events", "void_reason")
