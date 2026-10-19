"""The evidence scan refuses secrets before a folder is shared."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import tarfile
import uuid
import zlib
from pathlib import Path
from urllib.parse import quote

from app.core.dev_passwords import DEV_PASSWORD_LENGTH, generate_dev_password

REPO = Path(__file__).resolve().parents[2]
R38_CLEAN_LINES = Path(__file__).resolve().parent / "data" / "r38_clean_lines.txt"

_SPEC = importlib.util.spec_from_file_location(
    "scan_uat_evidence",
    REPO / "scripts" / "scan_uat_evidence.py",
)
scan = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(scan)

scan_main = scan.main
pool_token_on_line = scan.pool_token_on_line


def _mixed_token() -> str:
    bang = chr(33)
    return "".join(("A", "a", "1", bang, "b" * (DEV_PASSWORD_LENGTH - 4)))


def _token_with_symbol(symbol: str) -> str:
    body = "".join(("A", "a", "1", symbol))
    return body + ("b" * (DEV_PASSWORD_LENGTH - len(body)))


def _long_token() -> str:
    return _mixed_token() + ("c" * 6)


def _write_allowlist(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return path


def test_pool_token_requires_the_generated_password_mix():
    token = _mixed_token()
    assert len(token) == DEV_PASSWORD_LENGTH
    assert pool_token_on_line(token) is True
    assert pool_token_on_line(_long_token()) is True
    assert pool_token_on_line("a" * (DEV_PASSWORD_LENGTH - 1)) is False
    assert pool_token_on_line("ab" * 32) is False
    assert pool_token_on_line("see " + token + " now") is True


def test_pool_token_accepts_underscore_or_hyphen_as_only_symbol():
    underscore = _token_with_symbol("_")
    hyphen = _token_with_symbol("-")
    assert pool_token_on_line(underscore) is True
    assert pool_token_on_line(hyphen) is True


def test_hex_sha_uuid_and_snake_case_are_not_tokens():
    digest = hashlib.sha256(b"r38-evidence").hexdigest()
    uid = str(uuid.UUID(int=0xC0FFEE))
    volume = "nimblelims_postgres_data"
    assert pool_token_on_line(digest) is False
    assert pool_token_on_line(uid) is False
    assert pool_token_on_line(volume) is False
    assert pool_token_on_line("201_bob_other_GET_visible_via_project_users") is False
    assert pool_token_on_line("200_POST_explicit_2026-10-15") is False
    assert pool_token_on_line("r38_results_America_New_York.png") is False


def test_r38_style_evidence_lines_are_clean(tmp_path, capsys):
    digest = hashlib.sha256(b"r38-evidence").hexdigest()
    uid = str(uuid.UUID(int=0xC0FFEE))
    (tmp_path / "r38.txt").write_text(
        "\n".join(
            (
                f"commit {digest}",
                f"sample {uid}",
                "volume nimblelims_postgres_data",
                "image pgvector/pgvector:pg15",
                "2026-10-19T18:00:00Z",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    assert scan_main([str(tmp_path)]) == 0
    assert "clean" in capsys.readouterr().out


def test_r38_clean_lines_fixture_is_clean_without_allowlist(tmp_path, capsys):
    dest = tmp_path / "r38_clean_lines.txt"
    dest.write_bytes(R38_CLEAN_LINES.read_bytes())
    assert scan_main([str(tmp_path), "--no-allowlist"]) == 0
    captured = capsys.readouterr()
    assert "clean" in captured.out
    assert captured.err == ""


def test_r38_clean_lines_copy_hits_injected_pool_password(tmp_path, capsys):
    token = generate_dev_password()
    for _ in range(16):
        if pool_token_on_line(token):
            break
        token = generate_dev_password()
    assert pool_token_on_line(token)
    dest = tmp_path / "r38_clean_lines.txt"
    dest.write_bytes(R38_CLEAN_LINES.read_bytes())
    dest.write_bytes(dest.read_bytes() + f"{token}\n".encode("utf-8"))
    code = scan_main([str(tmp_path), "--no-allowlist"])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token:" in err
    assert token not in err


def test_checked_in_allowlist_lists_reviewed_r38_pngs():
    entries = scan.load_allowlist(scan.DEFAULT_ALLOWLIST)
    by_path = {entry.path: entry for entry in entries}
    approved = "Günter (CSO) re-review of #207, relayed by Marc 2026-10-19"
    york = by_path["ui/r38_results_America_New_York.png"]
    utc = by_path["ui/r38_results_UTC.png"]
    assert york.sha256 == "2a385847a8a74ded9419432cb2c433e2b65f0b4572b400e4426443a11b9197f6"
    assert utc.sha256 == "1bf37bd5116db5719831c93746cc5005a7211c9a5aaa21baaddfdd722422bdb2"
    assert york.line is None
    assert utc.line is None
    assert york.approved_by == approved
    assert utc.approved_by == approved
    assert york.date == "2026-10-19"
    assert utc.date == "2026-10-19"


def test_allowlist_sha256_skips_matching_binary(tmp_path, capsys):
    payload = b"\x89PNG\r\n\x1a\n" + bytes((1, 2, 3, 4))
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_America_New_York.png").write_bytes(payload)
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [
            {
                "path": "ui/r38_results_America_New_York.png",
                "sha256": digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            }
        ],
    )
    assert scan_main([str(evidence), "--allowlist", str(allow)]) == 0
    assert "clean" in capsys.readouterr().out


def test_allowlist_changed_bytes_no_longer_match(tmp_path, capsys):
    payload = b"\x89PNG\r\n\x1a\n" + bytes((1, 2, 3, 4))
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    png = evidence / "ui" / "r38_results_UTC.png"
    png.write_bytes(payload + b"x")
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [
            {
                "path": "ui/r38_results_UTC.png",
                "sha256": digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            }
        ],
    )
    code = scan_main([str(evidence), "--allowlist", str(allow)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT refuse binary: ui/r38_results_UTC.png" in err


def test_allowlist_does_not_allow_by_extension(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "other.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes((9, 8, 7)))
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [
            {
                "path": "*.png",
                "sha256": "0" * 64,
                "approved_by": "tester",
                "date": "2026-10-19",
            }
        ],
    )
    code = scan_main([str(evidence), "--allowlist", str(allow)])
    err = capsys.readouterr().err
    assert code == 2
    assert "must not allow by extension or glob" in err


def test_allowlist_line_entry_skips_that_line_only(tmp_path, capsys):
    token = _mixed_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(
        f"keep {token}\nsecond {token}\n",
        encoding="utf-8",
    )
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [
            {
                "path": "notes.txt",
                "line": 1,
                "approved_by": "tester",
                "date": "2026-10-19",
            }
        ],
    )
    code = scan_main([str(evidence), "--allowlist", str(allow)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: notes.txt:1" not in err
    assert "HIT password-pool token: notes.txt:2" in err
    assert token not in err


def test_clean_evidence_exits_zero(tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("sample id 123\n", encoding="utf-8")
    assert scan_main([str(tmp_path)]) == 0
    assert "clean" in capsys.readouterr().out


def test_directory_lists_header_token_bcrypt_and_dump(tmp_path, capsys):
    token = _mixed_token()
    (tmp_path / "log.txt").write_text(
        "admin (DEV_SEED_ADMIN_PASSWORD was unset; printed once):\n"
        f"{token}\n"
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
    assert token not in err


def test_printed_once_header_is_case_insensitive(tmp_path, capsys):
    (tmp_path / "log.txt").write_text("PRINTED ONCE\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT printed-once header: log.txt:1" in err


def test_pool_token_followed_by_at_host_in_url(tmp_path, capsys):
    token = generate_dev_password()
    (tmp_path / "url.txt").write_text(
        f"postgresql://lims_app:{token}@db:5432/lims_db\n",
        encoding="utf-8",
    )
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: url.txt:1" in err
    assert token not in err


def test_percent_encoded_token_is_decoded_and_rescanned(tmp_path, capsys):
    token = generate_dev_password()
    encoded = quote(token, safe="")
    for _ in range(8):
        if encoded != token:
            break
        token = generate_dev_password()
        encoded = quote(token, safe="")
    assert encoded != token
    (tmp_path / "enc.txt").write_text(f"value={encoded}\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: enc.txt:1" in err
    assert token not in err
    assert encoded not in err


def test_token_run_into_adjacent_characters(tmp_path, capsys):
    token = _mixed_token()
    (tmp_path / "adj.txt").write_text(f"xx{token}yy\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: adj.txt:1" in err
    assert token not in err


def test_thirty_char_pool_token_is_a_hit(tmp_path, capsys):
    long_token = _long_token()
    (tmp_path / "long-token.txt").write_text(f"prefix {long_token} suffix\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: long-token.txt:1" in err
    assert long_token not in err


def test_pgdmp_magic_hits_a_renamed_dump(tmp_path, capsys):
    (tmp_path / "renamed-backup.bin").write_bytes(b"PGDMP\x00custom-format")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT dump file: renamed-backup.bin" in err


def test_dump_extension_hits_without_pgdmp_magic(tmp_path, capsys):
    (tmp_path / "users.dump").write_text("users\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT dump file: users.dump" in err


def test_dump_gz_name_and_gzip_pgdmp(tmp_path, capsys):
    named = tmp_path / "users.dump.gz"
    named.write_bytes(gzip.compress(b"users-table\n"))
    packed = tmp_path / "renamed.gz"
    packed.write_bytes(gzip.compress(b"PGDMP\x00custom-format"))
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT dump file: users.dump.gz" in err
    assert "HIT dump file: renamed.gz|gunzip" in err


def test_zlib_payload_is_inflated_and_scanned(tmp_path, capsys):
    token = _mixed_token()
    (tmp_path / "note.zlib").write_bytes(zlib.compress(f"{token}\n".encode("utf-8")))
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: note.zlib|inflate:1" in err
    assert token not in err


def test_nested_tarball_is_recursed(tmp_path, capsys):
    token = _mixed_token()
    inner_notes = tmp_path / "inner.txt"
    inner_notes.write_text(f"{token}\n", encoding="utf-8")
    inner_tar = tmp_path / "inner.tar"
    with tarfile.open(inner_tar, "w") as bundle:
        bundle.add(inner_notes, arcname="inner.txt")
    outer = tmp_path / "outer.tar"
    with tarfile.open(outer, "w") as bundle:
        bundle.add(inner_tar, arcname="wrap/inner.tar")
    code = scan_main([str(outer)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token:" in err
    assert token not in err


def test_non_allowlisted_binary_is_refused(tmp_path, capsys):
    (tmp_path / "photo.bin").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes((0, 1, 2, 3)))
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT refuse binary: photo.bin" in err


def test_configured_secrets_match_literal_and_percent_encoded(
    tmp_path, monkeypatch, capsys
):
    secret = "".join(("s", "h", "o", "r", "t", chr(36), "y"))
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    monkeypatch.setenv("LIMS_MIGRATE_PASSWORD", "")
    (tmp_path / "plain.txt").write_text(f"pwd={secret}\n", encoding="utf-8")
    (tmp_path / "enc.txt").write_text(f"pwd={quote(secret, safe='')}\n", encoding="utf-8")
    code = scan_main([str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT configured secret: plain.txt:1" in err
    assert "HIT configured secret: enc.txt:1" in err
    assert secret not in err


def test_secrets_file_supplies_configured_values(tmp_path, capsys):
    secret = "".join(("f", "i", "l", "e", chr(38), "z"))
    secrets = tmp_path / "round.env"
    secrets.write_text(
        f"LIMS_APP_PASSWORD={secret!r}\n",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "note.txt").write_text(f"app={secret}\n", encoding="utf-8")
    code = scan_main([str(evidence), "--secrets-file", str(secrets)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT configured secret: note.txt:1" in err
    assert secret not in err


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
    assert "HIT bcrypt hash:" in err
    assert "HIT dump file:" in err
    assert "abcdefghijklmnopqrstuv" not in err


def test_missing_evidence_exits_nonzero(tmp_path, capsys):
    missing = tmp_path / "nope"
    assert scan_main([str(missing)]) == 2
    assert "not found" in capsys.readouterr().err


def test_scan_module_path_is_the_repo_script():
    assert Path(scan.__file__).name == "scan_uat_evidence.py"
