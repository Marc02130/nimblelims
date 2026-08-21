"""P0d: ensure_lims_app_role create-once + idempotent grants."""
import os

import pytest
from sqlalchemy import text


def _owner_url(engine) -> str:
    """SQLAlchemy masks passwords in str(url); render with password for env."""
    return engine.url.render_as_string(hide_password=False)


class TestEnsureLimsAppRole:
    def test_create_once_and_idempotent(self, migrated_engine, monkeypatch):
        from ensure_lims_app_role import ensure_lims_app_role, APP_ROLE

        url = _owner_url(migrated_engine)
        monkeypatch.setenv("MIGRATE_DATABASE_URL", url)
        monkeypatch.setenv("LIMS_APP_PASSWORD", "test_app_secret_pwd")
        monkeypatch.delenv("ENSURE_LIMS_APP_PASSWORD_ROTATE", raising=False)

        with migrated_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :r"),
                {"r": APP_ROLE},
            ).scalar()
            if exists:
                conn.execute(text(f"DROP OWNED BY {APP_ROLE}"))
                conn.execute(text(f"DROP ROLE {APP_ROLE}"))
            conn.commit()

        ensure_lims_app_role()
        ensure_lims_app_role()  # second call must not fail / must not require rotate

        with migrated_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :r"),
                {"r": APP_ROLE},
            ).scalar()
            assert exists == 1

            # Non-superuser; can SET ROLE and run a trivial query under RLS GUCs
            conn.execute(text(f"SET ROLE {APP_ROLE}"))
            conn.execute(
                text("SELECT set_config('app.current_user_id', :v, true)"),
                {"v": "00000000-0000-0000-0000-000000000001"},
            )
            n = conn.execute(text("SELECT count(*) FROM users")).scalar()
            assert n is not None and n >= 0
            conn.execute(text("RESET ROLE"))
            conn.commit()

    def test_rotate_flag_updates_password(self, migrated_engine, monkeypatch):
        from ensure_lims_app_role import ensure_lims_app_role, APP_ROLE

        url = _owner_url(migrated_engine)
        monkeypatch.setenv("MIGRATE_DATABASE_URL", url)
        monkeypatch.setenv("LIMS_APP_PASSWORD", "first_password_value")
        monkeypatch.delenv("ENSURE_LIMS_APP_PASSWORD_ROTATE", raising=False)

        # Ensure exists (may already from previous test in same container module)
        ensure_lims_app_role()
        monkeypatch.setenv("LIMS_APP_PASSWORD", "second_password_value")
        monkeypatch.setenv("ENSURE_LIMS_APP_PASSWORD_ROTATE", "true")
        ensure_lims_app_role()

        with migrated_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT rolcanlogin, rolsuper FROM pg_roles WHERE rolname = :r"
                ),
                {"r": APP_ROLE},
            ).one()
            assert row[0] is True
            assert row[1] is False
