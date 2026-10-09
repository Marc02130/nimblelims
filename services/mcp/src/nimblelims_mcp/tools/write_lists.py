"""Retire lists by setting active false. Registered only when writes are on. No DELETE."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import WRITE, expose, invoke, seg

NAMES = ("retire_list", "retire_list_entry")


def register(mcp, client, tokens) -> None:
    @expose(mcp, WRITE)
    async def retire_list(list_id: str, ctx: Context) -> Any:
        """Mark a list inactive. Calls PATCH /lists/{list_id} with {"active": false}.

        Requires config:edit. This is not a delete. The DELETE /lists/{list_id}
        route exists on the backend and is not exposed here.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "PATCH",
            f"/lists/{seg(list_id)}",
            json_body={"active": False},
        )

    @expose(mcp, WRITE)
    async def retire_list_entry(list_name: str, entry_id: str, ctx: Context) -> Any:
        """Mark a list entry inactive. Calls PATCH /lists/{list_name}/entries/{entry_id}.

        Body is {"active": false}. Requires config:edit. This is not a delete.
        The DELETE route for entries is not exposed.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "PATCH",
            f"/lists/{seg(list_name)}/entries/{seg(entry_id)}",
            json_body={"active": False},
        )
