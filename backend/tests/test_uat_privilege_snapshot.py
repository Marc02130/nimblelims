"""The UAT privilege snapshot refuses a lims_app role that bypasses RLS."""
from pathlib import Path

from sqlalchemy import text

SNAPSHOT = (
    Path(__file__).resolve().parents[2] / "db" / "scripts" / "uat_privilege_snapshot.sql"
)


def test_snapshot_requires_lims_app_nosuperuser_and_nobypassrls(migrated_engine):
    script = SNAPSHOT.read_text()
    assert "rolbypassrls" in script
    assert "rolsuper" in script
    select_sql, do_sql = script.split("DO $$", 1)
    with migrated_engine.connect() as conn:
        conn.execute(text(select_sql))
        conn.execute(text("DO $$" + do_sql))
        row = conn.execute(
            text(
                """
                SELECT rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = 'lims_app'
                """
            )
        ).one()
        assert row[0] is False
        assert row[1] is False
        owner = conn.execute(
            text(
                """
                SELECT r.rolname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_roles r ON r.oid = c.relowner
                WHERE n.nspname = 'public' AND c.relname = 'samples'
                """
            )
        ).scalar()
        assert owner == "lims_migrate"
        migrate = conn.execute(
            text(
                """
                SELECT rolcanlogin, rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = 'lims_migrate'
                """
            )
        ).one()
        assert migrate[0] is True
        assert migrate[1] is False
        assert migrate[2] is True
        ddl_owner = conn.execute(
            text(
                """
                SELECT r.rolname
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                JOIN pg_roles r ON r.oid = p.proowner
                WHERE n.nspname = 'public'
                  AND p.proname = 'ui_schema_create_table'
                """
            )
        ).scalar()
        assert ddl_owner == "lims_migrate"
        ddl_flags = conn.execute(
            text(
                """
                SELECT rolsuper, rolbypassrls
                FROM pg_roles
                WHERE rolname = 'schema_apply'
                """
            )
        ).one()
        assert ddl_flags[0] is False
        assert ddl_flags[1] is False
