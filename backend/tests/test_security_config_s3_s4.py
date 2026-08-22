"""P0a tests: S3 JWT secret resolution; S4 no body logging."""
import logging

import pytest


def test_resolve_secret_key_prefers_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "strong-secret-aaaaaaaa")
    monkeypatch.setenv("JWT_SECRET_KEY", "other-secret-bbbbbbbb")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)
    from app.core import config as cfg

    assert cfg.resolve_secret_key() == "strong-secret-aaaaaaaa"


def test_resolve_secret_key_falls_back_to_jwt_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "strong-secret-from-jwt-alias")
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)
    from app.core import config as cfg

    assert cfg.resolve_secret_key() == "strong-secret-from-jwt-alias"


def test_resolve_secret_key_refuses_default_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)
    monkeypatch.setenv("SECRET_KEY", "your-secret-key-change-in-production")
    from app.core import config as cfg

    with pytest.raises(RuntimeError, match="default JWT secret"):
        cfg.resolve_secret_key()


def test_resolve_secret_key_allows_default_only_with_explicit_flags(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "true")
    monkeypatch.setenv("SECRET_KEY", "your-secret-key-change-in-production")
    from app.core import config as cfg

    assert cfg.resolve_secret_key() == "your-secret-key-change-in-production"


def test_resolve_secret_key_refuses_default_in_development_without_flag(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "false")
    monkeypatch.setenv("SECRET_KEY", "your-secret-key-here")
    from app.core import config as cfg

    with pytest.raises(RuntimeError, match="default JWT secret"):
        cfg.resolve_secret_key()


@pytest.mark.asyncio
async def test_logging_middleware_does_not_log_body(caplog, monkeypatch):
    """S4: middleware must not read or log request bodies."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    from starlette.testclient import TestClient

    # Import after env already set by conftest
    from app.main import LoggingMiddleware

    async def homepage(request: Request):
        return PlainTextResponse("ok")

    app = Starlette()
    app.add_middleware(LoggingMiddleware)
    app.add_route("/auth/login", homepage, methods=["POST"])

    with caplog.at_level(logging.INFO):
        client = TestClient(app)
        r = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123-should-never-appear"},
        )
        assert r.status_code == 200

    joined = " ".join(r.message for r in caplog.records)
    assert "admin123-should-never-appear" not in joined
    assert "Body:" not in joined
    assert '{"username"' not in joined
