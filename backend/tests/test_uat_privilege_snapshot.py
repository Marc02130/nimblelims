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
