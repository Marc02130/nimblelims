"""Environment for the MCP process. Defaults match docker-compose.yml."""

import os
from dataclasses import dataclass


_READ_ONLY_OFF = {"0", "false", "no", "off"}


def _flag(name: str, default: str) -> bool:
    raw = os.environ.get(name, default).strip().lower()
    return raw not in _READ_ONLY_OFF


@dataclass(frozen=True)
class Settings:
    backend_base_url: str = "http://backend:8000"
    read_only: bool = True
    host: str = "0.0.0.0"
    port: int = 8100
    access_token: str | None = None
    transport: str = "streamable-http"

    @classmethod
    def from_env(cls) -> "Settings":
        port_raw = os.environ.get("MCP_PORT", "8100").strip()
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise SystemExit(f"MCP_PORT must be an integer, got {port_raw!r}") from exc
        if port < 1 or port > 65535:
            raise SystemExit(f"MCP_PORT out of range: {port}")
        token = os.environ.get("NIMBLELIMS_ACCESS_TOKEN", "").strip() or None
        transport = os.environ.get("MCP_TRANSPORT", "streamable-http").strip() or "streamable-http"
        return cls(
            backend_base_url=os.environ.get("BACKEND_BASE_URL", "http://backend:8000").strip(),
            read_only=_flag("MCP_READ_ONLY", "true"),
            host=os.environ.get("MCP_HOST", "0.0.0.0").strip() or "0.0.0.0",
            port=port,
            access_token=token,
            transport=transport,
        )
