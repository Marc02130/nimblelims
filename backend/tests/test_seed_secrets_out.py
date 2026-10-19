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
CLIENT_ENV = "DEV_SEED_CLIENT_PASSWORD"


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


def _source_secrets_file(path: Path, names: list[str]) -> dict[str, str]:
    quoted_names = " ".join(shlex.quote(name) for name in names)
    script = (
        "set -euo pipefail\n"
        "set -a\n"
        f". {shlex.quote(str(path))}\n"
        "set +a\n"
        "python3 -c "
        "'import json, os, sys; "
        "print(json.dumps({name: os.environ[name] for name in sys.argv[1:]}))' "
        f"{quoted_names}\n"
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _leftover_temps(directory: Path, name: str) -> list[Path]:
    return list(directory.glob(f".{name}.*.tmp"))


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
    assert captured.out == f"Generated passwords written to {dest}\n"
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


def test_secrets_file_refuses_an_existing_path_without_force(tmp_path):
    dest = tmp_path / "secrets.env"
    dest.write_text("keep\n", encoding="utf-8")
    with pytest.raises(seed_dev_passwords.SeedPasswordError, match="Refusing to overwrite"):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, _password("#"))]
        )
    assert dest.read_text(encoding="utf-8") == "keep\n"


def test_secrets_file_force_overwrites_at_0600(tmp_path):
    dest = tmp_path / "secrets.env"
    dest.write_text("keep\n", encoding="utf-8")
    password = _password("*")
    previous = os.umask(0)
    try:
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, password)], force=True
        )
    finally:
        os.umask(previous)
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    stored = dest.read_text(encoding="utf-8")
    assert stored != "keep\n"
    assert _value_from_secrets_file(stored, ENV_NAME) == password
    assert _leftover_temps(tmp_path, dest.name) == []


def test_secrets_file_refuses_a_symlink(tmp_path):
    real = tmp_path / "real.env"
    real.write_text("keep\n", encoding="utf-8")
    dest = tmp_path / "secrets.env"
    dest.symlink_to(real)
    with pytest.raises(
        seed_dev_passwords.SeedPasswordError,
        match="not a regular file",
    ):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, _password("!"))], force=True
        )
    assert dest.is_symlink()
    assert real.read_text(encoding="utf-8") == "keep\n"


def test_secrets_file_refuses_a_directory(tmp_path):
    dest = tmp_path / "secrets.env"
    dest.mkdir()
    with pytest.raises(
        seed_dev_passwords.SeedPasswordError,
        match="not a regular file",
    ):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, _password("!"))], force=True
        )
    assert dest.is_dir()
    assert list(dest.iterdir()) == []


def test_secrets_file_refuses_a_fifo(tmp_path):
    dest = tmp_path / "secrets.env"
    os.mkfifo(dest)
    with pytest.raises(
        seed_dev_passwords.SeedPasswordError,
        match="not a regular file",
    ):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, _password("!"))], force=True
        )
    assert stat.S_ISFIFO(os.lstat(dest).st_mode)


def test_secrets_file_force_only_keeps_other_accounts(tmp_path):
    dest = tmp_path / "secrets.env"
    admin_password = _password("!")
    old_client = _password("#")
    new_client = _password("*")
    seed_dev_passwords.write_secrets_file(
        dest,
        [
            ("admin", ENV_NAME, admin_password),
            ("client", CLIENT_ENV, old_client),
        ],
    )
    seed_dev_passwords.write_secrets_file(
        dest,
        [("client", CLIENT_ENV, new_client)],
        force=True,
        keep_others=True,
    )
    stored = dest.read_text(encoding="utf-8")
    assert _value_from_secrets_file(stored, ENV_NAME) == admin_password
    assert _value_from_secrets_file(stored, CLIENT_ENV) == new_client
    assert old_client not in stored


def test_secrets_file_refuses_invalid_key_names(tmp_path):
    dest = tmp_path / "secrets.env"
    password = _password("!")
    with pytest.raises(seed_dev_passwords.SeedPasswordError, match="Invalid secrets-file key"):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", "dev-seed-password", password)]
        )
    assert not dest.exists()


def test_secrets_file_missing_parent_is_a_one_line_error(tmp_path):
    dest = tmp_path / "missing" / "secrets.env"
    with pytest.raises(
        seed_dev_passwords.SeedPasswordError,
        match="Secrets file parent folder does not exist",
    ):
        seed_dev_passwords.write_secrets_file(
            dest, [("admin", ENV_NAME, _password("!"))]
        )


@pytest.mark.parametrize("symbol", list(DEV_PASSWORD_POOL))
def test_secrets_file_round_trips_every_pool_symbol_through_bash(symbol, tmp_path):
    password = _password(symbol)
    dest = tmp_path / "secrets.env"
    seed_dev_passwords.write_secrets_file(dest, [("admin", ENV_NAME, password)])
    loaded = _source_secrets_file(dest, [ENV_NAME])
    assert loaded == {ENV_NAME: password}


def test_secrets_file_round_trips_special_chars_through_bash(tmp_path):
    ampersand = chr(38)
    dollar = chr(36)
    generated = [
        ("admin", "DEV_SEED_ADMIN_PASSWORD", f"amp{ampersand}and{dollar}sign"),
        ("lab-tech", "DEV_SEED_LAB_TECH_PASSWORD", "has spaces and 'single' and \"double\""),
        ("client", "DEV_SEED_CLIENT_PASSWORD", f"all of {ampersand} {dollar} ' \"  together"),
    ]
    dest = tmp_path / "secrets.env"
    seed_dev_passwords.write_secrets_file(dest, generated)
    expected = {env_name: password for _username, env_name, password in generated}
    stored = dest.read_text(encoding="utf-8")
    for env_name, password in expected.items():
        assert _quoted_assignment(env_name, password) in stored
    loaded = _source_secrets_file(dest, list(expected))
    assert loaded == expected


def _locked_client(db_session, test_org):
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
    return user


def _mock_connect(monkeypatch, db_session):
    class _Engine:
        def dispose(self) -> None:
            return None

    monkeypatch.setattr(seed_dev_passwords, "_connect", lambda: (db_session, _Engine()))
    monkeypatch.setattr(db_session, "close", lambda: None)


def test_main_secrets_out_stdout_is_exactly_the_path_line(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "uat.env"
    code = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == f"Generated passwords written to {dest}\n"
    password = _value_from_secrets_file(dest.read_text(encoding="utf-8"), "DEV_SEED_CLIENT_PASSWORD")
    _assert_absent(captured.out, password)
    _assert_absent(captured.err, password)
    assert "client\tupdated\tgenerated" in captured.err


def test_main_secrets_out_existing_path_refuses_without_force(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "uat.env"
    first = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    )
    capsys.readouterr()
    stored = dest.read_text(encoding="utf-8")
    password = _value_from_secrets_file(stored, "DEV_SEED_CLIENT_PASSWORD")
    assert first == 0
    code_again = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    )
    again = capsys.readouterr()
    assert code_again != 0
    assert "Refusing to overwrite" in again.err
    assert again.out == ""
    _assert_absent(again.out, password)
    _assert_absent(again.err, password)
    assert dest.read_text(encoding="utf-8") == stored


def test_main_secrets_out_force_overwrites_existing_file(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "uat.env"
    assert seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    ) == 0
    first = dest.read_text(encoding="utf-8")
    capsys.readouterr()
    code = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--force", "--secrets-out", str(dest)]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == f"Generated passwords written to {dest}\n"
    assert stat.S_IMODE(dest.stat().st_mode) == 0o600
    second = dest.read_text(encoding="utf-8")
    assert second != first
    password = _value_from_secrets_file(second, "DEV_SEED_CLIENT_PASSWORD")
    _assert_absent(captured.out, password)
    _assert_absent(captured.err, password)
    assert _leftover_temps(tmp_path, dest.name) == []


def test_main_secrets_out_force_only_keeps_other_accounts(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "uat.env"
    admin_password = _password("_")
    old_client = _password("-")
    seed_dev_passwords.write_secrets_file(
        dest,
        [
            ("admin", ENV_NAME, admin_password),
            ("client", CLIENT_ENV, old_client),
        ],
    )
    code = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--force", "--secrets-out", str(dest)]
    )
    captured = capsys.readouterr()
    assert code == 0
    stored = dest.read_text(encoding="utf-8")
    assert _value_from_secrets_file(stored, ENV_NAME) == admin_password
    new_client = _value_from_secrets_file(stored, CLIENT_ENV)
    assert new_client != old_client
    _assert_absent(captured.out, new_client)
    _assert_absent(captured.err, new_client)
    _assert_absent(captured.out, admin_password)
    _assert_absent(captured.err, admin_password)


def test_main_commit_failure_leaves_existing_secrets_unchanged(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "uat.env"
    assert seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    ) == 0
    stored = dest.read_text(encoding="utf-8")
    capsys.readouterr()

    def _boom() -> None:
        raise RuntimeError("commit failed")

    monkeypatch.setattr(db_session, "commit", _boom)
    with pytest.raises(RuntimeError, match="commit failed"):
        seed_dev_passwords.main(
            ["--apply", "--only", "client", "--force", "--secrets-out", str(dest)]
        )
    assert dest.read_text(encoding="utf-8") == stored
    assert _leftover_temps(tmp_path, dest.name) == []


def test_main_secrets_out_missing_parent_exits_nonzero(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    dest = tmp_path / "no-such-dir" / "uat.env"
    code = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--secrets-out", str(dest)]
    )
    captured = capsys.readouterr()
    assert code != 0
    assert captured.out == ""
    assert captured.err.startswith("ERROR: Secrets file parent folder does not exist")
    assert "Traceback" not in captured.err


def test_main_secrets_out_refuses_symlink(
    db_session, test_org, monkeypatch, capsys, tmp_path
):
    _locked_client(db_session, test_org)
    _mock_connect(monkeypatch, db_session)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    real = tmp_path / "real.env"
    real.write_text("keep\n", encoding="utf-8")
    dest = tmp_path / "uat.env"
    dest.symlink_to(real)
    code = seed_dev_passwords.main(
        ["--apply", "--only", "client", "--force", "--secrets-out", str(dest)]
    )
    captured = capsys.readouterr()
    assert code != 0
    assert "not a regular file" in captured.err
    assert dest.is_symlink()
    assert real.read_text(encoding="utf-8") == "keep\n"


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
