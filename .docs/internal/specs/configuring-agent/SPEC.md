# Spec: Configuring agent

**PRD:** [../../prd/configuring-agent/PRD.md](../../prd/configuring-agent/PRD.md)  
**Design:** [../../design/configuring-agent.md](../../design/configuring-agent.md)  
**Date:** 2026-10-03  
**Status:** Working draft. The `configuring-agent` branch implements the contracts below plus Marc’s 2026-10-03 locks in the PRD.  
**Implement gate:** Those locks. This spec still has **no** UAT Pass.

No Accept, Confirm, or UAT Pass. Tobias’s earlier AC-1 through AC-6 are replaced. Cite only **FB-1 through FB-10** below.

Paths below are FastAPI routes as mounted in `backend/app/main.py` under `/v1/configuring-agent`. The UI calls them under `/api` because nginx strips that prefix.

Settings and runs are in `App.tsx`: `/admin/settings/configuring-agent` and `/admin/configuring-agent`. The gate is `config:edit`. Chunks and the ledger belong to a named configuration. Embeddings match ragged (local MiniLM, 384-d). Apply is one transaction: a failure rolls back every write from that apply, then records the failure. The agent uses `ui_schema_catalog.py` and no second Schema list.

---

## 1. Provider and model (Marc)

Exactly one provider: `openai`, `xai`, or `anthropic`.

An admin picks the provider and picks the model from **that provider’s** live models endpoint. Store both as `agent_provider` and `agent_model`. The LLM call uses those stored values. There is no fixed catalog in the product.

No models route exists in this repo. A later build calls the chosen provider’s models endpoint. Mathilda recommends that call be server-proxied. Browser-direct is **open**. Do not decide it here. The key must not appear in a URL, log, or toast on either path.

Changing provider clears the selected model and re-fetches models (Mathilda).

---

## 2. Key

Stored encrypted. Env fallback names, and only these, for the matching provider:

| `agent_provider` | Env fallback |
|------------------|--------------|
| `openai` | `OPENAI_API_KEY` |
| `xai` | `XAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |

No key for the chosen provider is a clear error that names that provider and that env name. No config writes. No LLM call. No fallback to another vendor.

The key is masked. After save it is not echoed. Set/update and Clear are separate from saving provider and model (Mathilda). Clear confirms: “Clear the {provider} key? Configuring agent can't call that provider until a key is set again.” Whether Clear also clears `agent_model` is **open**.

---

## 3. Existing API only

The agent configures NimbleLIMS only by calling existing APIs. No SQL. No code edits. No Alembic. No direct Postgres. No new write path.

If an existing API cannot express the change, stop (§4). Never a silent partial apply.

### 3.1 Schema — may call

Router `backend/app/routers/ui_schema.py`, prefix `/v1/schema`. Mutate requires `schema:edit` except layout, which allows `layout:edit` or `schema:edit`.

| Method | Path | What it does |
|--------|------|----------------|
| GET, POST | `/v1/schema/tables` | List shown tables. Create is real DDL via `ui_schema_create_table`. Physical name must be `x_<slug>` or `lab_<slug>`. Kind `ui`. |
| POST | `/v1/schema/tables/{table_id}/deprecate` | UI-created tables only. |
| POST | `/v1/schema/tables/{table_id}/drop` | Body includes confirm. UI-created tables only. |
| GET | `/v1/schema/tables/{table_id}/links` | Read-only. |
| GET, POST | `/v1/schema/columns` | Add column is real DDL. |
| POST | `/v1/schema/columns/{column_id}/deprecate` | |
| POST | `/v1/schema/columns/{column_id}/drop` | Body includes confirm. |
| GET, PUT | `/v1/schema/layouts` | Role layout. Query/body: `role_id`, `screen_key`, fields. |
| GET, PUT | `/v1/schema/privileges` | Role privileges. PUT body is a list. |
| GET, POST | `/v1/schema/relations` | Declare a side link. |
| DELETE | `/v1/schema/relations/{relation_id}` | |
| GET | `/v1/schema/runtime` | Read. |

Add-column types in `P1_TYPES`: `text`, `numeric`, `integer`, `boolean`, `date`, `timestamptz`, `list`. `jsonb`, `uuid`, and `other` are reflected-only. There is no reference/FK add-column type.

`_can_add_columns` refuses system tables, refuses core tables other than `samples`, and refuses `ADD_COLUMN_OUT`: `asked_for`, `tests`, `results`, `containers`, `contents`, `routing_map`, `work_orders`. The API message is “This table can't get new fields from the UI.” The agent stops. It does not work around that 422.

`POST /v1/schema/relations` cardinality is `one_to_many` or `one_to_one` only (`CARDINALITIES`). Anything else, including `many_to_many`, is 422: “Cardinality must be one-to-many or one-to-one”. The handler declares a registry row over an **existing** FK column on the child. It does not CREATE a junction and the service comment says it never mutates the database. 1:1 requires the key to be UNIQUE in Postgres.

A proposal that needs a new FK column, or an M:N junction, cannot be expressed by this API. The run stops and says so. It does not invent the junction. Many-to-many stays deferred. Product intent (Rolf) remains: junctions behind the scenes, operators link and unlink only. Intent is not an API.

`shown_in_schema` is false for `lists`, `list_entries`, and `units`. The agent does not document them as schema tables and does not add columns on them.

Caller without `schema:edit` on a schema mutate gets **403** and no write (FB-7). Today `require_permission` returns detail `Permission 'schema:edit' required`. The agent does not mint `schema:edit` and does not add a Schema-admin role.

### 3.2 Dropdown lists — may call, not Schema

`backend/app/routers/lists.py`, prefix `/lists`, mutate `config:edit`.

| Method | Path |
|--------|------|
| GET, POST | `/lists` |
| PATCH, DELETE | `/lists/{list_id}` |
| GET, POST | `/lists/{list_name}/entries` |
| PATCH, DELETE | `/lists/{list_name}/entries/{entry_id}` |

These set list rows (dropdown values). They do not add columns. They do not put `lists` or `list_entries` on Schema.

### 3.3 Other config APIs that exist and match Rolf’s write surface

Use only when the change is accession, sample processing, schema, layout, or privileges, and the route actually expresses it.

| Area | Prefix | Notes |
|------|--------|--------|
| Name templates | `/admin/name-templates` | `config:edit` to create. Sidebar link is already gone. Not a Schema table (`name_templates` is engine-internal). |
| Container types | `/containers/types` | Row catalog. `container_types` is a system Schema table; add-column on system tables is refused. |
| Sample type transitions | `/v1/sample-type-transitions` | GET/POST/PATCH/DELETE. Mutate `config:edit`. Catalog of aliquot/pool dest legality. This packet does not open dest-type mint. |
| Roles | `/roles`, `PUT /roles/{role_id}/permissions` | Create/update/delete role and replace its permissions require `user:manage` or `config:edit`. `GET /roles/{role_id}/permissions` is `get_current_user` only. |
| Users | `PATCH /users/{user_id}` | Can set `role_id` on an existing user. |
| Schema privileges | `PUT /v1/schema/privileges` | Role × table/column. `schema:edit`. |

No dedicated user × project membership route was found under `projects.py` (that router is GET/POST/PATCH/DELETE on the project itself). If personnel input asks for a project grant and no existing API expresses it, stop and say so. Do not invent `/projects/{id}/users`.

`result:enter` and `result:review` already exist as permission names. Enterer versus reviewer (US-10) uses those. No new columns.

### 3.4 Exist, and this packet does not assign them to the agent

Rolf: parsers, ELN, dose-response, a second results store, and a workflow engine are out. Asked-for and routing stay as built. Calling these to slip a change through is a workaround. Stop.

| Area | Verified prefix | Why it stays out |
|------|-----------------|------------------|
| Asked-for | `/v1/asked-for` | Stay as built. |
| Routing map | `/v1/routing-map` | Stay as built. |
| ELN process definitions | `/v1/eln-process-definitions` | ELN. Includes POST steps and POST `/{id}/instantiate`. |
| Step accepted sample types | `PUT /v1/eln-process-definitions/{id}/steps/{step_id}/accepted-sample-types` | Same ELN surface. Permission on PUT is `experiment:manage`. |
| Data parsers | `/v1/data-parsers` | Parsers. |
| Dose-response | `/v1/lims-runs` dose-response router | Lab-analysis. Fitted numbers are results, not config. |
| Results | `POST /results/`, `POST /results/batch` | Classic results stay as they are. Instrument rows are payload, not a config write. This packet does not add an importer. |
| Field definitions | `/admin/fields` | Custom fields. Do not call. |
| Custom attributes | `/admin/custom-attributes` | Do not call. UI `/admin/custom-fields` redirects to `/admin/schema/tables`. |
| Workflow templates | `/admin/workflow-templates` | No workflow engine as P1. |
| Config schema catalog | `GET /admin/config/schema`, `POST /admin/config/validate` | Read and dry-run. The module says nothing is stored. |

Receive (`POST /samples/receive`) is a lab motion, not a configuration write. Katinka: receive is identity plus first vessel; it does not mint tests. The agent does not use receive to configure the lab.

---

## 4. Stop message

When no existing API can express the change:

- Status **Stopped**.
- Banner text, exact: `Can't apply this change through configuration APIs`
- Show the blocked step and the gap in plain words.
- Write nothing for that step. No workaround. No silent drop. No continue into later steps.
- If apply already wrote earlier accepted steps in the same transaction, roll those back too. Do not leave a partial configuration. Record Stopped or Failed only after that rollback.

An HTTP error from an API the agent did call stays on that row with the API error (Mathilda). That is not a license to retry through SQL, JSONB, or `custom_attributes`.

---

## 5. Privilege

FB-7. A caller without `schema:edit` who reaches a schema mutate gets **403** and no writes.

Settings use the same `config:edit` gate. The copy for a caller who lacks it is “You can't change configuring-agent settings.”

Lab personnel input does not grant `schema:edit`. The agent does not grant it to itself.

---

## 6. Fail bars (Tobias)

For a later product tip. Provisional in the sense that this docs packet is not a UAT. Do not cite AC-1 through AC-6.

| Bar | Pass condition | Fail |
|-----|----------------|------|
| **FB-1 Provider** | Exactly one of `openai`, `xai`, `anthropic`. | A second vendor in the same run, a vendor outside those three, or provider unset. |
| **FB-2 Model source** | Live models endpoint of `agent_provider`. | A fixed catalog, or models from a different provider than `agent_provider`. |
| **FB-3 Stored choice** | Store `agent_provider` and `agent_model`. The LLM call uses those. | Either missing, or the call uses a different provider or model. |
| **FB-4 Key** | Encrypted. Env fallback only `OPENAI_API_KEY`, `XAI_API_KEY`, or `ANTHROPIC_API_KEY` for that provider. No key means a clear error naming the missing key, no config writes, no vendor fallback. | Plaintext key, fallback to another vendor, or a write before the key check. |
| **FB-5 APIs only** | Existing APIs only. | SQL, a code edit, a new write path, JSONB or `custom_attributes` as config, or a related-ids array. |
| **FB-6 Cannot express** | Stop, say so, write nothing. | Silent drop, partial apply, or a workaround. |
| **FB-7 Privilege** | Caller without `schema:edit` gets 403 and no writes. | A schema write without `schema:edit`. |
| **FB-8 Out of scope** | No chat and no lab-analysis assistant. | A chat product or a lab-analysis assistant in this packet. |
| **FB-9 Schema lists** | `lists` and `list_entries` stay off Schema. | Either table shown as a Schema table, or a column added on them. |
| **FB-10 Lab input** | Empty or missing lab input means no LLM call and a clear error. | Configure with no lab input, or invent needs the input did not state. |

Katinka’s CASCADE / silent wipe on a sample or barcode vessel is her refuse position. It is **not** an eleventh fail bar. OQ-5b stays open until Marc answers (Rolf).

---

## 7. Katinka and Anton

Respect, refuse, links, and shapes are in the PRD §8 and §9. The spec adds only the contract:

- A proposal that mints tests at receive, treats a fitted number as a config param, puts a list on Schema, or grants `schema:edit` from personnel input fails FB-5, FB-7, FB-8, or FB-9 as applicable, and stops under §4 when the API cannot express it.
- Anton’s emit list is §3. Shapes are names for a later Brief. This packet has no fixtures and no new IDs.
- Instrument payload belongs on the existing results API as JSONB data. That sentence is not a config write and not a new importer.

---

## 8. Out of this spec

Chat. Lab-analysis assistant. Parser authoring. ELN authoring. Dose-response. Second results store. Workflow engine. 21 CFR package. Customer-specific scope. SQL. Code edits. Alembic from the agent. Vendor fallback. Fixed model catalog. Custom Fields. JSONB-as-config. Universal join table. Freezing OQ-1 or OQ-5b.
