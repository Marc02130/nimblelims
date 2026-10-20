#!/usr/bin/env python3
"""Scan a UAT evidence folder, then pack it only if the scan is clean.

Usage:

    python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz
    python scripts/pack_uat_evidence.py --verify evidence.tgz

The pack step is ``tar -C <parent> -czf <name>.tgz <dir>`` (no ``./``).
A dirty folder produces no ``.tgz``. The SHA-256 of a successful pack is
printed next to the scan result and written to ``<name>.tgz.sha256``.

Verify extracts with ``tar -C <tmp> -xzf <name>.tgz``, scans the extracted
folder (must be clean), and compares the hash to the sidecar.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

SCANNER = Path(__file__).resolve().parent / "scan_uat_evidence.py"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_scan(folder: Path, extra: list[str]) -> int:
    proc = subprocess.run(
        [sys.executable, str(SCANNER), str(folder), *extra],
        check=False,
    )
    return proc.returncode


def pack_folder(
    folder: Path,
    output: Path,
    extra_scan: list[str],
) -> int:
    folder = folder.resolve()
    output = output.resolve()
    if not folder.is_dir():
        print(f"ERROR: evidence path is not a directory: {folder}", file=sys.stderr)
        return 2
    if output.exists():
        print(f"ERROR: output already exists: {output}", file=sys.stderr)
        return 2
    code = _run_scan(folder, extra_scan)
    if code != 0:
        return code
    parent = folder.parent
    name = folder.name
    if name.startswith("./") or name in (".", "..") or "/" in name:
        print(f"ERROR: refuse to pack non-canonical directory name: {name}", file=sys.stderr)
        return 2
    built = subprocess.run(
        ["tar", "-C", str(parent), "-czf", str(output), name],
        check=False,
        capture_output=True,
        text=True,
    )
    if built.returncode != 0:
        if output.exists():
            output.unlink()
        if built.stderr:
            print(built.stderr, file=sys.stderr, end="")
        print("ERROR: tar pack failed", file=sys.stderr)
        return 2
    digest = _sha256_file(output)
    sidecar = Path(str(output) + ".sha256")
    sidecar.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"packed: {output}")
    print(f"sha256: {digest}")
    return 0


def verify_pack(archive: Path, extra_scan: list[str]) -> int:
    archive = archive.resolve()
    if not archive.is_file():
        print(f"ERROR: pack not found: {archive}", file=sys.stderr)
        return 2
    digest = _sha256_file(archive)
    sidecar = Path(str(archive) + ".sha256")
    if sidecar.is_file():
        recorded = sidecar.read_text(encoding="utf-8").split()[0]
        if recorded != digest:
            print("ERROR: pack sha256 does not match sidecar", file=sys.stderr)
            return 1
    with tempfile.TemporaryDirectory(dir=str(archive.parent)) as tmp:
        extract = Path(tmp)
        unpacked = subprocess.run(
            ["tar", "-C", str(extract), "-xzf", str(archive)],
            check=False,
            capture_output=True,
            text=True,
        )
        if unpacked.returncode != 0:
            if unpacked.stderr:
                print(unpacked.stderr, file=sys.stderr, end="")
            print("ERROR: tar extract failed", file=sys.stderr)
            return 2
        kids = [child for child in extract.iterdir() if child.is_dir()]
        if len(kids) != 1:
            print("ERROR: pack must contain exactly one directory", file=sys.stderr)
            return 1
        code = _run_scan(kids[0], extra_scan)
        if code != 0:
            return code
    print(f"verify clean: {archive}")
    print(f"sha256: {digest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "evidence",
        nargs="?",
        default="",
        help="Evidence directory to scan and pack.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Destination .tgz (default: <folder>.tgz next to the folder).",
    )
    parser.add_argument(
        "--verify",
        default="",
        help="Verify an existing .tgz: extract, scan, compare sha256.",
    )
    parser.add_argument("--secrets-file", default="")
    parser.add_argument("--allowlist", default="")
    parser.add_argument("--no-allowlist", action="store_true")
    args = parser.parse_args(argv)
    extra: list[str] = []
    if args.secrets_file:
        extra.extend(["--secrets-file", args.secrets_file])
    if args.allowlist:
        extra.extend(["--allowlist", args.allowlist])
    if args.no_allowlist:
        extra.append("--no-allowlist")
    if args.verify:
        return verify_pack(Path(args.verify), extra)
    if not args.evidence:
        print("ERROR: evidence directory is required", file=sys.stderr)
        return 2
    folder = Path(args.evidence)
    output = Path(args.output) if args.output else folder.resolve().parent / f"{folder.resolve().name}.tgz"
    return pack_folder(folder, output, extra)


if __name__ == "__main__":
    sys.exit(main())
