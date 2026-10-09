"""Auth and health tools. Always registered."""

from typing import Any

from mcp.server.mcpserver import Context

from mcp.types import ToolAnnotations

from nimblelims_mcp.tools.common import READ, expose, invoke

NAMES = ("health_check", "whoami", "login", "logout")

# Login stores a token. Logout revokes the JWT. Neither changes lab data.
_SESSION = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def health_check() -> Any:
        """Backend liveness. Calls GET /health. No token."""
        return await invoke(client, tokens, None, "GET", "/health", anonymous=True)

    @expose(mcp, READ)
    async def whoami(ctx: Context) -> Any:
        """Who this token is. Calls GET /auth/me. Returns id, username, role, and permissions."""
        return await invoke(client, tokens, ctx, "GET", "/auth/me")

    @expose(mcp, _SESSION)
    async def login(username: str, password: str, ctx: Context) -> Any:
        """Sign in as a NimbleLIMS user. Calls POST /auth/login with username and password.

        Stores the access token in memory for this MCP session only. The token
        is not returned. On a shared HTTP server without a session id, that
        memory slot is process-wide: prefer an Authorization: Bearer header
        on the MCP request, or NIMBLELIMS_ACCESS_TOKEN, when more than one
        person uses the process. Token lifetime is JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        (default 30). There is no long-lived API key.
        """
        body = await invoke(
            client,
            tokens,
            ctx,
            "POST",
            "/auth/login",
            json_body={"username": username, "password": password},
            anonymous=True,
        )
        if not isinstance(body, dict) or not body.get("access_token"):
            from mcp.server.mcpserver.exceptions import ToolError

            raise ToolError("login response had no access_token")
        tokens.store(ctx, body["access_token"])
        return {
            "username": body.get("username"),
            "role": body.get("role"),
            "permissions": body.get("permissions"),
            "must_change_password": body.get("must_change_password"),
            "token_stored": True,
        }

    @expose(mcp, _SESSION)
    async def logout(ctx: Context) -> Any:
        """Revoke this JWT. Calls POST /auth/logout (jti denylist) and drops the stored token.

        This does not delete lab data.
        """
        result = await invoke(client, tokens, ctx, "POST", "/auth/logout")
        tokens.clear(ctx)
        return result or {"message": "Logged out"}
