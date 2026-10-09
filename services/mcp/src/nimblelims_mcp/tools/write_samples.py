"""Sample writes. Registered only when MCP_READ_ONLY is false. No DELETE."""

from typing import Any

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from nimblelims_mcp.tools.common import WRITE, expose, invoke, omit_none, seg

NAMES = ("update_sample", "update_sample_status")


def register(mcp, client, tokens) -> None:
    @expose(mcp, WRITE)
    async def update_sample(
        sample_id: str,
        ctx: Context,
        name: str | None = None,
        description: str | None = None,
        due_date: str | None = None,
        received_date: str | None = None,
        report_date: str | None = None,
        date_sampled: str | None = None,
        sample_type: str | None = None,
        status: str | None = None,
        matrix: str | None = None,
        temperature: float | None = None,
        parent_sample_id: str | None = None,
        project_id: str | None = None,
        qc_type: str | None = None,
        custom_attributes: dict[str, Any] | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> Any:
        """Patch a sample. Calls PATCH /samples/{sample_id}. Requires sample:update.

        Sends only fields you set. Dates are ISO-8601 strings. This does not
        delete the sample and does not set active. To change status by id,
        use update_sample_status. Omitted fields are left unchanged. A field
        cannot be cleared to null from this tool.
        """
        body = omit_none(
            {
                "name": name,
                "description": description,
                "due_date": due_date,
                "received_date": received_date,
                "report_date": report_date,
                "date_sampled": date_sampled,
                "sample_type": sample_type,
                "status": status,
                "matrix": matrix,
                "temperature": temperature,
                "parent_sample_id": parent_sample_id,
                "project_id": project_id,
                "qc_type": qc_type,
                "custom_attributes": custom_attributes,
                "extra_fields": extra_fields,
            }
        )
        if not body:
            raise ToolError("no fields to update")
        return await invoke(
            client,
            tokens,
            ctx,
            "PATCH",
            f"/samples/{seg(sample_id)}",
            json_body=body,
        )

    @expose(mcp, WRITE)
    async def update_sample_status(sample_id: str, status_id: str, ctx: Context) -> Any:
        """Set a sample's status. Calls PATCH /samples/{sample_id}/status?status_id=.

        Requires sample:update. status_id is the list entry id the route expects
        as a query parameter. This does not delete the sample.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "PATCH",
            f"/samples/{seg(sample_id)}/status",
            params={"status_id": status_id},
        )
