#!/usr/bin/env python3
"""Scan a UAT evidence folder, then pack it only if the scan is clean.

Usage:

    python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz
    python scripts/pack_uat_evidence.py --verify evidence.tgz

The pack step requires GNU tar and GNU gzip (``tar --version`` and
``gzip --version``). On macOS put ``gtar`` and ``ggzip`` first on
``PATH``. It writes a temp archive with ``--format=gnu`` and
``gzip -n -9`` (no name or mtime in the gzip header, compression
level 9):

    tar --format=gnu -C <parent> -cf <temp> --owner=0 --group=0
        --numeric-owner --sort=name --mtime=@0 --mode=u=rwX,go=
        --use-compress-program='gzip -n -9' -- <dir>

(no ``./``). Modes are normalized so the SHA-256 does not depend on
the operator umask or the source file modes. It extracts that temp
archive with ``-p`` (same permissions), requires exactly one
top-level real directory, scans that directory as the evidence root
(so allowlist paths stay ``ui/...png``), name-scans the directory's
own name, rebuilds with the same flags, and requires a byte-identical
SHA-256. Only then is the archive renamed into place and recorded in
``<name>.tgz.sha256``. Pack and verify need the same tar and gzip
implementation. A dirty folder or a dirty packed result produces no
``.tgz``. Failed tar stderr is redacted for pool tokens and
configured secrets before it is printed.

Verify requires a sidecar line ``^[0-9a-f]{64}  <archive-name>$``,
extracts with ``-p``, scans the single evidence directory, and
requires a byte-identical rebuild.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SCANNER = Path(__file__).resolve().parent / "scan_uat_evidence.py"
TAR_MTIME = "@0"
TAR_MODE = "u=rwX,go="
TAR_BIN = "tar"
GZIP_BIN = "gzip"
TAR_COMPRESS = "gzip -n -9"
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_SIDECAR_RE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def _load_scanner():
    name = "scan_uat_evidence"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, SCANNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scan_uat_evidence")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_SCAN = _load_scanner()


def _is_gnu(path: str) -> bool:
    proc = subprocess.run(
        [path, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    text = f"{proc.stdout}{proc.stderr}"
    return proc.returncode == 0 and "GNU" in text


def require_gnu_tools() -> int:
    """Refuse unless GNU tar and GNU gzip are on PATH (gtar/ggzip allowed)."""
    global TAR_BIN, GZIP_BIN, TAR_COMPRESS
    tar = None
    for name in ("tar", "gtar"):
        path = shutil.which(name)
        if path and _is_gnu(path):
            tar = path
            break
    gzip_path = None
    for name in ("gzip", "ggzip"):
        path = shutil.which(name)
        if path and _is_gnu(path):
            gzip_path = path
            break
    if tar is None:
        print(
            "ERROR: tar must be GNU tar; run pack and verify on Linux "
            "or put gtar first on PATH",
            file=sys.stderr,
        )
        return 2
    if gzip_path is None:
        print(
            "ERROR: gzip must be GNU gzip; run pack and verify on Linux "
            "or put ggzip first on PATH",
            file=sys.stderr,
        )
        return 2
    TAR_BIN = tar
    GZIP_BIN = gzip_path
    TAR_COMPRESS = f"{gzip_path} -n -9"
    return 0


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


def tar_pack_argv(parent: Path, name: str, dest: Path) -> list[str]:
    """Exact GNU tar command used to pack. Tests assert ``--`` stays in place."""
    return [
        TAR_BIN,
        "--format=gnu",
        "-C",
        str(parent),
        "-cf",
        str(dest),
        "--owner=0",
        "--group=0",
        "--numeric-owner",
        "--sort=name",
        f"--mtime={TAR_MTIME}",
        f"--mode={TAR_MODE}",
        f"--use-compress-program={TAR_COMPRESS}",
        "--",
        name,
    ]


def _secrets_from_extra(extra: list[str]) -> tuple[str, ...]:
    secrets_file = None
    index = 0
    while index < len(extra):
        if extra[index] == "--secrets-file" and index + 1 < len(extra):
            secrets_file = Path(extra[index + 1])
            index += 2
            continue
        index += 1
    return _SCAN.load_scan_secrets(secrets_file=secrets_file)


def _print_tar_stderr(text: str, secrets: tuple[str, ...]) -> None:
    if not text:
        return
    print(_SCAN.redact_text(text, secrets), file=sys.stderr, end="")


def _tar_pack(
    parent: Path,
    name: str,
    dest: Path,
    secrets: tuple[str, ...] = (),
) -> int:
    built = subprocess.run(
        tar_pack_argv(parent, name, dest),
        check=False,
        capture_output=True,
        text=True,
    )
    if built.returncode != 0:
        _print_tar_stderr(built.stderr, secrets)
        print("ERROR: tar pack failed", file=sys.stderr)
    return built.returncode


def tar_extract_argv(archive: Path, dest: Path) -> list[str]:
    """Extract with ``-p`` so stored modes survive the operator umask."""
    return [
        TAR_BIN,
        "-C",
        str(dest),
        "-xpf",
        str(archive),
        f"--use-compress-program={TAR_COMPRESS}",
    ]


def _tar_extract(
    archive: Path,
    dest: Path,
    secrets: tuple[str, ...] = (),
) -> int:
    unpacked = subprocess.run(
        tar_extract_argv(archive, dest),
        check=False,
        capture_output=True,
        text=True,
    )
    if unpacked.returncode != 0:
        _print_tar_stderr(unpacked.stderr, secrets)
        print("ERROR: tar extract failed", file=sys.stderr)
    return unpacked.returncode


def _top_level_entries(root: Path) -> list[Path]:
    return [root / name for name in sorted(os.listdir(root))]


def _read_sidecar(sidecar: Path, archive_name: str) -> str | None:
    try:
        side_st = os.lstat(sidecar)
    except OSError:
        print("ERROR: pack sidecar is missing", file=sys.stderr)
        return None
    if stat.S_ISLNK(side_st.st_mode) or not stat.S_ISREG(side_st.st_mode):
        print("ERROR: pack sidecar is missing", file=sys.stderr)
        return None
    lines = sidecar.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1:
        print("ERROR: pack sidecar is not a single hash line", file=sys.stderr)
        return None
    matched = _SIDECAR_RE.fullmatch(lines[0])
    if matched is None or matched.group(2) != archive_name:
        print("ERROR: pack sidecar is not a valid hash line", file=sys.stderr)
        return None
    return matched.group(1)


def extract_and_scan(archive: Path, extra_scan: list[str]) -> int:
    """Extract, scan the evidence directory, and require a byte-identical rebuild."""
    secrets = _secrets_from_extra(extra_scan)
    with tempfile.TemporaryDirectory(dir=str(archive.parent)) as tmp:
        work = Path(tmp)
        extract = work / "tree"
        extract.mkdir()
        if _tar_extract(archive, extract, secrets) != 0:
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
        code = _run_scan(kids[0], extra_scan)
        if code != 0:
            return code
        rebuilt = work / "rebuilt.tgz"
        if _tar_pack(extract, kids[0].name, rebuilt, secrets) != 0:
            return 2
        if _sha256_file(rebuilt) != _sha256_file(archive):
            print(
                "ERROR: pack is not a byte-identical rebuild",
                file=sys.stderr,
            )
            return 1
        return 0


def pack_folder(
    folder: Path,
    output: Path,
    extra_scan: list[str],
) -> int:
    tools = require_gnu_tools()
    if tools != 0:
        return tools
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
    pack_secrets = _secrets_from_extra(extra_scan)
    try:
        _create_excl(temp)
    except OSError as exc:
        print(f"ERROR: cannot create temp pack: {exc}", file=sys.stderr)
        return 2
    try:
        built = _tar_pack(parent, name, temp, pack_secrets)
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
    tools = require_gnu_tools()
    if tools != 0:
        return tools
    try:
        st = os.lstat(archive)
    except OSError:
        print(f"ERROR: pack not found: {archive}", file=sys.stderr)
        return 2
    if stat.S_ISLNK(st.st_mode):
        print("ERROR: refuse a symlinked pack", file=sys.stderr)
        return 2
    if not stat.S_ISREG(st.st_mode):
        print(f"ERROR: pack not found: {archive}", file=sys.stderr)
        return 2
    archive = archive.resolve()
    digest = _sha256_file(archive)
    sidecar = Path(str(archive) + ".sha256")
    recorded = _read_sidecar(sidecar, archive.name)
    if recorded is None:
        return 1
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
