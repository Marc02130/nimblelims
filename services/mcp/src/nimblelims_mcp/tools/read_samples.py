"""Sample reads. Requires sample:read. RLS still scopes rows."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke, seg

NAMES = ("list_samples", "get_sample")


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_samples(
        ctx: Context,
        project_id: str | None = None,
        status: str | None = None,
        qc_type: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """List samples. Calls GET /samples. Requires sample:read.

        Query params are the ones the route accepts: project_id, status
        (status id), qc_type, page (default 1), size (default 10, max 100).
        Row-level security limits rows to what this token can see.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/samples",
            params={
                "project_id": project_id,
                "status": status,
                "qc_type": qc_type,
                "page": page,
                "size": size,
            },
        )

    @expose(mcp, READ)
    async def get_sample(sample_id: str, ctx: Context) -> Any:
        """One sample. Calls GET /samples/{sample_id}. Requires sample:read."""
        return await invoke(client, tokens, ctx, "GET", f"/samples/{seg(sample_id)}")
