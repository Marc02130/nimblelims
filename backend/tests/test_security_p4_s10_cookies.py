"""
P4 / S10: httpOnly cookie AuthN + double-submit CSRF.
"""
from fastapi.testclient import TestClient

from app.core.config import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME


def _login(client: TestClient, username: str = "testuser", password: str = "testpassword"):
    return client.post("/auth/login", json={"username": username, "password": password})


def _set_cookie_headers(response) -> list[str]:
    if hasattr(response.headers, "getlist"):
        values = response.headers.getlist("set-cookie")
        if values:
            return values
    raw = response.headers.get("set-cookie")
    if not raw:
        return []
    # Single header or comma-joined — keep simple split on cookie name boundaries
    return [raw]


class TestCookieAuthN:
    def test_login_sets_httponly_access_and_csrf_cookies(self, client: TestClient, test_user):
        r = _login(client)
        assert r.status_code == 200
        assert "access_token" in r.json()  # scripts / UAT still get Bearer material

        assert AUTH_COOKIE_NAME in r.cookies
        assert CSRF_COOKIE_NAME in r.cookies

        set_cookies = _set_cookie_headers(r)
        joined = "\n".join(set_cookies).lower()
        assert f"{AUTH_COOKIE_NAME.lower()}=" in joined
        assert f"{CSRF_COOKIE_NAME.lower()}=" in joined
        # Access cookie must be HttpOnly
        access_line = next(
            (line for line in set_cookies if line.lower().startswith(f"{AUTH_COOKIE_NAME.lower()}=")),
            joined,
        )
        assert "httponly" in access_line.lower()
        csrf_line = next(
            (line for line in set_cookies if line.lower().startswith(f"{CSRF_COOKIE_NAME.lower()}=")),
            "",
        )
        if csrf_line:
            csrf_flags = [p.strip().lower() for p in csrf_line.split(";")]
            assert "httponly" not in csrf_flags

    def test_me_works_with_cookie_only(self, client: TestClient, test_user):
        assert _login(client).status_code == 200
        r = client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_me_works_with_bearer(self, client: TestClient, test_user):
        login = _login(client)
        token = login.json()["access_token"]
        client.cookies.clear()
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "testuser"

    def test_cookie_mutation_without_csrf_rejected(self, client: TestClient, test_user):
        assert _login(client).status_code == 200
        r = client.post("/auth/logout")
        assert r.status_code == 403
        detail = r.json()["detail"]
        assert detail.get("code") == "csrf_failed"

    def test_cookie_mutation_with_csrf_ok(self, client: TestClient, test_user):
        login = _login(client)
        csrf = login.cookies.get(CSRF_COOKIE_NAME)
        assert csrf
        r = client.post("/auth/logout", headers={CSRF_HEADER_NAME: csrf})
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out"

        client.cookies.clear()
        me = client.get("/auth/me")
        assert me.status_code == 401

    def test_bearer_mutation_skips_csrf(self, client: TestClient, test_user):
        login = _login(client)
        token = login.json()["access_token"]
        client.cookies.clear()
        # Authenticated mutating call with Bearer only — no CSRF header
        r = client.post(
            "/auth/change-password",
            json={
                "current_password": "testpassword",
                "new_password": "BearerSkipCsrf1!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    def test_unauthenticated_me_is_401(self, client: TestClient, test_user):
        client.cookies.clear()
        r = client.get("/auth/me")
        assert r.status_code == 401
