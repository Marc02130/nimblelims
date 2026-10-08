# NimbleLIMS MCP server

A separate Compose service that exposes a small, typed slice of the NimbleLIMS HTTP API to MCP clients (Claude Desktop, Cursor, and others). It does not open Postgres and it does not import the backend package. Every backend call uses the caller's own JWT.

Default mode is read-only. There is no delete tool and no schema-drop tool.

Spec: [`.docs/internal/specs/mcp-server/SPEC.md`](../../.docs/internal/specs/mcp-server/SPEC.md).

## What it talks to

| | |
|---|---|
| In Compose | `BACKEND_BASE_URL=http://backend:8000` on `lims-network` |
| On the host | Streamable HTTP at `http://localhost:8100/mcp` |
| Process health | `GET http://localhost:8100/health` returns `{"status":"ok"}` (this process only) |
| Backend health tool | `health_check` calls `GET /health` on the API (`{"status":"healthy"}`) |

The API's access token lasts `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (30 in `docker-compose.yml`). There is no long-lived API key or service account. When a call returns 401, the tool error is `token missing/expired; call login or refresh`. A failed login says `login failed` instead.

## Compose

From the repo root, with the rest of the stack:

```bash
COMPOSE_PARALLEL_LIMIT=1 docker compose up -d --build mcp
```

`mcp` waits until `backend` is healthy. Container name is `lims-mcp`. Host port `8100`.

Production overlay (`docker compose -f docker-compose.yml -f docker-compose.prod.yml`) puts this service on profile `mcp`, so a normal prod up does **not** start it. That stays off until Marc says otherwise. Enabling the profile publishes host port 8100:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile mcp up -d mcp
```

## Run on the host (stdio or HTTP)

```bash
cd services/mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
BACKEND_BASE_URL=http://localhost:8000 MCP_READ_ONLY=true nimblelims-mcp
```

`python -m nimblelims_mcp` is the same entrypoint. `--transport stdio` is for an IDE that launches the process. `--transport streamable-http` is the default.

Do not point stdio at `http://backend:8000`. That name exists only on the Compose network. Use `http://localhost:8000` when the process runs on the host.

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `BACKEND_BASE_URL` | `http://backend:8000` | NimbleLIMS API origin. No trailing path. |
| `MCP_READ_ONLY` | `true` | Write tools are registered only when this is `0`, `false`, `no`, or `off`. Anything else, including unset, stays read-only. |
| `MCP_HOST` | `0.0.0.0` | HTTP bind address. |
| `MCP_PORT` | `8100` | HTTP port. Must be an integer from 1 to 65535. |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio`. |
| `NIMBLELIMS_ACCESS_TOKEN` | empty | Optional Bearer token for local dogfood. Never commit a real token. Not set in the image or in Compose. |

## Auth

The server forwards `Authorization: Bearer <token>` and does not use the SPA cookies or the CSRF header.

Resolution order for each tool call:

1. `Authorization: Bearer` on **this** MCP request, if the client sent one.
2. Token stored by `login` for this MCP session.
3. `NIMBLELIMS_ACCESS_TOKEN`.

`login` calls `POST /auth/login` and keeps `access_token` in memory. The tool result does not include the token. `logout` calls `POST /auth/logout` (revokes the JWT) and drops the stored token. It does not delete lab data.

Streamable HTTP in mcp 2.3 does not mint a session id. Without an `mcp-session-id` header, `login` stores one process-wide token under an internal `"http"` slot. A request that brings its own `Authorization` header still wins, so that stored token is not applied to a caller who sent a different one. On stdio the slot is per process (`"stdio"`). Do not share one HTTP process among people who should have different permissions.

Claude Desktop's usual config is a URL and does not send `Authorization`. Use the `login` tool, or set `NIMBLELIMS_ACCESS_TOKEN` for a single local user. If your client has a real headers field, send `Authorization: Bearer <token>`. Do not add a headers key to a client that does not support one.

Do not turn on SDK debug logging that prints tool arguments. `login` receives a password. This server logs backend method and path only.

## Client config

Streamable HTTP:

```json
{
  "mcpServers": {
    "nimblelims": {
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

Stdio, after `pip install -e .` so `nimblelims-mcp` is on `PATH`:

```json
{
  "mcpServers": {
    "nimblelims": {
      "command": "nimblelims-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "BACKEND_BASE_URL": "http://localhost:8000",
        "MCP_READ_ONLY": "true"
      }
    }
  }
}
```

## Read-only and writes

`MCP_READ_ONLY=true` (the Compose default) registers read tools only: health, whoami, login, logout, and list/get for samples, containers, tests, results, projects, lists, the schema catalog, and `GET /admin/config/schema`.

Set `MCP_READ_ONLY=false` and recreate the container to add:

- `PATCH /samples/{id}` and `PATCH /samples/{id}/status`
- `PATCH /containers/{id}` and `PATCH /containers/{id}/contents/{sample_id}`
- `PATCH /lists/{id}` and `PATCH /lists/{name}/entries/{id}` with `{"active": false}`
- `POST /v1/schema/tables/{id}/deprecate` and `POST /v1/schema/columns/{id}/deprecate`

Setting a content `amount` to `0` is the retire path for a container row. The HTTP client rejects `DELETE` and any `/v1/schema/.../drop` path even if a tool tried to call one. No tool does.

Write tools are not a second permission system. The backend still enforces the caller's role, permissions, and row-level security.

## Tests

```bash
cd services/mcp
pip install -e ".[dev]"
pytest
```

Unit tests mock the API. They do not need Docker.

The Compose smoke test is opt-in so a normal `pytest` run stays green without a stack:

```bash
MCP_SMOKE=1 pytest tests/test_smoke.py
```

It logs in as the `lab-tech` development user from `Agents.md`, calls `whoami`, and lists samples against a real backend. Override with `MCP_SMOKE_USERNAME` and `MCP_SMOKE_PASSWORD`. Do not point this at production. The skip reason is written in `tests/test_smoke.py`.

## Security notes

- No database URL, no backend imports, no admin password in the image.
- Tokens and passwords are not logged.
- Read-only is the default. Writes are explicit and described as status changes, `active: false`, amount `0`, or schema deprecate.
- This is not the configuring agent. It does not call `/v1/configuring-agent/...`.
