# Spec: MCP server

**Owner:** Wilhelmina  
**Date:** 2026-10-08  
**Status:** Working draft for branch `mcp-server-container`. No UAT pass.  
**Code:** `services/mcp/`  
**Policy reference (not imported):** [configuring-agent SPEC](../configuring-agent/SPEC.md), `backend/app/services/configuring_agent_allow.py`

The MCP server is a Compose sidecar. It calls the NimbleLIMS HTTP API with the caller's JWT. It is not the configuring agent.

---

## 1. Goal

Give an MCP client (Claude Desktop, Cursor, a local stdio process) a curated set of tools over the existing REST API. The backend still enforces permissions and row-level security. The agent cannot see or change more than the signed-in user can.

## 2. Non-goals

- Not the configuring agent. No tool calls `/v1/configuring-agent/...`. Do not reuse `configuring_agent_allow.py` as this allowlist.
- No Postgres connection. No import of `backend/` or `models`.
- No `DELETE` tool, including soft-delete routes (`DELETE /samples/{id}`, `DELETE /projects/{id}`, `DELETE /containers/{id}/contents/{sample_id}`, `DELETE /lists/...`, `DELETE /tests/{id}`, `DELETE /results/{id}`, `DELETE /v1/schema/relations/{id}`).
- No schema drop (`POST /v1/schema/tables/{id}/drop`, `POST /v1/schema/columns/{id}/drop`). The HTTP client rejects those paths even if a tool tried to call one.
- No long-lived API key or service account. That would be a backend change first.
- No n8n, webhooks, or publishing Postgres or r-calculator to the host.
- v1 does not wrap the whole OpenAPI document. Deferred routes are listed in §8.

## 3. Process

| | |
|---|---|
| Package | `services/mcp/` (`nimblelims-mcp`) |
| Compose service | `mcp`, container `lims-mcp`, network `lims-network` |
| In-compose API | `http://backend:8000` |
| Listen | Container `:8100`, host `8100:8100` |
| Transport | Streamable HTTP at `/mcp` (primary). `nimblelims-mcp --transport stdio` for a local IDE |
| Process health | `GET /health` on port 8100 returns `{"status":"ok"}`. This is not the API health payload |
| API health tool | `health_check` → `GET /health` on the backend (`{"status":"healthy"}`) |
| Default mode | `MCP_READ_ONLY=true`. Write tools register only when the value is `0`, `false`, `no`, or `off` |
| Image | `python:3.12-slim-bookworm`, non-root user `mcp`, `curl` for the Compose healthcheck |

Production (`docker compose -f docker-compose.yml -f docker-compose.prod.yml`) adds `profiles: ["mcp"]`. A normal prod up does not start this service. That stays off until Marc says otherwise. Turning the profile on publishes host port 8100. The image still has no database URL and no baked-in token.

`depends_on` is `backend` healthy. The service does not depend on `db`.

## 4. Auth

Clients send `Authorization: Bearer <access_token>`. The SPA cookies (`nimble_access`, `nimble_csrf`) and `X-CSRF-Token` are not used. Bearer already skips CSRF in `backend/app/core/security.py`.

Token resolution, first match wins:

1. `Authorization` on this MCP request.
2. Token stored by the `login` tool for this session.
3. `NIMBLELIMS_ACCESS_TOKEN` in the process environment.

`login` calls `POST /auth/login` with `{ "username", "password" }` (`LoginResponse` in `backend/app/schemas/auth.py`). It stores `access_token` in memory and returns `username`, `role`, `permissions`, `must_change_password`, and `token_stored`. It does not return the token. `logout` calls `POST /auth/logout` (revokes the JWT `jti`) and drops the stored token. Logout does not delete lab data.

mcp 2.3 Streamable HTTP does not mint a session id for current clients. Without an `mcp-session-id` request header, `login` keeps one process-wide token. A caller who sends `Authorization` still wins over that stored token. Stdio uses a separate per-process slot. Do not share one HTTP process across users who must not share a token.

On 401 from any route except login, the tool error is `token missing/expired; call login or refresh`. Login 401 is `login failed`. A missing token is the same expired-token error and does not call the backend.

Nothing in the image or Compose defaults is an admin password or a real token. Logs are method and path only. Passwords and tokens are not logged.

Token lifetime is the backend setting `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`. Compose sets it to 30. There is no refresh-token route in this tool set. The caller logs in again.

Every backend request sends `X-Client: mcp` and `User-Agent: nimblelims-mcp/0.1.0`.

## 5. Tools (v1)

Paths are the FastAPI routes mounted in `backend/app/main.py`. Permission strings are what those routes require today. Row-level security still applies on top.

### Always registered

| Tool | HTTP | Permission |
|---|---|---|
| `health_check` | `GET /health` | none |
| `whoami` | `GET /auth/me` | signed-in user |
| `login` | `POST /auth/login` | none (this call). Stores the token |
| `logout` | `POST /auth/logout` | signed-in user. Revokes the JWT only |
| `list_samples` | `GET /samples` | `sample:read`. Query: `project_id`, `status` (status id), `qc_type`, `page` (default 1), `size` (default 10, max 100) |
| `get_sample` | `GET /samples/{sample_id}` | `sample:read` |
| `list_containers` | `GET /containers` | signed-in user. Query: `type_id`, `parent_id`, `project_ids` (comma-separated) |
| `get_container` | `GET /containers/{container_id}` | signed-in user |
| `list_container_types` | `GET /containers/types` | signed-in user. `config:edit` also sees inactive types |
| `list_tests` | `GET /tests` | signed-in user. Query: `sample_id`, `analysis_id`, `status`, `technician_id`, `page`, `size` |
| `get_test` | `GET /tests/{test_id}` | signed-in user |
| `list_results` | `GET /results/` | `result:read`. The list route keeps the trailing slash. Query: `test_id`, `analyte_id`, `entered_by`, `page`, `size` |
| `get_result` | `GET /results/{result_id}` | `result:read` |
| `list_projects` | `GET /projects` | signed-in user. The route does not check `project:read`. RLS scopes rows. Query: `status`, `client_id`, `page`, `size` |
| `get_project` | `GET /projects/{project_id}` | signed-in user |
| `list_lists` | `GET /lists` | signed-in user |
| `list_list_entries` | `GET /lists/{list_name}/entries` | signed-in user. `config:edit` also sees inactive entries |
| `list_schema_tables` | `GET /v1/schema/tables` | `schema:edit` or `layout:edit` |
| `list_schema_columns` | `GET /v1/schema/columns?table_id=` | `schema:edit` or `layout:edit`. `table_id` required |
| `list_schema_layouts` | `GET /v1/schema/layouts` | `schema:edit` or `layout:edit`. `role_id` and `screen_key` required |
| `list_schema_privileges` | `GET /v1/schema/privileges` | `schema:edit`. Optional `role_id`, `table_id` |
| `list_schema_relations` | `GET /v1/schema/relations` | `schema:edit` or `layout:edit`. Optional `table_id` |
| `get_schema_runtime` | `GET /v1/schema/runtime?screen_key=` | signed-in user. `screen_key` required |
| `get_config_schema_catalog` | `GET /admin/config/schema` | `config:edit` or `schema:edit`. Optional `name` |

`custom.*` query filters that some list routes accept are not parameters on these tools.

### Only when `MCP_READ_ONLY` is false

Descriptions tell the model these are writes. None of them is a delete.

| Tool | HTTP | Permission | Note |
|---|---|---|---|
| `update_sample` | `PATCH /samples/{id}` | `sample:update` | Body is `SampleUpdate` fields that were set. Omitted fields stay. Cannot clear a field to null. Empty body is an error |
| `update_sample_status` | `PATCH /samples/{id}/status?status_id=` | `sample:update` | `status_id` is the list entry id, as a query parameter |
| `update_container` | `PATCH /containers/{id}` | `sample:update` | `ContainerUpdate` fields that were set |
| `update_container_contents` | `PATCH /containers/{id}/contents/{sample_id}` | `sample:update` | `amount` 0 is sent. That is the retire path for a content row. `ContentsUpdate` allows 0 |
| `retire_list` | `PATCH /lists/{id}` | `config:edit` | Body is exactly `{"active": false}` |
| `retire_list_entry` | `PATCH /lists/{name}/entries/{id}` | `config:edit` | Body is exactly `{"active": false}` |
| `deprecate_schema_table` | `POST /v1/schema/tables/{id}/deprecate` | `schema:edit` | Not drop |
| `deprecate_schema_column` | `POST /v1/schema/columns/{id}/deprecate` | `schema:edit` | Not drop |

Users, roles, and permission replacement are not write tools in v1. If they are added later they stay behind write mode and the description must say they are sensitive. The backend would still refuse anything the token cannot do.

## 6. Locks

Same product locks as the configuring agent, applied here without importing that allowlist:

- The caller's permissions only. The MCP process has no superuser.
- No delete and no drop. Prefer a status change, `active: false`, or a container content amount of 0.
- `configuring_agent_allow.py` still lists some drop and DELETE routes as callable for that agent (configuring-agent SPEC §10, needs-build). This server refuses those anyway.
- Confirm-before-apply is that agent's lock. Here, write tools are off unless `MCP_READ_ONLY` is explicitly false, and each write description says what it changes.

## 7. Backend follow-up

`LoggingMiddleware` in `backend/app/main.py` logs method and path only. It does not read `X-Client`.

This PR sends `X-Client: mcp` and does not change the backend audit schema. A later backend change can record that header on the access log. Do not invent an audit row for it now.

There is still no API token or service account (`POST /auth/login` and a caller-supplied Bearer token are the only options).

## 8. Deferred tools

Not in v1, even with writes on: batches, aliquots, analyses, analytes, units, clients, client-projects, experiments, lims-runs, workflows, ELN, asked-for, work-orders, dose-response, help, users, roles, permissions, sample accession (`POST /samples/accession` and bulk), `GET /samples/eligible`, test create / patch / status / review, result enter / patch, project create / patch, `POST /admin/config/validate`, `GET /v1/schema/tables/{id}/links`, schema create routes, container type writes, and the configuring agent.

## 9. Tests

Unit tests in `services/mcp/tests/` mock the API (respx). They check header forwarding, read paths, write tools absent in the default mode, `DELETE` never sent, and schema drop refused.

`tests/test_smoke.py` is skipped unless `MCP_SMOKE=1`. The reason is in that file: the default run must not need Docker. With the flag, login uses only `MCP_SMOKE_USERNAME` and `MCP_SMOKE_PASSWORD`. If either is missing or empty, the test skips with a written reason and does not fall back to a seed user. No password is stored in the repo. It then calls `whoami` and `list_samples` with that token and checks `sample:read` is in the returned permissions. It does not seed a second tenant, so it does not prove a cross-client RLS diff by itself. The backend applies RLS on `GET /samples`. Do not point the smoke test at production. A failed login counts toward lockout.

## 10. Open questions

| Item | Status |
|---|---|
| Long-lived API token / service account | Open. Not built. Needs a backend PR if Marc wants it |
| Session id on Streamable HTTP | Open. mcp 2.3 does not mint one. Documented process-wide login slot |
| Record `X-Client` in backend logs | Open. Follow-up. Header is sent now |
| Prod profile stays off | Decided for this PR. Marc turns it on |
| Users / roles as MCP tools | Deferred |
| Configuring-agent allowlist still names drop/DELETE | Known. Out of this PR. MCP refuses them independently |
