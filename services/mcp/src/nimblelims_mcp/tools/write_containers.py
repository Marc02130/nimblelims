"""Container writes. Registered only when MCP_READ_ONLY is false. No DELETE."""

from typing import Any

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from nimblelims_mcp.tools.common import WRITE, expose, invoke, omit_none, seg

NAMES = ("update_container", "update_container_contents")


def register(mcp, client, tokens) -> None:
    @expose(mcp, WRITE)
    async def update_container(
        container_id: str,
        ctx: Context,
        name: str | None = None,
        description: str | None = None,
        row: int | None = None,
        column: int | None = None,
        concentration: float | None = None,
        concentration_units: str | None = None,
        amount: float | None = None,
        amount_units: str | None = None,
        type_id: str | None = None,
        parent_container_id: str | None = None,
    ) -> Any:
        """Patch a container. Calls PATCH /containers/{container_id}. Requires sample:update.

        Sends only fields you set. This does not remove the container.
        To retire a sample inside the container, use update_container_contents
        and set amount to 0. That is the retire path. There is no delete tool.
        """
        body = omit_none(
            {
                "name": name,
                "description": description,
                "row": row,
                "column": column,
                "concentration": concentration,
                "concentration_units": concentration_units,
                "amount": amount,
                "amount_units": amount_units,
                "type_id": type_id,
                "parent_container_id": parent_container_id,
            }
        )
        if not body:
            raise ToolError("no fields to update")
        return await invoke(
            client,
            tokens,
            ctx,
            "PATCH",
            f"/containers/{seg(container_id)}",
            json_body=body,
        )

    @expose(mcp, WRITE)
    async def update_container_contents(
        container_id: str,
        sample_id: str,
        ctx: Context,
        concentration: float | None = None,
        concentration_units: str | None = None,
        amount: float | None = None,
        amount_units: str | None = None,
    ) -> Any:
        """Patch one content row. Calls PATCH /containers/{container_id}/contents/{sample_id}.

        Requires sample:update. Setting amount to 0 is how a content row is
        retired. This tool does not call DELETE /containers/{container_id}/contents/{sample_id}.
        Amount 0 is a real value and is sent. Omitted fields are left unchanged.
        """
        body = omit_none(
            {
                "concentration": concentration,
                "concentration_units": concentration_units,
                "amount": amount,
                "amount_units": amount_units,
            }
        )
        if not body:
            raise ToolError("no fields to update")
        return await invoke(
            client,
            tokens,
            ctx,
            "PATCH",
            f"/containers/{seg(container_id)}/contents/{seg(sample_id)}",
            json_body=body,
        )
