"""The pack helper scans first and never writes a dirty .tgz."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import subprocess
import tarfile
from pathlib import Path

from app.core.dev_passwords import generate_dev_password

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


def _run_pack(args: list[str], planted: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["python3", str(PACK), *args],
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
