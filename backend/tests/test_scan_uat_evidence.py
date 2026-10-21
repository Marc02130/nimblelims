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
import time
import uuid
import zlib
from pathlib import Path
from urllib.parse import quote

import jwt
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


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _runtime_header_jwt(
    header: dict[str, object],
    length: int | None = None,
) -> str:
    first = _b64url(json.dumps(header, separators=(",", ":")).encode("ascii"))
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    def part(count: int) -> str:
        chars: list[str] = []
        for index in range(count):
            if index % 40 == 0:
                chars.append("g")
                continue
            chars.append(alphabet[os.urandom(1)[0] % len(alphabet)])
        return "".join(chars)

    if length is None:
        token = f"{first}.{part(12)}.{part(12)}"
        assert token.startswith("eyJ")
        assert len(token.split(".")) == 3
        assert len(token) < 200
        return token
    remaining = length - len(first) - 2
    assert remaining >= 2
    second = remaining // 2
    third = remaining - second
    token = f"{first}.{part(second)}.{part(third)}"
    assert token.startswith("eyJ")
    assert len(token.split(".")) == 3
    assert len(token) == length
    return token


def _runtime_jwt(length: int | None = None) -> str:
    return _runtime_header_jwt({"alg": "HS256", "typ": "JWT"}, length)


# PyJWT is already pinned in backend/requirements.txt (auth stack). Leak
# tests use it at runtime only; tokens are never committed, printed, or logged.
JWT_LEAK_TRIALS = 56


def _pyjwt_access_token() -> str:
    """Runtime PyJWT token. Do not print or log the return value."""
    key = os.urandom(32)
    claims = {
        "sub": uuid.uuid4().hex,
        "username": "u" + uuid.uuid4().hex[:12],
        "role": "lab-technician",
        "permissions": ["sample:read", "result:write"],
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, key, algorithm="HS256")
    if not isinstance(token, str):
        token = token.decode("ascii")
    if not (token.startswith("eyJ") and token.count(".") == 2):
        raise AssertionError("PyJWT produced a malformed test token")
    return token


def _jwt_fragments(token: str) -> tuple[str, str, str]:
    header, payload, _signature = token.split(".")
    return token, f"{header}.{payload}", payload


def _assert_jwt_absent(stdout: str, stderr: str, token: str) -> None:
    full, header_payload, payload = _jwt_fragments(token)
    blobs = (stdout, stderr)
    if any(
        fragment in blob
        for fragment in (full, header_payload, payload)
        for blob in blobs
        if fragment
    ):
        raise AssertionError("planted JWT fragment leaked into stdout or stderr")


def _jwt_dots_encoded(token: str) -> str:
    encoded = token.replace(".", "%2E")
    if encoded == token or "%2E" not in encoded:
        raise AssertionError("dot-encoded JWT was not percent-encoded")
    return encoded


def _jwt_segment_encoded(token: str) -> str:
    header, payload, signature = token.split(".")
    def _enc(part: str) -> str:
        return part.replace("-", "%2D").replace("_", "%5F").replace("e", "%65")
    encoded = f"{header}.{_enc(payload)}.{_enc(signature)}"
    if encoded == token or "%" not in encoded:
        raise AssertionError("segment-encoded JWT was not percent-encoded")
    return encoded


def _assert_no_jwt_windows(
    stdout: str, stderr: str, token: str, width: int = 24
) -> None:
    """Refuse a leftover payload/signature window. Never print the token."""
    _header, payload, signature = token.split(".")
    blobs = (stdout, stderr)
    for source in (payload, signature):
        if len(source) < width:
            if source and any(source in blob for blob in blobs):
                raise AssertionError("planted JWT fragment leaked")
            continue
        for index in range(len(source) - width + 1):
            window = source[index : index + width]
            if any(window in blob for blob in blobs):
                raise AssertionError("planted JWT window leaked")


def _jwt_quote_layers(token: str, layers: int) -> str:
    """Fully percent-encode every byte, then nest ``%`` → ``%25``."""
    encoded = "".join("%{:02X}".format(ord(char)) for char in token)
    for _ in range(max(0, layers - 1)):
        encoded = encoded.replace("%", "%25")
    if encoded == token or "%" not in encoded:
        raise AssertionError("quoted JWT was not percent-encoded")
    return encoded


def _pyjwt_signature_mark_token() -> str:
    """Header/payload have no -/_; signature has at least one. Runtime only."""
    for _ in range(4000):
        token = _pyjwt_access_token()
        header, payload, signature = token.split(".")
        if any(mark in header or mark in payload for mark in "-_"):
            continue
        if "-" in signature or "_" in signature:
            return token
    raise AssertionError("could not mint a signature-mark token")


def _jwt_signature_mark_encoded(token: str) -> str:
    header, payload, signature = token.split(".")
    encoded_sig = signature.replace("-", "%2D").replace("_", "%5F")
    encoded = f"{header}.{payload}.{encoded_sig}"
    if encoded == token or "%" not in encoded:
        raise AssertionError("signature-mark JWT was not percent-encoded")
    return encoded


def _assert_no_jwt_grams(stdout: str, stderr: str, token: str) -> None:
    _header, payload, signature = token.split(".")
    blobs = (stdout, stderr)
    sources = [payload, signature]
    for part in (payload, signature):
        quoted = quote(part, safe="")
        if quoted != part:
            sources.append(quoted)
        inner = part.replace("-", "%2D").replace("_", "%5F").replace("e", "%65")
        if inner != part:
            sources.append(inner)
    for source in sources:
        if len(source) < 8:
            if source and any(source in blob for blob in blobs):
                raise AssertionError("planted JWT fragment leaked")
            continue
        for index in range(len(source) - 7):
            gram = source[index : index + 8]
            if any(gram in blob for blob in blobs):
                raise AssertionError("planted JWT 8-gram leaked")


def _b64url_run(count: int) -> str:
    """A base64url run that is not a 200+ hex or standard-Base64 hit."""
    chars: list[str] = []
    for index in range(count):
        if index % 40 == 0:
            chars.append("_")
        elif index % 40 == 1:
            chars.append("g")
        else:
            chars.append("A")
    return "".join(chars)


def _runtime_segment_jwt(payload_len: int, signature_len: int = 12) -> str:
    first = _b64url(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode(
            "ascii"
        )
    )
    token = f"{first}.{_b64url_run(payload_len)}.{_b64url_run(signature_len)}"
    assert token.startswith("eyJ")
    assert len(token.split(".")) == 3
    assert len(token.split(".")[1]) == payload_len
    assert len(token.split(".")[2]) == signature_len
    return token


def _unpadded_alg_header() -> dict[str, object]:
    for extra in range(48):
        header: dict[str, object] = {"alg": "HS256", "n": extra}
        encoded = _b64url(json.dumps(header, separators=(",", ":")).encode("ascii"))
        if encoded.startswith("eyJ") and len(encoded) % 4 != 0:
            return header
    raise AssertionError(
        "could not build a header whose base64url length is not a multiple of 4"
    )


def _dotted_eyj_blob(size: int = 256 * 1024, period: int = 8000) -> str:
    """Repeated eyJ with a dot every ``period`` chars (Günter's superlinear case)."""
    parts: list[str] = []
    filled = 0
    while filled < size:
        run_len = min(period, size - filled)
        run = ("eyJ" * ((run_len + 2) // 3))[:run_len]
        parts.append(run)
        filled += len(run)
        if filled < size:
            parts.append(".")
            filled += 1
    blob = "".join(parts)
    assert len(blob) == size
    return blob


def _gzip_cap_payload(count: int) -> bytes:
    stub = b"\x1f\x8b\x08\x00" + (b"\xff" * 16)
    body = bytearray(b"RAND")
    for _ in range(count):
        body.extend(stub)
        body.extend(b"\x00\x11\x22")
    return bytes(body)


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
        "note.rar": b"Rar!\x1a\x07" + b"pad\x00",
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


def test_redact_text_redacts_jwt_in_tar_error_text():
    jwt = _runtime_jwt()
    shown = scan.redact_text(f"tar: round/{jwt}: Cannot hard link")
    assert jwt not in shown
    assert "<redacted name hmac:" in shown
    assert shown.startswith("tar: round/")


def test_jwt_named_file_is_a_hit_and_redacted(tmp_path, capsys):
    token = _runtime_pool_token()
    jwt = _runtime_jwt()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / f"{jwt}.txt").write_text("ok\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token, jwt))
    assert code == 1
    shown = _redacted_path(f"{jwt}.txt")
    assert _hit("jwt", shown) in err
    assert "<redacted name hmac:" in err
    assert jwt not in out
    assert jwt not in err


def test_eyjx_dot_y_dot_z_is_not_a_jwt(tmp_path, capsys):
    token = _runtime_pool_token()
    probe = "".join(("eyJ", "x", ".", "y", ".", "z"))
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"note {probe}\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token, probe))
    assert code == 0
    assert "jwt" not in err
    assert "clean" in out
    assert scan.jwt_on_line(probe) is False


def test_eyj_plus_dot_a_dot_b_is_not_a_jwt(tmp_path, capsys):
    """Zero extra header chars after eyJ is not a JWT; alg still required."""
    token = _runtime_pool_token()
    plus_probe = "".join(("eyJ", "+", ".", "a", ".", "b"))
    zero_probe = "".join(("eyJ", ".", "a", ".", "b"))
    jwt = _runtime_header_jwt({"alg": "HS256"})
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(
        f"note {plus_probe}\nnote {zero_probe}\n",
        encoding="utf-8",
    )
    code, out, err = _run(
        [str(evidence), "--no-allowlist"],
        capsys,
        (token, plus_probe, zero_probe, jwt),
    )
    assert code == 0
    assert "jwt" not in err
    assert "clean" in out
    assert scan.jwt_on_line(plus_probe) is False
    assert scan.jwt_on_line(zero_probe) is False
    assert scan.jwt_on_line(jwt) is True
    assert jwt not in out
    assert jwt not in err


def test_jwt_header_without_alg_is_not_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    probe = _runtime_header_jwt({"typ": "JWT"})
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {probe}\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token, probe))
    assert code == 0
    assert "jwt" not in err
    assert "clean" in out
    assert scan.jwt_on_line(probe) is False


def test_real_shaped_jwt_header_with_alg_is_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    jwt = _runtime_header_jwt({"alg": "HS256"})
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {jwt}\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, (token, jwt))
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err
    assert scan.jwt_on_line(jwt) is True


def test_jwt_after_failed_header_is_still_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    decoy = "".join(("eyJ", "x", ".", "y", ".", "z"))
    jwt = _runtime_header_jwt({"alg": "HS256"})
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{decoy} {jwt}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, decoy, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err
    assert decoy not in out
    assert decoy not in err


def test_repeated_eyj_jwt_scan_is_linear_time():
    """256 KiB of dotted eyJ must stay well under the CI budget.

    Günter's follow-up: the one-char walk after each failed ``eyJ`` was
    superlinear. Repeated ``eyJ`` with a dot every ~8000 chars took 71 s
    on 128 KiB. This test uses 256 KiB of that same shape (2× the repro)
    so a return to that walk fails by more than an order of magnitude.

    The walk now finds base64url runs once with a compiled
    ``re.finditer(r"[A-Za-z0-9_-]+")`` and does a constant-time
    structure check at each ``eyJ``. Reaching the 16-``eyJ`` bound
    on this eyJ-dense dotted shape is an unsuppressible jwt hit
    and the first triple is redacted; the walk must still finish
    well under 15 s. This test always runs (no skip).
    ``redact_text`` is not timed here because the password-pool
    window scan is a separate linear pass.
    """
    blob = _dotted_eyj_blob(256 * 1024, 8000)
    jwt = _runtime_header_jwt({"alg": "HS256"})
    started = time.perf_counter()
    if scan.jwt_on_line(blob) is False:
        raise AssertionError("dotted eyJ blob did not hit the eyJ bound")
    shown = scan._redact_jwts(blob)
    elapsed = time.perf_counter() - started
    if shown == blob:
        raise AssertionError("dotted eyJ bound hit was not redacted")
    assert elapsed < 15.0
    assert scan.jwt_on_line(jwt) is True
    assert jwt not in blob
    assert jwt not in shown


def test_jwt_payload_over_200_and_near_8192_are_hits(tmp_path, capsys):
    token = _runtime_pool_token()
    over_200 = _runtime_segment_jwt(201)
    near_8192 = _runtime_segment_jwt(8192)
    over_bound = _runtime_segment_jwt(8193)
    assert len(over_200.split(".")[1]) == 201
    assert len(near_8192.split(".")[1]) == 8192
    assert len(over_bound.split(".")[1]) == 8193
    assert scan.jwt_on_line(over_200) is True
    assert scan.jwt_on_line(near_8192) is True
    assert scan.jwt_on_line(over_bound) is False
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "over200.txt").write_text(f"auth {over_200}\n", encoding="utf-8")
    (evidence / "near8192.txt").write_text(f"auth {near_8192}\n", encoding="utf-8")
    (evidence / "overbound.txt").write_text(f"auth {over_bound}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"],
        capsys,
        (token, over_200, near_8192, over_bound),
    )
    assert code == 1
    assert _hit("jwt", "over200.txt", line=1) in err
    assert _hit("jwt", "near8192.txt", line=1) in err
    assert _hit("jwt", "overbound.txt", line=1) not in err
    assert over_200 not in out
    assert over_200 not in err
    assert near_8192 not in out
    assert near_8192 not in err
    assert over_bound not in out
    assert over_bound not in err


def test_jwt_header_length_not_multiple_of_four_is_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    header = _unpadded_alg_header()
    jwt = _runtime_header_jwt(header)
    first = jwt.split(".", 1)[0]
    assert len(first) % 4 != 0
    assert scan.jwt_on_line(jwt) is True
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {jwt}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err


def test_jwt_header_longer_than_8192_is_still_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    header = {"alg": "HS256", "pad": "A" * 7000}
    first = _b64url(json.dumps(header, separators=(",", ":")).encode("ascii"))
    jwt = f"{first}.{_b64url_run(12)}.{_b64url_run(12)}"
    assert first.startswith("eyJ")
    assert len(first) > 8192
    assert scan.jwt_on_line(jwt) is True
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {jwt}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err


def test_failed_eyj_adjacent_to_real_token_is_still_a_hit(tmp_path, capsys):
    token = _runtime_pool_token()
    decoy = "".join(("eyJ", "x", ".", "y", ".", "z"))
    jwt = _runtime_header_jwt({"alg": "HS256"})
    adjacent = f"{decoy}{jwt}"
    assert decoy + jwt == adjacent
    assert scan.jwt_on_line(adjacent) is True
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{adjacent}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, decoy, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err
    assert decoy not in out
    assert decoy not in err


def test_eyjx_without_dots_adjacent_to_real_token_is_still_a_hit(tmp_path, capsys):
    """D8: giving up after a failed eyJ must not skip an immediate real token."""
    token = _runtime_pool_token()
    decoy = "eyJx"
    jwt = _runtime_header_jwt({"alg": "HS256"})
    adjacent = f"{decoy}{jwt}"
    assert decoy + jwt == adjacent
    assert "." not in decoy
    assert scan.jwt_on_line(decoy) is False
    assert scan.jwt_on_line(adjacent) is True
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{adjacent}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, decoy, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err
    assert decoy not in out
    assert decoy not in err


def test_double_dot_between_jwt_segments_is_not_a_jwt(tmp_path, capsys):
    """D16: separators must be a single ``.``; ``..`` is not a JWT."""
    token = _runtime_pool_token()
    jwt = _runtime_header_jwt({"alg": "HS256"})
    header, payload, signature = jwt.split(".")
    probe = f"{header}..{payload}.{signature}"
    assert scan.jwt_on_line(jwt) is True
    assert scan.jwt_on_line(probe) is False
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {probe}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, probe, jwt)
    )
    assert code == 0
    assert "jwt" not in err
    assert "clean" in out
    assert jwt not in out
    assert jwt not in err
    assert probe not in out
    assert probe not in err


def test_redact_text_pyjwt_missing_link_target_does_not_leak():
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        shown = scan.redact_text(
            f"tar: round/link: Cannot hard link to 'missing_{token}': No such file"
        )
        _assert_jwt_absent("", shown, token)
        if "<redacted name hmac:" not in shown:
            raise AssertionError("missing_ JWT link target was not redacted")


def test_redact_text_pyjwt_gone_path_does_not_leak():
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        shown = scan.redact_text(
            f"tar: gone/{token}: Cannot hard link to 'round/missing': No such file"
        )
        _assert_jwt_absent("", shown, token)
        if "<redacted name hmac:" not in shown:
            raise AssertionError("gone/ JWT path was not redacted")


def test_redact_text_pyjwt_bare_token_does_not_leak():
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        shown = scan.redact_text(f"tar: {token}: Cannot open: No such file")
        _assert_jwt_absent("", shown, token)
        if "<redacted name hmac:" not in shown:
            raise AssertionError("bare JWT in tar error text was not redacted")


def test_redact_text_pyjwt_before_configured_secret_and_pool():
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        secret = "seed" + uuid.uuid4().hex[:12]
        shown = scan.redact_text(f"tar: {token} secret={secret}", (secret,))
        _assert_jwt_absent("", shown, token)
        if secret in shown:
            raise AssertionError("configured secret leaked beside a JWT")


def test_redact_text_overlapping_configured_secret_still_redacts_jwt():
    """D13: secrets-before-JWTs would punch a hole in the token."""
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        payload = token.split(".")[1]
        if len(payload) < 12:
            raise AssertionError("payload too short for overlap secret")
        secret = payload[2:14]
        shown = scan.redact_text(f"tar: {token}", (secret,))
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_grams("", shown, token)
        if "<redacted name hmac:" not in shown:
            raise AssertionError("overlapping-secret JWT was not redacted")


def test_redact_text_percent_dot_jwt_does_not_leak_grams():
    """D15: a missing percent-decoded pass leaks %2E JWTs."""
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        encoded = _jwt_dots_encoded(token)
        member = f"tar: gone/{encoded}: Cannot hard link to 'round/missing'"
        target = f"tar: round/link: Cannot hard link to 'missing_{encoded}'"
        for text in (member, target):
            shown = scan.redact_text(text)
            _assert_jwt_absent("", shown, token)
            _assert_no_jwt_grams("", shown, token)
            if encoded in shown:
                raise AssertionError("percent-dot JWT leaked")
            if "<redacted name hmac:" not in shown:
                raise AssertionError("percent-dot JWT was not redacted")


def test_redact_text_percent_segment_jwt_does_not_leak_grams():
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        encoded = _jwt_segment_encoded(token)
        member = f"tar: gone/{encoded}: Cannot hard link to 'round/missing'"
        target = f"tar: round/link: Cannot hard link to 'missing_{encoded}'"
        for text in (member, target):
            shown = scan.redact_text(text)
            _assert_jwt_absent("", shown, token)
            _assert_no_jwt_grams("", shown, token)
            if encoded in shown:
                raise AssertionError("percent-segment JWT leaked")
            if "<redacted name hmac:" not in shown:
                raise AssertionError("percent-segment JWT was not redacted")


def test_pyjwt_name_and_verify_identity_do_not_leak():
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_access_token()
        for raw in (token, f"gone/{token}", f"missing_{token}", f"{token}.txt"):
            shown = scan.redact_name_path(raw)
            _assert_jwt_absent("", shown, token)
            if "<redacted name hmac:" not in shown:
                raise AssertionError("JWT name path was not redacted")
            formatted = scan.Hit(scan.KIND_JWT, (raw,), secrets=()).format()
            _assert_jwt_absent("", formatted, token)


def test_pyjwt_content_hit_does_not_leak(tmp_path, capsys):
    tokens = [_pyjwt_access_token() for _ in range(JWT_LEAK_TRIALS)]
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    for index, token in enumerate(tokens):
        (evidence / f"notes{index}.txt").write_text(f"auth {token}\n", encoding="utf-8")
    code = scan_main([str(evidence), "--no-allowlist"])
    captured = capsys.readouterr()
    if code != 1:
        raise AssertionError("PyJWT content files did not hit")
    for token in tokens:
        _assert_jwt_absent(captured.out, captured.err, token)


def test_jwt_walk_runs_once_per_line(monkeypatch):
    seen: list[str] = []
    real = scan._iter_jwts

    def counted(text: str):
        seen.append(text)
        yield from real(text)

    monkeypatch.setattr(scan, "_iter_jwts", counted)
    scan.scan_text(("notes.txt",), "sample id 123\n")
    if seen != ["sample id 123"]:
        raise AssertionError("JWT walk was not one pass per line")
    seen.clear()
    scan.scan_text(("notes.txt",), "one\ntwo\n")
    if seen != ["one", "two"]:
        raise AssertionError("JWT walk was not one pass per two lines")


def test_percent_dot_jwt_is_jwt_hit_not_pool(tmp_path, capsys):
    """D15: a %2E-encoded token is a JWT hit, not a pool hit."""
    token = _pyjwt_access_token()
    encoded = _jwt_dots_encoded(token)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{encoded}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, encoded)
    )
    if code != 1:
        raise AssertionError("%2E JWT did not hit")
    if _hit("jwt", "notes.txt", line=1) not in err:
        raise AssertionError("%2E JWT was not reported as jwt")
    if _hit("password-pool token", "notes.txt", line=1) in err:
        raise AssertionError("%2E JWT was reported as a pool hit")
    _assert_jwt_absent(out, err, token)


def test_double_percent_encoded_jwt_is_detected_and_redacted(tmp_path, capsys):
    token = _pyjwt_access_token()
    encoded = token.replace(".", "%252E")
    if "%252E" not in encoded:
        raise AssertionError("double-encoded JWT was not percent-encoded")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{encoded}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, encoded)
    )
    if code != 1:
        raise AssertionError("double-encoded JWT did not hit")
    if _hit("jwt", "notes.txt", line=1) not in err:
        raise AssertionError("double-encoded JWT was not reported as jwt")
    shown = scan.redact_text(f"tar: {encoded}: Cannot open")
    _assert_jwt_absent("", shown, token)
    _assert_no_jwt_grams("", shown, token)
    _assert_no_jwt_windows("", shown, token)
    if encoded in shown:
        raise AssertionError("double-encoded JWT leaked")


def test_redact_text_signature_mark_encoded_leaves_no_24_window():
    """R47-F1: %2D/%5F in the signature must not leave a 24-char tail."""
    for _ in range(JWT_LEAK_TRIALS):
        token = _pyjwt_signature_mark_token()
        encoded = _jwt_signature_mark_encoded(token)
        shown = scan.redact_text(f"tar: {encoded}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_grams("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        if encoded in shown:
            raise AssertionError("signature-mark encoded JWT leaked")
        if "<redacted name hmac:" not in shown:
            raise AssertionError("signature-mark encoded JWT was not redacted")


def test_layered_percent_jwt_is_jwt_hit_in_name_and_content(tmp_path, capsys):
    """R47-F2: %252E, fully double-encoded, and triple-encoded are jwt hits."""
    cases = (
        lambda token: token.replace(".", "%252E"),
        lambda token: _jwt_quote_layers(token, 2),
        lambda token: token.replace(".", "%25252E"),
        lambda token: _jwt_quote_layers(token, 3),
    )
    for index, encode in enumerate(cases):
        token = _pyjwt_access_token()
        encoded = encode(token)
        evidence = tmp_path / f"evidence-{index}"
        evidence.mkdir()
        (evidence / "notes.txt").write_text(f"{encoded}\n", encoding="utf-8")
        code, out, err = _run(
            [str(evidence), "--no-allowlist"], capsys, (token, encoded)
        )
        if code != 1:
            raise AssertionError("layered percent JWT did not hit content")
        if _hit("jwt", "notes.txt", line=1) not in err:
            raise AssertionError("layered percent JWT was not a content jwt hit")
        if _hit("password-pool token", "notes.txt", line=1) in err:
            raise AssertionError("layered percent JWT was reported as a pool hit")
        _assert_jwt_absent(out, err, token)
        _assert_no_jwt_windows(out, err, token)
        shown = scan.redact_text(f"tar: {encoded}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        if encoded in shown:
            raise AssertionError("layered percent JWT leaked")
        name_hits = scan.scan_name((encoded,), encoded)
        if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
            raise AssertionError("layered percent JWT name was not a jwt hit")
        formatted = scan.Hit(scan.KIND_JWT, (encoded,), secrets=()).format()
        _assert_jwt_absent("", formatted, token)
        _assert_no_jwt_windows("", formatted, token)


def test_info_nfkc_u_percent_and_tar_newline_jwt_are_hits(tmp_path, capsys):
    """Info: NFKC and %u002E hit in content; tar escapes only in names/tar."""
    token = _pyjwt_access_token()
    content_probes = (
        token.replace(".", "\uff0e"),
        token.replace(".", "%u002E"),
    )
    for probe in content_probes:
        if scan.jwt_on_line(probe) is False and not any(
            scan.jwt_on_line(variant) for variant in scan._text_variants(probe)
        ):
            raise AssertionError("info-encoded JWT was not detected")
        hits = scan.scan_text(("notes.txt",), f"{probe}\n")
        if not any(hit.kind == scan.KIND_JWT for hit in hits):
            raise AssertionError("info-encoded JWT was not a content jwt hit")
        shown = scan.redact_text(f"tar: {probe}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        if token in shown:
            raise AssertionError("info-encoded JWT leaked")
    tar_probes = (
        token.replace(".", r"\n"),
        token.replace(".", r"\012"),
    )
    for probe in tar_probes:
        name_hits = scan.scan_name((probe,), probe)
        if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
            raise AssertionError("tar-escaped JWT name was not a jwt hit")
        shown = scan.redact_text(f"tar: {probe}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        content_hits = scan.scan_text(("notes.txt",), f"{probe}\n")
        if not any(hit.kind == scan.KIND_JWT for hit in content_hits):
            raise AssertionError("content JWT-only unescape missed a tar-split token")
        if any(hit.kind == scan.KIND_POOL for hit in content_hits):
            raise AssertionError("content JWT-only unescape ran pool rules")


def test_tar_octal_escape_jwt_is_detected_and_redacted(tmp_path, capsys):
    token = _pyjwt_access_token()
    escaped = token.replace(".", r"\056")
    if r"\056" not in escaped:
        raise AssertionError("tar-escaped JWT was not octal-encoded")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{escaped}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, escaped)
    )
    if _hit("jwt", "notes.txt", line=1) not in err:
        raise AssertionError("content \\056 JWT was not a jwt hit")
    if "password-pool token" in err:
        raise AssertionError("content \\056 JWT was reported as a pool hit")
    shown = scan.redact_text(f"tar: {escaped}: Cannot open")
    _assert_jwt_absent("", shown, token)
    _assert_no_jwt_grams("", shown, token)
    if token.replace(".", ".") in shown and token in shown:
        raise AssertionError("tar-escaped JWT leaked")
    if escaped in shown:
        raise AssertionError("tar-escaped JWT leaked")
    name_hits = scan.scan_name((escaped,), escaped)
    if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
        raise AssertionError("tar-escaped JWT name was not a jwt hit")


def test_jwt_signature_over_8192_is_a_hit_and_redacted(tmp_path, capsys):
    token = _runtime_pool_token()
    jwt = _runtime_segment_jwt(12, 8193)
    assert len(jwt.split(".")[2]) == 8193
    assert scan.jwt_on_line(jwt) is True
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"auth {jwt}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, jwt)
    )
    assert code == 1
    assert _hit("jwt", "notes.txt", line=1) in err
    assert jwt not in out
    assert jwt not in err
    shown = scan.redact_text(f"tar: {jwt}: Cannot open")
    if jwt in shown or jwt.split(".")[2] in shown:
        raise AssertionError("long signature was not fully redacted")


def test_repeated_eyj_then_dot_a_dot_b_256kib_is_fast():
    """One eyJ run plus .a.b at 256 KiB stays linear (bound-hit path).

    Also times a decoy run at the 32 KiB header cap (bound hit).
    """
    size = 256 * 1024
    header = ("eyJ" * ((size + 2) // 3))[:size]
    blob = f"{header}.a.b"
    started = time.perf_counter()
    if scan.jwt_on_line(blob) is False:
        raise AssertionError("over-cap eyJ header was not a bound hit")
    shown = scan._redact_jwts(blob)
    elapsed = time.perf_counter() - started
    if blob in shown:
        raise AssertionError("over-cap eyJ header was not fully redacted")
    assert elapsed < 5.0
    cap_header = ("eyJ" * ((scan._JWT_HEADER_MAX + 2) // 3))[: scan._JWT_HEADER_MAX]
    decoy_blob = f"{cap_header}.a.b"
    started = time.perf_counter()
    if scan.jwt_on_line(decoy_blob) is False:
        raise AssertionError("eyJ bound was not a hit on a max-header decoy run")
    decoy_shown = scan._redact_jwts(decoy_blob)
    assert time.perf_counter() - started < 2.0
    if decoy_blob in decoy_shown:
        raise AssertionError("eyJ bound did not redact the whole decoy run")
    jwt = _runtime_header_jwt({"alg": "HS256"})
    assert scan.jwt_on_line(jwt) is True


def test_jwt_header_over_32kib_is_bound_hit_and_is_fast():
    """A header run over 32 KiB with a dotted triple is a bound hit."""
    over = scan._JWT_HEADER_MAX + 64
    header = ("eyJ" * ((over + 2) // 3))[:over]
    blob = f"{header}.aa.bb"
    assert len(header) > scan._JWT_HEADER_MAX
    started = time.perf_counter()
    if scan.jwt_on_line(blob) is False:
        raise AssertionError("over-cap header dotted triple was not a jwt hit")
    shown = scan._redact_jwts(blob)
    elapsed = time.perf_counter() - started
    if blob in shown:
        raise AssertionError("over-cap header dotted triple was not redacted")
    assert elapsed < 2.0
    jwt = _runtime_header_jwt({"alg": "HS256"})
    assert scan.jwt_on_line(jwt) is True


def test_jwt_walk_skips_finditer_when_line_has_no_eyj(monkeypatch):
    calls = {"n": 0}
    real = scan._jwt_run_finditer

    def counted(text: str, *args, **kwargs):
        calls["n"] += 1
        return real(text, *args, **kwargs)

    monkeypatch.setattr(scan, "_jwt_run_finditer", counted)
    assert scan.jwt_on_line("sample id 123") is False
    if calls["n"] != 0:
        raise AssertionError("JWT walk did not return early on a line with no eyJ")
    jwt = _runtime_header_jwt({"alg": "HS256"})
    assert scan.jwt_on_line(jwt) is True
    if calls["n"] < 1:
        raise AssertionError("JWT walk did not use finditer on an eyJ line")


def test_cli_jwt_walk_runs_once_per_content_line(tmp_path, capsys, monkeypatch):
    line = "sample id 123"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{line}\n", encoding="utf-8")
    content_calls = {"n": 0}
    real = scan._iter_jwts

    def counted(text: str):
        if text == line:
            content_calls["n"] += 1
        yield from real(text)

    monkeypatch.setattr(scan, "_iter_jwts", counted)
    code, _out, _err = _run(
        [str(evidence), "--no-allowlist"], capsys, (_runtime_pool_token(),)
    )
    if code != 0:
        raise AssertionError("clean one-line evidence did not scan clean")
    if content_calls["n"] != 1:
        raise AssertionError("CLI JWT walk was not one pass per content line")


_EYJ_DECOY = "eyJx"


def _glued_decoy_jwt(token: str, decoys: int) -> str:
    glued = (_EYJ_DECOY * decoys) + token
    if decoys and not glued.startswith(_EYJ_DECOY):
        raise AssertionError("decoy prefix was not glued")
    return glued


def test_eyj_decoy_prefix_0_15_40_still_hit(tmp_path, capsys):
    """Parity with main: 0, 15, and 40 glued decoys still hit."""
    for decoys in (0, 15, 40):
        token = _pyjwt_access_token()
        glued = _glued_decoy_jwt(token, decoys)
        evidence = tmp_path / f"evidence-{decoys}"
        evidence.mkdir()
        (evidence / "notes.txt").write_text(f"{glued}\n", encoding="utf-8")
        code, out, err = _run(
            [str(evidence), "--no-allowlist"], capsys, (token, glued)
        )
        if code != 1:
            raise AssertionError("decoy-prefixed JWT did not hit content")
        if _hit("jwt", "notes.txt", line=1) not in err:
            raise AssertionError("decoy-prefixed JWT was not a content jwt hit")
        _assert_jwt_absent(out, err, token)
        name_hits = scan.scan_name((glued,), glued)
        if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
            raise AssertionError("decoy-prefixed JWT name was not a jwt hit")
        formatted = scan.Hit(scan.KIND_JWT, (glued,), secrets=()).format()
        _assert_jwt_absent("", formatted, token)


def test_eyj_decoy_prefix_16_and_17_hit_and_redact(tmp_path, capsys, monkeypatch):
    """Bound reached is an unsuppressible jwt hit; whole run is redacted."""
    real_alg = scan._jwt_header_has_alg
    for decoys in (16, 17):
        token = _pyjwt_access_token()
        glued = _glued_decoy_jwt(token, decoys)
        calls = {"n": 0}

        def counted(header: str, _real=real_alg) -> bool:
            calls["n"] += 1
            return _real(header)

        monkeypatch.setattr(scan, "_jwt_header_has_alg", counted)
        if scan.jwt_on_line(glued) is False:
            raise AssertionError("bound-prefixed JWT was not a jwt hit")
        if calls["n"] > scan._JWT_EYJ_PER_RUN:
            raise AssertionError("eyJ bound was not applied")
        if calls["n"] < scan._JWT_EYJ_PER_RUN:
            raise AssertionError("eyJ bound did not examine the cap")
        monkeypatch.setattr(scan, "_jwt_header_has_alg", real_alg)
        evidence = tmp_path / f"bound-{decoys}"
        evidence.mkdir()
        (evidence / "notes.txt").write_text(f"{glued}\n", encoding="utf-8")
        digest = hashlib.sha256(f"{glued}\n".encode("utf-8")).hexdigest()
        allow = _write_allowlist(
            tmp_path / f"allow-{decoys}.json",
            [{"path": "notes.txt", "sha256": digest}],
        )
        code, out, err = _run(
            [str(evidence), "--allowlist", str(allow)], capsys, (token, glued)
        )
        if code != 1:
            raise AssertionError("bound-prefixed JWT did not hit content")
        if _hit("jwt", "notes.txt", line=1) not in err:
            raise AssertionError("bound-prefixed JWT was not a content jwt hit")
        _assert_jwt_absent(out, err, token)
        _assert_no_jwt_windows(out, err, token)
        name_hits = scan.scan_name((glued,), glued)
        if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
            raise AssertionError("bound-prefixed JWT name was not a jwt hit")
        shown = scan.redact_text(f"tar: {glued}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        if glued in shown:
            raise AssertionError("bound-prefixed JWT was not fully redacted")


def _dotted_decoy_jwt(token: str, decoys: int) -> str:
    """N ``eyJx`` decoys, then ``.``, then a real token (FU-1 shape)."""
    planted = (_EYJ_DECOY * decoys) + "." + token
    if planted.count(".") != token.count(".") + 1:
        raise AssertionError("dotted decoy prefix did not add a separator")
    return planted


def test_bound_hit_dotted_decoy_does_not_leak_signature_grams(monkeypatch):
    """FU-1: 16 decoys + '.' + token redacts through every following run."""
    real_extend = scan._extend_dot_joined_runs
    calls = {"n": 0}

    def counted(text: str, end: int) -> int:
        calls["n"] += 1
        return real_extend(text, end)

    monkeypatch.setattr(scan, "_extend_dot_joined_runs", counted)
    for decoys in (16, 17):
        token = _pyjwt_access_token()
        planted = _dotted_decoy_jwt(token, decoys)
        if scan.jwt_on_line(planted) is False:
            raise AssertionError("dotted decoy prefix was not a bound jwt hit")
        match = next(scan._iter_jwts(planted), None)
        if match is None:
            raise AssertionError("dotted decoy prefix produced no jwt span")
        _begin, end, _span = match
        if end != len(planted):
            raise AssertionError("bound redaction stopped before the last dotted run")
        shown = scan.redact_text(f"tar: {planted}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_grams("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        if planted in shown:
            raise AssertionError("dotted decoy JWT was not fully redacted")
        if token.split(".")[-1][:8] and any(
            token.split(".")[-1][i : i + 8] in shown
            for i in range(max(0, len(token.split(".")[-1]) - 7))
        ):
            raise AssertionError("signature 8-gram leaked after bound hit")
    if calls["n"] < 2:
        raise AssertionError("bound hit did not extend through following runs")


def test_over_cap_header_glued_token_does_not_leak_grams(monkeypatch):
    """FU-2: over-cap header with a glued token is a bound hit and redacted."""
    real_alg = scan._jwt_header_has_alg
    alg_calls = {"n": 0}

    def counted_alg(header: str) -> bool:
        alg_calls["n"] += 1
        return real_alg(header)

    monkeypatch.setattr(scan, "_jwt_header_has_alg", counted_alg)
    token = _pyjwt_access_token()
    over = scan._JWT_HEADER_MAX + 64
    header = ("eyJ" * ((over + 2) // 3))[:over]
    planted = header + token
    if len(header) <= scan._JWT_HEADER_MAX:
        raise AssertionError("over-cap header was not longer than 32 KiB")
    if scan.jwt_on_line(planted) is False:
        raise AssertionError("over-cap glued token was not a jwt hit")
    if alg_calls["n"] > scan._JWT_EYJ_PER_RUN:
        raise AssertionError("over-cap header exceeded the eyJ bound")
    match = next(scan._iter_jwts(planted), None)
    if match is None:
        raise AssertionError("over-cap glued token produced no jwt span")
    _begin, end, _span = match
    if end != len(planted):
        raise AssertionError("over-cap redaction missed the glued token")
    shown = scan.redact_text(f"tar: {planted}: Cannot open")
    _assert_jwt_absent("", shown, token)
    _assert_no_jwt_grams("", shown, token)
    _assert_no_jwt_windows("", shown, token)
    if planted in shown:
        raise AssertionError("over-cap glued JWT was not fully redacted")


def test_long_base64url_prefix_finds_glued_token_and_does_not_leak(monkeypatch):
    """R48-F1: search the last 32 KiB of a long run for a real token."""
    real_alg = scan._jwt_header_has_alg
    alg_calls = {"n": 0}

    def counted_alg(header: str) -> bool:
        alg_calls["n"] += 1
        return real_alg(header)

    monkeypatch.setattr(scan, "_jwt_header_has_alg", counted_alg)
    token = _pyjwt_access_token()
    prefix = _b64url_run(scan._JWT_HEADER_MAX)
    planted = prefix + token
    if scan.jwt_on_line(planted) is False:
        raise AssertionError("token after a 32 KiB prefix was not a jwt hit")
    if alg_calls["n"] < 1:
        raise AssertionError("last-32-KiB search did not examine the glued token")
    if alg_calls["n"] > scan._JWT_EYJ_PER_RUN:
        raise AssertionError("last-32-KiB search exceeded the eyJ bound")
    match = next(scan._iter_jwts(planted), None)
    if match is None:
        raise AssertionError("long prefix produced no jwt span")
    begin, end, span = match
    if begin != len(prefix):
        raise AssertionError("last-32-KiB search did not start at the real token")
    if end != len(planted):
        raise AssertionError("long-prefix redaction missed the glued token")
    if span != token:
        raise AssertionError("long-prefix hit was not the real token span")
    shown = scan.redact_text(f"tar: {planted}: Cannot open")
    _assert_jwt_absent("", shown, token)
    _assert_no_jwt_grams("", shown, token)
    _assert_no_jwt_windows("", shown, token)
    if token in shown:
        raise AssertionError("token after a 32 KiB prefix leaked")


def test_join_tar_newlines_collapses_crlf_and_dot_newline():
    """R48-F2 mutant: ``.\\n`` or CRLF must become one ``.``, not ``..``."""
    if scan._join_tar_newlines("a.\nb") != "a.b":
        raise AssertionError("dot-newline was not collapsed to one dot")
    if scan._join_tar_newlines("a\r\nb") != "a.b":
        raise AssertionError("CRLF was not collapsed to one dot")
    if scan._join_tar_newlines("a.\r\n.b") != "a.b":
        raise AssertionError("dot-CRLF-dot was not collapsed to one dot")
    if ".." in scan._join_tar_newlines("hdr.\npay.sig"):
        raise AssertionError("dot-newline collapse left a double dot")


def test_redact_text_crlf_and_dot_newline_jwt_does_not_leak():
    """R48-F2: CRLF or '.' + newline must not leak payload 8-grams."""
    token = _pyjwt_access_token()
    header, payload, signature = token.split(".")
    crlf = f"{header}\r\n{payload}.{signature}"
    dot_nl = f"{header}.\n{payload}.{signature}"
    for planted in (crlf, dot_nl):
        shown = scan.redact_text(f"tar: {planted}: Cannot open")
        _assert_jwt_absent("", shown, token)
        _assert_no_jwt_grams("", shown, token)
        _assert_no_jwt_windows("", shown, token)
        if payload in shown or signature in shown:
            raise AssertionError("newline-split JWT leaked after join")
        if planted in shown:
            raise AssertionError("newline-split JWT was not redacted")


def test_json_unicode_escapes_in_content_are_not_tar_unescaped(tmp_path, capsys):
    """F4: JSON \\uXXXX in file content must not become a new pool hit."""
    bait = None
    token = None
    for _ in range(400):
        candidate = _runtime_pool_token()
        for index, char in enumerate(candidate):
            if char not in "uU":
                continue
            probe = candidate[:index] + "\\" + candidate[index:]
            if scan.pool_token_on_line(probe):
                continue
            if not scan.pool_token_on_line(scan._unescape_tar(probe)):
                continue
            bait = probe
            token = candidate
            break
        if bait is not None:
            break
    if bait is None or token is None:
        raise AssertionError("could not build a JSON \\uXXXX pool bait")
    content = '{"note": "' + bait + '", "mark": "\\u0041\\u0026\\u0031"}\n'
    if scan.pool_token_on_line(content) or scan.jwt_on_line(content):
        raise AssertionError("raw JSON bait already looks like a secret")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(content, encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token,)
    )
    if code != 0:
        raise AssertionError("JSON \\uXXXX in content produced a new hit")
    if "password-pool token" in err or "jwt" in err:
        raise AssertionError("JSON \\uXXXX in content was tar-unescaped")
    if "clean" not in out:
        raise AssertionError("JSON \\uXXXX evidence did not scan clean")


def test_gzip_candidate_cap_is_unsuppressible_archive(tmp_path, capsys):
    token = _runtime_pool_token()
    under = _gzip_cap_payload(31)
    payload = _gzip_cap_payload(32)
    assert scan.archive_kind(under) is None
    assert scan.archive_kind(payload) == "gzip"
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "capped.bin").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "capped.bin", "sha256": digest}],
    )
    code, out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, (token,)
    )
    assert code == 1
    assert _hit("archive", "capped.bin") in err
    assert _hit("refuse binary", "capped.bin") not in err
    assert "clean" not in out


def test_octal_fullwidth_dot_is_utf8_under_c_locale(monkeypatch):
    """R48-F3 / F2: octal runs decode as UTF-8 even under LC_ALL=C."""
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    token = _pyjwt_access_token()
    header, payload, signature = token.split(".")
    # U+FF0E full-width dot is UTF-8 EF BC 8E = \357\274\216
    planted = header + "\\357\\274\\216" + payload + "\\357\\274\\216" + signature
    decoded = scan._unescape_tar(planted)
    if "\uff0e" not in decoded:
        raise AssertionError("octal full-width dot was not decoded as UTF-8")
    name_hits = scan.scan_name((planted,), planted)
    if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
        raise AssertionError("octal full-width-dot JWT name was not a jwt hit")
    shown = scan.redact_text(f"tar: {planted}: Cannot open")
    _assert_no_jwt_grams("", shown, token)
    _assert_jwt_absent("", shown, token)


def test_four_percent_layers_fail_closed_and_literal_056_name():
    """R48-F4 / F6: still-decoding text is an encoded-run hit; \\056 in names."""
    token = _pyjwt_access_token()
    layered = _jwt_quote_layers(token, 4)
    if not scan._still_decodes(layered, unescape=False):
        raise AssertionError("four percent layers did not fail closed")
    hits = scan.scan_text(("notes.txt",), f"{layered}\n")
    if not any(hit.kind == scan.KIND_ENCODED for hit in hits):
        raise AssertionError("four percent layers were not an encoded-run hit")
    escaped = token.replace(".", r"\056")
    name_hits = scan.scan_name((escaped,), escaped)
    if not any(hit.kind == scan.KIND_JWT for hit in name_hits):
        raise AssertionError("literal \\056 name was not a jwt hit")
    shown = scan.redact_text(f"tar: {escaped}: Cannot open")
    _assert_no_jwt_grams("", shown, token)


def test_content_backslash_056_is_jwt_not_pool(tmp_path, capsys):
    """R48-F5: content \\056 is a jwt hit; JSON \\uXXXX is still not a pool hit."""
    token = _pyjwt_access_token()
    escaped = token.replace(".", r"\056")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(f"{escaped}\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, escaped)
    )
    if code != 1:
        raise AssertionError("content \\056 JWT did not hit")
    if _hit("jwt", "notes.txt", line=1) not in err:
        raise AssertionError("content \\056 JWT was not a jwt hit")
    if "password-pool token" in err:
        raise AssertionError("content \\056 JWT was reported as a pool hit")


def test_work_order_json_unicode_content_is_not_a_pool_hit(tmp_path, capsys):
    """R48-F5 / F4: uat-work-order-p2-9c4f9da-style JSON \\uXXXX stays clean."""
    content = (
        '{"work_order": "WO-9c4f9da", "note": "path \\\\u0041\\\\u0026\\\\u0031",'
        ' "status": "asked-for"}\n'
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "work-order.json").write_text(content, encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, ()
    )
    if code != 0:
        raise AssertionError("work-order JSON \\uXXXX produced a new hit")
    if "password-pool token" in err:
        raise AssertionError("work-order JSON was tar-unescaped for pool")
    if "clean" not in out:
        raise AssertionError("work-order JSON evidence did not scan clean")


def test_redact_text_maps_spans_back_to_original_escapes():
    """R48-F6: redact_text keeps original escapes and only replaces spans."""
    token = _pyjwt_access_token()
    escaped = token.replace(".", r"\056")
    prefix = "tar: "
    suffix = ": Cannot open"
    shown = scan.redact_text(prefix + escaped + suffix)
    if r"\056" not in shown and "<redacted name hmac:" not in shown:
        raise AssertionError("redact_text did not keep original escapes or tag")
    if shown.startswith(prefix) is False:
        raise AssertionError("redact_text did not keep the original prefix")
    if shown.endswith(suffix) is False:
        raise AssertionError("redact_text did not keep the original suffix")
    _assert_no_jwt_grams("", shown, token)
    if escaped in shown:
        raise AssertionError("escaped JWT span was not replaced in the original")


def test_redact_text_reescapes_control_characters():
    """F5: raw controls are re-escaped before printing."""
    token = _pyjwt_access_token()
    raw = f"pre\x01{token}\tpost"
    shown = scan.redact_text(raw)
    if "\x01" in shown:
        raise AssertionError("raw SOH was printed")
    if "\t" in shown:
        raise AssertionError("raw tab was printed")
    if "\\001" not in shown and "\\t" not in shown:
        raise AssertionError("controls were not re-escaped")
    _assert_no_jwt_grams("", shown, token)


def test_decode_variants_skipped_on_plain_ascii(monkeypatch):
    """F8: no %, \\, or non-ASCII means decode layers are not called."""
    calls = {"n": 0}
    real = scan._decode_layers

    def counted(text: str, limit: int = scan._DECODE_LAYERS) -> tuple[str, ...]:
        calls["n"] += 1
        return real(text, limit)

    monkeypatch.setattr(scan, "_decode_layers", counted)
    variants = scan._text_variants("sample id 123")
    if variants != ("sample id 123",):
        raise AssertionError("plain ASCII line produced extra decode variants")
    if calls["n"] != 0:
        raise AssertionError("decode layers ran on a plain ASCII line")
    _ = scan._text_variants("sample %2E id")
    if calls["n"] < 1:
        raise AssertionError("decode layers did not run on a percent line")


def test_wrapped_base64_jwt_is_a_hit(tmp_path, capsys):
    token = _pyjwt_access_token()
    wrapped = "\n".join(token[index : index + 76] for index in range(0, len(token), 76))
    if "\n" not in wrapped:
        wrapped = token[:20] + "\n" + token[20:]
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(wrapped + "\n", encoding="utf-8")
    code, out, err = _run(
        [str(evidence), "--no-allowlist"], capsys, (token, wrapped)
    )
    if code != 1:
        raise AssertionError("wrapped JWT did not hit")
    if "jwt" not in err:
        raise AssertionError("wrapped JWT was not a jwt hit")


def test_png_text_chunk_is_unsuppressible(tmp_path, capsys):
    def _chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return len(data).to_bytes(4, "big") + name + data + crc.to_bytes(4, "big")

    ihdr = _chunk(b"IHDR", (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + bytes((8, 0, 0, 0, 0)))
    text = _chunk(b"tEXt", b"Comment\x00hidden")
    iend = _chunk(b"IEND", b"")
    payload = b"\x89PNG\r\n\x1a\n" + ihdr + text + iend
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "photo.png").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "photo.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, ()
    )
    if code != 1:
        raise AssertionError("PNG tEXt chunk was not a hit")
    if _hit("png-trailing", "photo.png") not in err:
        raise AssertionError("PNG tEXt chunk was not png-trailing")


def test_gzip_flg_reserved_and_failed_inflate_are_not_archive():
    reserved = b"\x1f\x8b\x08\xe0" + (b"\x00" * 16)
    if scan.archive_kind(b"xxxx" + reserved) is not None:
        raise AssertionError("reserved FLG gzip was treated as an archive")
    failed = b"xxxx" + b"\x1f\x8b\x08\x00" + (b"\xff" * 16)
    if scan._gzip_inflates(failed, 4):
        raise AssertionError("failed inflate was treated as success")
    if scan.archive_kind(failed) is not None:
        raise AssertionError("failed inflate after junk was an archive")


def test_read_nofollow_uses_o_nofollow():
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    source = Path(scan.__file__).read_text(encoding="utf-8")
    if "O_NOFOLLOW" not in source:
        raise AssertionError("scanner lost O_NOFOLLOW")
    if "os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK" not in source:
        raise AssertionError("scanner open flags dropped O_NOFOLLOW")
    assert flags & os.O_NOFOLLOW


def test_pool_token_excludes_iso_timestamps():
    stamp = "2026-10-20t23:19:31.123Z"
    if len(stamp) != 24:
        raise AssertionError("timestamp fixture is not 24 characters")
    if scan.pool_token_on_line(stamp):
        raise AssertionError("ISO timestamp was a pool-token hit")
    token = _runtime_pool_token()
    if not scan.pool_token_on_line(token):
        raise AssertionError("runtime pool token was not a hit")


def test_pool_token_excludes_compact_iso_timestamps():
    compact = "Aa1!20261020T231931xxxxx"
    if len(compact) != DEV_PASSWORD_LENGTH:
        raise AssertionError("compact timestamp fixture is not 24 characters")
    if scan._TIMESTAMP_RE.search("20261020T231931") is None:
        raise AssertionError("compact timestamp regex did not match")
    if scan.pool_token_on_line(compact):
        raise AssertionError("compact ISO timestamp was a pool-token hit")
    token = _runtime_pool_token()
    if not scan.pool_token_on_line(token):
        raise AssertionError("runtime pool token was not a hit")


def test_lzip_and_rar_text_are_not_archive(tmp_path, capsys):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "note-lzip.txt").write_text("LZIP is a compressor note\n", encoding="utf-8")
    (evidence / "note-rar.txt").write_bytes(b"Rar!\x1a\x07 just a mention\n")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, ())
    if "archive" in err:
        raise AssertionError("LZIP or Rar! text was an archive hit")
    if code != 0:
        raise AssertionError("LZIP/Rar! text evidence did not scan clean")


def test_missing_secrets_file_without_env_exits_2(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text("ok\n", encoding="utf-8")
    missing = tmp_path / "missing-secrets.env"
    code, _out, err = _run(
        [str(evidence), "--no-allowlist", "--secrets-file", str(missing)],
        capsys,
        (),
    )
    if code != 2:
        raise AssertionError("missing --secrets-file did not exit 2")
    if "secrets file not found" not in err:
        raise AssertionError("missing --secrets-file was not reported")


def _png_chunk(name: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(name + data) & 0xFFFFFFFF
    return len(data).to_bytes(4, "big") + name + data + crc.to_bytes(4, "big")


def _chunk_png(*chunks: bytes) -> bytes:
    ihdr = _png_chunk(
        b"IHDR",
        (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + bytes((8, 2, 0, 0, 0)),
    )
    iend = _png_chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + b"".join(chunks) + iend


def _runtime_env_secret(marker: str) -> str:
    return "seed" + uuid.uuid4().hex[:12] + marker + uuid.uuid4().hex[:12]


def _tar_escape_name(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\t", "\\t").replace("'", "\\'")


def _assert_secret_and_tail_absent(shown: str, secret: str) -> None:
    escaped = _tar_escape_name(secret)
    tail = ""
    for sep in ("\\", "\t", "'"):
        if sep in secret:
            tail = secret.split(sep, 1)[1]
            break
    if secret in shown:
        raise AssertionError("configured secret leaked")
    if escaped != secret and escaped in shown:
        raise AssertionError("tar-escaped configured secret leaked")
    if tail and tail in shown:
        raise AssertionError("configured secret tail leaked")


@pytest.mark.parametrize(
    "marker",
    ["\\", "\t", "'"],
    ids=["backslash", "tab", "quote"],
)
def test_redact_text_redacts_tar_escaped_configured_secret(marker):
    secret = _runtime_env_secret(marker)
    escaped = _tar_escape_name(secret)
    shown = scan.redact_text(f"tar: round/{escaped}: Cannot hard link", (secret,))
    _assert_secret_and_tail_absent(shown, secret)
    if "<redacted name hmac:" not in shown:
        raise AssertionError("tar-escaped configured secret was not redacted")


def test_redact_text_several_mib_is_linear_time():
    """Several MiB of ``eyJ*17.a.b `` must redact well under the CI budget.

    The quadratic rope/per-character path took 177 s at 8 MiB. This
    uses 4 MiB and the same 15 s budget as the dotted-eyJ walk so a
    return to that path fails by more than an order of magnitude.
    A trailing space keeps each unit a separate run.
    """
    unit = ("eyJ" * 17) + ".a.b "
    blob = unit * ((4 * 1024 * 1024) // len(unit))
    started = time.perf_counter()
    shown = scan.redact_text(blob)
    elapsed = time.perf_counter() - started
    if elapsed >= 15.0:
        raise AssertionError("redact_text on several MiB exceeded 15s")
    if "<redacted name hmac:" not in shown:
        raise AssertionError("several-MiB eyJ blob was not redacted")


def test_redact_text_escapes_plus_pool_is_linear_time():
    """~512 KiB of escaped pool windows must redact under 3 s."""
    token = _runtime_pool_token()
    unit = token + r"\t"
    blob = unit * ((512 * 1024) // len(unit))
    started = time.perf_counter()
    shown = scan.redact_text(blob)
    elapsed = time.perf_counter() - started
    if elapsed >= 3.0:
        raise AssertionError("escapes-plus-pool redact_text exceeded 3s")
    if "<redacted name hmac:" not in shown:
        raise AssertionError("escapes-plus-pool blob was not redacted")
    if token in shown:
        raise AssertionError("pool token leaked from escapes-plus-pool redact")


def test_plain_many_backslash_text_is_not_encoded_run(tmp_path, capsys):
    line = "notes " + ("\\" * 24) + " path only"
    if scan._still_decodes(line, unescape=True):
        raise AssertionError("plain backslash text failed closed")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "notes.txt").write_text(line + "\n", encoding="utf-8")
    code, out, err = _run([str(evidence), "--no-allowlist"], capsys, ())
    if "encoded run" in err:
        raise AssertionError("plain backslash text was an encoded-run hit")
    if code != 0:
        raise AssertionError("plain backslash evidence did not scan clean")


def test_fail_closed_layers_and_octal_dot_leave_no_8gram():
    token = _pyjwt_access_token()
    for layers in (4, 5):
        layered = _jwt_quote_layers(token, layers)
        if not scan._still_decodes(layered, unescape=False):
            raise AssertionError("layered JWT did not fail closed")
        shown = scan.redact_text(f"tar: {layered}: Cannot open")
        _assert_no_jwt_grams("", shown, token)
        if layered in shown:
            raise AssertionError("layered JWT run was not redacted whole")
    escaped = token.replace(".", r"\056")
    shown = scan.redact_text(f"tar: {escaped}: Cannot open")
    _assert_no_jwt_grams("", shown, token)
    if escaped in shown:
        raise AssertionError("octal-dot JWT was not redacted")


def test_png_srgb_phys_is_suppressible(tmp_path, capsys):
    extra = (
        _png_chunk(b"sRGB", b"\x00"),
        _png_chunk(
            b"pHYs",
            (2835).to_bytes(4, "big") + (2835).to_bytes(4, "big") + b"\x01",
        ),
        _png_chunk(b"gAMA", (45455).to_bytes(4, "big")),
        _png_chunk(b"cHRM", b"\x00" * 32),
    )
    payload = _chunk_png(*extra)
    if scan._png_disallowed_chunk(payload):
        raise AssertionError("sRGB/pHYs PNG was treated as disallowed")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "photo.png").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "photo.png", "sha256": digest}],
    )
    code, out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, ()
    )
    if code != 0:
        raise AssertionError("sRGB/pHYs PNG did not stay suppressible")
    if "png-trailing" in err:
        raise AssertionError("sRGB/pHYs PNG was png-trailing")
    if "clean" not in out:
        raise AssertionError("sRGB/pHYs PNG evidence did not scan clean")


def test_png_truncated_chunk_is_unsuppressible(tmp_path, capsys):
    payload = _chunk_png()[:-8]
    if scan._png_disallowed_chunk(payload) is not True:
        raise AssertionError("truncated PNG was not suspicious")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "photo.png").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "photo.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, ()
    )
    if code != 1:
        raise AssertionError("truncated PNG was not a hit")
    if _hit("png-trailing", "photo.png") not in err:
        raise AssertionError("truncated PNG was not png-trailing")


def test_png_length_overflow_is_unsuppressible(tmp_path, capsys):
    ihdr = _png_chunk(
        b"IHDR",
        (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + bytes((8, 2, 0, 0, 0)),
    )
    overflow = (2**24).to_bytes(4, "big") + b"IDAT" + b"\x00" * 8
    payload = b"\x89PNG\r\n\x1a\n" + ihdr + overflow
    if scan._png_disallowed_chunk(payload) is not True:
        raise AssertionError("length-overflow PNG was not suspicious")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "photo.png").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "photo.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, ()
    )
    if code != 1:
        raise AssertionError("length-overflow PNG was not a hit")
    if _hit("png-trailing", "photo.png") not in err:
        raise AssertionError("length-overflow PNG was not png-trailing")


def test_png_bad_crc_is_unsuppressible(tmp_path, capsys):
    good = _chunk_png()
    payload = bytearray(good)
    payload[8 + 4 + 4 + 13] ^= 0xFF
    payload = bytes(payload)
    if scan._png_disallowed_chunk(payload) is not True:
        raise AssertionError("bad-CRC PNG was not suspicious")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "photo.png").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": "photo.png", "sha256": digest}],
    )
    code, _out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, ()
    )
    if code != 1:
        raise AssertionError("bad-CRC PNG was not a hit")
    if _hit("png-trailing", "photo.png") not in err:
        raise AssertionError("bad-CRC PNG was not png-trailing")


def test_r38_magic_bytes_png_is_not_a_chunk_stream(tmp_path, capsys):
    if scan._png_disallowed_chunk(UTC_PNG):
        raise AssertionError("r38 magic-plus-bytes PNG was walked as chunks")
    evidence = tmp_path / "evidence"
    (evidence / "ui").mkdir(parents=True)
    (evidence / "ui" / UTC_NAME).write_bytes(UTC_PNG)
    allow = _write_allowlist(
        tmp_path / "allow.json",
        [{"path": UTC_REL, "sha256": UTC_SHA}],
    )
    code, out, err = _run(
        [str(evidence), "--allowlist", str(allow)], capsys, ()
    )
    if code != 0:
        raise AssertionError("r38 magic-plus-bytes PNG did not stay suppressible")
    if "png-trailing" in err:
        raise AssertionError("r38 PNG became png-trailing")
    if "clean" not in out:
        raise AssertionError("r38 PNG evidence did not scan clean")
