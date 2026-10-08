"""Backend client: headers, refusals, and what must never be logged."""

import logging

import httpx
import pytest
import respx

from nimblelims_mcp.client import BackendClient
from nimblelims_mcp.errors import BackendError

BASE = "http://backend:8000"


def _client() -> BackendClient:
    return BackendClient(BASE)


@respx.mock
async def test_forwards_bearer_client_and_user_agent(caplog):
    route = respx.get(f"{BASE}/auth/me").mock(
        return_value=httpx.Response(200, json={"username": "lab-tech"})
    )
    token = "sekret-token-do-not-log"
    with caplog.at_level(logging.INFO, logger="nimblelims_mcp.client"):
        body = await _client().request("GET", "/auth/me", token=token)

    assert body["username"] == "lab-tech"
    sent = route.calls[0].request
    assert sent.headers["authorization"] == f"Bearer {token}"
    assert sent.headers["x-client"] == "mcp"
    assert sent.headers["user-agent"] == "nimblelims-mcp/0.1.0"
    assert token not in caplog.text
    assert "backend GET /auth/me" in caplog.text


@respx.mock
async def test_omits_authorization_when_anonymous():
    route = respx.get(f"{BASE}/health").mock(
        return_value=httpx.Response(200, json={"status": "healthy"})
    )
    await _client().request("GET", "/health", token=None)
    assert "authorization" not in route.calls[0].request.headers


@respx.mock
async def test_401_says_token_missing():
    respx.get(f"{BASE}/samples").mock(return_value=httpx.Response(401, json={"detail": "nope"}))
    with pytest.raises(BackendError, match="token missing/expired; call login or refresh"):
        await _client().request("GET", "/samples", token="expired")


@respx.mock
async def test_login_401_is_not_the_expired_token_message():
    respx.post(f"{BASE}/auth/login").mock(return_value=httpx.Response(401, text="bad credentials"))
    with pytest.raises(BackendError, match="login failed") as exc:
        await _client().request(
            "POST",
            "/auth/login",
            token=None,
            json_body={"username": "admin", "password": "wrong-password-do-not-log"},
        )
    assert "token missing/expired" not in str(exc.value)
    assert "wrong-password" not in str(exc.value)


@respx.mock
async def test_delete_is_refused_before_the_request():
    route = respx.delete(f"{BASE}/samples/abc").mock(return_value=httpx.Response(204))
    with pytest.raises(BackendError, match="DELETE is not available"):
        await _client().request("DELETE", "/samples/abc", token="t")
    assert not route.called


@respx.mock
async def test_schema_drop_is_refused_before_the_request():
    route = respx.post(f"{BASE}/v1/schema/tables/abc/drop").mock(return_value=httpx.Response(204))
    with pytest.raises(BackendError, match="MCP refuses schema drop"):
        await _client().request("POST", "/v1/schema/tables/abc/drop", token="t")
    assert not route.called


@respx.mock
async def test_list_named_drop_is_not_a_schema_drop():
    route = respx.get(f"{BASE}/lists/drop/entries").mock(return_value=httpx.Response(200, json=[]))
    body = await _client().request("GET", "/lists/drop/entries", token="t")
    assert body == []
    assert route.called


@respx.mock
async def test_unreachable_hides_the_exception_text():
    respx.get(f"{BASE}/health").mock(
        side_effect=httpx.ConnectError("connection refused to secret-host")
    )
    with pytest.raises(BackendError, match=r"backend unreachable: ConnectError$") as exc:
        await _client().request("GET", "/health", token=None)
    assert "secret-host" not in str(exc.value)


@respx.mock
async def test_empty_body_is_none():
    respx.post(f"{BASE}/auth/logout").mock(return_value=httpx.Response(204))
    assert await _client().request("POST", "/auth/logout", token="t") is None
