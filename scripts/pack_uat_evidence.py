#!/usr/bin/env python3
"""Scan a UAT evidence folder, then pack it only if the scan is clean.

Usage:

    python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz
    python scripts/pack_uat_evidence.py --verify evidence.tgz

The pack step writes a temp archive with
``tar -C <parent> -czf <temp> --owner=0 --group=0 --numeric-owner
--sort=name --mtime=@0 -- <dir>`` (no ``./``), extracts and scans that
temp archive, and only then renames it into place and writes the
sidecar. A dirty folder or a dirty packed result produces no ``.tgz``.
The SHA-256 of a successful pack is printed next to the scan result and
written to ``<name>.tgz.sha256``.

Verify requires the sidecar and a matching SHA-256. It extracts with
``tar -C <tmp> -xzf <name>.tgz``, requires exactly one top-level entry
that ``lstat`` says is a real directory, scans the whole extraction
root (must be clean), and compares the hash.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SCANNER = Path(__file__).resolve().parent / "scan_uat_evidence.py"
TAR_MTIME = "@0"
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def _after_scan_hook(folder: Path) -> None:
    """Test hook. Runs after the folder scan and before tar."""
    del folder


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _create_excl(path: Path, body: bytes | None = None) -> None:
    fd = os.open(os.fspath(path), _CREATE_FLAGS, 0o600)
    try:
        if body:
            os.write(fd, body)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def _unlink_if_exists(path: Path) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        return


def _run_scan(folder: Path, extra: list[str]) -> int:
    proc = subprocess.run(
        [sys.executable, str(SCANNER), str(folder), *extra],
        check=False,
    )
    return proc.returncode


def _path_uses_symlink(path: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent


def _output_error(folder: Path, output: Path) -> str | None:
    sidecar = Path(str(output) + ".sha256")
    if output.is_symlink() or os.path.lexists(output):
        return f"ERROR: output already exists: {output}"
    if sidecar.is_symlink() or os.path.lexists(sidecar):
        return f"ERROR: sidecar already exists: {sidecar}"
    if _path_uses_symlink(output):
        return f"ERROR: refuse output through a symlink: {output}"
    try:
        dest = output.parent.resolve() / output.name
        dest.relative_to(folder.resolve())
    except ValueError:
        return None
    except OSError:
        return f"ERROR: cannot resolve output path: {output}"
    return f"ERROR: refuse output inside the scanned folder: {output}"


def _tar_pack(parent: Path, name: str, dest: Path) -> int:
    built = subprocess.run(
        [
            "tar",
            "-C",
            str(parent),
            "-czf",
            str(dest),
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "--sort=name",
            f"--mtime={TAR_MTIME}",
            "--",
            name,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if built.returncode != 0:
        if built.stderr:
            print(built.stderr, file=sys.stderr, end="")
        print("ERROR: tar pack failed", file=sys.stderr)
    return built.returncode


def _top_level_entries(root: Path) -> list[Path]:
    return [root / name for name in sorted(os.listdir(root))]


def extract_and_scan(archive: Path, extra_scan: list[str]) -> int:
    """Extract ``archive`` and scan the whole extraction root."""
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
        kids = _top_level_entries(extract)
        if len(kids) != 1:
            print("ERROR: pack must contain exactly one top-level entry", file=sys.stderr)
            return 1
        try:
            st = os.lstat(kids[0])
        except OSError:
            print("ERROR: pack top-level entry is unreadable", file=sys.stderr)
            return 1
        if not stat.S_ISDIR(st.st_mode):
            print(
                "ERROR: pack top-level entry must be a real directory",
                file=sys.stderr,
            )
            return 1
        return _run_scan(extract, extra_scan)


def pack_folder(
    folder: Path,
    output: Path,
    extra_scan: list[str],
) -> int:
    try:
        root_st = os.lstat(folder)
    except OSError:
        print(f"ERROR: evidence path not found: {folder}", file=sys.stderr)
        return 2
    if stat.S_ISLNK(root_st.st_mode):
        print("ERROR: refuse to pack a symlinked evidence root", file=sys.stderr)
        return 2
    if not stat.S_ISDIR(root_st.st_mode):
        print(f"ERROR: evidence path is not a directory: {folder}", file=sys.stderr)
        return 2
    folder = folder.resolve()
    if output.is_absolute():
        output = Path(os.fsdecode(os.path.abspath(output)))
    else:
        output = Path.cwd() / output
    problem = _output_error(folder, output)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    code = _run_scan(folder, extra_scan)
    if code != 0:
        return code
    _after_scan_hook(folder)
    parent = folder.parent
    name = folder.name
    if name.startswith("./") or name in (".", "..") or "/" in name:
        print(
            f"ERROR: refuse to pack non-canonical directory name: {name}",
            file=sys.stderr,
        )
        return 2
    temp = output.parent / f".{output.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    try:
        _create_excl(temp)
    except OSError as exc:
        print(f"ERROR: cannot create temp pack: {exc}", file=sys.stderr)
        return 2
    try:
        built = _tar_pack(parent, name, temp)
        if built != 0:
            return 2
        os.chmod(temp, 0o600)
        verify_code = extract_and_scan(temp, extra_scan)
        if verify_code != 0:
            return verify_code
        try:
            os.link(temp, output)
        except OSError as exc:
            print(f"ERROR: cannot publish pack: {exc}", file=sys.stderr)
            return 2
        os.chmod(output, 0o600)
        digest = _sha256_file(output)
        sidecar = Path(str(output) + ".sha256")
        try:
            _create_excl(sidecar, f"{digest}  {output.name}\n".encode("utf-8"))
        except OSError as exc:
            _unlink_if_exists(output)
            print(f"ERROR: cannot write sidecar: {exc}", file=sys.stderr)
            return 2
    finally:
        _unlink_if_exists(temp)
    print(f"packed: {output}")
    print(f"sha256: {digest}")
    return 0


def verify_pack(archive: Path, extra_scan: list[str]) -> int:
    archive = archive.resolve()
    if not archive.is_file() or archive.is_symlink():
        print(f"ERROR: pack not found: {archive}", file=sys.stderr)
        return 2
    digest = _sha256_file(archive)
    sidecar = Path(str(archive) + ".sha256")
    try:
        side_st = os.lstat(sidecar)
    except OSError:
        print("ERROR: pack sidecar is missing", file=sys.stderr)
        return 1
    if stat.S_ISLNK(side_st.st_mode) or not stat.S_ISREG(side_st.st_mode):
        print("ERROR: pack sidecar is missing", file=sys.stderr)
        return 1
    recorded = sidecar.read_text(encoding="utf-8").split()[0]
    if recorded != digest:
        print("ERROR: pack sha256 does not match sidecar", file=sys.stderr)
        return 1
    code = extract_and_scan(archive, extra_scan)
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
    if args.output:
        output = Path(args.output)
    else:
        output = folder.resolve().parent / f"{folder.resolve().name}.tgz"
    return pack_folder(folder, output, extra)


if __name__ == "__main__":
    sys.exit(main())
