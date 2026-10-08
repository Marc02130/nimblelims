"""Where the caller's NimbleLIMS JWT comes from. Tokens stay in memory."""

from typing import Any


class TokenStore:
    """Resolve a Bearer token for one tool call.

    Order: Authorization header on this MCP request, then a token `login`
    stored for this MCP session, then NIMBLELIMS_ACCESS_TOKEN.

    Streamable HTTP in mcp 2.3 does not mint a session id for current
    clients. `login` then keeps one process-wide token. A request that
    sends its own Authorization header still wins, so that stored token
    is not applied to someone who brought their own.
    """

    def __init__(self, env_token: str | None = None):
        self._env_token = env_token or None
        self._by_key: dict[str, str] = {}

    def resolve(self, ctx: Any) -> str | None:
        header = _bearer(getattr(ctx, "headers", None))
        if header:
            return header
        key = session_key(ctx)
        if key and key in self._by_key:
            return self._by_key[key]
        if key is None and "http" in self._by_key:
            return self._by_key["http"]
        return self._env_token

    def store(self, ctx: Any, token: str) -> None:
        key = session_key(ctx) or "http"
        self._by_key[key] = token

    def clear(self, ctx: Any) -> None:
        key = session_key(ctx) or "http"
        self._by_key.pop(key, None)


def session_key(ctx: Any) -> str | None:
    headers = getattr(ctx, "headers", None)
    if headers is None:
        return "stdio"
    session_id = _header(headers, "mcp-session-id")
    if session_id:
        return "sid:" + session_id
    return None


def _bearer(headers: Any) -> str | None:
    raw = _header(headers, "authorization")
    if not raw:
        return None
    scheme, _, value = raw.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return None


def _header(headers: Any, name: str) -> str | None:
    if not headers:
        return None
    getter = getattr(headers, "get", None)
    if getter is not None:
        direct = getter(name)
        if direct:
            return str(direct)
    try:
        pairs = list(headers.items())
    except Exception:
        return None
    wanted = name.lower()
    for key, value in pairs:
        if str(key).lower() == wanted and value:
            return str(value)
    return None
