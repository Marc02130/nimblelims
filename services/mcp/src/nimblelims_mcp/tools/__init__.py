"""Curated tool registration. Write tools stay off unless MCP_READ_ONLY is false."""

from nimblelims_mcp.tools import (
    read_auth,
    read_containers,
    read_lists,
    read_projects,
    read_results,
    read_samples,
    read_schema,
    read_tests,
    write_containers,
    write_lists,
    write_samples,
    write_schema,
)

_READ_MODULES = (
    read_auth,
    read_samples,
    read_containers,
    read_tests,
    read_results,
    read_projects,
    read_lists,
    read_schema,
)
_WRITE_MODULES = (
    write_samples,
    write_containers,
    write_lists,
    write_schema,
)

READ_TOOL_NAMES = frozenset(name for module in _READ_MODULES for name in module.NAMES)
WRITE_TOOL_NAMES = frozenset(name for module in _WRITE_MODULES for name in module.NAMES)


def register_read(mcp, client, tokens) -> None:
    for module in _READ_MODULES:
        module.register(mcp, client, tokens)


def register_write(mcp, client, tokens) -> None:
    for module in _WRITE_MODULES:
        module.register(mcp, client, tokens)
