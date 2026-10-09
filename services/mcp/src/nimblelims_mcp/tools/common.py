"""Shared tool helpers. Tool functions raise ToolError, not BackendError."""

from typing import Any
from urllib.parse import quote

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from nimblelims_mcp.errors import BackendError

READ = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)


def expose(mcp, annotations):
    def deco(fn):
        return mcp.tool(annotations=annotations, structured_output=False)(fn)

    return deco


def seg(value: str) -> str:
    return quote(str(value), safe="")


def omit_none(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


async def invoke(
    client,
    tokens,
    ctx,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    anonymous: bool = False,
) -> Any:
    token = None
    if not anonymous:
        token = tokens.resolve(ctx)
        if not token:
            raise ToolError("token missing/expired; call login or refresh")
    query = omit_none(params or {}) or None
    try:
        return await client.request(
            method,
            path,
            token=token,
            params=query,
            json_body=json_body,
        )
    except BackendError as exc:
        raise ToolError(str(exc)) from None
