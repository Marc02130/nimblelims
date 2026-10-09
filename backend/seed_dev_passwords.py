#!/usr/bin/env python3
"""Set dev/UAT seed passwords from the environment, or generate and print once.

Historical migrations 0004, 0013, and 0058 used to embed published dev
passwords (plaintext or unsalted SHA256). They now insert the locked marker
``!seed-locked`` (``app.core.dev_passwords.SEED_LOCKED``). 0061 still adds
``must_change_password`` and flags admin, lab-manager, lab-tech, and client.
It no longer contains digests or plaintext: fresh databases have no legacy
digest to rehash, and an older database still upgrades a leftover SHA256
hash on login.

This script is not a migration. Applied migrations never re-run, so an
existing database keeps its current hashes until you pass ``--apply``.
``--apply`` does not create or delete users. It updates existing persona
rows in one transaction and rolls back on any error.

Personas and env vars:
  admin           DEV_SEED_ADMIN_PASSWORD
  lab-manager     DEV_SEED_LAB_MANAGER_PASSWORD
  lab-tech        DEV_SEED_LAB_TECH_PASSWORD
  client          DEV_SEED_CLIENT_PASSWORD
  alice-tech      DEV_SEED_ALICE_TECH_PASSWORD
  bob-tech        DEV_SEED_BOB_TECH_PASSWORD
  carol-manager   DEV_SEED_CAROL_MANAGER_PASSWORD
  david-cro       DEV_SEED_DAVID_CRO_PASSWORD

``--check`` never prints a password. A row needs a password when the hash
is the locked marker, a legacy 64-hex digest, ``must_change_password`` is
true, or ``--defaults-file`` verifies the hash against a published default.
That file stays outside the repo (one secret per line, or ``secret==>…``).
Nothing from it is written into the repo or the log.

``--apply`` skips rows that do not need a password unless ``--force``.
Pass ``--defaults-file`` on ``--apply`` as well, or the four biotech users
on an old database (bcrypt of a published default, must-change false) are
treated as already rotated.

``must_change_password`` is set false after a successful apply. Same choice
as ``seed_config_agent_slice.py``: the operator supplied the env value, or
this process just printed the only copy.

Usage
-----
  python seed_dev_passwords.py --check
  python seed_dev_passwords.py --check --defaults-file ~/nimble-secrets-replace.txt
  python seed_dev_passwords.py --apply
  python seed_dev_passwords.py --apply --only lab-tech,client --force
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import warnings
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

warnings.filterwarnings("ignore", category=Warning, module="sqlalchemy")

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

import models  # noqa: F401  (register mappers)
from app.core.dev_passwords import (
    PERSONAS,
    SEED_LOCKED,
    generate_dev_password,
)
from app.core.security import (
    bump_password_epoch,
    get_password_hash,
    validate_password_complexity,
    verify_password,
)
from models.user import User

_LEGACY_SHA256 = re.compile(r"[0-9a-f]{64}")


class SeedPasswordError(RuntimeError):
    """Refused apply. The database is left unchanged."""


def seed_password_reason(
    password_hash: str | None,
    must_change: bool,
    defaults: list[str] | None,
) -> str | None:
    """Why this row still needs a password, or None when it looks rotated.

    Returned codes are ``seed-locked``, ``legacy-sha256``,
    ``published-default``, and ``must-change``. Never a password.
    """
    stored = password_hash or ""
    if stored == SEED_LOCKED:
        return "seed-locked"
    if _LEGACY_SHA256.fullmatch(stored):
        return "legacy-sha256"
    if defaults:
        for plain in defaults:
            if plain and verify_password(plain, stored):
                return "published-default"
    if must_change:
        return "must-change"
    return None


def load_defaults_file(path: str) -> list[str]:
    """Secrets from an outside file. ``value==>replacement`` keeps ``value`` only."""
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise SeedPasswordError(f"Defaults file not found: {file_path}")
    values: list[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if "==>" in text:
            text = text.split("==>", 1)[0]
        if text and text not in values:
            values.append(text)
    return values


def _owner_url() -> str:
    url = os.getenv("MIGRATE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SeedPasswordError(
            "Set MIGRATE_DATABASE_URL to the migrator owner connection. "
            "DATABASE_URL is accepted only when the migrator URL is unset."
        )
    return url


def _connect() -> tuple[Session, object]:
    url = _owner_url()
    host = url.split("@")[-1] if "@" in url else url
    user = "unknown"
    if "://" in url and "@" in url:
        user = url.split("://", 1)[1].split(":", 1)[0]
    print(f"Connecting as DB user '{user}' → {host}")
    if user == "lims_app":
        print(
            "WARNING: connected as lims_app. RLS can hide rows. "
            "Set MIGRATE_DATABASE_URL to the migrator owner."
        )
    engine = create_engine(url)
    session = sessionmaker(bind=engine)()
    return session, engine


def _selected(only: list[str] | None) -> tuple[tuple[str, str], ...]:
    if not only:
        return PERSONAS
    known = {username: env_name for username, env_name in PERSONAS}
    chosen: list[tuple[str, str]] = []
    for username in only:
        if username not in known:
            names = ", ".join(name for name, _env in PERSONAS)
            raise SeedPasswordError(
                f"Unknown persona {username!r}. Expected one of: {names}"
            )
        chosen.append((username, known[username]))
    return tuple(chosen)


def _report_line(username: str, state: str, detail: str) -> str:
    return f"{username}\t{state}\t{detail}"


def check_personas(
    session: Session,
    *,
    only: list[str] | None = None,
    defaults: list[str] | None = None,
) -> list[str]:
    """Status lines. No password is included."""
    lines: list[str] = []
    for username, _env_name in _selected(only):
        user = session.query(User).filter(User.username == username).one_or_none()
        if user is None:
            lines.append(_report_line(username, "missing", "user-not-found"))
            continue
        reason = seed_password_reason(
            user.password_hash,
            bool(user.must_change_password),
            defaults,
        )
        if reason is None:
            lines.append(_report_line(username, "ok", "already-rotated"))
        else:
            lines.append(_report_line(username, "needs-password", reason))
    return lines


def apply_personas(
    session: Session,
    *,
    only: list[str] | None = None,
    force: bool = False,
    defaults: list[str] | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Update hashes. Does not commit. Returns report lines and generated triples.

    Generated triples are ``(username, env name, password)`` and are safe to
    print only after the caller commits.
    """
    source = environ if environ is not None else os.environ
    selected = _selected(only)
    planned: list[tuple[User, str, str, bool]] = []
    lines: list[str] = []

    for username, env_name in selected:
        user = session.query(User).filter(User.username == username).one_or_none()
        if user is None:
            lines.append(_report_line(username, "missing", "user-not-found"))
            continue
        reason = seed_password_reason(
            user.password_hash,
            bool(user.must_change_password),
            defaults,
        )
        if reason is None and not force:
            lines.append(_report_line(username, "skipped", "already-rotated"))
            continue
        raw = (source.get(env_name) or "").strip()
        generated = False
        if raw:
            errors = validate_password_complexity(
                raw, username=username, current_password=None
            )
            if errors:
                detail = "; ".join(errors)
                raise SeedPasswordError(f"{env_name} fails complexity: {detail}")
            password = raw
        else:
            password = generate_dev_password()
            generated = True
        planned.append((user, env_name, password, generated))

    generated_out: list[tuple[str, str, str]] = []
    for user, env_name, password, generated in planned:
        user.password_hash = get_password_hash(password)
        bump_password_epoch(user)
        # Slice script sets this false for both env and generated passwords.
        user.must_change_password = False
        if generated:
            generated_out.append((user.username, env_name, password))
            lines.append(_report_line(user.username, "updated", "generated"))
        else:
            lines.append(_report_line(user.username, "updated", "from-env"))
    session.flush()
    return lines, generated_out


def print_generated(generated: list[tuple[str, str, str]]) -> None:
    """Stdout once, after a successful commit. Never written to a file."""
    for username, env_name, password in generated:
        print(f"{username} ({env_name} was unset; printed once):")
        print(password)


def user_count(session: Session) -> int:
    return int(session.query(func.count(User.id)).scalar() or 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report each persona. Never prints a password.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Set passwords from env, or generate and print once.",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated usernames to limit the run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rotate rows that already look changed.",
    )
    parser.add_argument(
        "--defaults-file",
        default="",
        help="Outside-repo file of published defaults. Used to detect old hashes. Not logged.",
    )
    args = parser.parse_args(argv)
    if args.apply and args.check:
        print("Pass only one of --check or --apply.", file=sys.stderr)
        return 2
    only = [part.strip() for part in args.only.split(",") if part.strip()]
    try:
        defaults = load_defaults_file(args.defaults_file) if args.defaults_file else None
        session, engine = _connect()
    except SeedPasswordError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        if args.apply:
            before = user_count(session)
            lines, generated = apply_personas(
                session, only=only or None, force=args.force, defaults=defaults
            )
            after = user_count(session)
            if before != after:
                raise SeedPasswordError(
                    f"user count changed ({before} → {after}); refusing to commit"
                )
            session.commit()
            for line in lines:
                print(line)
            print_generated(generated)
            return 0
        for line in check_personas(session, only=only or None, defaults=defaults):
            print(line)
        return 0
    except SeedPasswordError as exc:
        session.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
