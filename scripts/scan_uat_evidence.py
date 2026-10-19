#!/usr/bin/env python3
"""Refuse to share a UAT evidence folder or tarball that contains secrets.

Exit 0 when the tree is clean. Exit 1 and list hits when it finds any of:

- a ``printed once`` header in any case
- a 24-character password-pool window that contains upper, lower, digit,
  and a pool symbol (the mix ``generate_dev_password`` requires). ``_``
  and ``-`` count as symbols. Mixed-case snake_case keys with three or
  more ``_``/``-`` separators and no other pool symbol are not hits.
- a configured compose or seed secret from the environment or
  ``--secrets-file``, matched literally and percent-encoded
- a bcrypt hash marker (``$2a$``, ``$2b$``, ``$2y$``)
- a ``.dump`` / ``.dump.gz`` name, or the ``PGDMP`` magic
- gzip or zlib payloads (decompressed, then scanned)
- nested tarballs
- a binary file that is not gzip, zlib, tar, PGDMP, or UTF-8 text

A reviewed allowlist (default ``scripts/uat_evidence_allowlist.json``) may
suppress a hit. Each entry is a concrete path plus either a line number
or a file SHA-256, with ``approved_by`` and ``date``. Changed bytes no
longer match. There is no allow-by-extension.

Hits name the file and the line. They do not repeat the secret.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shlex
import sys
import tarfile
import zlib
from pathlib import Path
from urllib.parse import quote, unquote

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.dev_passwords import DEV_PASSWORD_LENGTH, DEV_PASSWORD_POOL  # noqa: E402

PRINTED_ONCE_RE = re.compile(r"printed once", re.IGNORECASE)
BCRYPT_RE = re.compile(r"\$2[aby]\$")
SECRET_NAME_RE = re.compile(
    r"^(POSTGRES_PASSWORD|LIMS_MIGRATE_PASSWORD|LIMS_APP_PASSWORD|"
    r"SECRET_KEY|DEV_SEED_[A-Z0-9_]+_PASSWORD|SLICE_[A-Z0-9_]+_PASSWORD)$"
)
PGDMP_MAGIC = b"PGDMP"
GZIP_MAGIC = b"\x1f\x8b"
ZLIB_MAGICS = (b"\x78\x01", b"\x78\x9c", b"\x78\xda")
_POOL = set(DEV_PASSWORD_POOL)
_SYMBOLS = set("!@#$%^&*-_")
_SEPARATORS = set("_-")
_OTHER_SYMBOLS = _SYMBOLS - _SEPARATORS
MAX_NEST = 8
DEFAULT_ALLOWLIST = Path(__file__).resolve().parent / "uat_evidence_allowlist.json"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class AllowlistEntry:
    """One reviewed path. Either ``sha256`` or ``line`` is set, never both."""

    def __init__(
        self,
        path: str,
        approved_by: str,
        date: str,
        sha256: str | None = None,
        line: int | None = None,
    ) -> None:
        self.path = path
        self.approved_by = approved_by
        self.date = date
        self.sha256 = sha256
        self.line = line


def _is_strong_window(window: str) -> bool:
    if not (
        any(char.isupper() for char in window)
        and any(char.islower() for char in window)
        and any(char.isdigit() for char in window)
        and any(char in _SYMBOLS for char in window)
    ):
        return False
    separators = sum(char in _SEPARATORS for char in window)
    if separators >= 3 and not any(char in _OTHER_SYMBOLS for char in window):
        return False
    return True


def pool_token_on_line(line: str) -> bool:
    """True when a 24-character pool window has the generated-password mix."""
    run: list[str] = []

    def flush() -> bool:
        if len(run) < DEV_PASSWORD_LENGTH:
            return False
        text = "".join(run)
        last = len(text) - DEV_PASSWORD_LENGTH
        for offset in range(0, last + 1):
            if _is_strong_window(text[offset : offset + DEV_PASSWORD_LENGTH]):
                return True
        return False

    for char in line:
        if char in _POOL:
            run.append(char)
            continue
        if flush():
            return True
        run = []
    return flush()


def configured_secret_on_line(line: str, secrets: tuple[str, ...]) -> bool:
    for secret in secrets:
        if secret and secret in line:
            return True
        encoded = quote(secret, safe="")
        if encoded and encoded != secret and encoded in line:
            return True
    return False


def scan_text(name: str, text: str, secrets: tuple[str, ...] = ()) -> list[str]:
    hits: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        variants = (line, unquote(line))
        if any(PRINTED_ONCE_RE.search(variant) for variant in variants):
            hits.append(f"HIT printed-once header: {name}:{number}")
        if any(BCRYPT_RE.search(variant) for variant in variants):
            hits.append(f"HIT bcrypt hash: {name}:{number}")
        if any(pool_token_on_line(variant) for variant in variants):
            hits.append(f"HIT password-pool token: {name}:{number}")
        if any(configured_secret_on_line(variant, secrets) for variant in variants):
            hits.append(f"HIT configured secret: {name}:{number}")
    return hits


def load_scan_secrets(
    environ: dict[str, str] | None = None,
    secrets_file: Path | None = None,
) -> tuple[str, ...]:
    source = environ if environ is not None else os.environ
    values: list[str] = []
    for key, raw in source.items():
        if SECRET_NAME_RE.fullmatch(key):
            text = (raw or "").strip()
            if text and text not in values:
                values.append(text)
    if secrets_file is not None:
        for key, text in _read_secrets_file(secrets_file):
            if SECRET_NAME_RE.fullmatch(key) and text and text not in values:
                values.append(text)
    return tuple(values)


def _read_secrets_file(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        raise SystemExit(f"ERROR: secrets file not found: {path}")
    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, raw = text.split("=", 1)
        parsed = shlex.split(raw)
        if len(parsed) != 1:
            continue
        pairs.append((key, parsed[0]))
    return pairs


def load_allowlist(path: Path) -> list[AllowlistEntry]:
    """Load a reviewed allowlist. Refuses extension/glob entries."""
    if not path.is_file():
        raise SystemExit(f"ERROR: allowlist not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: allowlist is not valid JSON: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise SystemExit(f"ERROR: allowlist must be an object with entries: {path}")
    return [_parse_allowlist_entry(item, path) for item in raw["entries"]]


def _parse_allowlist_entry(item: object, source: Path) -> AllowlistEntry:
    if not isinstance(item, dict):
        raise SystemExit(f"ERROR: allowlist entry must be an object: {source}")
    if "extension" in item or "glob" in item:
        raise SystemExit(
            f"ERROR: allowlist must not allow by extension or glob: {source}"
        )
    rel = item.get("path")
    if not isinstance(rel, str) or not rel.strip() or rel.startswith("/"):
        raise SystemExit(f"ERROR: allowlist path must be a relative file path: {source}")
    if any(part == ".." for part in Path(rel).parts) or any(
        char in rel for char in "*?[]"
    ):
        raise SystemExit(
            f"ERROR: allowlist must not allow by extension or glob: {source}"
        )
    approved = item.get("approved_by")
    date = item.get("date")
    if not isinstance(approved, str) or not approved.strip():
        raise SystemExit(f"ERROR: allowlist entry needs approved_by: {source}")
    if not isinstance(date, str) or not date.strip():
        raise SystemExit(f"ERROR: allowlist entry needs date: {source}")
    sha = item.get("sha256")
    line = item.get("line")
    has_sha = sha is not None
    has_line = line is not None
    if has_sha == has_line:
        raise SystemExit(
            f"ERROR: allowlist entry needs path plus either line or sha256: {source}"
        )
    if has_sha:
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            raise SystemExit(
                f"ERROR: allowlist sha256 must be 64 hex characters: {source}"
            )
        return AllowlistEntry(
            path=rel,
            approved_by=approved,
            date=date,
            sha256=sha.lower(),
        )
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        raise SystemExit(f"ERROR: allowlist line must be a positive integer: {source}")
    return AllowlistEntry(
        path=rel,
        approved_by=approved,
        date=date,
        line=line,
    )


def _path_matches(candidate: str, allowed: str) -> bool:
    base = candidate.split("|", 1)[0]
    return base == allowed or base.endswith("/" + allowed)


def filter_allowlist_hits(
    hits: list[str],
    entries: tuple[AllowlistEntry, ...] | list[AllowlistEntry],
    digests: dict[str, str],
) -> list[str]:
    sha_ok: set[str] = set()
    line_ok: set[tuple[str, int]] = set()
    for entry in entries:
        if entry.sha256:
            for name, digest in digests.items():
                if _path_matches(name, entry.path) and digest == entry.sha256:
                    sha_ok.add(entry.path)
        elif entry.line is not None:
            line_ok.add((entry.path, entry.line))
    kept: list[str] = []
    for hit in hits:
        loc = hit.split(": ", 1)[1]
        path_part, _sep, rest = loc.partition(":")
        file_path = path_part.split("|", 1)[0]
        if any(_path_matches(file_path, allowed) for allowed in sha_ok):
            continue
        if rest.isdigit():
            line_no = int(rest)
            if (path_part, line_no) in line_ok or (file_path, line_no) in line_ok:
                continue
        kept.append(hit)
    return kept


def _is_dump_name(name: str) -> bool:
    lower = Path(name).name.lower()
    return lower.endswith(".dump") or lower.endswith(".dump.gz")


def _has_pgdmp_magic(data: bytes) -> bool:
    return data.startswith(PGDMP_MAGIC)


def _is_gzip(data: bytes) -> bool:
    return data.startswith(GZIP_MAGIC)


def _is_zlib(data: bytes) -> bool:
    return data[:2] in ZLIB_MAGICS


def _is_tar_bytes(data: bytes) -> bool:
    if len(data) < 512:
        return False
    handle = io.BytesIO(data)
    try:
        with tarfile.open(fileobj=handle, mode="r:*") as archive:
            archive.getmembers()
        return True
    except tarfile.TarError:
        return False


def _looks_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _record_digest(digests: dict[str, str], name: str, data: bytes) -> None:
    digest = hashlib.sha256(data).hexdigest()
    digests[name] = digest
    base = name.split("|", 1)[0]
    if base and base not in digests:
        digests[base] = digest
    leaf = Path(base).name
    if leaf and "/" in base:
        # Nested tar prefixes keep the member's evidence-relative path too.
        pass


def _scan_payload(
    name: str,
    data: bytes,
    secrets: tuple[str, ...],
    depth: int = 0,
    digests: dict[str, str] | None = None,
) -> list[str]:
    if digests is not None and name:
        _record_digest(digests, name, data)
    hits: list[str] = []
    if _is_dump_name(name) or _has_pgdmp_magic(data):
        hits.append(f"HIT dump file: {name}")
    if depth > MAX_NEST:
        return hits
    if _is_gzip(data):
        try:
            inner = gzip.decompress(data)
        except OSError:
            hits.append(f"HIT refuse binary: {name}")
            return hits
        hits.extend(_scan_payload(f"{name}|gunzip", inner, secrets, depth + 1, digests))
        return hits
    if _is_zlib(data):
        try:
            inner = zlib.decompress(data)
        except zlib.error:
            hits.append(f"HIT refuse binary: {name}")
            return hits
        hits.extend(_scan_payload(f"{name}|inflate", inner, secrets, depth + 1, digests))
        return hits
    if _is_tar_bytes(data):
        hits.extend(_scan_tar_bytes(name, data, secrets, depth + 1, digests))
        return hits
    if _looks_text(data):
        hits.extend(scan_text(name, data.decode("utf-8"), secrets))
        return hits
    if not (_is_dump_name(name) or _has_pgdmp_magic(data)):
        hits.append(f"HIT refuse binary: {name}")
    return hits


def _scan_tar_bytes(
    name: str,
    data: bytes,
    secrets: tuple[str, ...],
    depth: int,
    digests: dict[str, str] | None = None,
) -> list[str]:
    hits: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive.getmembers():
            if member.isdir() or not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            inner_name = f"{name}/{member.name}" if name else member.name
            payload = extracted.read()
            if digests is not None:
                _record_digest(digests, member.name, payload)
                _record_digest(digests, inner_name, payload)
            hits.extend(_scan_payload(inner_name, payload, secrets, depth, digests))
    return hits


def scan_path(
    path: Path,
    secrets: tuple[str, ...] = (),
    allowlist: tuple[AllowlistEntry, ...] | list[AllowlistEntry] = (),
) -> list[str]:
    digests: dict[str, str] = {}
    if path.is_dir():
        hits = _scan_directory(path, secrets, digests)
        return filter_allowlist_hits(hits, allowlist, digests)
    data = path.read_bytes()
    if _is_tar_bytes(data) or tarfile.is_tarfile(path):
        hits = _scan_payload("", data, secrets, digests=digests)
        return filter_allowlist_hits(hits, allowlist, digests)
    raise SystemExit(f"ERROR: {path} is not a directory or a tarball")


def _scan_directory(
    root: Path,
    secrets: tuple[str, ...],
    digests: dict[str, str],
) -> list[str]:
    hits: list[str] = []
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root).as_posix()
        data = file_path.read_bytes()
        _record_digest(digests, relative, data)
        hits.extend(_scan_payload(relative, data, secrets, digests=digests))
    return hits


def _resolve_allowlist(args: argparse.Namespace) -> tuple[AllowlistEntry, ...]:
    if args.no_allowlist:
        return ()
    allow_path = (
        Path(args.allowlist).expanduser() if args.allowlist else DEFAULT_ALLOWLIST
    )
    if args.allowlist and not allow_path.is_file():
        raise SystemExit(f"ERROR: allowlist not found: {allow_path}")
    if not allow_path.is_file():
        return ()
    return tuple(load_allowlist(allow_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence",
        help="Evidence directory or tarball to scan before it is shared.",
    )
    parser.add_argument(
        "--secrets-file",
        default="",
        help=(
            "Optional KEY=<quoted> file of compose or seed secrets. "
            "Values are matched literally and percent-encoded."
        ),
    )
    parser.add_argument(
        "--allowlist",
        default="",
        help=(
            "Reviewed allowlist JSON (path plus line or sha256, with "
            "approved_by and date). Defaults to scripts/uat_evidence_allowlist.json."
        ),
    )
    parser.add_argument(
        "--no-allowlist",
        action="store_true",
        help="Scan with no reviewed allowlist.",
    )
    args = parser.parse_args(argv)
    target = Path(args.evidence)
    if not target.exists():
        print(f"ERROR: evidence path not found: {target}", file=sys.stderr)
        return 2
    secrets_path = Path(args.secrets_file).expanduser() if args.secrets_file else None
    try:
        secrets = load_scan_secrets(secrets_file=secrets_path)
        allowlist = _resolve_allowlist(args)
        hits = scan_path(target, secrets, allowlist)
    except SystemExit as exc:
        message = str(exc)
        if message:
            print(message, file=sys.stderr)
        return 2
    if hits:
        for hit in hits:
            print(hit, file=sys.stderr)
        print(f"ERROR: {len(hits)} evidence hit(s); refusing to share", file=sys.stderr)
        return 1
    print(f"evidence scan clean: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
