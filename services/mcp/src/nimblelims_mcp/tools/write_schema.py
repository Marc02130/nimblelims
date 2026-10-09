"""Schema deprecate only. Registered only when writes are on. Drop is refused."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import WRITE, expose, invoke, seg

NAMES = ("deprecate_schema_table", "deprecate_schema_column")


def register(mcp, client, tokens) -> None:
    @expose(mcp, WRITE)
    async def deprecate_schema_table(table_id: str, ctx: Context) -> Any:
        """Deprecate a schema table. Calls POST /v1/schema/tables/{table_id}/deprecate.

        Requires schema:edit. This is not a drop. POST .../drop is refused
        by the HTTP client and is not a tool.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "POST",
            f"/v1/schema/tables/{seg(table_id)}/deprecate",
        )

    @expose(mcp, WRITE)
    async def deprecate_schema_column(column_id: str, ctx: Context) -> Any:
        """Deprecate a schema column. Calls POST /v1/schema/columns/{column_id}/deprecate.

        Requires schema:edit. This is not a drop.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "POST",
            f"/v1/schema/columns/{seg(column_id)}/deprecate",
        )
