"""httpx client for the NimbleLIMS API. Never opens Postgres."""

import logging
from typing import Any
from urllib.parse import urlsplit

import httpx

from nimblelims_mcp import __version__
from nimblelims_mcp.errors import BackendError

logger = logging.getLogger(__name__)

_ALLOWED_METHODS = frozenset({"GET", "POST", "PATCH"})


class BackendClient:
    def __init__(self, base_url: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self.user_agent = f"nimblelims-mcp/{__version__}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        verb = method.upper()
        if verb not in _ALLOWED_METHODS:
            raise BackendError(
                "MCP refuses this HTTP method. DELETE is not available. "
                "Use a status flag or set a container content amount to 0."
            )
        self._refuse_schema_drop(path)
        headers = {
            "Accept": "application/json",
            "X-Client": "mcp",
            "User-Agent": self.user_agent,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = self.base_url + path
        # Method and path only. Never log the token, the password, or the query.
        logger.info("backend %s %s", verb, path)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as http:
                response = await http.request(
                    verb,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise BackendError(f"backend unreachable: {exc.__class__.__name__}") from None
        return self._decode(path, response)

    @staticmethod
    def _refuse_schema_drop(path: str) -> None:
        raw = urlsplit(path).path
        parts = [part for part in raw.split("/") if part]
        if len(parts) >= 2 and parts[0] == "v1" and parts[1] == "schema" and "drop" in parts:
            raise BackendError("MCP refuses schema drop.")

    @staticmethod
    def _decode(path: str, response: httpx.Response) -> Any:
        if response.status_code == 401:
            if path.split("?", 1)[0].rstrip("/") == "/auth/login":
                raise BackendError("login failed")
            raise BackendError("token missing/expired; call login or refresh")
        if response.status_code >= 400:
            detail = response.text[:500]
            raise BackendError(f"backend {response.status_code}: {detail}")
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return {"text": response.text[:4000]}
        return response.json()
