#!/usr/bin/env python3
"""Set dev/UAT seed passwords from the environment, or generate them.

UAT passes ``--secrets-out PATH``. Generated passwords are written to a
temp file in the same directory, created with
``O_CREAT|O_EXCL|O_NOFOLLOW`` and mode ``0600``. Each line is
``KEY=<shlex.quote(value)>``. The temp file replaces ``PATH`` with
``os.replace`` only after the database commit succeeds. A failed apply
removes the temp file and leaves ``PATH`` unchanged. Load that file with
``set -a; . PATH; set +a``. Stdout names that path and does not print a
password. Without ``--secrets-out``, a local ``--apply`` still prints
each generated password once. UAT does not use that path.

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
  config-editor   DEV_SEED_CONFIG_EDITOR_PASSWORD

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
this process just wrote the only copy to ``--secrets-out``.

Usage
-----
  python seed_dev_passwords.py --check
  python seed_dev_passwords.py --check --defaults-file ~/nimble-secrets-replace.txt
  python seed_dev_passwords.py --apply --secrets-out ~/uat-secrets.env
  python seed_dev_passwords.py --apply --only lab-tech,client --force
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import stat
import sys
import warnings
from pathlib import Path
from secrets import token_hex

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
_SECRETS_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


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
    print(f"Connecting as DB user '{user}' → {host}", file=sys.stderr)
    if user == "lims_app":
        print(
            "WARNING: connected as lims_app. RLS can hide rows. "
            "Set MIGRATE_DATABASE_URL to the migrator owner.",
            file=sys.stderr,
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
    """Stdout once, after a successful commit, when ``--secrets-out`` was not used.

    UAT does not call this. It uses ``write_secrets_file``.
    """
    for username, env_name, password in generated:
        print(f"{username} ({env_name} was unset; printed once):")
        print(password)


def _is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except FileNotFoundError:
        return False


def assert_secrets_target_usable(path: Path, *, force: bool) -> None:
    """Refuse a missing parent, a non-regular existing path, or a stale file."""
    target = path.expanduser()
    parent = target.parent
    if not parent.is_dir():
        raise SeedPasswordError(f"Secrets file parent folder does not exist: {parent}")
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode):
        raise SeedPasswordError(
            f"Refusing secrets file that is not a regular file: {target}"
        )
    if not force:
        raise SeedPasswordError(f"Refusing to overwrite secrets file: {target}")


def _read_secrets_assignments(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, raw = text.split("=", 1)
        if not _SECRETS_KEY_RE.fullmatch(key):
            continue
        parsed = shlex.split(raw)
        if len(parsed) != 1:
            continue
        pairs[key] = parsed[0]
    return pairs


def _merge_secret_pairs(
    existing: dict[str, str],
    generated: list[tuple[str, str, str]],
    *,
    keep_others: bool,
) -> list[tuple[str, str]]:
    overlay = {env_name: password for _username, env_name, password in generated}
    if not keep_others:
        return [(env_name, overlay[env_name]) for _username, env_name, _pw in generated]
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key, value in existing.items():
        ordered.append((key, overlay.get(key, value)))
        seen.add(key)
    for _username, env_name, password in generated:
        if env_name not in seen:
            ordered.append((env_name, password))
            seen.add(env_name)
    return ordered


def _secrets_file_body(pairs: list[tuple[str, str]]) -> str:
    lines = ["# Generated by seed_dev_passwords.py. Do not print this file.\n"]
    for key, password in pairs:
        if not _SECRETS_KEY_RE.fullmatch(key):
            raise SeedPasswordError(f"Invalid secrets-file key: {key}")
        lines.append(f"{key}={shlex.quote(password)}\n")
    return "".join(lines)


def write_secrets_temp(target: Path, body: str) -> Path:
    """Create an exclusive 0600 temp file next to ``target`` (O_NOFOLLOW)."""
    parent = target.parent
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
    while True:
        temp = parent / f".{target.name}.{os.getpid()}.{token_hex(8)}.tmp"
        try:
            descriptor = os.open(str(temp), flags, 0o600)
            break
        except FileExistsError:
            continue
        except FileNotFoundError as exc:
            raise SeedPasswordError(
                f"Secrets file parent folder does not exist: {parent}"
            ) from exc
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(body)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        temp.unlink(missing_ok=True)
        raise
    return temp


def prepare_secrets_file(
    path: Path,
    generated: list[tuple[str, str, str]],
    *,
    force: bool = False,
    keep_others: bool = False,
) -> Path:
    """Write ``KEY=<quoted>`` lines to a new temp file next to ``path``.

    The caller must ``os.replace`` the temp over ``path`` after a successful
    database commit, or unlink it on failure. Keys must match
    ``^[A-Z_][A-Z0-9_]*$``. ``keep_others`` copies unselected keys from an
    existing regular file. A missing parent folder or a non-regular existing
    path raises ``SeedPasswordError``.
    """
    target = path.expanduser()
    assert_secrets_target_usable(target, force=force)
    for _username, env_name, _password in generated:
        if not _SECRETS_KEY_RE.fullmatch(env_name):
            raise SeedPasswordError(f"Invalid secrets-file key: {env_name}")
    existing: dict[str, str] = {}
    if keep_others and _is_regular_file(target):
        existing = _read_secrets_assignments(target)
    pairs = _merge_secret_pairs(existing, generated, keep_others=keep_others)
    return write_secrets_temp(target, _secrets_file_body(pairs))


def write_secrets_file(
    path: Path,
    generated: list[tuple[str, str, str]],
    *,
    force: bool = False,
    keep_others: bool = False,
) -> None:
    """Write ``KEY=<quoted>`` lines to ``path`` at mode 0600.

    Writes a same-directory temp file with ``O_CREAT|O_EXCL|O_NOFOLLOW``
    at ``0600``, then ``os.replace``s it over ``path``. Tests and
    ``report_generated`` use this helper. ``--apply`` delays the replace
    until after the database commit.
    """
    target = path.expanduser()
    temp = prepare_secrets_file(
        target, generated, force=force, keep_others=keep_others
    )
    os.replace(temp, target)


def report_generated(
    generated: list[tuple[str, str, str]],
    secrets_out: str | None,
    *,
    force: bool = False,
) -> None:
    """Tell the operator where passwords went. Streams never include one.

    ``secrets_out`` writes the file. Stdout is only the path line.
    Without it, local runs still print once.
    """
    if secrets_out:
        if not generated:
            print(f"No generated passwords. {secrets_out} was not created.")
            return
        write_secrets_file(Path(secrets_out), generated, force=force)
        print(f"Generated passwords written to {secrets_out}")
        return
    print_generated(generated)


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
        help="Set passwords from env, or generate them.",
    )
    parser.add_argument(
        "--secrets-out",
        default="",
        help=(
            "Write generated passwords to this file (mode 0600) as "
            "KEY=<shlex.quote(value)>. Load with set -a; . PATH; set +a. "
            "Creates an exclusive 0600 temp next to the path and replaces "
            "the target only after the database commit. Refuses if the "
            "file exists unless --force. Refuses a symlink, directory, or "
            "fifo. With --only, keeps other keys from an existing file. "
            "Stdout prints only the path line. UAT must use this."
        ),
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated usernames to limit the run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Rotate rows that already look changed. Overwrite an existing "
            "--secrets-out regular file after the database commit "
            "(temp file at mode 0600, then os.replace)."
        ),
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
    if args.secrets_out and not args.apply:
        print("--secrets-out is only valid with --apply.", file=sys.stderr)
        return 2
    only = [part.strip() for part in args.only.split(",") if part.strip()]
    try:
        defaults = load_defaults_file(args.defaults_file) if args.defaults_file else None
        session, engine = _connect()
    except SeedPasswordError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    temp: Path | None = None
    dest: Path | None = None
    try:
        if args.apply:
            if args.secrets_out:
                dest = Path(args.secrets_out).expanduser()
                assert_secrets_target_usable(dest, force=args.force)
            before = user_count(session)
            lines, generated = apply_personas(
                session, only=only or None, force=args.force, defaults=defaults
            )
            after = user_count(session)
            if before != after:
                raise SeedPasswordError(
                    f"user count changed ({before} → {after}); refusing to commit"
                )
            if dest is not None and generated:
                temp = prepare_secrets_file(
                    dest,
                    generated,
                    force=args.force,
                    keep_others=bool(only),
                )
            try:
                session.commit()
            except Exception:
                if temp is not None:
                    temp.unlink(missing_ok=True)
                    temp = None
                raise
            if temp is not None and dest is not None:
                os.replace(temp, dest)
                temp = None
            status = sys.stderr if args.secrets_out else sys.stdout
            for line in lines:
                print(line, file=status)
            if args.secrets_out:
                if dest is None or not generated:
                    print(f"No generated passwords. {args.secrets_out} was not created.")
                else:
                    print(f"Generated passwords written to {dest}")
            else:
                print_generated(generated)
            return 0
        for line in check_personas(session, only=only or None, defaults=defaults):
            print(line)
        return 0
    except SeedPasswordError as exc:
        session.rollback()
        if temp is not None:
            temp.unlink(missing_ok=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        session.rollback()
        if temp is not None:
            temp.unlink(missing_ok=True)
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
