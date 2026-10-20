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
- an evidence file or tar member whose name changes under normalization
  or contains ``|`` or ``\\``
- a duplicate evidence path or duplicate tar member name

A reviewed allowlist (default ``scripts/uat_evidence_allowlist.json``) may
suppress a hit. Each entry is an exact evidence-relative path (normalized
only on the allowlist side, no ``..``, no absolute path) plus the file's
SHA-256, with ``reviewed_by``, ``approved_by``, and ``date``. A line
entry also carries a line number and still requires that SHA-256. A hit
is suppressed only when that same scanned file's own SHA-256 equals the
entry hash. Line entries never suppress configured-secret, seed/pool
password, bcrypt, or dump hits. Tar members are separate paths
(``archive.tar!ui/name.png``). A file entry never covers a member, and a
member entry never covers a file. Digests and hits are keyed by the
exact on-disk path (and the exact member name within each tar). Changed
bytes no longer match. There is no allow-by-extension.

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
_PROCESS_SUFFIXES = ("|gunzip", "|inflate")
_NEVER_SUPPRESS_PREFIXES = (
    "HIT unsafe evidence path:",
    "HIT duplicate evidence path:",
    "HIT duplicate tar member:",
)
_LINE_UNSUPPRESSIBLE_PREFIXES = (
    "HIT password-pool token:",
    "HIT configured secret:",
    "HIT bcrypt hash:",
    "HIT dump file:",
)


class AllowlistEntry:
    """One reviewed path. ``sha256`` is required; ``line`` is optional."""

    def __init__(
        self,
        path: str,
        reviewed_by: str,
        approved_by: str,
        date: str,
        sha256: str,
        line: int | None = None,
    ) -> None:
        self.path = path
        self.reviewed_by = reviewed_by
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


def normalize_evidence_path(raw: str) -> str:
    """Exact evidence-relative path. Rejects absolute paths and ``..``."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("empty path")
    text = raw.strip().replace("\\", "/")
    if text.startswith("/") or (len(text) >= 2 and text[1] == ":"):
        raise ValueError("absolute path")
    segments = text.split("!")
    if any(not segment.strip() for segment in segments):
        raise ValueError("empty path segment")
    return "!".join(_normalize_rel_segment(segment) for segment in segments)


def _normalize_rel_segment(raw: str) -> str:
    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("parent path")
        parts.append(part)
    if not parts:
        raise ValueError("empty path")
    return "/".join(parts)


def is_unsafe_evidence_name(raw: str) -> bool:
    """True when a name changes under normalization or contains ``|`` or ``\\``."""
    if not isinstance(raw, str) or not raw:
        return True
    if "|" in raw or "\\" in raw:
        return True
    try:
        return normalize_evidence_path(raw) != raw
    except ValueError:
        return True


def _member_path(archive_name: str, member_name: str) -> str:
    if archive_name:
        return f"{archive_name}!{member_name}"
    return member_name


def _leaf_name(name: str) -> str:
    leaf = name.split("!")[-1]
    for suffix in _PROCESS_SUFFIXES:
        if leaf.endswith(suffix):
            leaf = leaf[: -len(suffix)]
    return leaf


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
    if not isinstance(rel, str) or any(char in rel for char in "*?[]"):
        raise SystemExit(
            f"ERROR: allowlist must not allow by extension or glob: {source}"
        )
    try:
        normalized = normalize_evidence_path(rel)
    except ValueError:
        raise SystemExit(
            f"ERROR: allowlist path must be a relative file path: {source}"
        ) from None
    reviewed = item.get("reviewed_by")
    approved = item.get("approved_by")
    date = item.get("date")
    if not isinstance(reviewed, str) or not reviewed.strip():
        raise SystemExit(f"ERROR: allowlist entry needs reviewed_by: {source}")
    if not isinstance(approved, str) or not approved.strip():
        raise SystemExit(f"ERROR: allowlist entry needs approved_by: {source}")
    if not isinstance(date, str) or not date.strip():
        raise SystemExit(f"ERROR: allowlist entry needs date: {source}")
    sha = item.get("sha256")
    if sha is None:
        raise SystemExit(f"ERROR: allowlist entry needs path plus sha256: {source}")
    if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
        raise SystemExit(
            f"ERROR: allowlist sha256 must be 64 hex characters: {source}"
        )
    line = item.get("line")
    parsed_line: int | None = None
    if line is not None:
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            raise SystemExit(
                f"ERROR: allowlist line must be a positive integer: {source}"
            )
        parsed_line = line
    return AllowlistEntry(
        path=normalized,
        reviewed_by=reviewed,
        approved_by=approved,
        date=date,
        sha256=sha.lower(),
        line=parsed_line,
    )


def _hit_location(hit: str) -> tuple[str, int | None]:
    loc = hit.split(": ", 1)[1]
    path_part, _sep, rest = loc.rpartition(":")
    if path_part and rest.isdigit():
        return path_part, int(rest)
    return loc, None


def _allowlist_identity(name: str, digests: dict[str, str]) -> str:
    """Map a hit name to the exact on-disk or member path used for digests."""
    if name in digests:
        return name
    base = name
    while True:
        stripped = None
        for suffix in _PROCESS_SUFFIXES:
            if base.endswith(suffix):
                stripped = base[: -len(suffix)]
                break
        if stripped is None:
            return name
        if stripped in digests:
            return stripped
        base = stripped


def _entry_suppresses(
    entry: AllowlistEntry,
    hit: str,
    line_no: int | None,
    digest: str | None,
) -> bool:
    if not digest or digest != entry.sha256:
        return False
    if entry.line is None:
        return True
    if any(hit.startswith(prefix) for prefix in _LINE_UNSUPPRESSIBLE_PREFIXES):
        return False
    return line_no == entry.line


def filter_allowlist_hits(
    hits: list[str],
    entries: tuple[AllowlistEntry, ...] | list[AllowlistEntry],
    digests: dict[str, str],
) -> list[str]:
    by_path: dict[str, list[AllowlistEntry]] = {}
    for entry in entries:
        by_path.setdefault(entry.path, []).append(entry)
    kept: list[str] = []
    for hit in hits:
        if any(hit.startswith(prefix) for prefix in _NEVER_SUPPRESS_PREFIXES):
            kept.append(hit)
            continue
        name, line_no = _hit_location(hit)
        identity = _allowlist_identity(name, digests)
        candidates = by_path.get(identity, ())
        if not candidates:
            kept.append(hit)
            continue
        digest = digests.get(identity)
        if any(_entry_suppresses(entry, hit, line_no, digest) for entry in candidates):
            continue
        kept.append(hit)
    return kept


def _is_dump_name(name: str) -> bool:
    lower = Path(_leaf_name(name)).name.lower()
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
    if not name or name in digests:
        return
    digests[name] = hashlib.sha256(data).hexdigest()


def _scan_payload(
    name: str,
    data: bytes,
    secrets: tuple[str, ...],
    depth: int = 0,
    digests: dict[str, str] | None = None,
    record: bool = True,
) -> list[str]:
    if digests is not None and name and record:
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
        hits.extend(
            _scan_payload(
                f"{name}|gunzip",
                inner,
                secrets,
                depth + 1,
                digests,
                record=False,
            )
        )
        return hits
    if _is_zlib(data):
        try:
            inner = zlib.decompress(data)
        except zlib.error:
            hits.append(f"HIT refuse binary: {name}")
            return hits
        hits.extend(
            _scan_payload(
                f"{name}|inflate",
                inner,
                secrets,
                depth + 1,
                digests,
                record=False,
            )
        )
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
    seen_members: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive.getmembers():
            if member.isdir() or not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            inner_name = _member_path(name, member.name)
            if member.name in seen_members:
                hits.append(f"HIT duplicate tar member: {inner_name}")
            seen_members.add(member.name)
            if is_unsafe_evidence_name(member.name):
                hits.append(f"HIT unsafe evidence path: {inner_name}")
            payload = extracted.read()
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
        hits = _scan_payload(path.name, data, secrets, digests=digests)
        return filter_allowlist_hits(hits, allowlist, digests)
    raise SystemExit(f"ERROR: {path} is not a directory or a tarball")


def _scan_directory(
    root: Path,
    secrets: tuple[str, ...],
    digests: dict[str, str],
) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root).as_posix()
        if relative in seen:
            hits.append(f"HIT duplicate evidence path: {relative}")
        seen.add(relative)
        if is_unsafe_evidence_name(relative):
            hits.append(f"HIT unsafe evidence path: {relative}")
        data = file_path.read_bytes()
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
            "Reviewed allowlist JSON (exact path plus sha256, optional line "
            "plus sha256, with reviewed_by, approved_by, and date). Defaults "
            "to scripts/uat_evidence_allowlist.json."
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
