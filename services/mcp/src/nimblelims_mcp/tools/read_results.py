"""Result reads. Requires result:read. The list route keeps its trailing slash."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke, seg

NAMES = ("list_results", "get_result")


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_results(
        ctx: Context,
        test_id: str | None = None,
        analyte_id: str | None = None,
        entered_by: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """List results. Calls GET /results/ (trailing slash). Requires result:read.

        Filters: test_id, analyte_id, entered_by, page (default 1), size
        (default 10, max 100). Row-level security limits rows.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/results/",
            params={
                "test_id": test_id,
                "analyte_id": analyte_id,
                "entered_by": entered_by,
                "page": page,
                "size": size,
            },
        )

    @expose(mcp, READ)
    async def get_result(result_id: str, ctx: Context) -> Any:
        """One result. Calls GET /results/{result_id}. Requires result:read."""
        return await invoke(client, tokens, ctx, "GET", f"/results/{seg(result_id)}")
