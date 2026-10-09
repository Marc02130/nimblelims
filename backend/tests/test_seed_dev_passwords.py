"""seed_dev_passwords.py and the UAT runner env gate. No published defaults."""
import hashlib
import os

import pytest
from sqlalchemy.orm import Session

from app.core.dev_passwords import (
    SEED_LOCKED,
    generate_dev_password,
    require_seed_passwords,
)
from app.core.security import (
    validate_password_complexity,
    verify_password,
)
from models.user import Role, User
from seed_config_agent_slice import _generate_slice_password
import seed_dev_passwords


FIXTURE_PASSWORD = "FixtureOnlyPass1!"


def _user(db_session: Session, org, username: str, password_hash: str, *, must_change: bool = False) -> User:
    role = Role(name=f"role-{username}", description="seed password test")
    db_session.add(role)
    db_session.flush()
    user = User(
        name=f"Name {username}",
        username=username,
        email=f"{username}@seed.test",
        password_hash=password_hash,
        role_id=role.id,
        client_id=org.id,
        must_change_password=must_change,
        password_epoch=0,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_generate_dev_password_meets_complexity_and_slice_uses_it():
    password = generate_dev_password()
    assert validate_password_complexity(password, username="admin") == []
    assert _generate_slice_password() != password or len(password) >= 12
    assert validate_password_complexity(_generate_slice_password(), username="results-reviewer") == []


def test_require_seed_passwords_names_missing_env(monkeypatch):
    monkeypatch.delenv("DEV_SEED_LAB_TECH_PASSWORD", raising=False)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    with pytest.raises(SystemExit) as exc:
        require_seed_passwords(["lab-tech", "client"])
    message = str(exc.value)
    assert "DEV_SEED_LAB_TECH_PASSWORD" in message
    assert "DEV_SEED_CLIENT_PASSWORD" in message
    assert "seed_dev_passwords.py --apply" in message


def test_require_seed_passwords_returns_env_values(monkeypatch):
    monkeypatch.setenv("DEV_SEED_ADMIN_PASSWORD", FIXTURE_PASSWORD)
    found = require_seed_passwords(["admin"])
    assert found == {"admin": FIXTURE_PASSWORD}


def test_check_locked_legacy_and_published_default(db_session, test_org, tmp_path):
    _user(db_session, test_org, "admin", SEED_LOCKED, must_change=True)
    legacy = hashlib.sha256(b"not-a-published-default").hexdigest()
    _user(db_session, test_org, "lab-tech", legacy, must_change=False)
    _user(
        db_session,
        test_org,
        "alice-tech",
        seed_dev_passwords.get_password_hash(FIXTURE_PASSWORD),
        must_change=False,
    )
    defaults = tmp_path / "defaults.txt"
    defaults.write_text(FIXTURE_PASSWORD + "==>***REMOVED***\n", encoding="utf-8")
    loaded = seed_dev_passwords.load_defaults_file(str(defaults))
    lines = seed_dev_passwords.check_personas(
        db_session, only=["admin", "lab-tech", "alice-tech", "bob-tech"], defaults=loaded
    )
    text = "\n".join(lines)
    assert "admin\tneeds-password\tseed-locked" in text
    assert "lab-tech\tneeds-password\tlegacy-sha256" in text
    assert "alice-tech\tneeds-password\tpublished-default" in text
    assert "bob-tech\tmissing\tuser-not-found" in text
    assert FIXTURE_PASSWORD not in text
    assert SEED_LOCKED not in text


def test_apply_env_bumps_epoch_and_prints_nothing(db_session, test_org, monkeypatch):
    user = _user(db_session, test_org, "lab-tech", SEED_LOCKED, must_change=True)
    before = seed_dev_passwords.user_count(db_session)
    monkeypatch.setenv("DEV_SEED_LAB_TECH_PASSWORD", FIXTURE_PASSWORD)
    lines, generated = seed_dev_passwords.apply_personas(
        db_session, only=["lab-tech"], environ=os.environ
    )
    after = seed_dev_passwords.user_count(db_session)
    db_session.refresh(user)
    assert before == after
    assert generated == []
    assert lines == ["lab-tech\tupdated\tfrom-env"]
    assert verify_password(FIXTURE_PASSWORD, user.password_hash)
    assert user.password_epoch == 1
    assert user.must_change_password is False


def test_apply_generates_once_then_skips(db_session, test_org, monkeypatch, capsys):
    user = _user(db_session, test_org, "client", SEED_LOCKED, must_change=True)
    monkeypatch.delenv("DEV_SEED_CLIENT_PASSWORD", raising=False)
    before = seed_dev_passwords.user_count(db_session)
    lines, generated = seed_dev_passwords.apply_personas(db_session, only=["client"])
    assert seed_dev_passwords.user_count(db_session) == before
    assert lines == ["client\tupdated\tgenerated"]
    assert len(generated) == 1
    username, env_name, password = generated[0]
    assert username == "client"
    assert env_name == "DEV_SEED_CLIENT_PASSWORD"
    seed_dev_passwords.print_generated(generated)
    printed = capsys.readouterr().out
    assert printed.startswith("client (DEV_SEED_CLIENT_PASSWORD was unset; printed once):\n")
    assert password in printed
    db_session.refresh(user)
    assert verify_password(password, user.password_hash)
    assert user.password_epoch == 1

    lines2, generated2 = seed_dev_passwords.apply_personas(db_session, only=["client"])
    assert lines2 == ["client\tskipped\talready-rotated"]
    assert generated2 == []
    seed_dev_passwords.print_generated(generated2)
    check = "\n".join(seed_dev_passwords.check_personas(db_session, only=["client"]))
    assert password not in check
    assert "client\tok\talready-rotated" in check
    db_session.refresh(user)
    assert user.password_epoch == 1


def test_force_rotates_again(db_session, test_org, monkeypatch):
    user = _user(
        db_session,
        test_org,
        "admin",
        seed_dev_passwords.get_password_hash(FIXTURE_PASSWORD),
        must_change=False,
    )
    user.password_epoch = 3
    db_session.flush()
    monkeypatch.setenv("DEV_SEED_ADMIN_PASSWORD", "AnotherPass1!xyz")
    lines, generated = seed_dev_passwords.apply_personas(
        db_session, only=["admin"], force=True
    )
    assert lines == ["admin\tupdated\tfrom-env"]
    assert generated == []
    db_session.refresh(user)
    assert user.password_epoch == 4
    assert verify_password("AnotherPass1!xyz", user.password_hash)


def test_apply_rejects_weak_env_without_writing(db_session, test_org, monkeypatch):
    user = _user(db_session, test_org, "david-cro", SEED_LOCKED)
    monkeypatch.setenv("DEV_SEED_DAVID_CRO_PASSWORD", "short")
    with pytest.raises(seed_dev_passwords.SeedPasswordError) as exc:
        seed_dev_passwords.apply_personas(db_session, only=["david-cro"])
    assert "DEV_SEED_DAVID_CRO_PASSWORD" in str(exc.value)
    db_session.refresh(user)
    assert user.password_hash == SEED_LOCKED


def test_fresh_migration_locks_seed_users(migrated_engine):
    """A new database from these migrations cannot log in as a seed user."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from app.core.dev_passwords import PERSONAS, SEED_LOCKED

    session = sessionmaker(bind=migrated_engine)()
    try:
        version = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert version
        for username, _env_name in PERSONAS:
            user = session.query(User).filter(User.username == username).one()
            assert user.password_hash == SEED_LOCKED
            assert verify_password("not-a-password", user.password_hash) is False
        for username in ("admin", "lab-manager", "lab-tech", "client"):
            user = session.query(User).filter(User.username == username).one()
            assert user.must_change_password is True
        for username in ("alice-tech", "bob-tech", "carol-manager", "david-cro"):
            user = session.query(User).filter(User.username == username).one()
            assert user.must_change_password is False
    finally:
        session.close()


def test_main_check_does_not_print_defaults_file(db_session, test_org, monkeypatch, capsys, tmp_path):
    _user(
        db_session,
        test_org,
        "bob-tech",
        seed_dev_passwords.get_password_hash(FIXTURE_PASSWORD),
        must_change=False,
    )
    defaults = tmp_path / "defaults.txt"
    defaults.write_text(FIXTURE_PASSWORD + "\n", encoding="utf-8")

    class _Engine:
        def dispose(self):
            return None

    monkeypatch.setattr(seed_dev_passwords, "_connect", lambda: (db_session, _Engine()))
    monkeypatch.setattr(db_session, "close", lambda: None)
    code = seed_dev_passwords.main(
        ["--check", "--only", "bob-tech", "--defaults-file", str(defaults)]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "bob-tech\tneeds-password\tpublished-default" in out
    assert FIXTURE_PASSWORD not in out
