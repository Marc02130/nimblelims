#!/usr/bin/env python3
"""Scan a UAT evidence folder, then pack it only if the scan is clean.

Usage:

    python scripts/pack_uat_evidence.py /path/to/evidence --output evidence.tgz
    python scripts/pack_uat_evidence.py --verify evidence.tgz

The pack step requires GNU tar and GNU gzip (``tar --version`` and
``gzip --version``). On macOS install Homebrew ``gnu-tar`` and
``gzip`` and put ``/opt/homebrew/bin`` first on ``PATH`` (Homebrew
gzip is ``gzip``; gnu-tar is ``gtar``, or ``tar`` via gnubin). It
writes a temp archive with ``--format=gnu`` and
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
``.tgz``. Failed tar stderr is redacted JWTs first (tar-unescape
and NFKC, then encoded runs after percent-decoding until
unchanged (max 3, including ``%u002E``), then raw tokens), then
configured secrets, then pool windows, before
it is printed. Every printed path goes through
``redact_name_path``. An archive or output name that matches a
secret rule is refused. Sidecar names are redacted the same way.

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
_HOMEBREW_DIRS = (
    "/opt/homebrew/bin",
    "/opt/homebrew/opt/gnu-tar/libexec/gnubin",
    "/opt/homebrew/opt/gzip/libexec/gnubin",
    "/usr/local/bin",
    "/usr/local/opt/gnu-tar/libexec/gnubin",
    "/usr/local/opt/gzip/libexec/gnubin",
)


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


def _shown_path(path: Path | str, secrets: tuple[str, ...] = ()) -> str:
    return _SCAN.redact_name_path(str(path), secrets)


def _secret_named(path: Path, secrets: tuple[str, ...]) -> bool:
    """True when a path name or stem matches a JWT, pool, or secret rule."""
    names: set[str] = {path.name, path.stem}
    for part in path.parts:
        if part in {"/", ".", "..", ""}:
            continue
        names.add(part)
        stem = Path(part).stem
        if stem:
            names.add(stem)
    return any(_SCAN._segment_is_secret(name, secrets) for name in names)


def _is_gnu(path: str) -> bool:
    proc = subprocess.run(
        [path, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    text = f"{proc.stdout}{proc.stderr}"
    return proc.returncode == 0 and "GNU" in text


def _find_gnu(names: tuple[str, ...]) -> str | None:
    """Return the first GNU binary among PATH names and Homebrew prefixes."""
    seen: set[str] = set()
    candidates: list[str] = []
    for name in names:
        path = shutil.which(name)
        if path:
            candidates.append(path)
    for directory in _HOMEBREW_DIRS:
        for name in names:
            candidates.append(str(Path(directory) / name))
    for path in candidates:
        if path in seen or not os.path.isfile(path):
            continue
        if not os.access(path, os.X_OK):
            continue
        seen.add(path)
        if _is_gnu(path):
            return path
    return None


def require_gnu_tools() -> int:
    """Refuse unless GNU tar and GNU gzip are available.

    Accepts ``tar``/``gtar`` and ``gzip`` on PATH, including Homebrew
    ``gnu-tar`` (``gtar``, or ``tar`` via gnubin) and Homebrew ``gzip``.
    """
    global TAR_BIN, GZIP_BIN, TAR_COMPRESS
    tar = _find_gnu(("tar", "gtar"))
    gzip_path = _find_gnu(("gzip",))
    if tar is None:
        print(
            "ERROR: tar must be GNU tar; run pack and verify on Linux "
            "or install Homebrew gnu-tar and put /opt/homebrew/bin first "
            "on PATH",
            file=sys.stderr,
        )
        return 2
    if gzip_path is None:
        print(
            "ERROR: gzip must be GNU gzip; run pack and verify on Linux "
            "or install Homebrew gzip and put /opt/homebrew/bin first "
            "on PATH",
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


def _output_error(
    folder: Path,
    output: Path,
    secrets: tuple[str, ...] = (),
) -> str | None:
    sidecar = Path(str(output) + ".sha256")
    shown_out = _shown_path(output, secrets)
    shown_side = _shown_path(sidecar, secrets)
    if _secret_named(output, secrets):
        return f"ERROR: refuse output name that matches a secret rule: {shown_out}"
    if _secret_named(sidecar, secrets):
        return f"ERROR: refuse sidecar name that matches a secret rule: {shown_side}"
    if output.is_symlink() or os.path.lexists(output):
        return f"ERROR: output already exists: {shown_out}"
    if sidecar.is_symlink() or os.path.lexists(sidecar):
        return f"ERROR: sidecar already exists: {shown_side}"
    if _path_uses_symlink(output):
        return f"ERROR: refuse output through a symlink: {shown_out}"
    try:
        dest = output.parent.resolve() / output.name
        dest.relative_to(folder.resolve())
    except ValueError:
        return None
    except OSError:
        return f"ERROR: cannot resolve output path: {shown_out}"
    return f"ERROR: refuse output inside the scanned folder: {shown_out}"


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
    try:
        return _SCAN.load_scan_secrets(secrets_file=secrets_file)
    except SystemExit as exc:
        message = str(exc)
        if message:
            print(message, file=sys.stderr)
        raise SystemExit(2) from exc


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
    pack_secrets = _secrets_from_extra(extra_scan)
    try:
        root_st = os.lstat(folder)
    except OSError:
        print(
            f"ERROR: evidence path not found: {_shown_path(folder, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    if stat.S_ISLNK(root_st.st_mode):
        print("ERROR: refuse to pack a symlinked evidence root", file=sys.stderr)
        return 2
    if not stat.S_ISDIR(root_st.st_mode):
        print(
            "ERROR: evidence path is not a directory: "
            f"{_shown_path(folder, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    folder = folder.resolve()
    if output.is_absolute():
        output = Path(os.fsdecode(os.path.abspath(output)))
    else:
        output = Path.cwd() / output
    problem = _output_error(folder, output, pack_secrets)
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
            "ERROR: refuse to pack non-canonical directory name: "
            f"{_shown_path(name, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    temp = output.parent / f".{output.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp"
    try:
        _create_excl(temp)
    except OSError as exc:
        shown_exc = _SCAN.redact_text(str(exc), pack_secrets)
        print(f"ERROR: cannot create temp pack: {shown_exc}", file=sys.stderr)
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
            shown_exc = _SCAN.redact_text(str(exc), pack_secrets)
            print(f"ERROR: cannot publish pack: {shown_exc}", file=sys.stderr)
            return 2
        os.chmod(output, 0o600)
        digest = _sha256_file(output)
        sidecar = Path(str(output) + ".sha256")
        try:
            _create_excl(sidecar, f"{digest}  {output.name}\n".encode("utf-8"))
        except OSError as exc:
            _unlink_if_exists(output)
            shown_exc = _SCAN.redact_text(str(exc), pack_secrets)
            print(f"ERROR: cannot write sidecar: {shown_exc}", file=sys.stderr)
            return 2
    finally:
        _unlink_if_exists(temp)
    print(f"packed: {_shown_path(output, pack_secrets)}")
    print(f"sha256: {digest}")
    return 0


def verify_pack(archive: Path, extra_scan: list[str]) -> int:
    tools = require_gnu_tools()
    if tools != 0:
        return tools
    pack_secrets = _secrets_from_extra(extra_scan)
    try:
        st = os.lstat(archive)
    except OSError:
        print(
            f"ERROR: pack not found: {_shown_path(archive, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    if stat.S_ISLNK(st.st_mode):
        print("ERROR: refuse a symlinked pack", file=sys.stderr)
        return 2
    if not stat.S_ISREG(st.st_mode):
        print(
            f"ERROR: pack not found: {_shown_path(archive, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    if _secret_named(archive, pack_secrets):
        print(
            "ERROR: refuse archive name that matches a secret rule: "
            f"{_shown_path(archive, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    archive = archive.resolve()
    digest = _sha256_file(archive)
    sidecar = Path(str(archive) + ".sha256")
    if _secret_named(sidecar, pack_secrets):
        print(
            "ERROR: refuse sidecar name that matches a secret rule: "
            f"{_shown_path(sidecar, pack_secrets)}",
            file=sys.stderr,
        )
        return 2
    recorded = _read_sidecar(sidecar, archive.name)
    if recorded is None:
        return 1
    if recorded != digest:
        print("ERROR: pack sha256 does not match sidecar", file=sys.stderr)
        return 1
    code = extract_and_scan(archive, extra_scan)
    if code != 0:
        return code
    print(f"verify clean: {_shown_path(archive, pack_secrets)}")
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
    try:
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
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 2


if __name__ == "__main__":
    sys.exit(main())
