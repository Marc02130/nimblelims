"""Create the same Postgres roles as ``db/zz-roles.sh``.

Compose init runs that script as the bootstrap superuser, then Alembic
runs as non-superuser ``lims_migrate``. Pytest and CI must do the same so
the privilege snapshot can fail the session when ``lims_app`` is a
superuser or bypasses row security.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATE_ROLE = "lims_migrate"
APP_ROLE = "lims_app"
# Historical GRANT target from early migrations. NOLOGIN. Not a secret.
HISTORICAL_ROLE = "lims_user"  # pragma: allowlist secret
SCHEMA_APPLY_ROLE = "schema_apply"

def _role_login(kind: str) -> str:
    """Local testcontainer login. Not a production secret."""
    return f"pytest-{kind}"


TEST_MIGRATE_PASSWORD = _role_login("migrate")
TEST_APP_PASSWORD = _role_login("app")

SNAPSHOT = (
    Path(__file__).resolve().parents[3] / "db" / "scripts" / "uat_privilege_snapshot.sql"
)


def migrate_database_url(engine: Engine, password: str = TEST_MIGRATE_PASSWORD) -> str:
    """Connection URL for Alembic as non-superuser ``lims_migrate``."""
    return engine.url.set(
        username=MIGRATE_ROLE, password=password
    ).render_as_string(hide_password=False)


def apply_init_extensions(engine: Engine) -> None:
    """Match ``db/init.sql``. Superuser creates untrusted extensions."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS lims"))


def apply_zz_roles(
    engine: Engine,
    *,
    migrate_password: str = TEST_MIGRATE_PASSWORD,
    app_password: str = TEST_APP_PASSWORD,
) -> None:
    """Create the Compose bootstrap roles, including the historical grant target.

    The engine must be the bootstrap superuser. Flags match ``db/zz-roles.sh``.
    """
    database = engine.url.database
    if not database:
        raise RuntimeError("bootstrap roles need a database name on the engine URL")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        _ensure_login_role(
            conn,
            MIGRATE_ROLE,
            migrate_password,
            create_attrs=(
                "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT BYPASSRLS"
            ),
            alter_attrs="NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN BYPASSRLS",
        )
        _ensure_login_role(
            conn,
            APP_ROLE,
            app_password,
            create_attrs=(
                "LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT"
            ),
            alter_attrs="NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE",
        )
        _ensure_nologin_role(
            conn,
            HISTORICAL_ROLE,
            create_attrs=(
                "NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT"
            ),
            alter_attrs="NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOLOGIN",
        )
        _ensure_nologin_role(
            conn,
            SCHEMA_APPLY_ROLE,
            create_attrs=(
                "NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT"
            ),
            alter_attrs="NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOLOGIN",
        )
        conn.execute(text(f"GRANT {SCHEMA_APPLY_ROLE} TO {MIGRATE_ROLE}"))
        conn.execute(text(f'ALTER DATABASE "{database}" OWNER TO {MIGRATE_ROLE}'))
        conn.execute(text(f"ALTER SCHEMA public OWNER TO {MIGRATE_ROLE}"))
        conn.execute(text(f"ALTER SCHEMA lims OWNER TO {MIGRATE_ROLE}"))
        conn.execute(text(f'GRANT CONNECT ON DATABASE "{database}" TO {MIGRATE_ROLE}'))
        conn.execute(text(f'GRANT CONNECT ON DATABASE "{database}" TO {APP_ROLE}'))


def run_privilege_snapshot(engine: Engine) -> None:
    """Run ``db/scripts/uat_privilege_snapshot.sql``. Raises on a bad role."""
    script = SNAPSHOT.read_text(encoding="utf-8")
    select_sql, do_sql = script.split("DO $$", 1)
    with engine.connect() as conn:
        conn.execute(text(select_sql))
        conn.execute(text("DO $$" + do_sql))
        conn.commit()


def _ensure_login_role(
    conn,
    name: str,
    password: str,
    *,
    create_attrs: str,
    alter_attrs: str,
) -> None:
    exists = conn.execute(
        text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :n"),
        {"n": name},
    ).scalar()
    if exists:
        conn.execute(text(f"ALTER ROLE {name} {alter_attrs}"))
        conn.execute(text(f"ALTER ROLE {name} PASSWORD :pwd"), {"pwd": password})
        return
    conn.execute(
        text(f"CREATE ROLE {name} {create_attrs} PASSWORD :pwd"),
        {"pwd": password},
    )


def _ensure_nologin_role(
    conn,
    name: str,
    *,
    create_attrs: str,
    alter_attrs: str,
) -> None:
    exists = conn.execute(
        text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :n"),
        {"n": name},
    ).scalar()
    if exists:
        conn.execute(text(f"ALTER ROLE {name} {alter_attrs}"))
        return
    conn.execute(text(f"CREATE ROLE {name} {create_attrs}"))
