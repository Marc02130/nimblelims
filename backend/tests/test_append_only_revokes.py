"""Canonical append-only REVOKEs match migrations and survive ensure."""
from __future__ import annotations

import os
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from db.append_only_tables import APPEND_ONLY_REVOKES, MAINTENANCE_SESSION_ROLES

VERSIONS = Path(__file__).resolve().parents[1] / "db" / "migrations" / "versions"

# Privileges 0118 would REVOKE from the historical role by importing the live
# map. A later list change needs a new migration; update this pin then.
APPEND_ONLY_REVOKES_AT_0118 = {
    "lab_settings": frozenset({"DELETE"}),
    "result_acceptances": frozenset({"DELETE"}),
    "vendors": frozenset({"DELETE"}),
    "reagents": frozenset({"DELETE"}),
    "reagent_vendors": frozenset({"DELETE"}),
    "reagent_lots": frozenset({"DELETE"}),
    "reagent_uses": frozenset({"DELETE"}),
    "instruments": frozenset({"DELETE"}),
    "cro_sources": frozenset({"DELETE"}),
    "instrument_maintenance_schedules": frozenset({"DELETE"}),
    "instrument_maintenance_events": frozenset({"DELETE"}),
    "instrument_downtime": frozenset({"DELETE"}),
    "instrument_uses": frozenset({"DELETE"}),
    "instrument_types_legacy": frozenset({"INSERT", "UPDATE", "DELETE"}),
    "instrument_type_defaults": frozenset({"INSERT", "UPDATE", "DELETE"}),
    "instrument_maintenance_audits": frozenset({"UPDATE", "DELETE"}),
    "instrument_schedule_audits": frozenset({"UPDATE", "DELETE"}),
    "lims_run_type_substitutions": frozenset({"UPDATE", "DELETE"}),
    "instrument_template_inactivations": frozenset({"UPDATE", "DELETE"}),
    "instrument_entry_slot_audits": frozenset({"UPDATE", "DELETE"}),
    "lims_run_imports": frozenset({"UPDATE", "DELETE"}),
    "lims_run_data": frozenset({"UPDATE", "DELETE"}),
}

_PRIV = r"(?:INSERT|UPDATE|DELETE)"
_REVOKE = re.compile(
    r"REVOKE\s+"
    rf"({_PRIV}(?:\s*,\s*{_PRIV})*)"
    r"\s+ON(?:\s+TABLE)?(?:\s+ONLY)?"
    r"\s+(.+?)"
    r"\s+FROM\s+lims_app\b",
    re.IGNORECASE,
)


def _loop_tables(text_src: str) -> set[str]:
    names = set(re.findall(r'_secure\("(\w+)"', text_src))
    names.update(re.findall(r'_lock\("(\w+)"', text_src))
    block = re.search(r"REAGENT_TABLES\s*=\s*\((.*?)\)", text_src, re.S)
    if block:
        names.update(re.findall(r'"(\w+)"', block.group(1)))
    listed = re.search(
        r"for table in \(\s*((?:\"[^\"]+\",\s*)+\"[^\"]+\",?)\s*\)",
        text_src,
    )
    if listed:
        names.update(re.findall(r'"(\w+)"', listed.group(1)))
    return names


def _table_name(raw: str) -> str:
    name = raw.strip().strip("\"'`")
    if "." in name:
        name = name.rsplit(".", 1)[-1]
    name = name.strip("\"'`{}")
    if not re.fullmatch(r"\w+", name):
        return ""
    return name


def _revokes_in_migrations() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in VERSIONS.glob("*.py"):
        text_src = path.read_text()
        for match in _REVOKE.finditer(text_src):
            privileges = {p.strip().upper() for p in match.group(1).split(",")}
            targets = [part.strip() for part in match.group(2).split(",") if part.strip()]
            for raw in targets:
                table = _table_name(raw)
                if not table:
                    continue
                if table == "table":
                    loop_privs = set()
                    for line in text_src.splitlines():
                        if "REVOKE" not in line or "{table}" not in line:
                            continue
                        if not re.search(r"FROM\s+lims_app\b", line, re.I):
                            continue
                        for privilege in ("INSERT", "UPDATE", "DELETE"):
                            if privilege in line.upper():
                                loop_privs.add(privilege)
                    assert loop_privs, f"{path.name} expanded {{table}} without I/U/D"
                    for loop_table in _loop_tables(text_src):
                        found.setdefault(loop_table, set()).update(loop_privs)
                    continue
                if table in {"SCHEMA", ""}:
                    continue
                found.setdefault(table, set()).update(privileges)
    return found


def test_canonical_list_matches_migration_revokes():
    found = _revokes_in_migrations()
    missing = []
    for table, privileges in found.items():
        needed = privileges & {"INSERT", "UPDATE", "DELETE"}
        if not needed:
            continue
        if table not in APPEND_ONLY_REVOKES:
            missing.append((table, needed))
            continue
        listed = APPEND_ONLY_REVOKES[table] & {"INSERT", "UPDATE", "DELETE"}
        assert needed == listed, (table, needed, listed)
    assert missing == [], missing
    extras = set(APPEND_ONLY_REVOKES) - set(found)
    assert extras == set(), extras


def test_0117_inlined_roles_match_maintenance_session_roles():
    text_src = (VERSIONS / "0117_e3_hardening.py").read_text()
    rendered = ", ".join(repr(name) for name in MAINTENANCE_SESSION_ROLES)
    assert f"ARRAY[{rendered}]::name[]" in text_src
    assert tuple(MAINTENANCE_SESSION_ROLES) == (
        "lims_migrate",
        "schema_apply",
        "postgres",
    )


def test_append_only_revokes_pinned_at_0118():
    text_src = (VERSIONS / "0118_e3_followups.py").read_text()
    assert "from db.append_only_tables import APPEND_ONLY_REVOKES" in text_src
    assert set(APPEND_ONLY_REVOKES_AT_0118) <= set(APPEND_ONLY_REVOKES)
    for table, privileges in APPEND_ONLY_REVOKES_AT_0118.items():
        assert APPEND_ONLY_REVOKES[table] == privileges, table


def test_ensure_script_reapplies_revokes(migrated_engine, monkeypatch):
    from app.core.bootstrap_roles import HISTORICAL_ROLE, TEST_APP_PASSWORD
    from ensure_lims_app_role import ensure_lims_app_role

    monkeypatch.setenv(
        "MIGRATE_DATABASE_URL",
        migrated_engine.url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("LIMS_APP_PASSWORD", TEST_APP_PASSWORD)
    monkeypatch.delenv("ENSURE_LIMS_APP_PASSWORD_ROTATE", raising=False)
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                "IN SCHEMA public TO lims_app"
            )
        )
        if conn.execute(
            text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :r"),
            {"r": HISTORICAL_ROLE},
        ).scalar():
            conn.execute(
                text(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                    f"IN SCHEMA public TO {HISTORICAL_ROLE}"
                )
            )
    ensure_lims_app_role()
    with migrated_engine.connect() as conn:
        existing = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname = 'public'"
                )
            ).all()
        }
        missing = set(APPEND_ONLY_REVOKES) - existing
        assert missing == set(), missing
        for table, privileges in APPEND_ONLY_REVOKES.items():
            for privilege in privileges:
                allowed = conn.execute(
                    text("SELECT has_table_privilege('lims_app', :t, :p)"),
                    {"t": table, "p": privilege},
                ).scalar()
                assert allowed is False, f"{table} {privilege}"
        if conn.execute(
            text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :r"),
            {"r": HISTORICAL_ROLE},
        ).scalar():
            for table, privileges in APPEND_ONLY_REVOKES.items():
                for privilege in privileges:
                    allowed = conn.execute(
                        text("SELECT has_table_privilege(:r, :t, :p)"),
                        {"r": HISTORICAL_ROLE, "t": table, "p": privilege},
                    ).scalar()
                    assert allowed is False, f"{HISTORICAL_ROLE} {table} {privilege}"


def test_0118_upgrade_revokes_historical_role_grants(migrated_engine):
    from app.core.bootstrap_roles import HISTORICAL_ROLE

    backend = Path(__file__).resolve().parents[1]
    url = migrated_engine.url.render_as_string(hide_password=False)
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    previous_database = os.environ.get("DATABASE_URL")
    previous_migrate = os.environ.get("MIGRATE_DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    os.environ["MIGRATE_DATABASE_URL"] = url
    sample = (
        "lab_settings",
        "instrument_maintenance_audits",
        "lims_run_imports",
        "lims_run_data",
    )
    try:
        from tests.conftest import clear_0117_downgrade_blockers

        clear_0117_downgrade_blockers(migrated_engine)
        command.downgrade(cfg, "0117_e3_hardening")
        with migrated_engine.begin() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :r"),
                {"r": HISTORICAL_ROLE},
            ).scalar()
            if not exists:
                conn.execute(
                    text(
                        f"CREATE ROLE {HISTORICAL_ROLE} NOLOGIN "
                        "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT"
                    )
                )
            existing = {
                r[0]
                for r in conn.execute(
                    text(
                        "SELECT tablename FROM pg_catalog.pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                ).all()
            }
            for table in sample:
                assert table in existing, table
                conn.execute(
                    text(f"GRANT UPDATE, DELETE ON TABLE {table} TO {HISTORICAL_ROLE}")
                )
                for privilege in ("UPDATE", "DELETE"):
                    allowed = conn.execute(
                        text("SELECT has_table_privilege(:r, :t, :p)"),
                        {"r": HISTORICAL_ROLE, "t": table, "p": privilege},
                    ).scalar()
                    assert allowed is True, f"pre-0118 {table} {privilege}"
        command.upgrade(cfg, "0118_e3_followups")
        with migrated_engine.connect() as conn:
            for table in sample:
                for privilege in APPEND_ONLY_REVOKES[table]:
                    allowed = conn.execute(
                        text("SELECT has_table_privilege(:r, :t, :p)"),
                        {"r": HISTORICAL_ROLE, "t": table, "p": privilege},
                    ).scalar()
                    assert allowed is False, f"post-0118 {table} {privilege}"
    finally:
        command.upgrade(cfg, "head")
        if previous_database is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database
        if previous_migrate is None:
            os.environ.pop("MIGRATE_DATABASE_URL", None)
        else:
            os.environ["MIGRATE_DATABASE_URL"] = previous_migrate
