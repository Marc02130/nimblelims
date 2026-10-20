"""The pack helper scans first and never writes a dirty .tgz."""
from __future__ import annotations

import hashlib
import importlib.util
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
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    assert digest in packed.stdout
    assert sidecar.read_text(encoding="utf-8").startswith(digest)
    names = tarfile.open(output, "r:gz").getnames()
    assert names
    assert all(not name.startswith("./") for name in names)
    assert any(name == "round-r38" or name.startswith("round-r38/") for name in names)
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
