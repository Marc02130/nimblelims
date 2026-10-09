# Grok Build prompt — NimbleLIMS MCP server (separate container)

Copy everything below the line into Grok Build. Do **not** invent endpoints, ports, env vars, or auth mechanisms; use only what this prompt cites from `main` (`Marc02130/nimblelims` @ tip when you start). If something is missing in the repo, treat it as an **item to add** and call it out in the PR description / docs, not as something that already exists.

---

## Assumptions (Marc may change these before coding)

| Assumption | Choice | Why |
|---|---|---|
| Package location | `services/mcp/` (not top-level `mcp/`) | Matches existing sidecar `services/r-calculator/` in compose. |
| Compose service name | `mcp` | Parallel to `backend`, `r-calculator`. Container name `lims-mcp`. |
| Network | Join existing `lims-network` from `docker-compose.yml` | Same as backend / r-calculator. |
| Backend base URL (in-compose) | `http://backend:8000` | Service name `backend`, listens on 8000 (`ports: "8000:8000"`). |
| MCP HTTP listen | Container `:8100`, host publish `"8100:8100"` | 8000 is backend; r-calculator is internal-only on its own 8000; mail UI is 8025; frontend 3000; db 5432. |
| Transport | Streamable HTTP (primary) + optional stdio entrypoint for local IDE use | Official MCP Python SDK / FastMCP. |
| Auth | Caller’s own NimbleLIMS JWT (Bearer). MCP forwards it. No shared superuser / service account. | Matches Marc lock: agent acts within the calling user’s permissions. Repo has **no** API-token or service-account mechanism today. |
| Default mode | **Read-only** (`MCP_READ_ONLY=true` by default) | Regulated LIMS; FB-11 no-delete; safer first ship. Writes only when explicitly enabled. |
| Writes when enabled | Wrap existing POST/PATCH (and status / amount→0) only. **Zero DELETE tools.** No drop tools. | Marc locks L-B / FB-11; SPEC must-not-call list. |
| DB access | **None.** HTTP client to backend only. Never import `backend/` code. Never open Postgres. | Same isolation idea as configuring-agent “existing APIs only.” |
| Docs owner | Wilhelmina | Spec under `.docs/internal/specs/mcp-server/SPEC.md`. |
| Branch | `mcp-server-container` | Suggested. |
| Coding | Local Grok Build only; no Cursor cloud agents; open a PR when ready (Marc reviews). | Marc’s rule. |

---

## Goal

Add an MCP server that exposes a **curated, typed** subset of the NimbleLIMS REST API so AI clients (Claude Desktop, Cursor, etc.) can read (and optionally write) lab data through the same auth, RBAC, and RLS path as any other API client. Ship it as its **own Docker Compose service** beside `backend`.

This is **not** the configuring agent. Do not reuse `backend/app/services/configuring_agent_allow.py` as the MCP allowlist (different product surface). Do respect the same **locks**: user permissions, no delete/drop, prefer status flag / container amount → 0.

---

## Repo facts (verified on `main` — use these)

### Compose (`docker-compose.yml`)

Services today:

- `db` → container `lims-db`, host `5432:5432`, network `lims-network`
- `mail` → Mailpit, host `8025:8025` (SMTP internal to compose on 1025)
- `r-calculator` → `services/r-calculator`, **no host ports**, reached as `http://r-calculator:8000`
- `backend` → `./backend`, container `lims-backend`, host `8000:8000`, health `http://localhost:8000/health`
- `frontend` → host `3000:3000`

Backend env (compose) already sets JWT via `SECRET_KEY` / `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30`, `DATABASE_URL` to `db:5432`, `R_CALCULATOR_URL=http://r-calculator:8000`, etc. See also root `.env.example`.

Prod overlay: `docker-compose.prod.yml` (use with `-f docker-compose.yml -f docker-compose.prod.yml`). Add the `mcp` service to the base compose; keep it off or profile-gated in prod until Marc says otherwise (call out in docs).

### Auth (no inventing)

- Login: `POST /auth/login` body `{ "username", "password" }` → `LoginResponse` with `access_token`, `token_type: "bearer"`, role, permissions (`backend/app/routers/auth.py`, `backend/app/schemas/auth.py`).
- API clients: `Authorization: Bearer <access_token>` (HTTPBearer; CSRF **skipped** for Bearer — `backend/app/core/security.py`).
- SPA also uses httpOnly cookie `nimble_access` + CSRF header `X-CSRF-Token` / cookie `nimble_csrf`. **MCP should use Bearer only**, not cookies.
- Me: `GET /auth/me`
- Logout: `POST /auth/logout` (optional tool; revoke jti)
- Permissions are role-based strings (`sample:read`, `sample:update`, `config:edit`, `schema:edit`, …) in `CORE_PERMISSIONS` (`backend/app/core/security.py`). RLS also scopes samples/projects by `app.current_user_id`.
- **Gap:** there is **no** long-lived API key / service account. MCP must obtain a user JWT (login tool or caller-supplied token). Document token lifetime (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 30).

### OpenAPI

FastAPI app in `backend/app/main.py` does **not** disable docs. OpenAPI is available at:

- `http://localhost:8000/openapi.json` (and `/docs`)

Use that (or the routers below) as the source of truth for request/response shapes. Do not invent fields.

### API surface (mounted in `backend/app/main.py`)

Curate MCP tools around these groups (read first; writes only if `MCP_READ_ONLY=false`):

| Area | Prefix(es) | Router file(s) |
|---|---|---|
| Auth | `/auth` | `backend/app/routers/auth.py` |
| Samples | `/samples` | `backend/app/routers/samples.py` — e.g. `GET /samples`, `GET /samples/{id}`, `GET /samples/eligible`, `PATCH /samples/{id}`, `PATCH /samples/{id}/status`, `POST /samples/accession` … **Do not expose** `DELETE /samples/{id}` (even though it soft-deletes). Prefer `PATCH` status / `active` via update paths that exist. |
| Containers | `/containers` | `backend/app/routers/containers.py` — `GET /containers`, `GET /containers/{id}`, `GET /containers/types`, `PATCH /containers/{id}`, `PATCH /containers/{id}/contents/{sample_id}` (amount → 0). **Do not expose** `DELETE /containers/{id}/contents/{sample_id}`. |
| Tests | `/tests` | `backend/app/routers/tests.py` — list/get/patch/status/review. **No DELETE tool.** |
| Results | `/results` | `backend/app/routers/results.py` — list/get/patch/enter. **No DELETE tool.** |
| Projects | `/projects` | `backend/app/routers/projects.py` — `GET /projects`, `GET /projects/{id}`, create/patch if writes on. **No DELETE tool** (`DELETE /projects/{id}` is soft-delete; still banned for MCP). |
| Lists | `/lists` | `backend/app/routers/lists.py` — `GET /lists`, `GET /lists/{list_name}/entries`, PATCH with `active` for retire. **No DELETE tools** (`DELETE /lists/...` exist but must not be MCP tools; use PATCH `active: false`). |
| Schema catalog | `/v1/schema/...` | `backend/app/routers/ui_schema.py` mounted under `/v1` — read: `GET /v1/schema/tables`, `columns`, `layouts`, `privileges`, `relations`, `runtime`. **Never** expose drop: `POST .../drop`, or `DELETE /v1/schema/relations/{id}`. Deprecate (`.../deprecate`) only if writes enabled and caller has `schema:edit`. |
| Config schema (read/dry-run) | `/admin/config/schema`, `/admin/config/validate` | `backend/app/routers/config_schema.py` |
| Configuring agent | `/v1/configuring-agent/...` | `backend/app/routers/configuring_agent.py` — **out of v1 MCP tools** (separate product). Mention in SPEC as non-goal. |
| Users / roles | `/users`, `/roles`, `/permissions` | Include **read** (`GET`) tools if useful; writes (role assign, permission replace) only behind write mode **and** clearly marked sensitive / second-confirm in tool descriptions. Never grant privileges from MCP beyond what the user’s token already allows (backend enforces). |
| Health | `GET /health` | `backend/app/main.py` — use for MCP↔backend smoke. |

Also registered (do not auto-expose everything): batches, aliquots, analyses, analytes, units, clients, client-projects, experiments (`/v1`), lims-runs, workflows, ELN, asked-for, work-orders, dose-response, help, admin, etc. Prefer a **small curated set** for v1; list “deferred tools” in the SPEC rather than wrapping the entire OpenAPI.

### Locks to honor (from configuring-agent SPEC + Marc)

Cite `.docs/internal/specs/configuring-agent/SPEC.md` and `backend/app/services/configuring_agent_allow.py` as **policy reference**, not as code to import:

- Confirm-before-apply is a product lock for the configuring agent; for MCP, tool descriptions must make destructive-adjacent writes explicit (set inactive, amount → 0). Prefer read-only default so confirm is less critical for v1.
- No delete / no drop. Status flag or container amount → 0 instead.
- Acts with the **caller’s** permissions only (forward Bearer token).
- Audit: confirming user / agent-assisted / run id / provider / model are configuring-agent fields. For MCP: see Audit gap below.

### Docs convention

- Working specs: `.docs/internal/specs/<feature>/SPEC.md` (see configuring-agent, containers, sample-accessioning, …).
- Map: `.docs/README.md`, `.docs/internal/README.md`.
- Do not use old `.docs-internal/` / `.docs-review/` paths.

---

## What to build

### 1. Layout

```text
services/mcp/
  Dockerfile
  pyproject.toml   # or requirements.txt — pin mcp / FastMCP + httpx
  README.md
  src/nimblelims_mcp/   # package name ok to adjust
    __init__.py
    server.py          # FastMCP app, tool registration
    client.py          # httpx AsyncClient → BACKEND_BASE_URL
    auth.py            # token resolution (env / tool login / per-session)
    tools/
      read_samples.py
      read_containers.py
      read_tests.py
      read_results.py
      read_projects.py
      read_lists.py
      read_schema.py
      write_*.py       # only registered when MCP_READ_ONLY is false
    config.py          # env: BACKEND_BASE_URL, MCP_READ_ONLY, MCP_HOST, MCP_PORT, …
  tests/
    test_client_unit.py
    test_tools_readonly.py
    …                  # mocked backend (respx / httpx mock)
docker-compose.yml     # add `mcp` service
.docs/internal/specs/mcp-server/SPEC.md
```

Mirror `r-calculator` style: own Dockerfile, compose service on `lims-network`, depends_on `backend` healthy.

### 2. Compose service sketch (adapt; keep real names)

```yaml
  mcp:
    build:
      context: ./services/mcp
      dockerfile: Dockerfile
    container_name: lims-mcp
    environment:
      BACKEND_BASE_URL: http://backend:8000
      MCP_READ_ONLY: "true"
      MCP_HOST: "0.0.0.0"
      MCP_PORT: "8100"
      # Optional default token for local dogfood only — never commit a real token
      # NIMBLELIMS_ACCESS_TOKEN:
    ports:
      - "8100:8100"
    networks:
      - lims-network
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]  # or MCP SDK health path you implement
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

Document how to point Claude Desktop / Cursor at `http://localhost:8100` (streamable HTTP) and how to run stdio locally (`python -m nimblelims_mcp` or equivalent).

### 3. Auth behavior

1. Prefer `Authorization` / token supplied by the MCP client session (document how: env `NIMBLELIMS_ACCESS_TOKEN`, or a `login` tool that calls `POST /auth/login` and keeps the token **in memory for that MCP session only**).
2. Every backend call: `Authorization: Bearer <token>`.
3. On 401, return a clear MCP tool error (“token missing/expired; call login or refresh”).
4. Never log tokens or passwords.
5. Do **not** embed admin credentials in the image or compose defaults.

### 4. Tools (v1 curated)

**Always (read-only set):**

- `health_check` → `GET /health`
- `whoami` → `GET /auth/me`
- `login` (username/password) → `POST /auth/login` (stores token for session); optional if token always provided via env
- `list_samples` / `get_sample` → `GET /samples`, `GET /samples/{sample_id}` (pass through query params that exist: `project_id`, `status`, `qc_type`, `page`, `size`)
- `list_containers` / `get_container` → `GET /containers`, `GET /containers/{container_id}`
- `list_container_types` → `GET /containers/types`
- `list_tests` / `get_test` → `GET /tests`, `GET /tests/{test_id}`
- `list_results` / `get_result` → `GET /results/`, `GET /results/{result_id}` (note trailing slash on list in router)
- `list_projects` / `get_project` → `GET /projects`, `GET /projects/{project_id}`
- `list_lists` / `list_list_entries` → `GET /lists`, `GET /lists/{list_name}/entries`
- `list_schema_tables` / `list_schema_columns` / `get_schema_runtime` → corresponding `GET /v1/schema/...`
- `get_config_schema_catalog` → `GET /admin/config/schema`

**Only when `MCP_READ_ONLY=false`:**

- Sample update / status: `PATCH /samples/{id}`, `PATCH /samples/{id}/status`
- Container update / contents amount: `PATCH /containers/{id}`, `PATCH /containers/{id}/contents/{sample_id}` (document amount → 0 as the retire path)
- List / entry retire: `PATCH /lists/{id}` or `PATCH /lists/{name}/entries/{id}` with `active: false` — **not** DELETE
- Schema deprecate (not drop): `POST /v1/schema/tables/{id}/deprecate`, `.../columns/{id}/deprecate`
- Explicitly **omit** every DELETE route and every `.../drop` route, including soft-delete DELETE endpoints.

Tool descriptions must state the required permission string when known (e.g. `sample:read`).

### 5. Audit (gap — do not invent backend behavior)

Today the backend logging middleware logs method + path only (`LoggingMiddleware` in `main.py`). There is **no** `X-Client` / MCP origin header handling.

**In this PR:**

- Have the MCP client send `X-Client: mcp` (and optionally `User-Agent: nimblelims-mcp/...`) on every backend request.
- SPEC section “Backend follow-up”: optionally record `X-Client` in access/audit logs. **Do not** change backend audit schema in this PR unless Marc expands scope.

### 6. Tests (Marc’s rule: never silently skip)

- Unit tests with mocked backend (httpx/respx): auth header forwarding, read tools map to correct paths, write tools absent when `MCP_READ_ONLY=true`, DELETE paths never called.
- One compose-level smoke: with stack up, `login` + `whoami` + `list_samples` against real `backend` (document seed user from README/AGENTS.md for local only). If Docker/smoke cannot run in the environment, **document the reason in the test file or SPEC** — do not `@pytest.mark.skip` without a written reason in-repo.

### 7. Docs

- `services/mcp/README.md` — run locally, compose, env vars, Claude/Cursor config snippets, read-only vs write mode, security notes.
- `.docs/internal/specs/mcp-server/SPEC.md` — owner **Wilhelmina**; goal, non-goals (not configuring-agent; not DB access; no delete), auth, tool table with real paths, open questions, backend follow-ups (`X-Client` audit).
- Short pointer from root `README.md` or `AGENTS.md` Architecture Overview (four → five containers) — keep minimal.

### 8. Out of scope

- Embedding configuring-agent LLM runs via MCP
- Direct SQL / Alembic / importing backend packages
- Publishing Postgres or r-calculator to the host
- n8n / webhooks (Marc: wait for requirements)
- Inventing API tokens / service accounts (unless Marc asks; then that is a **backend** PR first)

---

## Acceptance checklist

- [ ] `docker compose up -d --build` starts `lims-mcp` on `lims-network`; reaches backend at `http://backend:8000`
- [ ] MCP streamable HTTP listening on host `8100`
- [ ] Default `MCP_READ_ONLY=true`: no write/delete tools registered
- [ ] With a real user JWT, `whoami` and at least one list tool succeed; with a lab user’s token, scope matches that user’s RLS/permissions
- [ ] No tool issues DELETE or schema drop
- [ ] Unit tests green with mocks; smoke test run **or** reason documented
- [ ] SPEC + README present; branch `mcp-server-container`

---

## Items missing in repo today (add or document)

1. **No API token / service-account** — JWT login or caller-supplied Bearer only.
2. **No MCP-origin audit** — send `X-Client: mcp`; backend logging of that header is a follow-up.
3. **configuring_agent_allow.py still lists some drop/DELETE routes as callable for the agent** (SPEC §10 needs-build). MCP must still refuse those regardless of that allowlist.
4. Optional: dedicated MCP health route if the SDK does not provide one for compose healthcheck.

---

## Suggested commit / PR title

`Add MCP server container wrapping NimbleLIMS API (read-only default)`

End of prompt.
