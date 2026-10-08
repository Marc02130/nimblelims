"""Schema catalog and config-schema reads. No drop routes."""

from typing import Any

from mcp.server.mcpserver import Context

from nimblelims_mcp.tools.common import READ, expose, invoke

NAMES = (
    "list_schema_tables",
    "list_schema_columns",
    "list_schema_layouts",
    "list_schema_privileges",
    "list_schema_relations",
    "get_schema_runtime",
    "get_config_schema_catalog",
)


def register(mcp, client, tokens) -> None:
    @expose(mcp, READ)
    async def list_schema_tables(ctx: Context) -> Any:
        """Schema tables. Calls GET /v1/schema/tables.

        Requires schema:edit or layout:edit.
        """
        return await invoke(client, tokens, ctx, "GET", "/v1/schema/tables")

    @expose(mcp, READ)
    async def list_schema_columns(table_id: str, ctx: Context) -> Any:
        """Columns for one schema table. Calls GET /v1/schema/columns?table_id=.

        table_id is required by the route. Requires schema:edit or layout:edit.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/v1/schema/columns",
            params={"table_id": table_id},
        )

    @expose(mcp, READ)
    async def list_schema_layouts(role_id: str, screen_key: str, ctx: Context) -> Any:
        """One layout. Calls GET /v1/schema/layouts. Requires schema:edit or layout:edit.

        role_id and screen_key are required by the route.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/v1/schema/layouts",
            params={"role_id": role_id, "screen_key": screen_key},
        )

    @expose(mcp, READ)
    async def list_schema_privileges(
        ctx: Context,
        role_id: str | None = None,
        table_id: str | None = None,
    ) -> Any:
        """Schema privileges. Calls GET /v1/schema/privileges. Requires schema:edit.

        Optional filters: role_id, table_id.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/v1/schema/privileges",
            params={"role_id": role_id, "table_id": table_id},
        )

    @expose(mcp, READ)
    async def list_schema_relations(ctx: Context, table_id: str | None = None) -> Any:
        """Schema relations. Calls GET /v1/schema/relations.

        Requires schema:edit or layout:edit. Optional filter: table_id.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/v1/schema/relations",
            params={"table_id": table_id},
        )

    @expose(mcp, READ)
    async def get_schema_runtime(screen_key: str, ctx: Context) -> Any:
        """Runtime columns for a screen. Calls GET /v1/schema/runtime.

        screen_key is required. Requires a signed-in user.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/v1/schema/runtime",
            params={"screen_key": screen_key},
        )

    @expose(mcp, READ)
    async def get_config_schema_catalog(ctx: Context, name: str | None = None) -> Any:
        """Config v1 catalog, or one schema. Calls GET /admin/config/schema.

        Requires config:edit or schema:edit. Pass name to fetch one schema.
        This does not write configuration.
        """
        return await invoke(
            client,
            tokens,
            ctx,
            "GET",
            "/admin/config/schema",
            params={"name": name},
        )
