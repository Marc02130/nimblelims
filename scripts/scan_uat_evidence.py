#!/usr/bin/env python3
"""Refuse to share a UAT evidence folder that contains secrets or archives.

Scan only a plain folder. Archives and compressed files are detected by
signature, not extension, and are an unsuppressible hit. There is no
archive walk and no decompression. Pack only after a clean scan with
``scripts/pack_uat_evidence.py``.

Exit 0 when the tree is clean. Exit 1 and list hits when it finds any of:

- a ``printed once`` header in any case
- a 24-character password-pool window that contains upper, lower, digit,
  and a pool symbol (the mix ``generate_dev_password`` requires). ``_``
  and ``-`` count as symbols. Mixed-case snake_case keys with three or
  more ``_``/``-`` separators and no other pool symbol are not hits.
- a configured compose or seed secret from the environment or
  ``--secrets-file``, matched literally and percent-encoded
- a configured secret or pool token in a file or directory name (whole
  path and each segment)
- a bcrypt hash marker (``$2a$``, ``$2b$``, ``$2y$``)
- a ``.dump`` / ``.dump.gz`` name, or the ``PGDMP`` magic
- an archive or compressed payload (tar, gzip, zlib, xz, bz2, zip,
  zstd, 7z, lz4, rar, cpio, lzma, compress ``.Z``, lzip) detected
  by signature, including a gzip member after junk only when the
  bytes are ``1f 8b 08``, the FLG reserved bits are zero, and a
  bounded inflate succeeds, except short or weak signatures in
  valid UTF-8 text
- bytes after the IEND chunk of a PNG
- a binary file that is not PGDMP or UTF-8 text
- an unsafe name in any directory or file
- a duplicate identity
- a symlink, fifo, socket, or device
- a folder whose scanned files exceed the 64 MiB total cap
  (67108864 bytes)
- a 200-character or longer hex or Base64 run
- a JWT under 200 characters (three base64url segments starting
  ``eyJ``)
- an unreadable directory or file

A reviewed allowlist (default ``scripts/uat_evidence_allowlist.json``) may
suppress a hit. Each entry is a canonical evidence-relative path plus
the file's SHA-256, with ``reviewed_by``, ``approved_by``, and ``date``.
There are no line entries. A hit is suppressed only when the identity
tuple matches exactly and that same object's SHA-256 equals the entry
hash. A sha entry may suppress only refused-binary and password-pool
hits. It never suppresses configured-secret, bcrypt, dump/PGDMP,
printed-once, unsafe-name, duplicate, link, archive, size-cap,
encoded-run, jwt, png-trailing, or unreadable hits. Identities are exact
one-element tuples: the on-disk
relative path. No name is normalized. Duplicate or non-canonical
allowlist paths refuse the whole allowlist (exit 2). There is no
allow-by-extension.

Hits name the identity with ``json.dumps``. A name segment that is a
configured secret or pool token is printed as
``<redacted name hmac:xxxxxxxx>`` (HMAC-SHA256 of the segment with a
per-run random key, first 8 hex). A parent segment that matches is
redacted the same way. A secret that contains ``/`` redacts the whole
path. They do not print the secret.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import hmac
import json
import os
import re
import secrets as _secretsmod
import shlex
import stat
import sys
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
GZIP_DEFLATE = b"\x1f\x8b\x08"
GZIP_FLG_RESERVED = 0xE0
GZIP_PROBE_LIMIT = 8 * 1024
GZIP_CANDIDATE_CAP = 32
ZLIB_MAGICS = (b"\x78\x01", b"\x78\x5e", b"\x78\x9c", b"\x78\xda")
XZ_MAGIC = b"\xfd7zXZ\x00"
BZ2_MAGIC = b"BZh"
ZIP_LOCAL = b"PK\x03\x04"
ZIP_EMPTY = b"PK\x05\x06"
ZIP_SPAN = b"PK\x07\x08"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
SEVEN_Z_MAGIC = b"7z\xbc\xaf'\x1c"
USTAR_MAGIC = b"ustar"
LZ4_MAGIC = b"\x04\"M\x18"
RAR_MAGIC = b"Rar!\x1a\x07"
LZIP_MAGIC = b"LZIP"
COMPRESS_MAGIC = b"\x1f\x9d"
CPIO_NEWC = b"070701"
CPIO_ODC = b"070707"
CPIO_BIN_BE = b"\xc7\x71"
CPIO_BIN_LE = b"\x71\xc7"
LZMA_MAGIC = b"\x5d\x00\x00"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG_IEND = b"\x00\x00\x00\x00IEND"
WEAK_ARCHIVE = frozenset({"zlib", "lzma", "cpio", "bz2"})
_POOL = set(DEV_PASSWORD_POOL)
_SYMBOLS = set("!@#$%^&*-_")
_SEPARATORS = set("_-")
_OTHER_SYMBOLS = _SYMBOLS - _SEPARATORS
MAX_SCAN_BYTES = 64 * 1024 * 1024
DEFAULT_ALLOWLIST = Path(__file__).resolve().parent / "uat_evidence_allowlist.json"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._+=@,-]+(?: [A-Za-z0-9._+=@,-]+)*$")
KIND_PRINTED_ONCE = "printed-once header"
KIND_POOL = "password-pool token"
KIND_CONFIGURED = "configured secret"
KIND_BCRYPT = "bcrypt hash"
KIND_DUMP = "dump file"
KIND_BINARY = "refuse binary"
KIND_UNSAFE = "unsafe-name"
KIND_DUPLICATE = "duplicate"
KIND_LINK = "link"
KIND_ARCHIVE = "archive"
KIND_SIZE_CAP = "size-cap"
KIND_UNREADABLE = "unreadable"
KIND_ENCODED = "encoded run"
KIND_JWT = "jwt"
KIND_PNG_TRAIL = "png-trailing"
SHA_SUPPRESSIBLE = frozenset({KIND_BINARY, KIND_POOL})
HEX_RUN_RE = re.compile(r"[0-9a-fA-F]{200,}")
B64_RUN_RE = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
MAX_JWT_CHARS = 200
Identity = tuple[str, ...]
_REDACT_KEY = _secretsmod.token_bytes(32)


def _name_bytes(raw: str) -> bytes:
    try:
        return os.fsencode(raw)
    except (UnicodeError, ValueError, OSError):
        return raw.encode("utf-8", errors="surrogateescape")


def _redact_tag(raw: str) -> str:
    digest = hmac.new(_REDACT_KEY, _name_bytes(raw), hashlib.sha256).hexdigest()[:8]
    return f"<redacted name hmac:{digest}>"


def _segment_is_secret(segment: str, secrets: tuple[str, ...]) -> bool:
    if not segment:
        return False
    variants = (segment, unquote(segment))
    if any(pool_token_on_line(variant) for variant in variants):
        return True
    return any(configured_secret_on_line(variant, secrets) for variant in variants)


def redact_name_path(raw: str, secrets: tuple[str, ...] = ()) -> str:
    """Replace secret names with a per-run HMAC tag. Keep the parent path."""
    if not raw:
        return raw
    for secret in secrets:
        if not secret or "/" not in secret:
            continue
        encoded = quote(secret, safe="")
        if secret in raw or secret in unquote(raw):
            return _redact_tag(raw)
        if encoded and encoded != secret and encoded in raw:
            return _redact_tag(raw)
    parts = raw.split("/")
    shown: list[str] = []
    for part in parts:
        if _segment_is_secret(part, secrets):
            shown.append(_redact_tag(part))
        else:
            shown.append(part)
    return "/".join(shown)


def _redact_pool_windows(text: str) -> str:
    """Replace each strong password-pool window with an HMAC tag."""
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if not run:
            return
        chunk = "".join(run)
        index = 0
        while index <= len(chunk) - DEV_PASSWORD_LENGTH:
            window = chunk[index : index + DEV_PASSWORD_LENGTH]
            if _is_strong_window(window):
                out.append(_redact_tag(window))
                index += DEV_PASSWORD_LENGTH
            else:
                out.append(chunk[index])
                index += 1
        if index < len(chunk):
            out.append(chunk[index:])
        run.clear()

    for char in text:
        if char in _POOL:
            run.append(char)
            continue
        flush()
        out.append(char)
    flush()
    return "".join(out)


def redact_text(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Redact configured secrets and pool-token windows in arbitrary text."""
    if not text:
        return text
    shown = text
    needles: list[tuple[str, str]] = []
    for secret in sorted((item for item in secrets if item), key=len, reverse=True):
        needles.append((secret, _redact_tag(secret)))
        encoded = quote(secret, safe="")
        if encoded and encoded != secret:
            needles.append((encoded, _redact_tag(secret)))
    for needle, tag in needles:
        if needle in shown:
            shown = shown.replace(needle, tag)
    return _redact_pool_windows(shown)


class Hit:
    """One structured finding. ``identity`` is never normalized."""

    def __init__(
        self,
        kind: str,
        identity: Identity,
        line: int | None = None,
        secrets: tuple[str, ...] = (),
    ) -> None:
        self.kind = kind
        self.identity = identity
        self.line = line
        self.secrets = secrets

    def display_identity(self) -> Identity:
        return tuple(redact_name_path(part, self.secrets) for part in self.identity)

    def format(self) -> str:
        loc = json.dumps(list(self.display_identity()))
        if self.line is None:
            return f"HIT {self.kind}: {loc}"
        return f"HIT {self.kind}: {loc}:{self.line}"

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return self.format()


class AllowlistEntry:
    """One reviewed identity. ``sha256`` is required. No line entries."""

    def __init__(
        self,
        identity: Identity,
        reviewed_by: str,
        approved_by: str,
        date: str,
        sha256: str,
    ) -> None:
        self.identity = identity
        self.path = identity[0] if len(identity) == 1 else json.dumps(list(identity))
        self.reviewed_by = reviewed_by
        self.approved_by = approved_by
        self.date = date
        self.sha256 = sha256
        self.line = None


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


def scan_text(
    identity: Identity,
    text: str,
    secrets: tuple[str, ...] = (),
) -> list[Hit]:
    hits: list[Hit] = []
    for number, line in enumerate(text.splitlines(), start=1):
        variants = (line, unquote(line))
        if any(PRINTED_ONCE_RE.search(variant) for variant in variants):
            hits.append(Hit(KIND_PRINTED_ONCE, identity, number, secrets))
        if any(BCRYPT_RE.search(variant) for variant in variants):
            hits.append(Hit(KIND_BCRYPT, identity, number, secrets))
        if any(pool_token_on_line(variant) for variant in variants):
            hits.append(Hit(KIND_POOL, identity, number, secrets))
        if any(configured_secret_on_line(variant, secrets) for variant in variants):
            hits.append(Hit(KIND_CONFIGURED, identity, number, secrets))
        if any(HEX_RUN_RE.search(variant) or B64_RUN_RE.search(variant) for variant in variants):
            hits.append(Hit(KIND_ENCODED, identity, number, secrets))
        if any(jwt_on_line(variant) for variant in variants):
            hits.append(Hit(KIND_JWT, identity, number, secrets))
    return hits


def jwt_on_line(line: str) -> bool:
    """True when a JWT under 200 characters starts with eyJ and has three segments."""
    for match in JWT_RE.finditer(line):
        if len(match.group(0)) < MAX_JWT_CHARS:
            return True
    return False


def scan_name(
    identity: Identity,
    raw: str,
    secrets: tuple[str, ...] = (),
) -> list[Hit]:
    """Content-scan a file or directory name, whole and per segment."""
    hits: list[Hit] = []
    seen: set[tuple[str, str]] = set()
    parts = [raw, *[part for part in raw.split("/") if part]]
    for text in parts:
        variants = (text, unquote(text))
        if any(pool_token_on_line(variant) for variant in variants):
            key = (KIND_POOL, text)
            if key not in seen:
                hits.append(Hit(KIND_POOL, identity, secrets=secrets))
                seen.add(key)
        if any(configured_secret_on_line(variant, secrets) for variant in variants):
            key = (KIND_CONFIGURED, text)
            if key not in seen:
                hits.append(Hit(KIND_CONFIGURED, identity, secrets=secrets))
                seen.add(key)
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
        if not secrets_file.is_file():
            shown = redact_name_path(str(secrets_file), tuple(values))
            raise SystemExit(f"ERROR: secrets file not found: {shown}")
        for key, text in _read_secrets_file(secrets_file):
            if SECRET_NAME_RE.fullmatch(key) and text and text not in values:
                values.append(text)
    return tuple(values)


def _read_secrets_file(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        shown = redact_name_path(str(path), ())
        raise SystemExit(f"ERROR: secrets file not found: {shown}")
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


def _has_invalid_utf8(raw: str) -> bool:
    if any(0xD800 <= ord(char) <= 0xDFFF for char in raw):
        return True
    try:
        raw.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return True
    return False


def _segment_is_unsafe(segment: str) -> bool:
    if not segment or segment in (".", ".."):
        return True
    if segment != segment.strip():
        return True
    if any(char in segment for char in "|\\!"):
        return True
    if any(ord(char) < 32 or ord(char) == 127 or 128 <= ord(char) <= 159 for char in segment):
        return True
    return _SEGMENT_RE.fullmatch(segment) is None


def is_unsafe_name(raw: str) -> bool:
    """True when a dir or file name is not a canonical relative path."""
    if not isinstance(raw, str) or not raw:
        return True
    if raw.startswith("/") or raw.startswith("./"):
        return True
    if len(raw) >= 2 and raw[1] == ":":
        return True
    if "//" in raw:
        return True
    if any(char in raw for char in "|\\!"):
        return True
    if _has_invalid_utf8(raw):
        return True
    return any(_segment_is_unsafe(part) for part in raw.split("/"))


def is_canonical_path(raw: str) -> bool:
    return isinstance(raw, str) and bool(raw) and not is_unsafe_name(raw)


def is_unsafe_evidence_name(raw: str) -> bool:
    """Alias used by tests. Same rules as ``is_unsafe_name``."""
    return is_unsafe_name(raw)


def _allowlist_shown(path: Path, secrets: tuple[str, ...]) -> str:
    return redact_name_path(str(path), secrets)


def load_allowlist(
    path: Path,
    secrets: tuple[str, ...] = (),
) -> list[AllowlistEntry]:
    """Load a reviewed allowlist. Refuses extension/glob and non-canonical paths."""
    shown = _allowlist_shown(path, secrets)
    if not path.is_file():
        raise SystemExit(f"ERROR: allowlist not found: {shown}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: allowlist is not valid JSON: {shown}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise SystemExit(f"ERROR: allowlist must be an object with entries: {shown}")
    entries = [_parse_allowlist_entry(item, path, secrets) for item in raw["entries"]]
    seen: set[Identity] = set()
    for entry in entries:
        if entry.identity in seen:
            raise SystemExit(f"ERROR: allowlist has a duplicate path: {shown}")
        seen.add(entry.identity)
    return entries


def _parse_allowlist_entry(
    item: object,
    source: Path,
    secrets: tuple[str, ...] = (),
) -> AllowlistEntry:
    shown = _allowlist_shown(source, secrets)
    if not isinstance(item, dict):
        raise SystemExit(f"ERROR: allowlist entry must be an object: {shown}")
    if "extension" in item or "glob" in item:
        raise SystemExit(
            f"ERROR: allowlist must not allow by extension or glob: {shown}"
        )
    if "line" in item:
        raise SystemExit(f"ERROR: allowlist must not use line entries: {shown}")
    rel = item.get("path")
    if isinstance(rel, str):
        if any(char in rel for char in "*?[]"):
            raise SystemExit(
                f"ERROR: allowlist must not allow by extension or glob: {shown}"
            )
        if not is_canonical_path(rel):
            raise SystemExit(
                f"ERROR: allowlist path must be a relative file path: {shown}"
            )
        identity: Identity = (rel,)
    elif isinstance(rel, list) and rel and all(isinstance(part, str) for part in rel):
        if any(any(char in part for char in "*?[]") for part in rel):
            raise SystemExit(
                f"ERROR: allowlist must not allow by extension or glob: {shown}"
            )
        if any(not is_canonical_path(part) for part in rel):
            raise SystemExit(
                f"ERROR: allowlist path must be a relative file path: {shown}"
            )
        identity = tuple(rel)
    else:
        raise SystemExit(
            f"ERROR: allowlist must not allow by extension or glob: {shown}"
        )
    reviewed = item.get("reviewed_by")
    approved = item.get("approved_by")
    date = item.get("date")
    if not isinstance(reviewed, str) or not reviewed.strip():
        raise SystemExit(f"ERROR: allowlist entry needs reviewed_by: {shown}")
    if not isinstance(approved, str) or not approved.strip():
        raise SystemExit(f"ERROR: allowlist entry needs approved_by: {shown}")
    if not isinstance(date, str) or not date.strip():
        raise SystemExit(f"ERROR: allowlist entry needs date: {shown}")
    sha = item.get("sha256")
    if sha is None:
        raise SystemExit(f"ERROR: allowlist entry needs path plus sha256: {shown}")
    if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
        raise SystemExit(
            f"ERROR: allowlist sha256 must be 64 hex characters: {shown}"
        )
    return AllowlistEntry(
        identity=identity,
        reviewed_by=reviewed,
        approved_by=approved,
        date=date,
        sha256=sha.lower(),
    )


def filter_allowlist_hits(
    hits: list[Hit],
    entries: tuple[AllowlistEntry, ...] | list[AllowlistEntry],
    digests: dict[Identity, str],
) -> list[Hit]:
    by_identity: dict[Identity, list[AllowlistEntry]] = {}
    for entry in entries:
        by_identity.setdefault(entry.identity, []).append(entry)
    kept: list[Hit] = []
    for hit in hits:
        if hit.kind not in SHA_SUPPRESSIBLE:
            kept.append(hit)
            continue
        digest = digests.get(hit.identity)
        candidates = by_identity.get(hit.identity, ())
        if any(digest and digest == entry.sha256 for entry in candidates):
            continue
        kept.append(hit)
    return kept


def _identity_leaf(identity: Identity) -> str:
    return Path(identity[-1]).name if identity else ""


def _is_dump_name(identity: Identity) -> bool:
    lower = _identity_leaf(identity).lower()
    return lower.endswith(".dump") or lower.endswith(".dump.gz")


def _has_pgdmp_magic(data: bytes) -> bool:
    return data.startswith(PGDMP_MAGIC)


def _tar_checksum_ok(header: bytes) -> bool:
    if len(header) < 512:
        return False
    field = header[148:156]
    stripped = field.replace(b"\x00", b" ").strip()
    if not stripped or any(char not in b"01234567" for char in stripped):
        return False
    try:
        stored = int(stripped, 8)
    except ValueError:
        return False
    computed = sum(header[:148]) + sum(b" " * 8) + sum(header[156:512])
    return computed == stored


def _is_old_style_tar_header(data: bytes) -> bool:
    if len(data) < 512 or data[:512] == b"\x00" * 512:
        return False
    if data[0] == 0:
        return False
    return _tar_checksum_ok(data[:512])


def _is_tar_signature(data: bytes) -> bool:
    if len(data) >= 262 and data[257:262] == USTAR_MAGIC:
        return True
    return _is_old_style_tar_header(data)


def _gzip_header_ok(data: bytes, offset: int) -> bool:
    if offset + 4 > len(data):
        return False
    if data[offset : offset + 3] != GZIP_DEFLATE:
        return False
    return (data[offset + 3] & GZIP_FLG_RESERVED) == 0


def _gzip_inflates(data: bytes, offset: int) -> bool:
    if not _gzip_header_ok(data, offset):
        return False
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    incoming = data[offset : offset + GZIP_PROBE_LIMIT]
    try:
        out = decoder.decompress(incoming, max_length=GZIP_PROBE_LIMIT)
    except zlib.error:
        return False
    return bool(out) or bool(decoder.eof)


def _has_inflating_gzip(data: bytes) -> bool:
    """True when a deflate gzip member after junk actually inflates."""
    tried = 0
    start = 0
    while tried < GZIP_CANDIDATE_CAP:
        pos = data.find(GZIP_DEFLATE, start)
        if pos < 0:
            return False
        if _gzip_header_ok(data, pos):
            tried += 1
            if _gzip_inflates(data, pos):
                return True
        start = pos + 1
    return False


def archive_kind(data: bytes) -> str | None:
    """Return the signature name when ``data`` is an archive or compressor."""
    if data.startswith(GZIP_MAGIC):
        return "gzip"
    if len(data) >= 2 and data[:2] in ZLIB_MAGICS:
        return "zlib"
    if data.startswith(XZ_MAGIC):
        return "xz"
    if data.startswith(BZ2_MAGIC):
        return "bz2"
    if data.startswith(ZIP_LOCAL) or data.startswith(ZIP_EMPTY) or data.startswith(
        ZIP_SPAN
    ):
        return "zip"
    if data.startswith(ZSTD_MAGIC):
        return "zstd"
    if data.startswith(SEVEN_Z_MAGIC):
        return "7z"
    if data.startswith(LZ4_MAGIC):
        return "lz4"
    if data.startswith(RAR_MAGIC):
        return "rar"
    if data.startswith(LZIP_MAGIC):
        return "lzip"
    if data.startswith(COMPRESS_MAGIC):
        return "compress"
    if (
        data.startswith(CPIO_NEWC)
        or data.startswith(CPIO_ODC)
        or data.startswith(CPIO_BIN_BE)
        or data.startswith(CPIO_BIN_LE)
    ):
        return "cpio"
    if data.startswith(LZMA_MAGIC):
        return "lzma"
    if _is_tar_signature(data):
        return "tar"
    if not data.startswith(PNG_MAGIC) and _has_inflating_gzip(data):
        return "gzip"
    return None


def _png_has_trailing(data: bytes) -> bool:
    if not data.startswith(PNG_MAGIC):
        return False
    pos = data.find(PNG_IEND)
    if pos < 0:
        return False
    end = pos + len(PNG_IEND) + 4
    return end < len(data)


def _looks_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _special_kind(mode: int) -> bool:
    return bool(
        stat.S_ISLNK(mode)
        or stat.S_ISFIFO(mode)
        or stat.S_ISSOCK(mode)
        or stat.S_ISCHR(mode)
        or stat.S_ISBLK(mode)
    )


def _read_nofollow(path: Path) -> bytes:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open(os.fspath(path), flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(errno.ELOOP, "not a regular file")
        if opened.st_size <= 0:
            return b""
        return os.read(fd, opened.st_size)
    finally:
        os.close(fd)


def _record_digest(
    digests: dict[Identity, str],
    announced: set[Identity],
    identity: Identity,
    data: bytes,
    hits: list[Hit],
    secrets: tuple[str, ...],
) -> None:
    digest = hashlib.sha256(data).hexdigest()
    if identity in digests:
        hits.append(Hit(KIND_DUPLICATE, identity, secrets=secrets))
        if identity not in announced:
            hits.append(Hit(KIND_DUPLICATE, identity, secrets=secrets))
            announced.add(identity)
        return
    digests[identity] = digest


def _scan_payload(
    identity: Identity,
    data: bytes,
    secrets: tuple[str, ...],
    digests: dict[Identity, str],
    announced: set[Identity],
) -> list[Hit]:
    hits: list[Hit] = []
    if identity:
        _record_digest(digests, announced, identity, data, hits, secrets)
    if _is_dump_name(identity) or _has_pgdmp_magic(data):
        hits.append(Hit(KIND_DUMP, identity, secrets=secrets))
    kind = archive_kind(data)
    if kind is not None and not (kind in WEAK_ARCHIVE and _looks_text(data)):
        hits.append(Hit(KIND_ARCHIVE, identity, secrets=secrets))
        return hits
    if _png_has_trailing(data):
        hits.append(Hit(KIND_PNG_TRAIL, identity, secrets=secrets))
        return hits
    if _looks_text(data):
        hits.extend(scan_text(identity, data.decode("utf-8"), secrets))
        return hits
    if not (_is_dump_name(identity) or _has_pgdmp_magic(data)):
        hits.append(Hit(KIND_BINARY, identity, secrets=secrets))
    return hits


def _rel_path(root: Path, path: Path) -> str:
    rel = os.path.relpath(os.fspath(path), os.fspath(root))
    if rel in (".", os.curdir):
        return path.name
    return rel.replace(os.sep, "/")


def _casefold_collisions(names: list[str]) -> set[str]:
    groups: dict[str, list[str]] = {}
    for name in names:
        groups.setdefault(name.casefold(), []).append(name)
    collided: set[str] = set()
    for group in groups.values():
        if len(group) > 1:
            collided.update(group)
    return collided


def _scan_directory(
    root: Path,
    secrets: tuple[str, ...],
    digests: dict[Identity, str],
    announced: set[Identity],
    budget: list[int],
) -> list[Hit]:
    hits: list[Hit] = []

    def _onerror(err: OSError) -> None:
        name = getattr(err, "filename", None) or ""
        rel = _rel_path(root, Path(name)) if name else root.name
        hits.append(Hit(KIND_UNREADABLE, (rel,), secrets=secrets))

    for dirpath, dirnames, filenames in os.walk(
        os.fspath(root), followlinks=False, topdown=True, onerror=_onerror
    ):
        dirnames.sort()
        filenames.sort()
        collided = _casefold_collisions(dirnames + filenames)
        keep: list[str] = []
        for name in dirnames:
            child = Path(dirpath) / name
            rel = _rel_path(root, child)
            identity = (rel,)
            if name in collided or is_unsafe_name(rel):
                hits.append(Hit(KIND_UNSAFE, identity, secrets=secrets))
            hits.extend(scan_name(identity, rel, secrets))
            try:
                st = os.lstat(child)
            except OSError:
                continue
            if _special_kind(st.st_mode):
                hits.append(Hit(KIND_LINK, identity, secrets=secrets))
                continue
            keep.append(name)
        dirnames[:] = keep
        for name in filenames:
            child = Path(dirpath) / name
            rel = _rel_path(root, child)
            identity = (rel,)
            if name in collided or is_unsafe_name(rel):
                hits.append(Hit(KIND_UNSAFE, identity, secrets=secrets))
            hits.extend(scan_name(identity, rel, secrets))
            try:
                st = os.lstat(child)
            except OSError:
                continue
            if _special_kind(st.st_mode):
                hits.append(Hit(KIND_LINK, identity, secrets=secrets))
                continue
            if not stat.S_ISREG(st.st_mode):
                hits.append(Hit(KIND_LINK, identity, secrets=secrets))
                continue
            if st.st_size > MAX_SCAN_BYTES:
                hits.append(Hit(KIND_SIZE_CAP, identity, secrets=secrets))
                continue
            budget[0] += st.st_size
            if budget[0] > MAX_SCAN_BYTES:
                hits.append(Hit(KIND_SIZE_CAP, identity, secrets=secrets))
                continue
            try:
                data = _read_nofollow(child)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENXIO, errno.EPERM):
                    hits.append(Hit(KIND_LINK, identity, secrets=secrets))
                    continue
                hits.append(Hit(KIND_UNREADABLE, identity, secrets=secrets))
                continue
            hits.extend(_scan_payload(identity, data, secrets, digests, announced))
    return hits


def scan_path(
    path: Path,
    secrets: tuple[str, ...] = (),
    allowlist: tuple[AllowlistEntry, ...] | list[AllowlistEntry] = (),
) -> list[str]:
    digests: dict[Identity, str] = {}
    announced: set[Identity] = set()
    budget = [0]
    shown = redact_name_path(str(path), secrets)
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise SystemExit(f"ERROR: evidence path not found: {shown}") from exc
    root_id: Identity = (path.name,)
    if _special_kind(st.st_mode):
        hits = [Hit(KIND_LINK, root_id, secrets=secrets)]
        return [hit.format() for hit in filter_allowlist_hits(hits, allowlist, digests)]
    if stat.S_ISDIR(st.st_mode):
        hits = scan_name((path.name,), path.name, secrets)
        hits.extend(_scan_directory(path, secrets, digests, announced, budget))
        return [hit.format() for hit in filter_allowlist_hits(hits, allowlist, digests)]
    raise SystemExit(f"ERROR: {shown} is not a directory")


def _resolve_allowlist(
    args: argparse.Namespace,
    secrets: tuple[str, ...] = (),
) -> tuple[AllowlistEntry, ...]:
    if args.no_allowlist:
        return ()
    allow_path = (
        Path(args.allowlist).expanduser() if args.allowlist else DEFAULT_ALLOWLIST
    )
    if args.allowlist and not allow_path.is_file():
        shown = redact_name_path(str(allow_path), secrets)
        raise SystemExit(f"ERROR: allowlist not found: {shown}")
    if not allow_path.is_file():
        return ()
    return tuple(load_allowlist(allow_path, secrets))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence",
        help="Evidence directory to scan before it is packed or shared.",
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
            "Reviewed allowlist JSON (canonical path plus sha256, with "
            "reviewed_by, approved_by, and date). Defaults to "
            "scripts/uat_evidence_allowlist.json."
        ),
    )
    parser.add_argument(
        "--no-allowlist",
        action="store_true",
        help="Scan with no reviewed allowlist.",
    )
    args = parser.parse_args(argv)
    target = Path(args.evidence)
    secrets_path = Path(args.secrets_file).expanduser() if args.secrets_file else None
    try:
        secrets = load_scan_secrets(secrets_file=secrets_path)
        allowlist = _resolve_allowlist(args, secrets)
    except SystemExit as exc:
        message = str(exc)
        if message:
            print(message, file=sys.stderr)
        return 2
    if not target.exists() and not os.path.lexists(target):
        shown = redact_name_path(str(target), secrets)
        print(f"ERROR: evidence path not found: {shown}", file=sys.stderr)
        return 2
    try:
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
    print(f"evidence scan clean: {redact_name_path(str(target), secrets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
