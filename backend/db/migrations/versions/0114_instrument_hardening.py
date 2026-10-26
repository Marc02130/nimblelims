"""E1 instrument hardening: audits, retired type defaults, schedule roles.

Revision ID: 0114_instrument_hardening
Revises: 0113_maintenance_tracked

Revision id stays at or under 32 characters because
``alembic_version.version_num`` is varchar(32).

No new tables. Nothing is dropped. No DELETE grants.
"""

from __future__ import annotations

from alembic import op

revision = "0114_instrument_hardening"
down_revision = "0113_maintenance_tracked"
branch_labels = None
depends_on = None

_CONFIG_EDIT = """EXISTS (
    SELECT 1 FROM users u
    JOIN role_permissions rp ON rp.role_id = u.role_id
    JOIN permissions p ON p.id = rp.permission_id
    WHERE u.id = current_user_id() AND p.name = 'config:edit' AND p.active = true
)"""
_CATALOG_POLICY = f"is_admin() OR has_experiment_access() OR {_CONFIG_EDIT}"
_AUDIT_INSERT = f"is_admin() OR {_CONFIG_EDIT}"


def upgrade() -> None:
    op.execute("REVOKE UPDATE ON instrument_maintenance_audits FROM lims_app")
    op.execute("REVOKE INSERT, UPDATE ON instrument_type_defaults FROM lims_app")
    op.execute("REVOKE DELETE ON instrument_maintenance_audits FROM lims_app")
    op.execute("REVOKE DELETE ON instrument_type_defaults FROM lims_app")
    op.execute("REVOKE DELETE ON instrument_maintenance_schedules FROM lims_app")
    op.execute(
        "COMMENT ON TABLE instrument_type_defaults IS "
        "'Retired. Maintenance tracking is per instrument. "
        "Rows are kept as history. Unused.'"
    )

    op.execute("DROP POLICY IF EXISTS instrument_maintenance_audits_access ON instrument_maintenance_audits")
    op.execute(
        "CREATE POLICY instrument_maintenance_audits_select "
        "ON instrument_maintenance_audits FOR SELECT "
        f"USING ({_CATALOG_POLICY})"
    )
    op.execute(
        "CREATE POLICY instrument_maintenance_audits_insert "
        "ON instrument_maintenance_audits FOR INSERT "
        f"WITH CHECK ({_AUDIT_INSERT})"
    )

    op.execute("DROP POLICY IF EXISTS instrument_type_defaults_access ON instrument_type_defaults")
    op.execute(
        "CREATE POLICY instrument_type_defaults_select "
        "ON instrument_type_defaults FOR SELECT "
        f"USING ({_CATALOG_POLICY})"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION is_lab_manager_or_admin()
        RETURNS BOOLEAN AS $$
        DECLARE
            user_role_name TEXT;
        BEGIN
            SELECT r.name INTO user_role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = current_user_id();
            RETURN user_role_name IN ('Administrator', 'Lab Manager');
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )
    op.execute("GRANT EXECUTE ON FUNCTION is_lab_manager_or_admin() TO lims_app")

    op.execute(
        "DROP POLICY IF EXISTS instrument_maintenance_schedules_access "
        "ON instrument_maintenance_schedules"
    )
    op.execute(
        "CREATE POLICY instrument_maintenance_schedules_select "
        "ON instrument_maintenance_schedules FOR SELECT "
        f"USING ({_CATALOG_POLICY})"
    )
    op.execute(
        "CREATE POLICY instrument_maintenance_schedules_update "
        "ON instrument_maintenance_schedules FOR UPDATE "
        f"USING ({_CATALOG_POLICY}) WITH CHECK ({_CATALOG_POLICY})"
    )
    op.execute(
        "CREATE POLICY instrument_maintenance_schedules_insert "
        "ON instrument_maintenance_schedules FOR INSERT "
        "WITH CHECK (is_lab_manager_or_admin())"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION instrument_maintenance_schedules_guard()
        RETURNS trigger AS $$
        DECLARE
            derived_last date;
        BEGIN
            IF is_lab_manager_or_admin() THEN
                RETURN NEW;
            END IF;
            IF NEW.instrument_id IS DISTINCT FROM OLD.instrument_id
               OR NEW.kind_id IS DISTINCT FROM OLD.kind_id
               OR NEW.interval_days IS DISTINCT FROM OLD.interval_days
               OR NEW.service_vendor_id IS DISTINCT FROM OLD.service_vendor_id
               OR NEW.active IS DISTINCT FROM OLD.active THEN
                RAISE EXCEPTION 'instrument_maintenance_schedules_guard'
                    USING ERRCODE = '42501';
            END IF;
            SELECT e.performed_on
              INTO derived_last
              FROM instrument_maintenance_events e
             WHERE e.schedule_id = NEW.id
               AND e.active IS TRUE
               AND e.passed IS TRUE
             ORDER BY e.performed_on DESC, e.created_at DESC
             LIMIT 1;
            IF derived_last IS NULL THEN
                IF NEW.last_done IS NOT NULL OR NEW.next_due IS NOT NULL THEN
                    RAISE EXCEPTION 'instrument_maintenance_schedules_guard'
                        USING ERRCODE = '42501';
                END IF;
                RETURN NEW;
            END IF;
            IF OLD.next_due IS NULL THEN
                IF NEW.last_done IS DISTINCT FROM OLD.last_done
                   OR NEW.next_due IS DISTINCT FROM OLD.next_due THEN
                    RAISE EXCEPTION 'instrument_maintenance_schedules_guard'
                        USING ERRCODE = '42501';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.last_done IS DISTINCT FROM derived_last
               OR NEW.next_due IS DISTINCT FROM (derived_last + NEW.interval_days) THEN
                RAISE EXCEPTION 'instrument_maintenance_schedules_guard'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )
    op.execute(
        "DROP TRIGGER IF EXISTS instrument_maintenance_schedules_guard "
        "ON instrument_maintenance_schedules"
    )
    op.execute(
        """
        CREATE TRIGGER instrument_maintenance_schedules_guard
        BEFORE UPDATE ON instrument_maintenance_schedules
        FOR EACH ROW
        EXECUTE FUNCTION instrument_maintenance_schedules_guard()
        """
    )

    op.execute(
        "ALTER TABLE lims_run_imports ALTER COLUMN parser_id DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE lims_run_imports DROP CONSTRAINT IF EXISTS ck_lims_run_imports_source_xor"
    )
    op.execute(
        """
        ALTER TABLE lims_run_imports
        ADD CONSTRAINT ck_lims_run_imports_source_xor CHECK (
            (instrument_id IS NOT NULL AND cro_source_id IS NULL AND parser_id IS NOT NULL)
            OR (instrument_id IS NULL AND cro_source_id IS NOT NULL AND parser_id IS NOT NULL)
            OR (
                instrument_id IS NULL
                AND cro_source_id IS NULL
                AND parser_id IS NULL
                AND filename = 'admin_override'
            )
        )
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    leftover = conn.exec_driver_sql(
        "SELECT count(*) FROM lims_run_imports WHERE filename = 'admin_override'"
    ).scalar()
    if leftover:
        raise RuntimeError(
            "0114 downgrade refuses: admin_override import rows exist"
        )
    op.execute(
        "ALTER TABLE lims_run_imports DROP CONSTRAINT IF EXISTS ck_lims_run_imports_source_xor"
    )
    op.execute(
        """
        ALTER TABLE lims_run_imports
        ADD CONSTRAINT ck_lims_run_imports_source_xor CHECK (
            (instrument_id IS NOT NULL AND cro_source_id IS NULL)
            OR (instrument_id IS NULL AND cro_source_id IS NOT NULL)
        )
        """
    )
    op.execute(
        "ALTER TABLE lims_run_imports ALTER COLUMN parser_id SET NOT NULL"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS instrument_maintenance_schedules_guard "
        "ON instrument_maintenance_schedules"
    )
    op.execute("DROP FUNCTION IF EXISTS instrument_maintenance_schedules_guard()")
    op.execute(
        "DROP POLICY IF EXISTS instrument_maintenance_schedules_select "
        "ON instrument_maintenance_schedules"
    )
    op.execute(
        "DROP POLICY IF EXISTS instrument_maintenance_schedules_update "
        "ON instrument_maintenance_schedules"
    )
    op.execute(
        "DROP POLICY IF EXISTS instrument_maintenance_schedules_insert "
        "ON instrument_maintenance_schedules"
    )
    op.execute(
        "CREATE POLICY instrument_maintenance_schedules_access "
        "ON instrument_maintenance_schedules FOR ALL "
        f"USING ({_CATALOG_POLICY}) WITH CHECK ({_CATALOG_POLICY})"
    )
    op.execute("DROP FUNCTION IF EXISTS is_lab_manager_or_admin()")
    op.execute("DROP POLICY IF EXISTS instrument_type_defaults_select ON instrument_type_defaults")
    op.execute(
        "CREATE POLICY instrument_type_defaults_access ON instrument_type_defaults FOR ALL "
        f"USING ({_CATALOG_POLICY}) WITH CHECK ({_CATALOG_POLICY})"
    )
    op.execute(
        "DROP POLICY IF EXISTS instrument_maintenance_audits_select "
        "ON instrument_maintenance_audits"
    )
    op.execute(
        "DROP POLICY IF EXISTS instrument_maintenance_audits_insert "
        "ON instrument_maintenance_audits"
    )
    op.execute(
        "CREATE POLICY instrument_maintenance_audits_access "
        "ON instrument_maintenance_audits FOR ALL "
        f"USING ({_CATALOG_POLICY}) WITH CHECK ({_CATALOG_POLICY})"
    )
    op.execute("COMMENT ON TABLE instrument_type_defaults IS NULL")
    op.execute("GRANT INSERT, UPDATE ON instrument_type_defaults TO lims_app")
    op.execute("GRANT UPDATE ON instrument_maintenance_audits TO lims_app")
