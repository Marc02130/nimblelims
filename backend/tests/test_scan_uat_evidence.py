"""The evidence scan refuses secrets before a folder is shared."""
from __future__ import annotations

import base64
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import socket
import stat
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


def _hit(kind: str, *parts: str, line: int | None = None) -> str:
    loc = json.dumps(list(parts))
    if line is None:
        return f"HIT {kind}: {loc}"
    return f"HIT {kind}: {loc}:{line}"


def _redacted_path(raw: str, secrets: tuple[str, ...] = ()) -> str:
    return scan.redact_name_path(raw, secrets)


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


def _runtime_jwt(length: int | None = None) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"

    def part(count: int, prefix: str = "") -> str:
        need = count - len(prefix)
        body = "".join(alphabet[os.urandom(1)[0] % 64] for _ in range(need))
        return prefix + body

    if length is None:
        raw = os.urandom(12)
        first = "eyJ" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        token = f"{first}.{part(24)}.{part(20)}"
        assert token.startswith("eyJ")
        assert len(token.split(".")) == 3
        assert len(token) < 200
        return token
    inner = length - 2
    first = 3 + (inner - 3) // 3
    second = (inner - 3) // 3
    third = inner - first - second
    token = f"{part(first, 'eyJ')}.{part(second)}.{part(third)}"
    assert token.startswith("eyJ")
    assert len(token.split(".")) == 3
    assert len(token) == length
    return token


def _binary_with_stray_gzip(prefix: bytes, size: int = 64 * 1024) -> bytes:
    body = bytearray(prefix)
    pad = b"\x11\x22\x33\x44"
    while len(body) < size:
        body.extend(pad)
    del body[size:]
    body[1024:1026] = b"\x1f\x8b"
    body[1026] = 0x00
    body[2048:2051] = b"\x1f\x8b\x08"
    body[2051] = 0xE0
    body[3072:3075] = b"\x1f\x8b\x08"
    body[3075] = 0x00
    body[3076:3092] = b"\xff" * 16
    return bytes(body)


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


def _run(
    argv: list[str], capsys, planted: tuple[str, ...] = ()
) -> tuple[int, str, str]:
    code = scan_main(argv)
    captured = capsys.readouterr()
    for value in planted:
        assert value not in captured.out
        assert value not in captured.err
    return code, captured.out, captured.err


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
    planted = _runtime_pool_token()
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
    code, out, err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 0
    assert "clean" in out
    assert err == ""


def test_r38_clean_lines_fixture_is_clean_without_allowlist(tmp_path, capsys):
    dest = tmp_path / "r38_clean_lines.txt"
    dest.write_bytes(R38_CLEAN_LINES.read_bytes())
    planted = _runtime_pool_token()
    code, out, err = _run([str(tmp_path), "--no-allowlist"], capsys, (planted,))
    assert code == 0
    assert "clean" in out
    assert err == ""


def test_r38_clean_lines_copy_hits_injected_pool_password(tmp_path, capsys):
    token = _runtime_pool_token()
    dest = tmp_path / "r38_clean_lines.txt"
    dest.write_bytes(R38_CLEAN_LINES.read_bytes())
    dest.write_bytes(dest.read_bytes() + f"{token}\n".encode("utf-8"))
    code, _out, err = _run([str(tmp_path), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert "HIT password-pool token:" in err


def test_checked_in_allowlist_lists_reviewed_r38_pngs():
    entries = scan.load_allowlist(scan.DEFAULT_ALLOWLIST)
    by_path = {entry.path: entry for entry in entries}
    york = by_path["ui/r38_results_America_New_York.png"]
    utc = by_path["ui/r38_results_UTC.png"]
    assert york.sha256 == "2a385847a8a74ded9419432cb2c433e2b65f0b4572b400e4426443a11b9197f6"
    assert utc.sha256 == "1bf37bd5116db5719831c93746cc5005a7211c9a5aaa21baaddfdd722422bdb2"
    assert york.line is None
    assert utc.line is None
    assert york.identity == ("ui/r38_results_America_New_York.png",)
    assert utc.identity == ("ui/r38_results_UTC.png",)
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
    planted = _runtime_pool_token()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "ui/r38_results_America_New_York.png", "sha256": digest}],
    )
    code, out, _err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (planted,)
    )
    assert code == 0
    assert "clean" in out


def test_allowlist_changed_bytes_no_longer_match(tmp_path, capsys):
    payload = b"\x89PNG\r\n\x1a\n" + bytes((1, 2, 3, 4))
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_UTC.png").write_bytes(payload + b"x")
    planted = _runtime_pool_token()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "ui/r38_results_UTC.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (planted,)
    )
    assert code == 1
    assert _hit("refuse binary", "ui/r38_results_UTC.png") in err


def test_allowlist_does_not_allow_by_extension(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "other.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes((9, 8, 7)))
    planted = _runtime_pool_token()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "*.png", "sha256": "0" * 64}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (planted,)
    )
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
        [{"path": "ui/r38_results_UTC.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("password-pool token", "other/ui/r38_results_UTC.png", line=1) in err


def test_allowlist_file_entry_does_not_cover_tar_member(tmp_path, capsys):
    token = _runtime_pool_token()
    payload = b"\x89PNG\r\n\x1a\n" + bytes((1, 2, 3, 4))
    digest = hashlib.sha256(payload).hexdigest()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_UTC.png").write_bytes(payload)
    archive = evidence / "archive.tar"
    with tarfile.open(archive, "w") as bundle:
        _add_tar_member(bundle, "ui/r38_results_UTC.png", f"{token}\n".encode("utf-8"))
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "ui/r38_results_UTC.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("archive", "archive.tar") in err


def test_allowlist_line_entry_is_refused(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    token = _runtime_pool_token()
    (evidence / "notes.txt").write_text(_secret_text(token), encoding="utf-8")
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "notes.txt", "line": 1, "sha256": "a" * 64}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 2
    assert "must not use line entries" in err


def test_allowlist_line_entry_without_sha256_is_refused(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    token = _runtime_pool_token()
    (evidence / "notes.txt").write_text(_secret_text(token), encoding="utf-8")
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "notes.txt", "line": 1}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 2
    assert "must not use line entries" in err


def test_sha_entry_does_not_suppress_configured_bcrypt_or_printed_once(
    tmp_path, capsys, monkeypatch
):
    configured = _runtime_configured_secret()
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    text = f"PRINTED ONCE\nstored $2a$06$not-a-real-hash\n{configured}\n"
    (evidence / "notes.txt").write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "notes.txt", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (configured,)
    )
    assert code == 1
    assert _hit("printed-once header", "notes.txt", line=1) in err
    assert _hit("bcrypt hash", "notes.txt", line=2) in err
    assert _hit("configured secret", "notes.txt", line=3) in err


def test_clean_evidence_exits_zero(tmp_path, capsys):
    (tmp_path / "notes.txt").write_text("sample id 123\n", encoding="utf-8")
    planted = _runtime_pool_token()
    code, out, _err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 0
    assert "clean" in out


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
    code, _out, err = _run([str(tmp_path)], capsys, (token,))
    assert code == 1
    assert _hit("printed-once header", "log.txt", line=1) in err
    assert _hit("password-pool token", "log.txt", line=2) in err
    assert _hit("bcrypt hash", "log.txt", line=3) in err
    assert _hit("bcrypt hash", "log.txt", line=4) in err
    assert _hit("dump file", "lims.dump") in err


def test_printed_once_header_is_case_insensitive(tmp_path, capsys):
    planted = _runtime_pool_token()
    (tmp_path / "log.txt").write_text("PRINTED ONCE\n", encoding="utf-8")
    code, _out, err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 1
    assert _hit("printed-once header", "log.txt", line=1) in err


def test_pool_token_followed_by_at_host_in_url(tmp_path, capsys):
    token = generate_dev_password()
    (tmp_path / "url.txt").write_text(
        f"postgresql://lims_app:{token}@db:5432/lims_db\n",
        encoding="utf-8",
    )
    code, _out, err = _run([str(tmp_path)], capsys, (token,))
    assert code == 1
    assert _hit("password-pool token", "url.txt", line=1) in err


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
    code, _out, err = _run([str(tmp_path)], capsys, (token, encoded))
    assert code == 1
    assert _hit("password-pool token", "enc.txt", line=1) in err


def test_token_run_into_adjacent_characters(tmp_path, capsys):
    token = _mixed_token()
    (tmp_path / "adj.txt").write_text(f"xx{token}yy\n", encoding="utf-8")
    code, _out, err = _run([str(tmp_path)], capsys, (token,))
    assert code == 1
    assert _hit("password-pool token", "adj.txt", line=1) in err


def test_thirty_char_pool_token_is_a_hit(tmp_path, capsys):
    long_token = _long_token()
    (tmp_path / "long-token.txt").write_text(
        f"prefix {long_token} suffix\n", encoding="utf-8"
    )
    code, _out, err = _run([str(tmp_path)], capsys, (long_token,))
    assert code == 1
    assert _hit("password-pool token", "long-token.txt", line=1) in err


def test_pgdmp_magic_hits_a_renamed_dump(tmp_path, capsys):
    planted = _runtime_pool_token()
    (tmp_path / "renamed-backup.bin").write_bytes(b"PGDMP\x00custom-format")
    code, _out, err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 1
    assert _hit("dump file", "renamed-backup.bin") in err


def test_dump_extension_hits_without_pgdmp_magic(tmp_path, capsys):
    planted = _runtime_pool_token()
    (tmp_path / "users.dump").write_text("users\n", encoding="utf-8")
    code, _out, err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 1
    assert _hit("dump file", "users.dump") in err


def test_dump_gz_name_and_gzip_pgdmp(tmp_path, capsys):
    planted = _runtime_pool_token()
    (tmp_path / "users.dump.gz").write_bytes(gzip.compress(b"users-table\n"))
    (tmp_path / "renamed.gz").write_bytes(gzip.compress(b"PGDMP\x00custom-format"))
    code, _out, err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 1
    assert _hit("dump file", "users.dump.gz") in err
    assert _hit("archive", "users.dump.gz") in err
    assert _hit("archive", "renamed.gz") in err


def test_zlib_payload_is_inflated_and_scanned(tmp_path, capsys):
    token = _mixed_token()
    (tmp_path / "note.zlib").write_bytes(zlib.compress(f"{token}\n".encode("utf-8")))
    code, _out, err = _run([str(tmp_path)], capsys, (token,))
    assert code == 1
    assert _hit("archive", "note.zlib") in err


def test_nested_tarball_is_recursed(tmp_path, capsys):
    token = _mixed_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    inner_notes = tmp_path / "inner.txt"
    inner_notes.write_text(f"{token}\n", encoding="utf-8")
    inner_tar = tmp_path / "inner.tar"
    with tarfile.open(inner_tar, "w") as bundle:
        bundle.add(inner_notes, arcname="inner.txt")
    with tarfile.open(evidence / "outer.tar", "w") as bundle:
        bundle.add(inner_tar, arcname="wrap/inner.tar")
    code, _out, err = _run([str(evidence)], capsys, (token,))
    assert code == 1
    assert _hit("archive", "outer.tar") in err


def test_non_allowlisted_binary_is_refused(tmp_path, capsys):
    planted = _runtime_pool_token()
    (tmp_path / "photo.bin").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes((0, 1, 2, 3)))
    code, _out, err = _run([str(tmp_path)], capsys, (planted,))
    assert code == 1
    assert _hit("refuse binary", "photo.bin") in err


def test_configured_secrets_match_literal_and_percent_encoded(
    tmp_path, monkeypatch, capsys
):
    secret = "".join(("s", "h", "o", "r", "t", chr(36), "y"))
    monkeypatch.setenv("POSTGRES_PASSWORD", secret)
    monkeypatch.setenv("LIMS_MIGRATE_PASSWORD", "")
    (tmp_path / "plain.txt").write_text(f"pwd={secret}\n", encoding="utf-8")
    (tmp_path / "enc.txt").write_text(f"pwd={quote(secret, safe='')}\n", encoding="utf-8")
    code, _out, err = _run([str(tmp_path)], capsys, (secret,))
    assert code == 1
    assert _hit("configured secret", "plain.txt", line=1) in err
    assert _hit("configured secret", "enc.txt", line=1) in err


def test_secrets_file_supplies_configured_values(tmp_path, capsys):
    secret = "".join(("f", "i", "l", "e", chr(38), "z"))
    secrets = tmp_path / "round.env"
    secrets.write_text(f"LIMS_APP_PASSWORD={secret!r}\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "note.txt").write_text(f"app={secret}\n", encoding="utf-8")
    code, _out, err = _run(
        [str(evidence), "--secrets-file", str(secrets)], capsys, (secret,)
    )
    assert code == 1
    assert _hit("configured secret", "note.txt", line=1) in err


def test_tarball_lists_bcrypt_dump_and_pgdmp(tmp_path, capsys):
    planted = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    notes = tmp_path / "notes.txt"
    notes.write_text("prefix $2b$12$abcdefghijklmnopqrstuv suffix\n", encoding="utf-8")
    dump = tmp_path / "users.dump"
    dump.write_text("users\n", encoding="utf-8")
    renamed = tmp_path / "renamed-backup.bin"
    renamed.write_bytes(b"PGDMP\x00custom-format")
    archive = evidence / "evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(notes, arcname="notes.txt")
        bundle.add(dump, arcname="round/users.dump")
        bundle.add(renamed, arcname="round/renamed-backup.bin")
    code, _out, err = _run(
        [str(evidence)], capsys, (planted, "abcdefghijklmnopqrstuv")
    )
    assert code == 1
    assert _hit("archive", "evidence.tar.gz") in err


def test_missing_evidence_exits_nonzero(tmp_path, capsys):
    missing = tmp_path / "nope"
    planted = _runtime_pool_token()
    code, _out, err = _run([str(missing)], capsys, (planted,))
    assert code == 2
    assert "not found" in err


def test_scan_module_path_is_the_repo_script():
    assert Path(scan.__file__).name == "scan_uat_evidence.py"


def test_unsafe_names_cover_spec_rules():
    assert scan.is_unsafe_name("ui/r38_results_UTC.png ") is True
    assert scan.is_unsafe_name("ui\\r38_results_UTC.png") is True
    assert scan.is_unsafe_name("ui/r38_results_UTC.png|x") is True
    assert scan.is_unsafe_name("./ui/r38_results_UTC.png") is True
    assert scan.is_unsafe_name("ui/r38_results_UTC.png") is False
    assert scan.is_unsafe_name("ui /r38_results_UTC.png") is True
    assert scan.is_unsafe_name("pack.tar!ui") is True
    assert scan.is_unsafe_name("ui/r38_results_UTC.png:1") is True
    assert scan.is_canonical_path("ui/r38_results_UTC.png") is True


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
        (evidence / "ui" / YORK_NAME).write_bytes(
            YORK_PNG + b"\n" + token.encode("utf-8")
        )
    elif case_id == "B03":
        (evidence / "ui" / UTC_NAME).write_text(_secret_text(token), encoding="utf-8")
    elif case_id == "B04a":
        (evidence / "ui" / "r38_results_U\u0422C.png").write_text(
            _secret_text(token), encoding="utf-8"
        )
    elif case_id == "B04b":
        (evidence / "ui" / f"{UTC_NAME} ").write_text(
            _secret_text(token), encoding="utf-8"
        )
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
        entries = [{"path": UTC_REL, "sha256": YORK_SHA}]
    elif case_id == "B05b":
        entries = [{"path": UTC_REL, "sha256": "ab" * 32}]
    elif case_id == "B05c":
        entries = [
            {"path": YORK_REL, "sha256": YORK_SHA},
            {"path": UTC_REL, "sha256": UTC_SHA.upper()},
        ]
    elif case_id == "B05d":
        entries = [{"path": UTC_REL, "sha256": UTC_SHA, "line": 2}]
    elif case_id == "B05e":
        entries = [{"path": UTC_REL, "sha256": "a" * 63}]
    elif case_id == "B05f":
        entries = [
            {
                "path": UTC_REL,
                "sha256": UTC_SHA,
                "reviewed_by": "Günter (CSO)",
                "approved_by": "",
            }
        ]
    elif case_id == "B06a":
        outside = tmp_path / "outside.txt"
        outside.write_text(_secret_text(token), encoding="utf-8")
        target = evidence / "ui" / UTC_NAME
        target.unlink()
        target.symlink_to(outside)
    elif case_id == "B06b":
        outside = tmp_path / "changed.png"
        outside.write_bytes(UTC_PNG + b"x")
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
        entries = [{"path": "ui/*.png", "sha256": UTC_SHA}]
    elif case_id == "B11b":
        entries = [{"path": "ui/r38_results_*.png", "sha256": UTC_SHA}]
    elif case_id == "B11c":
        entries = [{"path": "ui/r38_results_UT?.png", "sha256": UTC_SHA}]
    elif case_id == "B11d":
        entries = [{"path": "ui/[r]38_results_UTC.png", "sha256": UTC_SHA}]
    elif case_id == "B11e":
        entries = [{"path": "**", "sha256": UTC_SHA}]
    elif case_id == "B11f":
        entries = [{"path": "ui/x.png", "sha256": UTC_SHA, "extension": ".png"}]
    elif case_id == "B11g":
        entries = [{"path": "ui/x.png", "sha256": UTC_SHA, "glob": "*.png"}]
    elif case_id == "B11h":
        entries = [{"path": "ui", "sha256": UTC_SHA}]
    elif case_id == "B11i":
        entries = [{"path": "ui/", "sha256": UTC_SHA}]
    elif case_id == "B11j":
        entries = [{"path": ".", "sha256": UTC_SHA}]
    elif case_id == "B12a":
        with tarfile.open(evidence / "pack.tar", "w") as bundle:
            _add_tar_member(bundle, UTC_REL, _secret_text(token).encode("utf-8"))
    elif case_id == "B12b":
        with tarfile.open(evidence / "pack.tar", "w") as bundle:
            _add_tar_member(bundle, UTC_REL, UTC_PNG)
    elif case_id == "B12c":
        with tarfile.open(evidence / "pack.tar", "w") as bundle:
            _add_tar_member(bundle, UTC_REL, UTC_PNG)
            _add_tar_member(bundle, UTC_REL, _secret_text(token).encode("utf-8"))
        entries = _reviewed_entries() + [
            {"path": ["pack.tar", UTC_REL], "sha256": UTC_SHA}
        ]
    elif case_id == "B12d":
        with tarfile.open(evidence / "pack.tar", "w") as bundle:
            _add_tar_member(bundle, UTC_REL, UTC_PNG)
            _add_tar_member(bundle, f"./{UTC_REL}", _secret_text(token).encode("utf-8"))
        entries = _reviewed_entries() + [
            {"path": ["pack.tar", UTC_REL], "sha256": UTC_SHA}
        ]
    elif case_id == "B13a":
        text = _secret_text(token)
        (evidence / "notes.txt").write_text(text, encoding="utf-8")
        entries = [
            {
                "path": "notes.txt",
                "line": 2,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        ]
    elif case_id == "B13b":
        planted = configured
        monkeypatch.setenv("POSTGRES_PASSWORD", configured)
        text = _secret_text(configured)
        (evidence / "notes.txt").write_text(text, encoding="utf-8")
        entries = [
            {
                "path": "notes.txt",
                "line": 2,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
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
    clean = {"A01", "B05c"}
    refused = {
        "B05d",
        "B05e",
        "B05f",
        "B07a",
        "B07b",
        "B07c",
        "B07d",
        "B07e",
        "B08a",
        "B08b",
        "B08c",
        "B11a",
        "B11b",
        "B11c",
        "B11d",
        "B11e",
        "B11f",
        "B11g",
        "B11i",
        "B11j",
        "B13a",
        "B13b",
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
    code, out, err = _run(argv, capsys, (planted,))
    assert code == expected_exit
    if expected_result == "clean":
        assert "clean" in out
        assert "HIT " not in err
        return
    if expected_result == "refused_allowlist":
        assert "ERROR:" in err
        assert "HIT " not in err
        return
    assert "HIT " in err
    if case_id == "B04b":
        assert _hit("unsafe-name", "ui/r38_results_UTC.png ") in err
    elif case_id == "B09a":
        assert "HIT unsafe-name:" in err
    elif case_id == "B09b":
        assert _hit("unsafe-name", "ui/r38_results_UTC.png|x") in err
    elif case_id == "B09c":
        assert _hit("unsafe-name", "ui/r38_results_UTC.png|gunzip") in err
    elif case_id == "B12c":
        assert _hit("archive", "pack.tar") in err
    elif case_id == "B12d":
        assert _hit("archive", "pack.tar") in err
    elif case_id == "B13c":
        assert _hit("password-pool token", "notes.txt", line=2) in err
        assert _hit("configured secret", "notes.txt", line=2) in err


def test_spec_trailing_space_name(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    _write_reviewed_pngs(evidence)
    (evidence / "ui" / f"{UTC_NAME} ").write_text(_secret_text(token), encoding="utf-8")
    allow = _write_allowlist(tmp_path / "allow.json", _reviewed_entries())
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("unsafe-name", f"ui/{UTC_NAME} ") in err


def test_spec_leading_space_folder(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    _write_reviewed_pngs(evidence)
    (evidence / " ui").mkdir()
    (evidence / " ui" / UTC_NAME).write_bytes(UTC_PNG)
    (evidence / "ui" / UTC_NAME).write_text(_secret_text(token), encoding="utf-8")
    allow = _write_allowlist(tmp_path / "allow.json", _reviewed_entries())
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("unsafe-name", f" ui/{UTC_NAME}") in err
    assert _hit("password-pool token", UTC_REL, line=2) in err


def test_spec_backslash_name(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    _write_reviewed_pngs(evidence)
    (evidence / f"ui\\{UTC_NAME}").write_text(_secret_text(token), encoding="utf-8")
    allow = _write_allowlist(tmp_path / "allow.json", _reviewed_entries())
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert "HIT unsafe-name:" in err


def test_spec_pipe_x_and_gunzip_names(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    _write_reviewed_pngs(evidence)
    (evidence / "ui" / f"{UTC_NAME}|x").write_text(_secret_text(token), encoding="utf-8")
    (evidence / "ui" / f"{UTC_NAME}|gunzip").write_text(
        _secret_text(token), encoding="utf-8"
    )
    allow = _write_allowlist(tmp_path / "allow.json", _reviewed_entries())
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("unsafe-name", f"ui/{UTC_NAME}|x") in err
    assert _hit("unsafe-name", f"ui/{UTC_NAME}|gunzip") in err


def test_spec_colon_one_binary_and_pgdmp_against_checked_in_allowlist(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    _write_reviewed_pngs(evidence)
    (evidence / "ui" / f"{UTC_NAME}:1").write_bytes(UTC_PNG)
    (evidence / "ui" / f"{YORK_NAME}:1").write_bytes(b"PGDMP")
    (evidence / "hidden.bin").write_bytes(b"\x00" + token.encode("utf-8"))
    allow = REPO / "scripts" / "uat_evidence_allowlist.json"
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("unsafe-name", f"ui/{UTC_NAME}:1") in err
    assert _hit("unsafe-name", f"ui/{YORK_NAME}:1") in err
    assert _hit("dump file", f"ui/{YORK_NAME}:1") in err
    assert _hit("refuse binary", "hidden.bin") in err


def test_spec_bang_in_folder_name(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    _write_tar_with_members(evidence / "pack.tar", [(UTC_REL, UTC_PNG)])
    (evidence / "pack.tar!ui").mkdir()
    (evidence / "pack.tar!ui" / UTC_NAME).write_text(
        _secret_text(token), encoding="utf-8"
    )
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": ["pack.tar", UTC_REL], "sha256": UTC_SHA}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("archive", "pack.tar") in err
    assert _hit("unsafe-name", f"pack.tar!ui/{UTC_NAME}") in err
    assert _hit("password-pool token", f"pack.tar!ui/{UTC_NAME}", line=2) in err


def test_spec_control_character_name(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / "r38_results_UTC\x01.png").write_text(
        _secret_text(token), encoding="utf-8"
    )
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert "HIT unsafe-name:" in err


def test_spec_non_ascii_fullwidth_cyrillic_nfd_zwsp(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    names = (
        "r38_results_\uff35TC.png",
        "r38_results_U\u0422C.png",
        "r38_re\u0301sults_UTC.png",
        "r38_results_UTC\u200b.png",
    )
    for name in names:
        (evidence / "ui" / name).write_text(_secret_text(token), encoding="utf-8")
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert err.count("HIT unsafe-name:") >= 4


def test_spec_casefold_collision(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "Note.txt").write_text(_secret_text(token), encoding="utf-8")
    (evidence / "note.txt").write_text("ok\n", encoding="utf-8")
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("unsafe-name", "Note.txt") in err
    assert _hit("unsafe-name", "note.txt") in err


def test_spec_invalid_utf8_name(tmp_path, capsys, monkeypatch):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    dir_fd = os.open(evidence / "ui", os.O_RDONLY)
    created = False
    try:
        fd = os.open(
            b"r38_results_UTC\xff.png",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=dir_fd,
        )
        os.write(fd, _secret_text(token).encode("utf-8"))
        os.close(fd)
        created = True
    except (OSError, OverflowError, ValueError, UnicodeError) as exc:
        pytest.skip(f"invalid-UTF-8 names not creatable here: {exc}")
    finally:
        os.close(dir_fd)
    if not created:
        pytest.skip("invalid-UTF-8 names not creatable here: create did not finish")
    names = os.listdir(evidence / "ui")
    presented = names[0]
    assert scan._has_invalid_utf8(presented)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert "HIT unsafe-name:" in err

    monkeypatch.setattr(scan, "_has_invalid_utf8", lambda raw: False)
    monkeypatch.setattr(scan, "_SEGMENT_RE", re.compile(r"^[\s\S]*$"))
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert "HIT unsafe-name:" not in err
    assert "HIT password-pool token:" in err


def _write_tar_with_members(path: Path, members: list[tuple[str, bytes]]) -> None:
    path.write_bytes(_tar_bytes(members))


def _tar_bytes(members: list[tuple[str, bytes]]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as bundle:
        for name, data in members:
            _add_tar_member(bundle, name, data)
    return raw.getvalue()


def test_spec_tar_duplicate_both_orders(tmp_path, capsys):
    token = _runtime_pool_token()
    secret = _secret_text(token).encode("utf-8")
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": ["pack.tar", UTC_REL], "sha256": UTC_SHA}],
    )
    for order in (
        ((UTC_REL, UTC_PNG), (UTC_REL, secret)),
        ((UTC_REL, secret), (UTC_REL, UTC_PNG)),
    ):
        evidence = tmp_path / f"ev-{order[0][1][:4].hex()}"
        evidence.mkdir()
        _write_tar_with_members(evidence / "pack.tar", list(order))
        code, _out, err = _run(
            [str(evidence), "--allowlist", str(allow)], capsys, (token,)
        )
        assert code == 1
        assert _hit("archive", "pack.tar") in err


def test_spec_tar_dot_slash_double_slash_backslash_trailing_space(tmp_path, capsys):
    token = _runtime_pool_token()
    secret = _secret_text(token).encode("utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    _write_tar_with_members(
        evidence / "pack.tar",
        [
            (UTC_REL, secret),
            (f"./{UTC_REL}", secret),
            ("a//b.txt", secret),
            (f"ui\\{UTC_NAME}", secret),
            (f"{UTC_REL} ", secret),
        ],
    )
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": ["pack.tar", UTC_REL], "sha256": UTC_SHA}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_tar_duplicate_inside_tgz(tmp_path, capsys):
    token = _runtime_pool_token()
    secret = _secret_text(token).encode("utf-8")
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as bundle:
        _add_tar_member(bundle, UTC_REL, UTC_PNG)
        _add_tar_member(bundle, UTC_REL, secret)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "pack.tgz").write_bytes(gzip.compress(raw.getvalue()))
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tgz") in err


def test_spec_tar_link_members(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    archive = evidence / "pack.tar"
    with tarfile.open(archive, "w") as bundle:
        _add_tar_member(bundle, "ui/notes.txt", _secret_text(token).encode("utf-8"))
        info = tarfile.TarInfo(name="ui/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "target"
        bundle.addfile(info)
        hard = tarfile.TarInfo(name="ui/hard")
        hard.type = tarfile.LNKTYPE
        hard.linkname = "ui/link"
        bundle.addfile(hard)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_allowlist_duplicate_and_non_canonical_paths(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(_secret_text(token), encoding="utf-8")
    digest = hashlib.sha256(_secret_text(token).encode("utf-8")).hexdigest()
    dup = _write_allowlist(
        tmp_path / "dup.json",
        [
            {"path": "notes.txt", "sha256": digest},
            {"path": "notes.txt", "sha256": digest},
        ],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(dup)], capsys, (token,)
    )
    assert code == 2
    assert "duplicate path" in err
    bad = _write_allowlist(
        tmp_path / "bad.json",
        [{"path": "./notes.txt", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(bad)], capsys, (token,)
    )
    assert code == 2
    assert "relative file path" in err


def test_spec_nesting_past_max(tmp_path, capsys):
    token = _runtime_pool_token()
    payload = token.encode("utf-8")
    for _ in range(9):
        payload = gzip.compress(payload)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "nested.gz").write_bytes(payload)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "nested.gz") in err


def test_spec_decompress_cap(tmp_path, capsys, monkeypatch):
    token = _runtime_pool_token()
    monkeypatch.setattr(scan, "MAX_SCAN_BYTES", 16)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    planted = token + ("x" * 64)
    (evidence / "big.txt").write_text(planted, encoding="utf-8")
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("size-cap", "big.txt") in err


def test_spec_symlink_exact_path_pack_dir_dangling_root_and_fifo(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    _write_reviewed_pngs(evidence)
    outside = tmp_path / "outside.txt"
    outside.write_text(_secret_text(token), encoding="utf-8")
    (evidence / "ui" / UTC_NAME).unlink()
    (evidence / "ui" / UTC_NAME).symlink_to(outside)
    (evidence / "in-pack.lnk").symlink_to(outside)
    (evidence / "dangling.lnk").symlink_to(tmp_path / "missing-target")
    fifo = evidence / "pipe.fifo"
    os.mkfifo(fifo)
    allow = _write_allowlist(tmp_path / "allow.json", _reviewed_entries())
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("link", UTC_REL) in err
    assert _hit("link", "in-pack.lnk") in err
    assert _hit("link", "dangling.lnk") in err
    assert _hit("link", "pipe.fifo") in err

    linked_root = tmp_path / "root-link"
    linked_root.symlink_to(evidence)
    code, _out, err = _run(
        [str(linked_root), "--no-allowlist"], capsys, (token,)
    )
    assert code == 1
    assert _hit("link", linked_root.name) in err

    dir_pack = tmp_path / "dir-pack"
    dir_pack.mkdir()
    (dir_pack / "ui").symlink_to(evidence / "ui")
    code, _out, err = _run([str(dir_pack), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("link", "ui") in err


def test_spec_secret_appended_to_tar_is_trailing_bytes(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "pack.tar").write_bytes(
        _tar_bytes([(UTC_REL, UTC_PNG)]) + _secret_text(token).encode("utf-8")
    )
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_two_tars_joined_with_cat(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    first = _tar_bytes([(UTC_REL, UTC_PNG)])
    second = _tar_bytes([("notes.txt", _secret_text(token).encode("utf-8"))])
    (evidence / "pack.tar").write_bytes(first + second)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_tgz_of_joined_tars(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    first = _tar_bytes([(UTC_REL, UTC_PNG)])
    second = _tar_bytes([("notes.txt", _secret_text(token).encode("utf-8"))])
    (evidence / "pack.tgz").write_bytes(gzip.compress(first + second))
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tgz") in err


def test_spec_corrupted_second_tar_header(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    first = _tar_bytes([(UTC_REL, UTC_PNG)])
    second = bytearray(_tar_bytes([("notes.txt", _secret_text(token).encode("utf-8"))]))
    second[0] ^= 0xFF
    (evidence / "pack.tar").write_bytes(first + bytes(second))
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_old_style_dir_member_with_payload(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    payload = _secret_text(token).encode("utf-8")
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as bundle:
        info = tarfile.TarInfo(name="hidden/")
        info.size = len(payload)
        info.type = tarfile.REGTYPE
        bundle.addfile(info, io.BytesIO(payload))
    (evidence / "pack.tar").write_bytes(raw.getvalue())
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_zlib_unused_data_secret(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "note.zlib").write_bytes(
        zlib.compress(b"ok\n") + _secret_text(token).encode("utf-8")
    )
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "note.zlib") in err


def test_spec_zlib_unused_data_pgdmp(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "note.zlib").write_bytes(zlib.compress(b"ok\n") + b"PGDMP\x00custom")
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "note.zlib") in err


def test_spec_unreadable_directory_is_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    locked = evidence / "locked"
    locked.mkdir(parents=True)
    (locked / "notes.txt").write_text(_secret_text(token), encoding="utf-8")
    os.chmod(locked, 0)
    try:
        try:
            os.listdir(locked)
        except OSError:
            pass
        else:
            pytest.skip(
                "unreadable directories not enforceable here: "
                "listdir succeeded after chmod 0 (likely running as root)"
            )
        code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
        assert code == 1
        assert _hit("unreadable", "locked") in err
        assert "Traceback" not in err
    finally:
        os.chmod(locked, 0o700)


def test_spec_unreadable_file_is_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    target = evidence / "notes.txt"
    target.write_text(_secret_text(token), encoding="utf-8")
    os.chmod(target, 0)
    opened = None
    try:
        try:
            opened = os.open(os.fspath(target), os.O_RDONLY)
        except OSError:
            opened = None
        else:
            pytest.skip(
                "unreadable files not enforceable here: "
                "open succeeded after chmod 0 (likely running as root)"
            )
        code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
        assert code == 1
        assert _hit("unreadable", "notes.txt") in err
        assert "Traceback" not in err
    finally:
        if opened is not None:
            os.close(opened)
        os.chmod(target, 0o600)


def test_spec_max_nest_exact_and_plus_one_gzip_and_zlib(tmp_path, capsys):
    token = _runtime_pool_token()
    gzip_dir = tmp_path / "gzip"
    gzip_dir.mkdir()
    payload = b"ok\n"
    for _ in range(8):
        payload = gzip.compress(payload)
    (gzip_dir / "nested.gz").write_bytes(payload)
    code, _out, err = _run([str(gzip_dir), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "nested.gz") in err

    zlib_dir = tmp_path / "zlib"
    zlib_dir.mkdir()
    payload = b"ok\n"
    for _ in range(8):
        payload = zlib.compress(payload)
    (zlib_dir / "nested.zlib").write_bytes(payload)
    code, _out, err = _run([str(zlib_dir), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "nested.zlib") in err


def test_spec_decompress_cap_exact_multifile_and_zlib(tmp_path, capsys, monkeypatch):
    token = _runtime_pool_token()
    monkeypatch.setattr(scan, "MAX_SCAN_BYTES", 16)
    exact = tmp_path / "exact"
    exact.mkdir()
    (exact / "exact.txt").write_text("x" * 16, encoding="utf-8")
    code, out, err = _run([str(exact), "--no-allowlist"], capsys, (token,))
    assert code == 0
    assert "clean" in out
    assert "HIT " not in err

    multi = tmp_path / "multi"
    multi.mkdir()
    (multi / "a.txt").write_text("x" * 16, encoding="utf-8")
    (multi / "b.txt").write_text("y", encoding="utf-8")
    code, _out, err = _run([str(multi), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("size-cap", "b.txt") in err

    over = tmp_path / "over"
    over.mkdir()
    (over / "over.txt").write_text("x" * 17, encoding="utf-8")
    code, _out, err = _run([str(over), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("size-cap", "over.txt") in err

    zipped = tmp_path / "zipped"
    zipped.mkdir()
    (zipped / "note.zlib").write_bytes(zlib.compress(b"x" * 16))
    code, _out, err = _run([str(zipped), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "note.zlib") in err


def test_spec_sha_entry_cannot_hide_dump(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    payload = b"PGDMP\x00custom-format"
    (evidence / "backup.bin").write_bytes(payload)
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "backup.bin", "sha256": hashlib.sha256(payload).hexdigest()}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("dump file", "backup.bin") in err


def test_spec_socket_file_is_a_link_hit(tmp_path, capsys):
    # Unix sockets need bind; skip with a reason if the OS refuses the path.
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    sock_path = evidence / "svc.sock"
    handle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        handle.bind(os.fspath(sock_path))
    except OSError as exc:
        pytest.skip(f"unix socket not creatable here: {exc}")
    finally:
        handle.close()
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("link", "svc.sock") in err


def test_spec_device_file_is_a_link_hit(tmp_path, capsys):
    # Block devices need mknod/root. The S_IFBLK/S_IFCHR unit test below
    # covers the classifier when this skip fires. Never skip silently.
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    dev = evidence / "blkdev"
    try:
        os.mknod(dev, 0o600 | stat.S_IFBLK, os.makedev(1, 0))
    except (OSError, AttributeError, PermissionError) as exc:
        pytest.skip(
            f"block device not creatable here (needs root or mknod): {exc}"
        )
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("link", "blkdev") in err


def test_special_kind_classifies_block_and_char_modes():
    assert scan._special_kind(stat.S_IFBLK | 0o600) is True
    assert scan._special_kind(stat.S_IFCHR | 0o600) is True
    assert scan._special_kind(stat.S_IFREG | 0o600) is False


def test_spec_tar_fifo_and_chardev_members(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    archive = evidence / "pack.tar"
    with tarfile.open(archive, "w") as bundle:
        _add_tar_member(bundle, "ui/notes.txt", _secret_text(token).encode("utf-8"))
        fifo = tarfile.TarInfo(name="ui/pipe")
        fifo.type = tarfile.FIFOTYPE
        bundle.addfile(fifo)
        chardev = tarfile.TarInfo(name="ui/tty")
        chardev.type = tarfile.CHRTYPE
        chardev.devmajor = 1
        chardev.devminor = 3
        bundle.addfile(chardev)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def test_spec_tar_casefold_collision_inside_archive(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    _write_tar_with_members(
        evidence / "pack.tar",
        [
            ("Note.txt", _secret_text(token).encode("utf-8")),
            ("note.txt", b"ok\n"),
        ],
    )
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "pack.tar") in err


def _old_style_tar(name: str, payload: bytes) -> bytes:
    header = bytearray(512)
    name_b = name.encode("ascii")[:100]
    header[0 : len(name_b)] = name_b
    header[100:108] = b"0000644\x00"
    header[108:116] = b"0000000\x00"
    header[116:124] = b"0000000\x00"
    header[124:136] = f"{len(payload):011o}\x00".encode("ascii")
    header[136:148] = b"00000000000\x00"
    header[156:157] = b"0"
    header[148:156] = b"        "
    checksum = sum(header)
    header[148:156] = f"{checksum:06o}\x00 ".encode("ascii")
    padded = payload + (b"\x00" * ((512 - (len(payload) % 512)) % 512))
    return bytes(header) + padded + (b"\x00" * 1024)


def test_archive_signatures_in_folder_are_hits(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    samples = {
        "ustar.tar": _tar_bytes([("notes.txt", b"ok\n")]),
        "oldstyle.tar": _old_style_tar("notes.txt", b"ok\n"),
        "note.gz": gzip.compress(b"ok\n"),
        "z78_01.bin": b"\x78\x01" + b"pad\x00",
        "z78_5e.bin": b"\x78\x5e" + b"pad\x00",
        "z78_9c.bin": b"\x78\x9c" + b"pad\x00",
        "z78_da.bin": b"\x78\xda" + b"pad\x00",
        "note.xz": b"\xfd7zXZ\x00" + b"pad",
        "note.bz2": b"BZh" + b"pad\x00",
        "note.lz4": b"\x04\"M\x18" + b"pad",
        "note.rar": b"Rar!\x1a\x07" + b"pad",
        "note.lzip": b"LZIP" + b"pad\x00",
        "note.Z": b"\x1f\x9d" + b"pad",
        "note.cpio": b"070701" + b"pad\x00",
        "note.lzma": b"\x5d\x00\x00" + b"pad\x00",
        "junk.gz": b"xxxx" + gzip.compress(b"ok\n"),
        "note.zip": b"PK\x03\x04" + b"pad",
        "empty.zip": b"PK\x05\x06" + b"pad",
        "span.zip": b"PK\x07\x08" + b"pad",
        "note.zst": b"\x28\xb5\x2f\xfd" + b"pad",
        "note.7z": b"7z\xbc\xaf'\x1c" + b"pad",
    }
    for name, data in samples.items():
        (evidence / name).write_bytes(data)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    for name in samples:
        assert _hit("archive", name) in err


def test_sha_entry_cannot_hide_archive(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    payload = gzip.compress(_secret_text(token).encode("utf-8"))
    (evidence / "hidden.gz").write_bytes(payload)
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "hidden.gz", "sha256": hashlib.sha256(payload).hexdigest()}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("archive", "hidden.gz") in err


def test_name_is_scanned_for_pool_token_and_configured_secret(
    tmp_path, capsys, monkeypatch
):
    token = _token_with_symbol("_")
    configured = "seed" + uuid.uuid4().hex[:12]
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    (evidence / token).mkdir(parents=True)
    (evidence / token / f"{configured}.txt").write_text("ok\n", encoding="utf-8")
    (evidence / configured).mkdir()
    (evidence / configured / "notes.txt").write_text("ok\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, configured)
    )
    assert code == 1
    folder_hit = _redacted_path(token, (configured,))
    file_hit = _redacted_path(f"{token}/{configured}.txt", (configured,))
    parent_hit = _redacted_path(configured, (configured,))
    child_hit = _redacted_path(f"{configured}/notes.txt", (configured,))
    assert _hit("password-pool token", folder_hit) in err
    assert _hit("configured secret", file_hit) in err
    assert _hit("configured secret", parent_hit) in err
    assert _hit("configured secret", child_hit) in err
    assert "<redacted name hmac:" in err
    assert token not in out
    assert token not in err
    assert configured not in out
    assert configured not in err


def test_content_hit_redacts_secret_parent_segment(tmp_path, capsys):
    token = _token_with_symbol("_")
    leak = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    (evidence / token).mkdir(parents=True)
    (evidence / token / "notes.txt").write_text(_secret_text(leak), encoding="utf-8")
    code, _out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, leak)
    )
    assert code == 1
    shown = _redacted_path(f"{token}/notes.txt")
    assert _hit("password-pool token", shown, line=2) in err
    assert token not in err
    assert leak not in err


def test_slash_secret_redacts_whole_path(tmp_path, capsys, monkeypatch):
    left = "seed" + uuid.uuid4().hex[:6]
    right = "part" + uuid.uuid4().hex[:6]
    configured = f"{left}/{right}"
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    (evidence / left).mkdir(parents=True)
    (evidence / left / right).write_text("ok\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (configured, left, right)
    )
    assert code == 1
    assert _hit("configured secret", _redacted_path(f"{left}/{right}", (configured,))) in err
    assert configured not in out
    assert configured not in err
    assert left not in err
    assert right not in err


def test_missing_evidence_redacts_secret_name(tmp_path, capsys):
    token = _token_with_symbol("_")
    missing = tmp_path / token
    code, out, err = _run([str(missing), "--no-allowlist"], capsys, (token,))
    assert code == 2
    assert "not found" in err
    assert token not in out
    assert token not in err


def test_clean_line_redacts_secret_parent(tmp_path, capsys, monkeypatch):
    configured = "seed" + uuid.uuid4().hex[:12]
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    parent = tmp_path / configured
    evidence = parent / "evidence"
    evidence.mkdir(parents=True)
    (evidence / "notes.txt").write_text("sample id 123\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (configured,))
    assert code == 0
    assert "clean" in out
    assert configured not in out
    assert configured not in err
    assert "<redacted name hmac:" in out


def test_source_scan_refuses_secret_named_root(tmp_path, capsys):
    token = _token_with_symbol("_")
    evidence = tmp_path / token
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("password-pool token", _redacted_path(token)) in err
    assert token not in out
    assert token not in err


def test_missing_allowlist_redacts_configured_secret(tmp_path, capsys, monkeypatch):
    configured = "seed" + uuid.uuid4().hex[:12]
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    missing = tmp_path / configured / "allow.json"
    code, out, err = _run(
        [str(evidence), "--allowlist", str(missing)], capsys, (configured,)
    )
    assert code == 2
    assert "allowlist not found" in err
    assert configured not in out
    assert configured not in err


def test_invalid_json_allowlist_redacts_configured_secret(
    tmp_path, capsys, monkeypatch
):
    configured = "seed" + uuid.uuid4().hex[:12]
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    allow_dir = tmp_path / configured
    allow_dir.mkdir()
    allow = allow_dir / "allow.json"
    allow.write_text("{not-json", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (configured,)
    )
    assert code == 2
    assert "allowlist is not valid JSON" in err
    assert configured not in out
    assert configured not in err


def test_missing_secrets_file_redacts_configured_secret(
    tmp_path, capsys, monkeypatch
):
    configured = "seed" + uuid.uuid4().hex[:12]
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    missing = tmp_path / configured / "secrets.env"
    code, out, err = _run(
        [str(evidence), "--no-allowlist", "--secrets-file", str(missing)],
        capsys,
        (configured,),
    )
    assert code == 2
    assert "secrets file not found" in err
    assert configured not in out
    assert configured not in err


def test_hmac_tag_is_not_plain_sha256_and_differs_across_runs():
    name = "seed" + uuid.uuid4().hex[:12]
    tag = scan._redact_tag(name)
    plain = hashlib.sha256(os.fsencode(name)).hexdigest()[:8]
    assert tag.startswith("<redacted name hmac:")
    assert plain not in tag
    previous = scan._REDACT_KEY
    try:
        scan._REDACT_KEY = os.urandom(32)
        other = scan._redact_tag(name)
        assert other != tag
        assert plain not in other
    finally:
        scan._REDACT_KEY = previous


def test_root_named_configured_secret_is_a_hit(tmp_path, capsys, monkeypatch):
    configured = "seed" + uuid.uuid4().hex[:12]
    monkeypatch.setenv("POSTGRES_PASSWORD", configured)
    evidence = tmp_path / configured
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (configured,))
    assert code == 1
    assert _hit("configured secret", _redacted_path(configured, (configured,))) in err
    assert configured not in out
    assert configured not in err


def test_hex_and_base64_runs_of_200_are_hits(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    hex_run = ("ab" * 100)
    b64_run = ("A" * 200) + "=="
    assert len(hex_run) == 200
    (evidence / "hex.txt").write_text(f"id {hex_run}\n", encoding="utf-8")
    (evidence / "b64.txt").write_text(f"blob {b64_run}\n", encoding="utf-8")
    code, _out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, hex_run, b64_run)
    )
    assert code == 1
    assert _hit("encoded run", "hex.txt", line=1) in err
    assert _hit("encoded run", "b64.txt", line=1) in err


def test_utf8_text_starting_x_caret_is_not_archive(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("x^ just a note\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 0
    assert "archive" not in err
    assert "clean" in out


def test_utf8_text_starting_bzh_is_not_archive(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("BZh just a note\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 0
    assert "archive" not in err
    assert "clean" in out


def test_png_bytes_after_iend_are_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    iend = b"\x00\x00\x00\x00IEND" + b"\x11\x22\x33\x44"
    png = b"\x89PNG\r\n\x1a\n" + b"idat" + iend + token.encode("utf-8")
    (evidence / "shot.png").write_bytes(png)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("png-trailing", "shot.png") in err


def test_regular_file_as_evidence_is_refused(tmp_path, capsys):
    token = _runtime_pool_token()
    target = tmp_path / "notes.txt"
    target.write_text("ok\n", encoding="utf-8")
    code, _out, err = _run([str(target), "--no-allowlist"], capsys, (token,))
    assert code == 2
    assert "not a directory" in err
    assert "not a directory" in err


def test_stray_gzip_magic_in_binary_and_pdf_is_not_archive(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    random_bin = _binary_with_stray_gzip(b"RAND")
    pdf_like = _binary_with_stray_gzip(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    assert b"\x1f\x8b" in random_bin
    assert b"\x1f\x8b\x08" in random_bin
    assert b"\x1f\x8b" in pdf_like
    assert b"\x1f\x8b\x08" in pdf_like
    assert scan.archive_kind(random_bin) is None
    assert scan.archive_kind(pdf_like) is None
    (evidence / "blob.bin").write_bytes(random_bin)
    (evidence / "note.pdf").write_bytes(pdf_like)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "blob.bin") not in err
    assert _hit("archive", "note.pdf") not in err
    assert "archive" not in err


def test_junk_then_real_gzip_is_still_an_archive_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    payload = b"xxxx" + gzip.compress(b"ok\n")
    (evidence / "junk.gz").write_bytes(payload)
    code, _out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 1
    assert _hit("archive", "junk.gz") in err


def test_runtime_jwt_is_an_unsuppressible_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    jwt = _runtime_jwt()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {jwt}\n", encoding="utf-8")
    digest = hashlib.sha256((evidence / "notes.txt").read_bytes()).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "notes.txt", "sha256": digest}],
    )
    code, out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err


def test_eyj_text_without_three_segments_is_not_a_jwt(tmp_path, capsys):
    token = _runtime_pool_token()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(
        "eyJ just a note about headers\neyJabc.def\n",
        encoding="utf-8",
    )
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token,))
    assert code == 0
    assert "jwt" not in err
    assert "clean" in out


@pytest.mark.parametrize("length", [220, 275])
def test_long_runtime_jwt_is_an_unsuppressible_hit(tmp_path, capsys, length):
    token = _runtime_pool_token()
    jwt = _runtime_jwt(length)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {jwt}\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token, jwt))
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err
