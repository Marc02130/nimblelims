"""The pack helper scans first and never writes a dirty .tgz."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import os
import shlex
import subprocess
import tarfile
import uuid
from pathlib import Path

import pytest
from app.core.dev_passwords import DEV_PASSWORD_LENGTH, generate_dev_password

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "scripts" / "pack_uat_evidence.py"

_SCAN_SPEC = importlib.util.spec_from_file_location(
    "scan_uat_evidence",
    REPO / "scripts" / "scan_uat_evidence.py",
)
scan = importlib.util.module_from_spec(_SCAN_SPEC)
assert _SCAN_SPEC.loader is not None
_SCAN_SPEC.loader.exec_module(scan)

_PACK_SPEC = importlib.util.spec_from_file_location("pack_uat_evidence", PACK)
pack = importlib.util.module_from_spec(_PACK_SPEC)
assert _PACK_SPEC.loader is not None
_PACK_SPEC.loader.exec_module(pack)


def _runtime_pool_token() -> str:
    token = generate_dev_password()
    for _ in range(16):
        if scan.pool_token_on_line(token):
            return token
        token = generate_dev_password()
    raise AssertionError("could not generate a pool token")


def _token_with_symbol(symbol: str) -> str:
    body = "".join(("A", "a", "1", symbol))
    return body + ("b" * (DEV_PASSWORD_LENGTH - len(body)))


def _write_allowlist(path: Path, entries: list[dict[str, object]]) -> Path:
    for entry in entries:
        entry.setdefault("reviewed_by", "Günter (CSO)")
        entry.setdefault("approved_by", "Günter (CSO) 2026-10-19")
        entry.setdefault("date", "2026-10-19")
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return path


def _gzip_n9(data: bytes) -> bytes:
    proc = subprocess.run(
        ["gzip", "-n", "-9"],
        input=data,
        check=True,
        capture_output=True,
    )
    return proc.stdout


def _run_pack(
    args: list[str],
    planted: tuple[str, ...] = (),
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["python3", str(PACK), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    for value in planted:
        assert value not in proc.stdout
        assert value not in proc.stderr
    return proc


def _run_pack_umask(
    umask: str,
    args: list[str],
    planted: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    quoted = " ".join(shlex.quote(part) for part in ["python3", str(PACK), *args])
    proc = subprocess.run(
        ["bash", "-lc", f"umask {umask} && exec {quoted}"],
        check=False,
        capture_output=True,
        text=True,
    )
    for value in planted:
        assert value not in proc.stdout
        assert value not in proc.stderr
    return proc


def _write_sidecar(archive: Path, digest: str | None = None) -> Path:
    sidecar = Path(str(archive) + ".sha256")
    if digest is None:
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return sidecar


def _mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_pack_clean_folder_writes_tgz_hash_and_verifies(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round-r38"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("sample id 123\n", encoding="utf-8")
    output = tmp_path / "round-r38.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    assert output.is_file()
    sidecar = Path(str(output) + ".sha256")
    assert sidecar.is_file()
    assert _mode(output) == 0o600
    assert _mode(sidecar) == 0o600
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    assert digest in packed.stdout
    assert sidecar.read_text(encoding="utf-8").startswith(digest)
    with tarfile.open(output, "r:gz") as bundle:
        names = bundle.getnames()
        assert names
        assert all(not name.startswith("./") for name in names)
        assert any(name == "round-r38" or name.startswith("round-r38/") for name in names)
        for member in bundle.getmembers():
            assert member.uid == 0
            assert member.gid == 0
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode == 0
    assert digest in verified.stdout


def test_pack_dirty_folder_writes_no_tgz(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "dirty"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"note\n{token}\n", encoding="utf-8")
    output = tmp_path / "dirty.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 1
    assert not output.exists()
    assert not Path(str(output) + ".sha256").exists()
    assert "HIT password-pool token:" in packed.stderr


def test_pack_race_after_scan_publishes_nothing(tmp_path, monkeypatch, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"

    def _inject(folder: Path) -> None:
        (folder / "notes.txt").write_text(f"note\n{token}\n", encoding="utf-8")

    monkeypatch.setattr(pack, "_after_scan_hook", _inject)
    code = pack.pack_folder(evidence, output, ["--no-allowlist"])
    captured = capsys.readouterr()
    assert token not in captured.out
    assert token not in captured.err
    assert code == 1
    assert not output.exists()
    assert not Path(str(output) + ".sha256").exists()
    leftovers = [
        path
        for path in tmp_path.iterdir()
        if path.name.endswith(".tmp") or ".tmp." in path.name
    ]
    assert leftovers == []


def test_verify_missing_sidecar_fails(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    Path(str(output) + ".sha256").unlink()
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "sidecar is missing" in verified.stderr


def test_verify_mismatched_sidecar_fails(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    sidecar = Path(str(output) + ".sha256")
    sidecar.write_text(("0" * 64) + f"  {output.name}\n", encoding="utf-8")
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "does not match sidecar" in verified.stderr


def test_verify_extra_top_level_file_with_secret_fails(tmp_path):
    token = _runtime_pool_token()
    archive = tmp_path / "mixed.tgz"
    with tarfile.open(archive, "w:gz") as bundle:
        notes = tarfile.TarInfo(name="round/notes.txt")
        payload = b"ok\n"
        notes.size = len(payload)
        bundle.addfile(notes, io.BytesIO(payload))
        leak = tarfile.TarInfo(name="leak.txt")
        secret = f"{token}\n".encode("utf-8")
        leak.size = len(secret)
        bundle.addfile(leak, io.BytesIO(secret))
    _write_sidecar(archive)
    verified = _run_pack(["--verify", str(archive), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "exactly one top-level entry" in verified.stderr


def test_verify_top_level_symlink_fails(tmp_path):
    token = _runtime_pool_token()
    archive = tmp_path / "link.tgz"
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo(name="round")
        info.type = tarfile.SYMTYPE
        info.linkname = "elsewhere"
        bundle.addfile(info)
    _write_sidecar(archive)
    verified = _run_pack(["--verify", str(archive), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "real directory" in verified.stderr


def test_pack_refuses_symlinked_root(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    linked = tmp_path / "linked"
    linked.symlink_to(evidence)
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(linked), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 2
    assert not output.exists()
    assert "symlinked evidence root" in packed.stderr


def test_pack_refuses_output_inside_folder(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = evidence / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 2
    assert not output.exists()
    assert "inside the scanned folder" in packed.stderr


def test_pack_refuses_symlinked_output_path(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    target = tmp_path / "elsewhere.tgz"
    output = tmp_path / "round.tgz"
    output.symlink_to(target)
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 2
    assert output.is_symlink()
    assert not target.exists()
    assert "already exists" in packed.stderr or "symlink" in packed.stderr


def test_pack_refuses_output_parent_symlink(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    real_dir = tmp_path / "dest"
    real_dir.mkdir()
    linked = tmp_path / "via-link"
    linked.symlink_to(real_dir)
    output = linked / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 2
    assert not (real_dir / "round.tgz").exists()
    assert "symlink" in packed.stderr


def test_pack_and_verify_allowlisted_png(tmp_path):
    token = _runtime_pool_token()
    payload = b"\x89PNG\r\n\x1a\n" + b"utc-reviewed-bytes-r38"
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "uat-r38"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_UTC.png").write_bytes(payload)
    (evidence / "notes.txt").write_text("sample id 123\n", encoding="utf-8")
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "ui/r38_results_UTC.png", "sha256": digest}],
    )
    output = tmp_path / "uat-r38.tgz"
    packed = _run_pack(
        [
            str(evidence),
            "--output",
            str(output),
            "--allowlist",
            str(allow),
        ],
        (token,),
    )
    assert packed.returncode == 0
    assert output.is_file()
    verified = _run_pack(
        ["--verify", str(output), "--allowlist", str(allow)],
        (token,),
    )
    assert verified.returncode == 0


def test_pack_secret_named_root_fails_without_printing(tmp_path):
    token = _token_with_symbol("_")
    evidence = tmp_path / token
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "named.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 1
    assert not output.exists()
    assert not Path(str(output) + ".sha256").exists()
    assert "<redacted name hmac:" in packed.stderr
    assert "HIT password-pool token:" in packed.stderr


def test_verify_duplicate_member_fails(tmp_path):
    token = _runtime_pool_token()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as bundle:
        secret = f"{token}\n".encode("utf-8")
        first = tarfile.TarInfo(name="round/notes.txt")
        first.size = len(secret)
        bundle.addfile(first, io.BytesIO(secret))
        clean = b"ok\n"
        second = tarfile.TarInfo(name="round/notes.txt")
        second.size = len(clean)
        bundle.addfile(second, io.BytesIO(clean))
    archive = tmp_path / "dup.tgz"
    archive.write_bytes(_gzip_n9(raw.getvalue()))
    _write_sidecar(archive)
    verified = _run_pack(["--verify", str(archive), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "byte-identical" in verified.stderr or "exactly one" in verified.stderr


def test_verify_bytes_after_end_marker_fails(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    output.write_bytes(output.read_bytes() + b"\n" + token.encode("utf-8"))
    _write_sidecar(output)
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode != 0
    assert (
        "byte-identical" in verified.stderr
        or "tar extract failed" in verified.stderr
    )


def test_verify_second_gzip_stream_fails(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    extra = gzip.compress(f"{token}\n".encode("utf-8"), compresslevel=9, mtime=0)
    output.write_bytes(output.read_bytes() + extra)
    _write_sidecar(output)
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "byte-identical" in verified.stderr


def test_verify_pax_comment_fails(tmp_path):
    token = _runtime_pool_token()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as bundle:
        info = tarfile.TarInfo(name="round/notes.txt")
        payload = b"ok\n"
        info.size = len(payload)
        info.pax_headers["comment"] = token
        bundle.addfile(info, io.BytesIO(payload))
    archive = tmp_path / "pax.tgz"
    archive.write_bytes(_gzip_n9(raw.getvalue()))
    _write_sidecar(archive)
    verified = _run_pack(["--verify", str(archive), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "byte-identical" in verified.stderr or "tar" in verified.stderr.lower()


def test_pack_refuses_existing_output(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    output.write_bytes(b"already")
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 2
    assert output.read_bytes() == b"already"
    assert "already exists" in packed.stderr


def test_pack_refuses_existing_sidecar(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    sidecar = Path(str(output) + ".sha256")
    sidecar.write_text("old\n", encoding="utf-8")
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 2
    assert not output.exists()
    assert sidecar.read_text(encoding="utf-8") == "old\n"
    assert "already exists" in packed.stderr


def test_tar_pack_argv_keeps_dash_dash_before_name():
    argv = pack.tar_pack_argv(Path("/parent"), "-f", Path("/out.tgz"))
    assert "--" in argv
    assert argv[argv.index("--") + 1] == "-f"
    assert "--format=gnu" in argv
    assert "--mode=u=rwX,go=" in argv
    assert any(
        item.startswith("--use-compress-program=") and "-n" in item and "gzip" in item
        for item in argv
    )


def test_pack_dash_named_folder_succeeds(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "-f"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "dash.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    assert output.is_file()


def test_create_excl_refuses_existing_file(tmp_path):
    token = _runtime_pool_token()
    path = tmp_path / "out.tgz"
    path.write_bytes(b"old")
    with pytest.raises(OSError):
        pack._create_excl(path, b"new")
    assert path.read_bytes() == b"old"
    assert token not in path.read_text(encoding="latin1")


def test_create_excl_refuses_symlink(tmp_path):
    token = _runtime_pool_token()
    target = tmp_path / "real"
    path = tmp_path / "link"
    path.symlink_to(target)
    with pytest.raises(OSError):
        pack._create_excl(path, b"new")
    assert not target.exists()
    assert token not in str(path)


def test_create_without_excl_overwrites(tmp_path, monkeypatch):
    token = _runtime_pool_token()
    path = tmp_path / "out.tgz"
    path.write_bytes(b"old")
    monkeypatch.setattr(
        pack,
        "_CREATE_FLAGS",
        os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW,
    )
    pack._create_excl(path, b"new")
    assert path.read_bytes() == b"new"
    assert token not in path.read_text(encoding="latin1")


def test_create_without_nofollow_writes_through_symlink(tmp_path, monkeypatch):
    token = _runtime_pool_token()
    target = tmp_path / "real"
    target.write_bytes(b"old")
    path = tmp_path / "link"
    path.symlink_to(target)
    monkeypatch.setattr(pack, "_CREATE_FLAGS", os.O_WRONLY | os.O_CREAT)
    pack._create_excl(path, b"new")
    assert target.read_bytes() == b"new"
    assert token not in target.read_text(encoding="latin1")


def test_create_excl_without_nofollow_still_refuses_symlink(tmp_path, monkeypatch):
    token = _runtime_pool_token()
    target = tmp_path / "real"
    path = tmp_path / "link"
    path.symlink_to(target)
    monkeypatch.setattr(
        pack,
        "_CREATE_FLAGS",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
    )
    with pytest.raises(OSError):
        pack._create_excl(path, b"new")
    assert not target.exists()
    assert token not in str(path)


def test_verify_sidecar_wrong_name_fails(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    Path(str(output) + ".sha256").write_text(f"{digest}  other.tgz\n", encoding="utf-8")
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode == 1
    assert "valid hash line" in verified.stderr


def test_pack_refuses_non_gnu_tar(tmp_path, monkeypatch, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    monkeypatch.setattr(pack, "_is_gnu", lambda _path: False)
    code = pack.pack_folder(evidence, output, ["--no-allowlist"])
    captured = capsys.readouterr()
    assert token not in captured.out
    assert token not in captured.err
    assert code == 2
    assert "GNU tar" in captured.err
    assert not output.exists()


def test_verify_bytes_after_tar_end_inside_gzip_fails(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    unzipped = subprocess.run(
        ["gzip", "-n", "-d", "-c", str(output)],
        check=True,
        capture_output=True,
    )
    mutated = unzipped.stdout + (b"\x00" * 512) + token.encode("utf-8")
    output.write_bytes(_gzip_n9(mutated))
    _write_sidecar(output)
    verified = _run_pack(["--verify", str(output), "--no-allowlist"], (token,))
    assert verified.returncode != 0
    assert (
        "byte-identical" in verified.stderr
        or "tar extract failed" in verified.stderr
    )


def test_verify_refuses_symlinked_archive(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    output = tmp_path / "round.tgz"
    packed = _run_pack(
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed.returncode == 0
    linked = tmp_path / "alias.tgz"
    linked.symlink_to(output)
    Path(str(linked) + ".sha256").write_text(
        Path(str(output) + ".sha256").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    verified = _run_pack(["--verify", str(linked), "--no-allowlist"], (token,))
    assert verified.returncode == 2
    assert "symlink" in verified.stderr


def test_pack_verify_is_stable_across_umask_and_mode_change(tmp_path):
    token = _runtime_pool_token()
    evidence = tmp_path / "round"
    evidence.mkdir()
    notes = evidence / "notes.txt"
    notes.write_text("sample id 123\n", encoding="utf-8")
    notes.chmod(0o644)
    output = tmp_path / "round.tgz"
    packed_077 = _run_pack_umask(
        "077",
        [str(evidence), "--output", str(output), "--no-allowlist"],
        (token,),
    )
    assert packed_077.returncode == 0
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    verified_022 = _run_pack_umask(
        "022",
        ["--verify", str(output), "--no-allowlist"],
        (token,),
    )
    assert verified_022.returncode == 0
    notes.chmod(0o664)
    output2 = tmp_path / "round2.tgz"
    packed_022 = _run_pack_umask(
        "022",
        [str(evidence), "--output", str(output2), "--no-allowlist"],
        (token,),
    )
    assert packed_022.returncode == 0
    verified_077 = _run_pack_umask(
        "077",
        ["--verify", str(output2), "--no-allowlist"],
        (token,),
    )
    assert verified_077.returncode == 0
    assert hashlib.sha256(output2.read_bytes()).hexdigest() == digest
    notes.chmod(0o600)
    verified_after_chmod = _run_pack_umask(
        "022",
        ["--verify", str(output), "--no-allowlist"],
        (token,),
    )
    assert verified_after_chmod.returncode == 0


def test_verify_failed_hardlink_redacts_tar_stderr(tmp_path):
    token = _token_with_symbol("_")
    configured = "seed" + uuid.uuid4().hex[:12]
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as bundle:
        root = tarfile.TarInfo(name="round")
        root.type = tarfile.DIRTYPE
        root.mode = 0o700
        bundle.addfile(root)
        leak = tarfile.TarInfo(name=f"round/{token}")
        leak.type = tarfile.LNKTYPE
        leak.linkname = f"round/{configured}"
        bundle.addfile(leak)
    archive = tmp_path / "crafted.tgz"
    archive.write_bytes(_gzip_n9(raw.getvalue()))
    _write_sidecar(archive)
    verified = _run_pack(
        ["--verify", str(archive), "--no-allowlist"],
        (token, configured),
        extra_env={"POSTGRES_PASSWORD": configured},
    )
    assert verified.returncode == 2
    assert "tar extract failed" in verified.stderr
    assert "<redacted name hmac:" in verified.stderr
