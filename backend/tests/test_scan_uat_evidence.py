"""The evidence scan refuses secrets before a folder is shared."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import tarfile
import uuid
import zlib
from pathlib import Path
from urllib.parse import quote

import pytest

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

UTC_NAME = "r38_results_UTC.png"
YORK_NAME = "r38_results_America_New_York.png"
UTC_REL = f"ui/{UTC_NAME}"
YORK_REL = f"ui/{YORK_NAME}"
UTC_PNG = b"\x89PNG\r\n\x1a\n" + b"utc-reviewed-bytes-r38"
YORK_PNG = b"\x89PNG\r\n\x1a\n" + b"york-reviewed-bytes-r38"
UTC_SHA = hashlib.sha256(UTC_PNG).hexdigest()
YORK_SHA = hashlib.sha256(YORK_PNG).hexdigest()
SPOOF_CASES = (
    "A01",
    "A02",
    "A03",
    "A04a",
    "A04b",
    "A04c",
    "A04d",
    "A04e",
    "A04f",
    "A04g",
    "A04h",
    "A05",
    "A06",
    "A07",
    "B01",
    "B02",
    "B03",
    "B04a",
    "B04b",
    "B04c",
    "B04d",
    "B04e",
    "B04f",
    "B05a",
    "B05b",
    "B05c",
    "B05d",
    "B05e",
    "B05f",
    "B06a",
    "B06b",
    "B06c",
    "B06d",
    "B06e",
    "B06f",
    "B06g",
    "B07a",
    "B07b",
    "B07c",
    "B07d",
    "B07e",
    "B08a",
    "B08b",
    "B08c",
    "B09a",
    "B09b",
    "B09c",
    "B09d",
    "B09e",
    "B10a",
    "B10b",
    "B10c",
    "B11a",
    "B11b",
    "B11c",
    "B11d",
    "B11e",
    "B11f",
    "B11g",
    "B11h",
    "B11i",
    "B11j",
    "B12a",
    "B12b",
    "B12c",
    "B12d",
    "B13a",
    "B13b",
    "B13c",
)


def _mixed_token() -> str:
    bang = chr(33)
    return "".join(("A", "a", "1", bang, "b" * (DEV_PASSWORD_LENGTH - 4)))


def _token_with_symbol(symbol: str) -> str:
    body = "".join(("A", "a", "1", symbol))
    return body + ("b" * (DEV_PASSWORD_LENGTH - len(body)))


def _long_token() -> str:
    return _mixed_token() + ("c" * 6)


def _runtime_pool_token() -> str:
    token = generate_dev_password()
    for _ in range(16):
        if pool_token_on_line(token):
            return token
        token = generate_dev_password()
    raise AssertionError("could not generate a pool token")


def _runtime_configured_secret() -> str:
    return "".join(("c", "f", "g", chr(36), "z", "9"))


def _write_allowlist(path: Path, entries: list[dict[str, object]]) -> Path:
    for entry in entries:
        entry.setdefault("reviewed_by", "Günter (CSO)")
        entry.setdefault("approved_by", "Günter (CSO) 2026-10-19")
        entry.setdefault("date", "2026-10-19")
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return path


def _reviewed_entries() -> list[dict[str, object]]:
    return [
        {
            "path": YORK_REL,
            "sha256": YORK_SHA,
            "reviewed_by": "Günter (CSO), visual review 2026-10-19, no secrets visible",
            "approved_by": "Günter (CSO) 2026-10-19",
            "date": "2026-10-19",
        },
        {
            "path": UTC_REL,
            "sha256": UTC_SHA,
            "reviewed_by": "Günter (CSO), visual review 2026-10-19, no secrets visible",
            "approved_by": "Günter (CSO) 2026-10-19",
            "date": "2026-10-19",
        },
    ]


def _write_reviewed_pngs(evidence: Path) -> None:
    (evidence / "ui").mkdir(parents=True, exist_ok=True)
    (evidence / "ui" / UTC_NAME).write_bytes(UTC_PNG)
    (evidence / "ui" / YORK_NAME).write_bytes(YORK_PNG)


def _secret_text(token: str) -> str:
    return f"note\n{token}\n"


def _add_tar_member(bundle: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    bundle.addfile(info, io.BytesIO(data))


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
    token = _runtime_pool_token()
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
    york = by_path["ui/r38_results_America_New_York.png"]
    utc = by_path["ui/r38_results_UTC.png"]
    assert york.sha256 == "2a385847a8a74ded9419432cb2c433e2b65f0b4572b400e4426443a11b9197f6"
    assert utc.sha256 == "1bf37bd5116db5719831c93746cc5005a7211c9a5aaa21baaddfdd722422bdb2"
    assert york.line is None
    assert utc.line is None
    assert york.reviewed_by.strip()
    assert utc.reviewed_by.strip()
    assert york.approved_by.strip()
    assert utc.approved_by.strip()
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


def test_allowlist_file_entry_does_not_cover_suffixed_path(tmp_path, capsys):
    token = _runtime_pool_token()
    payload = b"\x89PNG\r\n\x1a\n" + bytes((1, 2, 3, 4))
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "other" / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_UTC.png").write_bytes(payload)
    (evidence / "other" / "ui" / "r38_results_UTC.png").write_text(
        f"{token}\n", encoding="utf-8"
    )
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
    assert "HIT password-pool token: other/ui/r38_results_UTC.png:1" in err
    assert token not in err


def test_allowlist_file_entry_does_not_cover_tar_member(tmp_path, capsys):
    token = _runtime_pool_token()
    payload = b"\x89PNG\r\n\x1a\n" + bytes((1, 2, 3, 4))
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_UTC.png").write_bytes(payload)
    member = tmp_path / "member.txt"
    member.write_text(f"{token}\n", encoding="utf-8")
    archive = evidence / "archive.tar"
    with tarfile.open(archive, "w") as bundle:
        bundle.add(member, arcname="ui/r38_results_UTC.png")
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
    assert "HIT password-pool token: archive.tar!ui/r38_results_UTC.png:1" in err
    assert token not in err


def test_allowlist_line_entry_requires_sha256_and_skips_only_that_line(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    text = "PRINTED ONCE\nsecond printed once\n"
    (evidence / "notes.txt").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [
            {
                "path": "notes.txt",
                "line": 1,
                "sha256": digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            }
        ],
    )
    code = scan_main([str(evidence), "--allowlist", str(allow)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT printed-once header: notes.txt:1" not in err
    assert "HIT printed-once header: notes.txt:2" in err


def test_allowlist_line_entry_without_sha256_is_refused(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
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
    assert code == 2
    assert "needs path plus sha256" in err


def test_allowlist_line_entry_never_suppresses_pool_or_configured_secret(
    tmp_path, capsys, monkeypatch
):
    token = _runtime_pool_token()
    configured = _runtime_configured_secret()
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    text = f"keep\n{token}\n{configured}\nstored $2a$06$not-a-real-hash\n"
    (evidence / "notes.txt").write_text(text, encoding="utf-8")
    (evidence / "users.dump").write_text("users\n", encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    dump_digest = hashlib.sha256(b"users\n").hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [
            {
                "path": "notes.txt",
                "line": 2,
                "sha256": digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            },
            {
                "path": "notes.txt",
                "line": 3,
                "sha256": digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            },
            {
                "path": "notes.txt",
                "line": 4,
                "sha256": digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            },
            {
                "path": "users.dump",
                "line": 1,
                "sha256": dump_digest,
                "approved_by": "tester",
                "date": "2026-10-19",
            },
        ],
    )
    code = scan_main([str(evidence), "--allowlist", str(allow)])
    err = capsys.readouterr().err
    assert code == 1
    assert "HIT password-pool token: notes.txt:2" in err
    assert "HIT configured secret: notes.txt:3" in err
    assert "HIT bcrypt hash: notes.txt:4" in err
    assert "HIT dump file: users.dump" in err
    assert token not in err
    assert configured not in err


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


def test_unsafe_evidence_names_are_refused():
    assert scan.is_unsafe_evidence_name("ui/r38_results_UTC.png ") is True
    assert scan.is_unsafe_evidence_name("ui\\r38_results_UTC.png") is True
    assert scan.is_unsafe_evidence_name("ui/r38_results_UTC.png|x") is True
    assert scan.is_unsafe_evidence_name("./ui/r38_results_UTC.png") is True
    assert scan.is_unsafe_evidence_name("ui/r38_results_UTC.png") is False
    assert scan.is_unsafe_evidence_name("ui /r38_results_UTC.png") is False


def _setup_spoof_case(
    case_id: str,
    tmp_path: Path,
    monkeypatch,
) -> tuple[list[str], int, str, str]:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    token = _runtime_pool_token()
    configured = _runtime_configured_secret()
    entries = _reviewed_entries()
    no_allowlist = False
    planted = token

    if case_id != "B09d":
        _write_reviewed_pngs(evidence)

    if case_id == "A02":
        no_allowlist = True
    elif case_id == "A03":
        (evidence / "other" / "ui").mkdir(parents=True)
        (evidence / "other" / "ui" / UTC_NAME).write_bytes(UTC_PNG)
    elif case_id == "A04a":
        (evidence / "ui" / f"{UTC_NAME}.bak").write_bytes(UTC_PNG)
    elif case_id == "A04b":
        (evidence / "ui" / f"{UTC_NAME}2").write_bytes(UTC_PNG)
    elif case_id == "A04c":
        (evidence / "ui" / "r38_results_UTC.pn").write_bytes(UTC_PNG)
    elif case_id == "A04d":
        (evidence / "xui").mkdir()
        (evidence / "xui" / UTC_NAME).write_bytes(UTC_PNG)
    elif case_id == "A04e":
        (evidence / "ui" / "sub").mkdir()
        (evidence / "ui" / "sub" / UTC_NAME).write_bytes(UTC_PNG)
    elif case_id == "A04f":
        (evidence / UTC_NAME).write_bytes(UTC_PNG)
    elif case_id == "A04g":
        (evidence / "ui" / "r38_results_UTC").write_bytes(UTC_PNG)
    elif case_id == "A04h":
        (evidence / "ui" / f"prefix_{UTC_NAME}").write_bytes(UTC_PNG)
    elif case_id == "A05":
        (evidence / "ui" / UTC_NAME).write_bytes(YORK_PNG)
        (evidence / "ui" / YORK_NAME).write_bytes(UTC_PNG)
    elif case_id == "A06":
        flipped = bytearray(UTC_PNG)
        flipped[-1] ^= 0x01
        (evidence / "ui" / UTC_NAME).write_bytes(bytes(flipped))
    elif case_id == "A07":
        (evidence / "ui" / UTC_NAME).write_bytes(UTC_PNG[:-1])
    elif case_id == "B01":
        (evidence / "ui" / UTC_NAME).write_bytes(UTC_PNG + token.encode("utf-8"))
    elif case_id == "B02":
        (evidence / "ui" / YORK_NAME).write_bytes(YORK_PNG + b"\n" + token.encode("utf-8"))
    elif case_id == "B03":
        (evidence / "ui" / UTC_NAME).write_text(_secret_text(token), encoding="utf-8")
    elif case_id == "B04a":
        (evidence / "ui" / "r38_results_U\u0422C.png").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B04b":
        (evidence / "ui" / f"{UTC_NAME} ").write_text(_secret_text(token), encoding="utf-8")
    elif case_id == "B04c":
        (evidence / "ui" / "r38_results_UTC\u200b.png").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B04d":
        (evidence / "ui ").mkdir()
        (evidence / "ui " / UTC_NAME).write_text(_secret_text(token), encoding="utf-8")
    elif case_id == "B04e":
        (evidence / "ui" / "r38_results_\uff35TC.png").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B04f":
        (evidence / "ui" / f"{UTC_NAME}.txt").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B05a":
        entries = [
            {
                "path": UTC_REL,
                "sha256": YORK_SHA,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B05b":
        entries = [
            {
                "path": UTC_REL,
                "sha256": "ab" * 32,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B05c":
        entries = [
            {
                "path": YORK_REL,
                "sha256": YORK_SHA,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            },
            {
                "path": UTC_REL,
                "sha256": UTC_SHA.upper(),
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            },
        ]
    elif case_id == "B05d":
        entries = [
            {
                "path": UTC_REL,
                "sha256": UTC_SHA,
                "line": 2,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B05e":
        entries = [
            {
                "path": UTC_REL,
                "sha256": "a" * 63,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B05f":
        entries = [
            {
                "path": UTC_REL,
                "sha256": UTC_SHA,
                "reviewed_by": "Günter (CSO)",
                "approved_by": "",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B06a":
        outside = tmp_path / "outside.txt"
        outside.write_text(_secret_text(token), encoding="utf-8")
        target = evidence / "ui" / UTC_NAME
        target.unlink()
        target.symlink_to(outside)
    elif case_id == "B06b":
        changed = UTC_PNG + b"x"
        outside = tmp_path / "changed.png"
        outside.write_bytes(changed)
        target = evidence / "ui" / UTC_NAME
        target.unlink()
        target.symlink_to(outside)
    elif case_id == "B06c":
        (evidence / "other").mkdir()
        (evidence / "other" / "link.png").symlink_to(evidence / "ui" / UTC_NAME)
    elif case_id == "B06d":
        (evidence / "ui" / f"{UTC_NAME}.lnk").symlink_to(evidence / "ui" / UTC_NAME)
    elif case_id == "B06e":
        outside = tmp_path / "genuine.png"
        outside.write_bytes(UTC_PNG)
        target = evidence / "ui" / UTC_NAME
        target.unlink()
        target.symlink_to(outside)
    elif case_id == "B06f":
        outside = tmp_path / "outside_ui"
        outside.mkdir()
        (outside / UTC_NAME).write_bytes(UTC_PNG)
        (outside / YORK_NAME).write_bytes(YORK_PNG)
        ui_dir = evidence / "ui"
        for child in ui_dir.iterdir():
            child.unlink()
        ui_dir.rmdir()
        ui_dir.symlink_to(outside)
    elif case_id == "B06g":
        (evidence / "dangling.lnk").symlink_to(tmp_path / "missing-target")
    elif case_id == "B07a":
        entries[1]["path"] = f"../{UTC_REL}"
    elif case_id == "B07b":
        entries[1]["path"] = f"ui/../{UTC_REL}"
    elif case_id == "B07c":
        entries[1]["path"] = f"/{UTC_REL}"
    elif case_id == "B07d":
        entries[1]["path"] = f"C:/{UTC_REL}"
    elif case_id == "B07e":
        entries[1]["path"] = "ui/./../r38_results_UTC.png"
    elif case_id == "B08a":
        entries[1]["path"] = f"./{UTC_REL}"
    elif case_id == "B08b":
        entries[1]["path"] = "ui//r38_results_UTC.png"
    elif case_id == "B08c":
        entries[1]["path"] = "ui\\r38_results_UTC.png"
    elif case_id == "B09a":
        (evidence / f"ui\\{UTC_NAME}").write_text(_secret_text(token), encoding="utf-8")
    elif case_id == "B09b":
        (evidence / "ui" / f"{UTC_NAME}|x").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B09c":
        (evidence / "ui" / f"{UTC_NAME}|gunzip").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B09d":
        (evidence / f"ui\\{UTC_NAME}").write_text(_secret_text(token), encoding="utf-8")
    elif case_id == "B09e":
        (evidence / "ui" / f"{UTC_NAME}!x").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B10a":
        (evidence / "UI").mkdir()
        (evidence / "UI" / "R38_RESULTS_UTC.PNG").write_bytes(UTC_PNG)
    elif case_id == "B10b":
        (evidence / "ui" / "r38_results_utc.png").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B10c":
        entries[1]["path"] = "UI/R38_RESULTS_UTC.PNG"
    elif case_id == "B11a":
        entries = [{"path": "ui/*.png", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B11b":
        entries = [{"path": "ui/r38_results_*.png", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B11c":
        entries = [{"path": "ui/r38_results_UT?.png", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B11d":
        entries = [
            {"path": "ui/[r]38_results_UTC.png", "sha256": UTC_SHA, "date": "2026-10-19"}
        ]
    elif case_id == "B11e":
        entries = [{"path": "**", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B11f":
        entries = [
            {
                "path": "ui/x.png",
                "sha256": UTC_SHA,
                "extension": ".png",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B11g":
        entries = [
            {
                "path": "ui/x.png",
                "sha256": UTC_SHA,
                "glob": "*.png",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B11h":
        entries = [{"path": "ui", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B11i":
        entries = [{"path": "ui/", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B11j":
        entries = [{"path": ".", "sha256": UTC_SHA, "date": "2026-10-19"}]
    elif case_id == "B12a":
        archive = evidence / "pack.tar"
        with tarfile.open(archive, "w") as bundle:
            _add_tar_member(bundle, UTC_REL, _secret_text(token).encode("utf-8"))
    elif case_id == "B12b":
        archive = evidence / "pack.tar"
        with tarfile.open(archive, "w") as bundle:
            _add_tar_member(bundle, UTC_REL, UTC_PNG)
    elif case_id == "B12c":
        archive = evidence / "pack.tar"
        with tarfile.open(archive, "w") as bundle:
            _add_tar_member(bundle, UTC_REL, UTC_PNG)
            _add_tar_member(bundle, UTC_REL, _secret_text(token).encode("utf-8"))
        entries = _reviewed_entries() + [
            {
                "path": f"pack.tar!{UTC_REL}",
                "sha256": UTC_SHA,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B12d":
        archive = evidence / "pack.tar"
        with tarfile.open(archive, "w") as bundle:
            _add_tar_member(bundle, UTC_REL, UTC_PNG)
            _add_tar_member(
                bundle, f"./{UTC_REL}", _secret_text(token).encode("utf-8")
            )
        entries = _reviewed_entries() + [
            {
                "path": f"pack.tar!{UTC_REL}",
                "sha256": UTC_SHA,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B13a":
        text = _secret_text(token)
        (evidence / "notes.txt").write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        entries = [
            {
                "path": "notes.txt",
                "line": 2,
                "sha256": digest,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B13b":
        planted = configured
        monkeypatch.setenv("POSTGRES_PASSWORD", configured)
        text = _secret_text(configured)
        (evidence / "notes.txt").write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        entries = [
            {
                "path": "notes.txt",
                "line": 2,
                "sha256": digest,
                "approved_by": "Günter (CSO) 2026-10-19",
                "date": "2026-10-19",
            }
        ]
    elif case_id == "B13c":
        planted = token
        monkeypatch.setenv("POSTGRES_PASSWORD", token)
        (evidence / "notes.txt").write_text(_secret_text(token), encoding="utf-8")
        no_allowlist = True

    argv = [str(evidence)]
    if no_allowlist:
        argv.append("--no-allowlist")
    else:
        allow = _write_allowlist(tmp_path / "allow.json", entries)
        argv.extend(["--allowlist", str(allow)])
    expected_exit, expected_result = _spoof_expectation(case_id)
    return argv, expected_exit, expected_result, planted


def _spoof_expectation(case_id: str) -> tuple[int, str]:
    clean = {
        "A01",
        "B05c",
        "B06e",
        "B06f",
        "B06g",
        "B08a",
        "B08b",
        "B08c",
    }
    refused = {
        "B05e",
        "B05f",
        "B07a",
        "B07b",
        "B07c",
        "B07d",
        "B07e",
        "B11a",
        "B11b",
        "B11c",
        "B11d",
        "B11e",
        "B11f",
        "B11g",
        "B11j",
    }
    if case_id in clean:
        return 0, "clean"
    if case_id in refused:
        return 2, "refused_allowlist"
    return 1, "flagged"


@pytest.mark.parametrize("case_id", SPOOF_CASES)
def test_allowlist_spoof_case(case_id, tmp_path, capsys, monkeypatch):
    argv, expected_exit, expected_result, planted = _setup_spoof_case(
        case_id, tmp_path, monkeypatch
    )
    code = scan_main(argv)
    captured = capsys.readouterr()
    err = captured.err
    assert planted not in err
    assert planted not in captured.out
    assert code == expected_exit
    if expected_result == "clean":
        assert "clean" in captured.out
        assert "HIT " not in err
        return
    if expected_result == "refused_allowlist":
        assert "ERROR:" in err
        assert "HIT " not in err
        return
    assert "HIT " in err
    if case_id == "B04b":
        assert "HIT unsafe evidence path: ui/r38_results_UTC.png " in err
    elif case_id == "B09a":
        assert "HIT unsafe evidence path:" in err
        assert "\\" in err
    elif case_id == "B09b":
        assert "HIT unsafe evidence path: ui/r38_results_UTC.png|x" in err
    elif case_id == "B09c":
        assert "HIT unsafe evidence path: ui/r38_results_UTC.png|gunzip" in err
    elif case_id == "B12c":
        assert "HIT duplicate tar member: pack.tar!ui/r38_results_UTC.png" in err
    elif case_id == "B12d":
        assert "HIT unsafe evidence path: pack.tar!./ui/r38_results_UTC.png" in err
    elif case_id == "B13a":
        assert "HIT password-pool token: notes.txt:2" in err
    elif case_id == "B13b":
        assert "HIT configured secret: notes.txt:2" in err
    elif case_id == "B13c":
        assert "HIT password-pool token: notes.txt:2" in err
        assert "HIT configured secret: notes.txt:2" in err
    elif case_id == "B05d":
        assert "HIT refuse binary: ui/r38_results_UTC.png" in err
