"""The evidence scan refuses secrets before a folder is shared."""
from __future__ import annotations

import importlib.util
import tarfile
from pathlib import Path

from app.core.dev_passwords import DEV_PASSWORD_LENGTH

_SPEC = importlib.util.spec_from_file_location(
    "scan_uat_evidence",
    Path(__file__).resolve().parents[2] / "scripts" / "scan_uat_evidence.py",
)
scan = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(scan)

scan_main = scan.main
pool_token_on_line = scan.pool_token_on_line
TOKEN = "Aa1!" + ("b" * (DEV_PASSWORD_LENGTH - 4))
LONG_TOKEN = TOKEN + ("c" * 6)


def test_pool_token_is_twenty_four_or_more():
    assert len(TOKEN) == DEV_PASSWORD_LENGTH
    assert len(LONG_TOKEN) == 30
    assert pool_token_on_line(TOKEN) is True
    assert pool_token_on_line(LONG_TOKEN) is True
    assert pool_token_on_line("a" * (DEV_PASSWORD_LENGTH - 1)) is False
    assert pool_token_on_line("ab" * 32) is True
    assert pool_token_on_line("see " + TOKEN + " now") is True
    assert pool_token_on_line("see " + LONG_TOKEN + " now") is True


def test_clean_evidence_exits_zero(tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("sample id 123\n", encoding="utf-8")
    assert scan_main([str(tmp_path)]) == 0
    assert "clean" in capsys.readouterr().out


def test_directory_lists_header_token_bcrypt_and_dump(tmp_path, capsys):
    (tmp_path / "log.txt").write_text(
        "admin (DEV_SEED_ADMIN_PASSWORD was unset; printed once):\n"
        f"{TOKEN}\n"
        "stored $2a$06$not-a-real-hash\n"
        "also $2y$10$not-a-real-hash\n",
        encoding="utf-8",
    )
    (tmp_path / "lims.dump").write_bytes(b"PGDMP")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT printed-once header: log.txt:1" in err
    assert "HIT password-pool token: log.txt:2" in err
    assert "HIT bcrypt hash: log.txt:3" in err
    assert "HIT bcrypt hash: log.txt:4" in err
    assert "HIT dump file: lims.dump" in err
    assert TOKEN not in err


def test_thirty_char_pool_token_is_a_hit(tmp_path, capsys):
    (tmp_path / "long-token.txt").write_text(f"prefix {LONG_TOKEN} suffix\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: long-token.txt:1" in err
    assert LONG_TOKEN not in err


def test_pgdmp_magic_hits_a_renamed_dump(tmp_path, capsys):
    (tmp_path / "renamed-backup.bin").write_bytes(b"PGDMP\x00custom-format")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT dump file: renamed-backup.bin" in err


def test_dump_extension_hits_without_pgdmp_magic(tmp_path, capsys):
    (tmp_path / "users.dump").write_text("not a real dump\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT dump file: users.dump" in err


def test_tarball_lists_bcrypt_dump_and_pgdmp(tmp_path, capsys):
    notes = tmp_path / "notes.txt"
    notes.write_text("prefix $2b$12$abcdefghijklmnopqrstuv suffix\n", encoding="utf-8")
    dump = tmp_path / "users.dump"
    dump.write_text("users\n", encoding="utf-8")
    renamed = tmp_path / "renamed-backup.bin"
    renamed.write_bytes(b"PGDMP\x00custom-format")
    archive = tmp_path / "evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(notes, arcname="notes.txt")
        bundle.add(dump, arcname="round/users.dump")
        bundle.add(renamed, arcname="round/renamed-backup.bin")
    code = scan_main([str(archive)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT bcrypt hash: notes.txt:1" in err
    assert "HIT dump file: round/users.dump" in err
    assert "HIT dump file: round/renamed-backup.bin" in err
    assert "abcdefghijklmnopqrstuv" not in err


def test_missing_evidence_exits_nonzero(tmp_path, capsys):
    missing = tmp_path / "nope"
    assert scan_main([str(missing)]) == 2
    assert "not found" in capsys.readouterr().err


def test_scan_module_path_is_the_repo_script():
    assert Path(scan.__file__).name == "scan_uat_evidence.py"
