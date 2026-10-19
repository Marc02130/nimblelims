#!/usr/bin/env python3
"""Refuse to share a UAT evidence folder or tarball that contains secrets.

Exit 0 when the tree is clean. Exit 1 and list hits when it finds any of:

- a ``printed once`` header
- a 24-character token drawn from the dev password pool
- a bcrypt hash marker (``$2a$``, ``$2b$``, ``$2y$``)
- a file whose name ends in ``.dump``

Hits name the file and the line. They do not repeat the secret.
"""
from __future__ import annotations

import argparse
import re
import sys
import tarfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.dev_passwords import DEV_PASSWORD_LENGTH, DEV_PASSWORD_POOL  # noqa: E402

PRINTED_ONCE_HEADER = "printed once"
BCRYPT_RE = re.compile(r"\$2[aby]\$")
_POOL = set(DEV_PASSWORD_POOL)


def pool_token_on_line(line: str) -> bool:
    """True when a run of pool characters is exactly one generated password."""
    length = 0
    for char in line:
        if char in _POOL:
            length += 1
            continue
        if length == DEV_PASSWORD_LENGTH:
            return True
        length = 0
    return length == DEV_PASSWORD_LENGTH


def scan_text(name: str, text: str) -> list[str]:
    hits: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if PRINTED_ONCE_HEADER in line:
            hits.append(f"HIT printed-once header: {name}:{number}")
        if BCRYPT_RE.search(line):
            hits.append(f"HIT bcrypt hash: {name}:{number}")
        if pool_token_on_line(line):
            hits.append(f"HIT password-pool token: {name}:{number}")
    return hits


def _is_dump(name: str) -> bool:
    return Path(name).name.lower().endswith(".dump")


def scan_path(path: Path) -> list[str]:
    if path.is_dir():
        return _scan_directory(path)
    if tarfile.is_tarfile(path):
        return _scan_tar(path)
    raise SystemExit(f"ERROR: {path} is not a directory or a tarball")


def _scan_directory(root: Path) -> list[str]:
    hits: list[str] = []
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root).as_posix()
        if _is_dump(relative):
            hits.append(f"HIT dump file: {relative}")
        hits.extend(scan_text(relative, _read_text(file_path)))
    return hits


def _scan_tar(path: Path) -> list[str]:
    hits: list[str] = []
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            name = member.name
            if member.isdir():
                continue
            if _is_dump(name):
                hits.append(f"HIT dump file: {name}")
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            text = extracted.read().decode("utf-8", errors="replace")
            hits.extend(scan_text(name, text))
    return hits


def _read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence",
        help="Evidence directory or tarball to scan before it is shared.",
    )
    args = parser.parse_args(argv)
    target = Path(args.evidence)
    if not target.exists():
        print(f"ERROR: evidence path not found: {target}", file=sys.stderr)
        return 2
    hits = scan_path(target)
    if hits:
        for hit in hits:
            print(hit, file=sys.stderr)
        print(f"ERROR: {len(hits)} evidence hit(s); refusing to share", file=sys.stderr)
        return 1
    print(f"evidence scan clean: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
