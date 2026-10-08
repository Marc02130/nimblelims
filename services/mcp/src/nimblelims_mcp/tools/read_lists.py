"""List reads. GET requires a signed-in user. config:edit also sees inactive entries."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke, seg

NAMES = ("list_lists", "list_list_entries")


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_lists(ctx: Context) -> Any:
        """All active lists. Calls GET /lists. Requires a signed-in user."""
        return await invoke(client, tokens, ctx, "GET", "/lists")

    @expose(mcp, READ)
    async def list_list_entries(list_name: str, ctx: Context) -> Any:
        """Entries for one list. Calls GET /lists/{list_name}/entries.

        config:edit sees inactive entries. Other signed-in users see active entries.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            f"/lists/{seg(list_name)}/entries",
        )
