"""Test reads. GET /tests requires a signed-in user. RLS scopes rows."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke, seg

NAMES = ("list_tests", "get_test")


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_tests(
        ctx: Context,
        sample_id: str | None = None,
        analysis_id: str | None = None,
        status: str | None = None,
        technician_id: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """List tests. Calls GET /tests.

        Requires a signed-in user. Filters: sample_id, analysis_id, status
        (status id), technician_id, page (default 1), size (default 10, max 100).
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/tests",
            params={
                "sample_id": sample_id,
                "analysis_id": analysis_id,
                "status": status,
                "technician_id": technician_id,
                "page": page,
                "size": size,
            },
        )

    @expose(mcp, READ)
    async def get_test(test_id: str, ctx: Context) -> Any:
        """One test. Calls GET /tests/{test_id}."""
        return await invoke(client, tokens, ctx, "GET", f"/tests/{seg(test_id)}")
