"""Production email password reset. Same answer whether or not the email exists."""
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import config
from app.core.security import verify_password
from app.services import password_reset as reset_service
from models.login_throttle import LoginThrottle
from models.password_reset_token import PasswordResetToken
from models.user import User

NEW_PASSWORD = "ResetPass123!x"


@pytest.fixture(autouse=True)
def _never_send_real_mail(monkeypatch):
    monkeypatch.setattr(reset_service, "deliver_reset_email", lambda *args, **kwargs: None)


@pytest.fixture
def sent_mail(monkeypatch):
    sent = []

    def _send(to_address, link, ttl_minutes):
        sent.append({"to": to_address, "link": link, "ttl": ttl_minutes})

    monkeypatch.setattr(reset_service, "deliver_reset_email", _send)
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example")
    monkeypatch.setattr(config, "SMTP_FROM", "lims@example.com")
    monkeypatch.setattr(config, "PUBLIC_APP_URL", "https://lims.example")
    monkeypatch.setattr(config, "PASSWORD_RESET_TTL_MINUTES", 60)
    monkeypatch.setattr(config, "PASSWORD_RESET_MAX_PER_HOUR", 3)
    return sent


def _token_from_link(link: str) -> str:
    fragment = link.split("#", 1)[1]
    return unquote(fragment.split("token=", 1)[1])


def _request(client: TestClient, email: str):
    return client.post("/auth/password-reset", json={"email": email})


def test_production_without_public_url_is_not_configured(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example")
    monkeypatch.setattr(config, "SMTP_FROM", "lims@example.com")
    monkeypatch.setattr(config, "PUBLIC_APP_URL", "")
    assert reset_service.email_reset_configured() is False


def test_email_body_has_the_link_and_not_a_password():
    body = reset_service.reset_email_body("https://lims.example/reset-password#token=abc", 60)
    assert "https://lims.example/reset-password#token=abc" in body
    assert "choose a new password" in body
    assert "Your password stays the same" in body
    assert "ResetPass" not in body


def test_unavailable_is_the_same_for_known_and_unknown(client, test_user, monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "")
    monkeypatch.setattr(config, "SMTP_FROM", "")
    monkeypatch.setattr(config, "PUBLIC_APP_URL", "")
    known = _request(client, "test@example.com")
    unknown = _request(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 503
    assert known.json() == unknown.json()
    assert known.json()["detail"] == reset_service.NOT_CONFIGURED_MESSAGE
    assert client.post("/auth/password-reset", json={"email": "test@example.com"}).status_code != 404


def test_known_and_unknown_addresses_get_the_same_body(client, test_user, sent_mail):
    known = _request(client, "test@example.com")
    unknown = _request(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert known.json()["message"] == reset_service.generic_message()
    assert len(sent_mail) == 1
    assert sent_mail[0]["to"] == "test@example.com"
    assert "/reset-password#token=" in sent_mail[0]["link"]
    assert "?" not in sent_mail[0]["link"].split("/reset-password", 1)[1]


def test_stores_a_hash_and_clears_must_change_lockout_and_old_sessions(
    client: TestClient, db_session: Session, test_user: User, sent_mail
):
    test_user.must_change_password = True
    test_user.email = "Tech@Example.com"
    db_session.commit()

    login = client.post("/auth/login", json={"username": "testuser", "password": "testpassword"})
    assert login.status_code == 200
    old_token = login.json()["access_token"]

    db_session.add(
        LoginThrottle(
            username_normalized="testuser",
            failure_count=5,
            window_started_at=datetime.now(timezone.utc),
            locked_until=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    db_session.commit()

    requested = _request(client, "tech@example.com")
    assert requested.status_code == 200
    assert sent_mail[0]["to"] == "Tech@Example.com"
    raw = _token_from_link(sent_mail[0]["link"])
    row = db_session.query(PasswordResetToken).one()
    assert row.token_hash == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert raw not in row.token_hash
    assert len(row.token_hash) == 64

    weak = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw, "new_password": "short"},
    )
    assert weak.status_code == 400
    assert weak.json()["detail"]["code"] == "password_complexity"
    db_session.refresh(row)
    assert row.used_at is None

    same = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw, "new_password": "testpassword"},
    )
    assert same.status_code == 400
    assert any("current" in item.lower() for item in same.json()["detail"]["errors"])

    ok = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw, "new_password": NEW_PASSWORD},
    )
    assert ok.status_code == 200
    assert ok.json()["message"] == reset_service.CONFIRM_MESSAGE
    assert "access_token" not in ok.json()

    db_session.refresh(test_user)
    db_session.refresh(row)
    assert verify_password(NEW_PASSWORD, test_user.password_hash)
    assert test_user.must_change_password is False
    assert test_user.password_epoch == 1
    assert row.used_at is not None
    assert db_session.query(LoginThrottle).filter_by(username_normalized="testuser").first() is None

    stale = client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert stale.status_code == 401

    again = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw, "new_password": "AnotherPass123!x"},
    )
    assert again.status_code == 400
    assert again.json()["detail"] == reset_service.INVALID_LINK_MESSAGE

    old_login = client.post(
        "/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/auth/login", json={"username": "testuser", "password": NEW_PASSWORD}
    )
    assert new_login.status_code == 200
    assert new_login.json()["must_change_password"] is False


def test_inactive_user_is_not_emailed(client, db_session, test_user, sent_mail):
    test_user.active = False
    db_session.commit()
    response = _request(client, "test@example.com")
    assert response.status_code == 200
    assert response.json()["message"] == reset_service.generic_message()
    assert sent_mail == []


def test_new_link_replaces_the_previous_one(client, test_user, sent_mail):
    assert _request(client, "test@example.com").status_code == 200
    assert _request(client, "test@example.com").status_code == 200
    first = _token_from_link(sent_mail[0]["link"])
    second = _token_from_link(sent_mail[1]["link"])
    stale = client.post(
        "/auth/password-reset/confirm",
        json={"token": first, "new_password": NEW_PASSWORD},
    )
    assert stale.status_code == 400
    ok = client.post(
        "/auth/password-reset/confirm",
        json={"token": second, "new_password": NEW_PASSWORD},
    )
    assert ok.status_code == 200


def test_expired_and_unknown_tokens_are_rejected(client, db_session, test_user, sent_mail):
    assert _request(client, "test@example.com").status_code == 200
    raw = _token_from_link(sent_mail[0]["link"])
    row = db_session.query(PasswordResetToken).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    expired = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw, "new_password": NEW_PASSWORD},
    )
    missing = client.post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": NEW_PASSWORD},
    )
    assert expired.status_code == missing.status_code == 400
    assert expired.json() == missing.json()
    assert expired.json()["detail"] == reset_service.INVALID_LINK_MESSAGE


def test_hourly_cap_stops_further_mail_but_keeps_the_same_response(client, test_user, sent_mail):
    for _ in range(3):
        assert _request(client, "test@example.com").status_code == 200
    fourth = _request(client, "nobody-else@example.com")
    capped = _request(client, "test@example.com")
    assert capped.status_code == 200
    assert capped.json() == fourth.json()
    assert len(sent_mail) == 3


def test_send_failure_still_answers_the_same_and_drops_the_token(
    client, db_session, test_user, monkeypatch
):
    def _boom(*args, **kwargs):
        raise OSError("mailbox unavailable")

    monkeypatch.setattr(reset_service, "deliver_reset_email", _boom)
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.example")
    monkeypatch.setattr(config, "SMTP_FROM", "lims@example.com")
    monkeypatch.setattr(config, "PUBLIC_APP_URL", "https://lims.example")
    failed = _request(client, "test@example.com")
    unknown = _request(client, "nobody@example.com")
    assert failed.status_code == unknown.status_code == 200
    assert failed.json() == unknown.json()
    assert db_session.query(PasswordResetToken).count() == 0


def test_change_password_invalidates_the_previous_token(client, db_session, test_user):
    login = client.post("/auth/login", json={"username": "testuser", "password": "testpassword"})
    old = login.json()["access_token"]
    changed = client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {old}"},
        json={"current_password": "testpassword", "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401
    fresh = changed.json()["access_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {fresh}"}).status_code == 200
    db_session.refresh(test_user)
    assert test_user.password_epoch == 1
