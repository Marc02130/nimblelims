"""Compose smoke against a real NimbleLIMS backend.

This file is not part of the default unit run. `pytest` from `services/mcp`
skips it unless MCP_SMOKE=1. The skip is intentional: unit tests mock the
API and must stay green when Docker is down. Do not remove the skip marker
without replacing it with another written reason.

To run it locally, export a local user's username and password in the shell.
Credentials are env-only so no password is committed. If MCP_SMOKE=1 and
either variable is missing or empty, this file skips with a written reason.
Do not point MCP_SMOKE_BACKEND at production. A failed login counts toward
lockout, so use an account you mean to use.

    MCP_SMOKE=1 MCP_SMOKE_USERNAME=lab-tech MCP_SMOKE_PASSWORD=... pytest tests/test_smoke.py

Requires backend health at MCP_SMOKE_BACKEND (default http://localhost:8000).

Optional: MCP_SMOKE_MCP_URL (default http://localhost:8100) is checked when
that process is up. A down MCP port does not fail this file; the tools are
called in-process against the backend. Start the container with
`docker compose up -d --build mcp` when you also want the host port.
"""

import os

import httpx
import pytest

from nimblelims_mcp.config import Settings
from nimblelims_mcp.server import build_server
from nimblelims_mcp.tools import WRITE_TOOL_NAMES

pytestmark = pytest.mark.skipif(
    os.environ.get("MCP_SMOKE") != "1",
    reason=(
        "Compose smoke is opt-in. Set MCP_SMOKE=1 with the NimbleLIMS stack "
        "up (backend /health) to run login, whoami, and list_samples. "
        "Default unit runs do not start Docker. See the module docstring."
    ),
)


class Ctx:
    def __init__(self, headers=None):
        self.headers = headers


def _backend() -> str:
    return os.environ.get("MCP_SMOKE_BACKEND", "http://localhost:8000").rstrip("/")


def _credentials() -> tuple[str, str]:
    username = os.environ.get("MCP_SMOKE_USERNAME", "").strip()
    password = os.environ.get("MCP_SMOKE_PASSWORD", "").strip()
    if not username or not password:
        pytest.skip(
            "MCP_SMOKE=1 but MCP_SMOKE_USERNAME / MCP_SMOKE_PASSWORD are not set. "
            "Credentials are env-only so no password is committed. "
            "Export a local dev user's username and password "
            "(see services/mcp/README.md) and re-run."
        )
    return username, password


async def _call(server, name: str, arguments: dict):
    tool = server._tool_manager.get_tool(name)
    assert tool is not None, name
    return await tool.run(arguments, Ctx({}), convert_result=False)


async def test_login_whoami_and_list_samples():
    username, password = _credentials()
    backend = _backend()
    try:
        health = httpx.get(f"{backend}/health", timeout=5.0)
    except httpx.HTTPError as exc:
        pytest.fail(
            f"MCP_SMOKE=1 but {backend}/health is not reachable ({exc.__class__.__name__}). "
            "Start the stack, or unset MCP_SMOKE."
        )
    assert health.status_code == 200, health.text

    server = build_server(
        Settings(backend_base_url=backend, read_only=True, access_token=None)
    )
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert names.isdisjoint(WRITE_TOOL_NAMES)

    logged_in = await _call(server, "login", {"username": username, "password": password})
    assert logged_in.get("token_stored") is True
    assert "access_token" not in logged_in
    assert logged_in.get("username") == username

    me = await _call(server, "whoami", {})
    assert me.get("username") == username
    assert isinstance(me.get("permissions"), list)

    samples = await _call(server, "list_samples", {})
    assert isinstance(samples, dict)
    assert "sample:read" in me["permissions"]

    mcp_url = os.environ.get("MCP_SMOKE_MCP_URL", "http://localhost:8100").rstrip("/")
    try:
        probe = httpx.get(f"{mcp_url}/health", timeout=3.0)
    except httpx.HTTPError:
        return
    if probe.status_code == 200:
        assert probe.json().get("status") == "ok"
