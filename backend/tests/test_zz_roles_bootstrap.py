"""Pytest creates the same roles as db/zz-roles.sh before Alembic."""
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import InternalError

from app.core.bootstrap_roles import (
    APP_ROLE,
    HISTORICAL_ROLE,
    MIGRATE_ROLE,
    SCHEMA_APPLY_ROLE,
    run_privilege_snapshot,
)

ZZ_ROLES = Path(__file__).resolve().parents[2] / "db" / "zz-roles.sh"


def test_zz_roles_script_names_the_compose_roles():
    script = ZZ_ROLES.read_text(encoding="utf-8")
    assert "CREATE ROLE lims_migrate LOGIN" in script
    assert "BYPASSRLS" in script
    assert "CREATE ROLE lims_app LOGIN" in script
    assert "NOBYPASSRLS" in script
    assert f"CREATE ROLE {HISTORICAL_ROLE} NOLOGIN" in script
    assert "CREATE ROLE schema_apply NOLOGIN" in script
    assert "GRANT schema_apply TO lims_migrate" in script


def test_migrated_engine_roles_match_zz_roles(migrated_engine):
    with migrated_engine.connect() as conn:
        rows = {
            name: conn.execute(
                text(
                    """
                    SELECT rolsuper, rolbypassrls, rolcanlogin, rolcreatedb, rolcreaterole
                    FROM pg_catalog.pg_roles
                    WHERE rolname = :n
                    """
                ),
                {"n": name},
            ).one()
            for name in (MIGRATE_ROLE, APP_ROLE, HISTORICAL_ROLE, SCHEMA_APPLY_ROLE)
        }
    migrate = rows[MIGRATE_ROLE]
    assert migrate == (False, True, True, False, False)
    assert rows[APP_ROLE] == (False, False, True, False, False)
    assert rows[HISTORICAL_ROLE] == (False, False, False, False, False)
    assert rows[SCHEMA_APPLY_ROLE] == (False, False, False, False, False)


def test_privilege_snapshot_fails_when_lims_app_bypasses_rls(migrated_engine):
    with migrated_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ALTER ROLE lims_app BYPASSRLS"))
    try:
        with pytest.raises(InternalError):
            run_privilege_snapshot(migrated_engine)
    finally:
        with migrated_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("ALTER ROLE lims_app NOBYPASSRLS"))
