#!/usr/bin/env python3
"""
P0d / Q1 Option C: idempotent ensure of runtime DB role `lims_app`.

- Connects as owner/migrator (MIGRATE_DATABASE_URL or DATABASE_URL fallback).
- If role missing: CREATE LOGIN with LIMS_APP_PASSWORD + grants.
- If role exists: ensure grants only — does NOT alter password (unless
  ENSURE_LIMS_APP_PASSWORD_ROTATE=true).

Run after Alembic migrations, before uvicorn (see start.sh).
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text


APP_ROLE = "lims_app"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _owner_url() -> str:
    return (
        os.getenv("MIGRATE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://lims_user:lims_password@localhost:5432/lims_db"
    )


def _app_password() -> str:
    pwd = (os.getenv("LIMS_APP_PASSWORD") or "").strip()
    if pwd:
        return pwd
    env = (os.getenv("ENVIRONMENT") or "development").strip().lower()
    if env in ("development", "dev", "test") and _env_flag("ALLOW_INSECURE_DEFAULTS"):
        return "lims_app_password"
    raise SystemExit(
        "FATAL: LIMS_APP_PASSWORD is required to ensure lims_app role "
        "(or set ENVIRONMENT=development|test and ALLOW_INSECURE_DEFAULTS=true "
        "for a local default)."
    )


def ensure_lims_app_role() -> None:
    owner_url = _owner_url()
    password = _app_password()
    rotate = _env_flag("ENSURE_LIMS_APP_PASSWORD_ROTATE")

    # Hide credentials in logs
    host_part = owner_url.split("@")[-1] if "@" in owner_url else "hidden"
    print(f"Ensuring role {APP_ROLE} via owner connection ({host_part})...", flush=True)

    engine = create_engine(owner_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :r"),
            {"r": APP_ROLE},
        ).scalar()

        if not exists:
            # CREATE ROLE does not accept bind params for the role name in all drivers;
            # password is passed as a bound parameter via psycopg2 escaping.
            conn.execute(
                text(f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD :pwd NOSUPERUSER NOCREATEDB NOCREATEROLE"),
                {"pwd": password},
            )
            print(f"Created role {APP_ROLE}", flush=True)
        else:
            print(f"Role {APP_ROLE} already exists", flush=True)
            if rotate:
                conn.execute(
                    text(f"ALTER ROLE {APP_ROLE} PASSWORD :pwd"),
                    {"pwd": password},
                )
                print(f"Rotated password for {APP_ROLE} (ENSURE_LIMS_APP_PASSWORD_ROTATE)", flush=True)

        # Database connect
        dbname = conn.execute(text("SELECT current_database()")).scalar()
        conn.execute(text(f"GRANT CONNECT ON DATABASE {dbname} TO {APP_ROLE}"))

        # Schema + objects
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}"))
        conn.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}"
            )
        )
        conn.execute(
            text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")
        )
        conn.execute(
            text(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {APP_ROLE}")
        )

        # Future objects created by table owner (typical Docker lims_user)
        for grantor in ("lims_user", "CURRENT_USER"):
            try:
                prefix = (
                    "ALTER DEFAULT PRIVILEGES FOR ROLE lims_user IN SCHEMA public"
                    if grantor == "lims_user"
                    else "ALTER DEFAULT PRIVILEGES IN SCHEMA public"
                )
                conn.execute(
                    text(
                        f"{prefix} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
                    )
                )
                conn.execute(
                    text(
                        f"{prefix} GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}"
                    )
                )
            except Exception as exc:
                # lims_user may not exist outside Docker; CURRENT_USER path still applies
                print(f"Note: default privileges ({grantor}): {exc}", flush=True)

    engine.dispose()
    print(f"Role {APP_ROLE} grants ensured.", flush=True)


if __name__ == "__main__":
    try:
        ensure_lims_app_role()
    except SystemExit:
        raise
    except Exception as e:
        print(f"FATAL: ensure_lims_app_role failed: {e}", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)
