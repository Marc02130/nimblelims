"""P0b: bcrypt, must_change_password gate, complexity (Q7)."""
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import (
    get_password_hash,
    verify_password,
    needs_rehash,
    validate_password_complexity,
)
from models.user import User


class TestBcryptAndLegacy:
    def test_bcrypt_roundtrip(self):
        h = get_password_hash("ComplexPass1!")
        assert h.startswith("$2")
        assert verify_password("ComplexPass1!", h)
        assert not verify_password("wrong", h)

    def test_legacy_sha256_verify_and_needs_rehash(self):
        plain = "admin123"
        legacy = hashlib.sha256(plain.encode()).hexdigest()
        assert verify_password(plain, legacy)
        assert needs_rehash(legacy)
        assert not needs_rehash(get_password_hash(plain))

    def test_login_upgrades_sha256_to_bcrypt(self, client: TestClient, db_session: Session, test_user: User):
        legacy = hashlib.sha256(b"testpassword").hexdigest()
        test_user.password_hash = legacy
        test_user.must_change_password = False
        db_session.commit()

        r = client.post("/auth/login", json={"username": "testuser", "password": "testpassword"})
        assert r.status_code == 200
        db_session.refresh(test_user)
        assert test_user.password_hash.startswith("$2")
        assert verify_password("testpassword", test_user.password_hash)


class TestComplexity:
    def test_complexity_ok(self):
        assert validate_password_complexity(
            "GoodPass123!", username="alice", current_password="old"
        ) == []

    def test_complexity_failures(self):
        errs = validate_password_complexity("short", username="alice")
        assert any("12" in e for e in errs)
        errs = validate_password_complexity("alllowercase1!", username="x")
        assert any("uppercase" in e for e in errs)
        errs = validate_password_complexity("SameAsUser12!", username="SameAsUser12!")
        assert any("username" in e.lower() for e in errs)
        errs = validate_password_complexity(
            "SamePass123!", username="bob", current_password="SamePass123!"
        )
        assert any("current" in e.lower() for e in errs)


class TestInvalidTokenSub:
    def test_invalid_uuid_sub_returns_401_not_500(self, client: TestClient, test_user):
        """Forged/malformed sub must not 500 on UUID cast."""
        from datetime import timedelta
        from app.core.security import create_access_token

        token = create_access_token(
            {
                "sub": "not-a-uuid",
                "username": "x",
                "role": "Lab Technician",
                "permissions": [],
            },
            expires_delta=timedelta(minutes=5),
        )
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, r.text


class TestMustChangePassword:
    def test_login_returns_flag(self, client: TestClient, db_session: Session, test_user: User):
        test_user.must_change_password = True
        db_session.commit()

        r = client.post("/auth/login", json={"username": "testuser", "password": "testpassword"})
        assert r.status_code == 200
        data = r.json()
        assert data["must_change_password"] is True
        token = data["access_token"]

        blocked = client.get(
            "/samples",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert blocked.status_code == 403
        detail = blocked.json()["detail"]
        assert detail["code"] == "password_change_required"

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["must_change_password"] is True

    def test_change_password_clears_flag(
        self, client: TestClient, db_session: Session, test_user: User
    ):
        test_user.must_change_password = True
        db_session.commit()

        login = client.post(
            "/auth/login", json={"username": "testuser", "password": "testpassword"}
        )
        token = login.json()["access_token"]

        bad = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "testpassword", "new_password": "weak"},
        )
        assert bad.status_code == 400
        assert bad.json()["detail"]["code"] == "password_complexity"

        ok = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "testpassword",
                "new_password": "NewComplex1!xx",
            },
        )
        assert ok.status_code == 200
        new_token = ok.json()["access_token"]
        assert ok.json()["must_change_password"] is False

        db_session.refresh(test_user)
        assert test_user.must_change_password is False

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert me.status_code == 200
        assert me.json()["must_change_password"] is False
