"""Container reads. The list routes require a signed-in user, not a named permission."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke, seg

NAMES = ("list_containers", "get_container", "list_container_types")


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_containers(
        ctx: Context,
        type_id: str | None = None,
        parent_id: str | None = None,
        project_ids: str | None = None,
    ) -> Any:
        """List containers. Calls GET /containers.

        Requires a signed-in user. Filters: type_id, parent_id, and
        project_ids (comma-separated project ids) as the route defines them.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/containers",
            params={"type_id": type_id, "parent_id": parent_id, "project_ids": project_ids},
        )

    @expose(mcp, READ)
    async def get_container(container_id: str, ctx: Context) -> Any:
        """One container and its contents. Calls GET /containers/{container_id}."""
        return await invoke(client, tokens, ctx, "GET", f"/containers/{seg(container_id)}")

    @expose(mcp, READ)
    async def list_container_types(ctx: Context) -> Any:
        """Container types. Calls GET /containers/types.

        config:edit sees inactive types too. Other signed-in users see active types.
        """
        return await invoke(client, tokens, ctx, "GET", "/containers/types")
