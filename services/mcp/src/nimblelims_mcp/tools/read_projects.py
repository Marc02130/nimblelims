"""Project reads. GET /projects requires a signed-in user. RLS scopes rows."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke, seg

NAMES = ("list_projects", "get_project")


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_projects(
        ctx: Context,
        status: str | None = None,
        client_id: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """List projects. Calls GET /projects.

        Requires a signed-in user. The route does not check the project:read
        string; row-level security scopes rows. Filters: status (status id),
        client_id, page (default 1), size (default 10, max 100).
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/projects",
            params={"status": status, "client_id": client_id, "page": page, "size": size},
        )

    @expose(mcp, READ)
    async def get_project(project_id: str, ctx: Context) -> Any:
        """One project. Calls GET /projects/{project_id}."""
        return await invoke(client, tokens, ctx, "GET", f"/projects/{seg(project_id)}")
