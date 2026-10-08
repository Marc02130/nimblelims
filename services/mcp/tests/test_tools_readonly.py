"""Tool registration and the paths those tools call. Backend is mocked."""

from pathlib import Path

import json

import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError

from nimblelims_mcp.config import Settings
from nimblelims_mcp.server import build_server
from nimblelims_mcp.tools import READ_TOOL_NAMES, WRITE_TOOL_NAMES

BASE = "http://backend:8000"
SRC = Path(__file__).resolve().parents[1] / "src" / "nimblelims_mcp"


class Ctx:
    def __init__(self, headers=None):
        self.headers = headers


def _server(*, read_only: bool, token: str | None = None):
    return build_server(
        Settings(
            backend_base_url=BASE,
            read_only=read_only,
            access_token=token,
        )
    )


def _names(server) -> set[str]:
    return {tool.name for tool in server._tool_manager.list_tools()}


async def _call(server, name: str, arguments: dict | None = None, headers=None):
    tool = server._tool_manager.get_tool(name)
    assert tool is not None, name
    return await tool.run(arguments or {}, Ctx(headers), convert_result=False)


def test_read_only_server_has_no_write_tools():
    assert READ_TOOL_NAMES.isdisjoint(WRITE_TOOL_NAMES)
    names = _names(_server(read_only=True))
    assert names == set(READ_TOOL_NAMES)
    assert names.isdisjoint(WRITE_TOOL_NAMES)
    for name in names:
        assert "delete" not in name
        assert "drop" not in name


def test_write_mode_adds_write_tools_and_still_has_no_delete_name():
    names = _names(_server(read_only=False))
    assert names == set(READ_TOOL_NAMES | WRITE_TOOL_NAMES)
    for tool in _server(read_only=False)._tool_manager.list_tools():
        assert "Calls DELETE" not in (tool.description or "")
        lowered = tool.name.lower()
        assert "delete" not in lowered
        assert "drop" not in lowered


def test_read_and_write_annotations():
    server = _server(read_only=False)
    samples = server._tool_manager.get_tool("list_samples")
    update = server._tool_manager.get_tool("update_sample")
    login = server._tool_manager.get_tool("login")
    assert samples.annotations.read_only_hint is True
    assert samples.annotations.destructive_hint is False
    assert update.annotations.read_only_hint is False
    assert update.annotations.destructive_hint is True
    assert login.annotations.read_only_hint is False
    assert login.annotations.destructive_hint is False
    assert "ctx" not in samples.parameters.get("properties", {})


def test_package_does_not_import_the_backend_or_a_database():
    text = "\n".join(path.read_text() for path in SRC.rglob("*.py")).lower()
    assert "sqlalchemy" not in text
    assert "psycopg" not in text
    assert "backend.app" not in text
    assert "import models" not in text
    for path in (SRC / "tools").rglob("*.py"):
        source = path.read_text()
        assert '"DELETE"' not in source
        assert "'DELETE'" not in source


def test_settings_fail_closed(monkeypatch):
    monkeypatch.delenv("MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("NIMBLELIMS_ACCESS_TOKEN", raising=False)
    assert Settings.from_env().read_only is True
    assert Settings.from_env().access_token is None
    monkeypatch.setenv("MCP_READ_ONLY", "yes")
    assert Settings.from_env().read_only is True
    monkeypatch.setenv("MCP_READ_ONLY", "false")
    assert Settings.from_env().read_only is False
    monkeypatch.setenv("MCP_READ_ONLY", "off")
    assert Settings.from_env().read_only is False
    monkeypatch.setenv("NIMBLELIMS_ACCESS_TOKEN", "   ")
    assert Settings.from_env().access_token is None
    monkeypatch.setenv("MCP_PORT", "nope")
    with pytest.raises(SystemExit):
        Settings.from_env()


@respx.mock
async def test_list_samples_and_results_paths():
    samples = respx.get(f"{BASE}/samples").mock(return_value=httpx.Response(200, json={"items": []}))
    results = respx.get(f"{BASE}/results/").mock(return_value=httpx.Response(200, json={"items": []}))
    server = _server(read_only=True, token="env-token")
    await _call(server, "list_samples", {"project_id": "p1", "page": 2})
    await _call(server, "list_results", {})
    sample_query = samples.calls[0].request.url.params
    assert sample_query["project_id"] == "p1"
    assert sample_query["page"] == "2"
    assert sample_query["size"] == "10"
    assert "status" not in sample_query
    assert results.calls[0].request.url.path == "/results/"
    assert samples.calls[0].request.headers["authorization"] == "Bearer env-token"


@respx.mock
async def test_login_stores_token_and_does_not_return_it():
    respx.post(f"{BASE}/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "session-token",
                "token_type": "bearer",
                "username": "lab-tech",
                "role": "Lab Technician",
                "permissions": ["sample:read"],
                "must_change_password": False,
            },
        )
    )
    me = respx.get(f"{BASE}/auth/me").mock(
        return_value=httpx.Response(200, json={"username": "lab-tech"})
    )
    server = _server(read_only=True)
    logged_in = await _call(
        server,
        "login",
        {"username": "lab-tech", "password": "s3cret-pass"},
        headers={},
    )
    assert logged_in["token_stored"] is True
    assert "access_token" not in logged_in
    assert "s3cret-pass" not in str(logged_in)
    await _call(server, "whoami", {}, headers={})
    assert me.calls[0].request.headers["authorization"] == "Bearer session-token"


@respx.mock
async def test_request_authorization_overrides_the_stored_token():
    respx.post(f"{BASE}/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "stored-token",
                "username": "admin",
                "role": "Admin",
                "permissions": [],
            },
        )
    )
    me = respx.get(f"{BASE}/auth/me").mock(return_value=httpx.Response(200, json={"username": "other"}))
    server = _server(read_only=True)
    await _call(server, "login", {"username": "admin", "password": "x"}, headers={})
    await _call(
        server,
        "whoami",
        {},
        headers={"Authorization": "Bearer caller-token"},
    )
    assert me.calls[0].request.headers["authorization"] == "Bearer caller-token"


@respx.mock
async def test_missing_token_does_not_call_the_backend():
    route = respx.get(f"{BASE}/auth/me").mock(return_value=httpx.Response(200, json={}))
    server = _server(read_only=True)
    with pytest.raises(ToolError, match="token missing/expired; call login or refresh"):
        await _call(server, "whoami", {}, headers={})
    assert not route.called


@respx.mock
async def test_get_sample_encodes_the_path_segment():
    route = respx.get(url__regex=r".*/samples/a%2Fb$").mock(
        return_value=httpx.Response(200, json={"id": "a/b"})
    )
    server = _server(read_only=True, token="t")
    body = await _call(server, "get_sample", {"sample_id": "a/b"})
    assert body["id"] == "a/b"
    assert route.called


@respx.mock
async def test_update_sample_is_patch_and_empty_body_is_rejected():
    route = respx.patch(f"{BASE}/samples/s1").mock(return_value=httpx.Response(200, json={"id": "s1"}))
    deleted = respx.delete(f"{BASE}/samples/s1").mock(return_value=httpx.Response(204))
    server = _server(read_only=False, token="t")
    with pytest.raises(ToolError, match="no fields to update"):
        await _call(server, "update_sample", {"sample_id": "s1"})
    assert not route.called
    await _call(server, "update_sample", {"sample_id": "s1", "name": "Vial A"})
    assert route.calls[0].request.method == "PATCH"
    assert json.loads(route.calls[0].request.content) == {"name": "Vial A"}
    assert not deleted.called


@respx.mock
async def test_content_amount_zero_is_sent():
    route = respx.patch(f"{BASE}/containers/c1/contents/s1").mock(
        return_value=httpx.Response(200, json={"amount": 0})
    )
    server = _server(read_only=False, token="t")
    await _call(
        server,
        "update_container_contents",
        {"container_id": "c1", "sample_id": "s1", "amount": 0},
    )
    assert json.loads(route.calls[0].request.content) == {"amount": 0}


@respx.mock
async def test_process_health_route():
    app = _server(read_only=True).streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mcp") as http:
        response = await http.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
