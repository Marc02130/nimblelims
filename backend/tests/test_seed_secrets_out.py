"""Generated seed passwords stay off stdout and stderr."""
from __future__ import annotations

import json
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

from app.core.dev_passwords import DEV_PASSWORD_LENGTH, DEV_PASSWORD_POOL
from app.core.secret_output import MASK_TOKEN, SecretOutputError, mask_printed_once
import seed_dev_passwords

REPO = Path(__file__).resolve().parents[2]
MASK_CLI = REPO / "scripts" / "mask_printed_once.py"
ENV_NAME = "DEV_SEED_ADMIN_PASSWORD"


def _password(symbol: str) -> str:
    body = f"Aa1{symbol}"
    password = body + ("b" * (DEV_PASSWORD_LENGTH - len(body)))
    assert len(password) == DEV_PASSWORD_LENGTH
    assert symbol in password
    return password


def _forms(password: str) -> list[str]:
    encoded = quote(password, safe="")
    return [
        password,
        f"{ENV_NAME}={password}",
        f"postgresql://lims_app:{password}@db:5432/lims_db",
        f"postgresql://lims_app:{encoded}@db:5432/lims_db",
        json.dumps({"password": password}),
        json.dumps({ENV_NAME: password}),
    ]


def _assert_absent(text: str, password: str) -> None:
    for form in _forms(password):
        assert form not in text


def _value_from_secrets_file(text: str, env_name: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"{env_name}="):
            parsed = shlex.split(line[len(env_name) + 1 :])
            assert len(parsed) == 1
            return parsed[0]
    raise AssertionError(f"{env_name} missing from secrets file")


def _quoted_assignment(env_name: str, password: str) -> str:
    return f"{env_name}={shlex.quote(password)}"


@pytest.mark.parametrize("symbol", list(DEV_PASSWORD_POOL))
def test_secrets_out_streams_hide_every_pool_symbol(symbol, tmp_path, capsys):
    password = _password(symbol)
    dest = tmp_path / "secrets.env"
    seed_dev_passwords.report_generated(
        [("admin", ENV_NAME, password)],
        str(dest),
    )
    captured = capsys.readouterr()
    _assert_absent(captured.out, password)
    _assert_absent(captured.err, password)
    assert f"Generated passwords written to {dest}" in captured.out
    stored = dest.read_text(encoding="utf-8")
    assert _quoted_assignment(ENV_NAME, password) in stored
    assert _value_from_secrets_file(stored, ENV_NAME) == password
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600


@pytest.mark.parametrize("symbol", list(DEV_PASSWORD_POOL))
def test_mask_replaces_the_whole_line_for_every_pool_symbol(symbol, capsys):
    password = _password(symbol)
    header = f"admin ({ENV_NAME} was unset; printed once):"
    for form in _forms(password):
        masked = mask_printed_once(f"{header}\nnote {form} tail\n")
        captured = capsys.readouterr()
        _assert_absent(masked, password)
        _assert_absent(captured.out, password)
        _assert_absent(captured.err, password)
        assert "note " not in masked
        assert " tail" not in masked
        assert MASK_TOKEN in masked


def test_secrets_file_is_0600_under_a_permissive_umask(tmp_path):
    dest = tmp_path / "secrets.env"
    password = _password("!")
    previous = os.umask(0)
    try:
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, password)]
        )
    finally:
        os.umask(previous)
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    stored = dest.read_text(encoding="utf-8")
    assert _quoted_assignment(ENV_NAME, password) in stored


def test_secrets_file_refuses_an_existing_path(tmp_path):
    dest = tmp_path / "secrets.env"
    dest.write_text("keep\n", encoding="utf-8")
    with pytest.raises(seed_dev_passwords.SeedPasswordError, match="Refusing to overwrite"):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, _password("#"))]
        )
    assert dest.read_text(encoding="utf-8") == "keep\n"


def test_secrets_file_round_trips_special_chars_through_bash(tmp_path):
    generated = [
        ("admin", "DEV_SEED_ADMIN_PASSWORD", "amp&and$dollar"),
        ("lab-tech", "DEV_SEED_LAB_TECH_PASSWORD", "has spaces and 'single' and \"double\""),
        ("client", "DEV_SEED_CLIENT_PASSWORD", "all of & $ ' \"  together"),
    ]
    dest = tmp_path / "secrets.env"
    seed_dev_passwords.write_secrets_file(dest, generated)
    stored = dest.read_text(encoding="utf-8")
    expected = {env_name: password for _username, env_name, password in generated}
    for env_name, password in expected.items():
        assert _quoted_assignment(env_name, password) in stored
        assert _value_from_secrets_file(stored, env_name) == password

    names = " ".join(shlex.quote(name) for name in expected)
    script = (
        "set -euo pipefail\n"
        "set -a\n"
        f". {shlex.quote(str(dest))}\n"
        "set +a\n"
        "python3 -c "
        "'import json, os, sys; "
        "print(json.dumps({name: os.environ[name] for name in sys.argv[1:]}))' "
        f"{names}\n"
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    loaded = json.loads(proc.stdout)
    assert loaded == expected


def test_main_secrets_out_does_not_print_the_password(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    from models.user import Role, User

    role = Role(name="role-client-secrets", description="seed secrets")
    db_session.add(role)
    db_session.flush()
    user = User(
        name="Client",
        username="client",
        email="client-secrets@seed.test",
        password_hash="!seed-locked",
        role_id=role.id,
        client_id=test_org.id,
        must_change_password=True,
        password_epoch=0,
    )
    db_session.add(user)
    db_session.flush()

    class _Engine:
        def dispose(self) -> None:
            return None

    monkeypatch.setattr(seed_dev_passwords, "_connect", lambda: (db_session, _Engine()))
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "uat.env"
    code = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    stored = dest.read_text(encoding="utf-8")
    password = _value_from_secrets_file(stored, "DEV_SEED_CLIENT_PASSWORD")
    assert _quoted_assignment("DEV_SEED_CLIENT_PASSWORD", password) in stored
    _assert_absent(captured.out, password)
    _assert_absent(captured.err, password)
    assert "Generated passwords written to" in captured.out
    code_again = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--force", "--secrets-out", str(dest)]
    )
    again = capsys.readouterr()
    assert code_again != 0
    assert "Refusing to overwrite" in again.err
    _assert_absent(again.out, password)
    _assert_absent(again.err, password)
    assert dest.read_text(encoding="utf-8") == stored


def test_missing_header_aborts(capsys):
    with pytest.raises(SecretOutputError, match="printed-once header is missing"):
        mask_printed_once("no secret header here\n")
    assert "printed-once header is missing" in capsys.readouterr().err


def test_header_without_a_following_line_aborts(capsys):
    with pytest.raises(SecretOutputError, match="no following line"):
        mask_printed_once("admin (DEV_SEED_ADMIN_PASSWORD was unset; printed once):")
    assert "no following line" in capsys.readouterr().err


def test_missing_mask_token_aborts(monkeypatch, capsys):
    monkeypatch.setattr("app.core.secret_output.MASK_TOKEN", "")
    with pytest.raises(SecretOutputError, match="mask token is missing"):
        mask_printed_once(
            "admin (DEV_SEED_ADMIN_PASSWORD was unset; printed once):\nsecret-line\n"
        )
    assert "mask token is missing" in capsys.readouterr().err


def test_secrets_out_without_apply_exits_2():
    assert seed_dev_passwords.main(["--check", "--secrets-out", "/tmp/nope.env"]) == 2


def test_mask_cli_aborts_when_the_header_is_missing():
    proc = subprocess.run(
        [sys.executable, str(MASK_CLI)],
        input="nothing to mask\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "printed-once header is missing" in proc.stderr
