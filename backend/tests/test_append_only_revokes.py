"""Canonical append-only REVOKEs match migrations and survive ensure."""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import text

from db.append_only_tables import APPEND_ONLY_REVOKES

VERSIONS = Path(__file__).resolve().parents[1] / "db" / "migrations" / "versions"
_REVOKE = re.compile(
    r"REVOKE\s+((?:INSERT|UPDATE|DELETE)(?:\s*,\s*(?:INSERT|UPDATE|DELETE))*)"
    r"\s+ON(?:\s+TABLE)?\s+\{?['\"]?(\w+)",
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


def _revokes_in_migrations() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in VERSIONS.glob("*.py"):
        text_src = path.read_text()
        for match in _REVOKE.finditer(text_src):
            privileges = {p.strip().upper() for p in match.group(1).split(",")}
            table = match.group(2)
            if table == "table":
                loop_privs = set()
                for line in text_src.splitlines():
                    if "REVOKE" not in line or "{table}" not in line:
                        continue
                    for privilege in ("INSERT", "UPDATE", "DELETE"):
                        if privilege in line:
                            loop_privs.add(privilege)
                for loop_table in _loop_tables(text_src):
                    found.setdefault(loop_table, set()).update(loop_privs or {"DELETE"})
                continue
            found.setdefault(table, set()).update(privileges)
    return found


def test_canonical_list_matches_migration_revokes():
    found = _revokes_in_migrations()
    for table, privileges in APPEND_ONLY_REVOKES.items():
        assert table in found, table
        assert privileges <= found[table], (table, privileges, found[table])
    extras = {
        name
        for name in found
        if name not in APPEND_ONLY_REVOKES
        and name not in {"table", "SCHEMA"}
        and ("_" in name or name in {"vendors", "reagents"})
    }
    assert extras == set(), extras


def test_ensure_script_reapplies_revokes(migrated_engine, monkeypatch):
    from app.core.bootstrap_roles import TEST_APP_PASSWORD
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
        for table, privileges in APPEND_ONLY_REVOKES.items():
            if table not in existing:
                continue
            for privilege in privileges:
                allowed = conn.execute(
                    text("SELECT has_table_privilege('lims_app', :t, :p)"),
                    {"t": table, "p": privilege},
                ).scalar()
                assert allowed is False, f"{table} {privilege}"
