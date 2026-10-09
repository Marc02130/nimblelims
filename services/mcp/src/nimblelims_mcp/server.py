"""FastMCP app. Streamable HTTP on MCP_PORT, or stdio for a local IDE."""

from dataclasses import replace

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from nimblelims_mcp.auth import TokenStore
from nimblelims_mcp.client import BackendClient
from nimblelims_mcp.config import Settings
from nimblelims_mcp.tools import register_read, register_write


def build_server(settings: Settings) -> MCPServer:
    mcp = MCPServer("nimblelims")
    client = BackendClient(settings.backend_base_url)
    tokens = TokenStore(settings.access_token)
    register_read(mcp, client, tokens)
    if not settings.read_only:
        register_write(mcp, client, tokens)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    return mcp


def serve(settings: Settings | None = None) -> None:
    settings = settings or Settings.from_env()
    if settings.transport not in {"stdio", "streamable-http"}:
        raise SystemExit(
            "MCP_TRANSPORT must be stdio or streamable-http, "
            f"got {settings.transport!r}"
        )
    mcp = build_server(settings)
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
        return
    mcp.run(
        transport="streamable-http",
        host=settings.host,
        port=settings.port,
    )


def settings_for_cli(transport: str | None) -> Settings:
    settings = Settings.from_env()
    if transport:
        settings = replace(settings, transport=transport)
    return settings
