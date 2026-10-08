# Spec: Configuring agent

**PRD:** [../../prd/configuring-agent/PRD.md](../../prd/configuring-agent/PRD.md)  
**Design:** [../../design/configuring-agent.md](../../design/configuring-agent.md)  
**Date:** 2026-10-03  
**Status:** Working draft. The `configuring-agent` branch implements the 2026-10-03 contracts below. Marc 2026-10-04 locks (L-A, L-B, L-C) and Marc 2026-10-07 answers are folded here. That fold is not a claim that the branch already implements them. This spec still has **no** UAT Pass.  
**Implement gate:** The 2026-10-03 locks. This spec still has **no** UAT Pass.

No Accept, Confirm, or UAT Pass. Tobias’s earlier AC-1 through AC-6 are replaced. Cite **FB-1 through FB-10**, plus the Step 1 bars in §6 (D-1 through D-9, L-1 through L-4, and FB-11). Those Step 1 bars are Tobias 2026-10-07, Marc-approved. Spec only, no UAT stamp until there is a product tip.

Paths below are FastAPI routes as mounted in `backend/app/main.py` under `/v1/configuring-agent`. The UI calls them under `/api` because nginx strips that prefix.

Settings and runs are in `App.tsx`: `/admin/settings/configuring-agent` and `/admin/configuring-agent`. The gate is `config:edit`. Chunks and the ledger belong to a named configuration. Embeddings match ragged (local MiniLM, 384-d). Apply is one transaction with full rollback (Marc 2026-10-07): a failure rolls back every write from that apply, then records the failure. The agent may change any table the signed-in user can change (Marc 2026-10-04). The user is responsible for the change. `ui_schema_catalog.py` is not the agent's scope limit. The Schema display rule still governs the Schema screen (Marc 2026-10-07).

---

## 1. Provider and model (Marc)

Exactly one provider: `openai`, `xai`, or `anthropic`.

An admin picks the provider and picks the model from **that provider’s** live models endpoint. Store both as `agent_provider` and `agent_model`. The LLM call uses those stored values. There is no fixed catalog in the product.

`GET /v1/configuring-agent/models` exists. The router is `backend/app/routers/configuring_agent.py` (`prefix="/configuring-agent"`), mounted with `prefix="/v1"` in `backend/app/main.py`. `models_for` resolves the provider key and calls `list_models`, which requests that provider’s models endpoint from the server (`https://api.openai.com/v1/models`, `https://api.x.ai/v1/models`, or `https://api.anthropic.com/v1/models`). The call is server-proxied. The key must not appear in a URL, log, or toast.

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

The key is masked. After save it is not echoed. Set/update and Clear are separate from saving provider and model (Mathilda). Clear confirms: “Clear the {provider} key? Configuring agent can't call that provider until a key is set again.” Clear also clears `agent_model`. **Decided** in the [PRD](../../prd/configuring-agent/PRD.md) (Decisions locked 2026-10-03, and the §13 row “Clearing the key also clears `agent_model`”).

---

## 3. Existing API only

The agent configures NimbleLIMS only by calling existing APIs. No SQL. No code edits. No Alembic. No direct Postgres. No new write path.

If an existing API cannot express the change, stop (§4). Never a silent partial apply.

### 3.1 Schema — may call

Router `backend/app/routers/ui_schema.py`, prefix `/v1/schema`. Mutate requires `schema:edit` except layout, which allows `layout:edit` or `schema:edit`.

| Method | Path | What it does |
|--------|------|----------------|
| GET, POST | `/v1/schema/tables` | List shown tables. Create is real DDL via `ui_schema_create_table`. Physical name must be `x_<slug>` or `lab_<slug>`. Kind `ui`. |
| POST | `/v1/schema/tables/{table_id}/deprecate` | UI-created tables only. Deprecate is the status flag (Marc 2026-10-07). |
| GET | `/v1/schema/tables/{table_id}/links` | Read-only. |
| GET, POST | `/v1/schema/columns` | Add column is real DDL. |
| POST | `/v1/schema/columns/{column_id}/deprecate` | Deprecate is the status flag (Marc 2026-10-07). |
| GET, PUT | `/v1/schema/layouts` | Role layout. Query/body: `role_id`, `screen_key`, fields. |
| GET, PUT | `/v1/schema/privileges` | Role privileges. PUT body is a list. |
| GET, POST | `/v1/schema/relations` | Declare a side link. |
| GET | `/v1/schema/runtime` | Read. |

**Must not call (Marc 2026-10-07).** Drop is banned outright, even for a table the user just created in the same session. These routes exist. The agent must not call them:

| Method | Path |
|--------|------|
| POST | `/v1/schema/tables/{id}/drop` |
| POST | `/v1/schema/columns/{id}/drop` |
| DELETE | `/v1/schema/relations/{relation_id}` |

There is no status-flag route on relations. A request to remove a relation stops (§4). It does not call DELETE.

Add-column types in `P1_TYPES`: `text`, `numeric`, `integer`, `boolean`, `date`, `timestamptz`, `list`. `jsonb`, `uuid`, and `other` are reflected-only. There is no reference/FK add-column type.

`_can_add_columns` refuses system tables, refuses core tables other than `samples`, and refuses `ADD_COLUMN_OUT`: `asked_for`, `tests`, `results`, `containers`, `contents`, `routing_map`, `work_orders`. The API message is “This table can't get new fields from the UI.” The agent stops. It does not work around that 422. "Any table the user can change" is a permission scope only (Marc 2026-10-07). It does not lift these 422s. Those 422s still stop the run with the existing stop message.

`POST /v1/schema/relations` cardinality is `one_to_many` or `one_to_one` only (`CARDINALITIES`). Anything else, including `many_to_many`, is 422: “Cardinality must be one-to-many or one-to-one”. The handler declares a registry row over an **existing** FK column on the child. It does not CREATE a junction and the service comment says it never mutates the database. 1:1 requires the key to be UNIQUE in Postgres.

A proposal that needs a new FK column, or an M:N junction, cannot be expressed by this API. The run stops and says so. It does not invent the junction. Many-to-many stays deferred. Product intent (Rolf) remains: junctions behind the scenes, operators link and unlink only. Intent is not an API.

`shown_in_schema` is false for `lists`, `list_entries`, and `units`. The agent does not document them as schema tables and does not add columns on them.

Caller without `schema:edit` on a schema mutate gets **403** and no write (FB-7). Today `require_permission` returns detail `Permission 'schema:edit' required`. The agent does not mint `schema:edit` and does not add a Schema-admin role.

### 3.2 Dropdown lists — may call, not Schema

`backend/app/routers/lists.py`, prefix `/lists`, mutate `config:edit`.

| Method | Path |
|--------|------|
| GET, POST | `/lists` |
| PATCH | `/lists/{list_id}` |
| GET, POST | `/lists/{list_name}/entries` |
| PATCH | `/lists/{list_name}/entries/{entry_id}` |

These set list rows (dropdown values). They do not add columns. They do not put `lists` or `list_entries` on Schema.

**Must not call (Marc 2026-10-07):** `DELETE /lists/{list_id}` and `DELETE /lists/{list_name}/entries/{entry_id}`. Both PATCH routes accept `active` (`ListUpdate.active`, `ListEntryUpdate.active`). Retire a list or an entry by PATCH `active` false. If a retire cannot be expressed that way, the run stops.

### 3.3 Other config APIs that exist and match Rolf’s write surface

Use only when the change is accession, sample processing, schema, layout, or privileges, and the route actually expresses it.

| Area | Prefix | Notes |
|------|--------|--------|
| Name templates | `/admin/name-templates` | `config:edit` to create. Sidebar link is already gone. Not a Schema table (`name_templates` is engine-internal). |
| Container types | `/containers/types` | Row catalog. `container_types` is a system Schema table; add-column on system tables is refused. |
| Sample type transitions | `/v1/sample-type-transitions` | GET/POST/PATCH. Mutate `config:edit`. Catalog of aliquot/pool dest legality. This packet does not open dest-type mint. `DELETE /v1/sample-type-transitions/{row_id}` is must-not-call (Marc 2026-10-07). `PATCH` accepts `active`. |
| Roles | `/roles`, `PUT /roles/{role_id}/permissions` | Create, update, and replace permissions require `user:manage` or `config:edit`. `GET /roles/{role_id}/permissions` is `get_current_user` only. Role delete (`DELETE /roles/{role_id}`) is must-not-call (Marc 2026-10-07). `PATCH /roles/{role_id}` accepts `active`. |
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
- Apply is one transaction with full rollback (Marc 2026-10-07). If apply already wrote earlier confirmed steps in that transaction, roll those back too. Do not leave a partial configuration. Record Stopped or Failed only after that rollback.

Confirm-before-apply is a lock (Marc 2026-10-04). One change set per run. Each row has an include/exclude choice. A second confirm is required before roles and privileges, schema changes, set-inactive, and amount → 0. Apply only what was confirmed (Marc 2026-10-07).

The agent never grants the user new privileges. A request that would need one is a stop (Marc 2026-10-07).

The audit actor is the confirming user, flagged agent-assisted, and recorded with run id, provider, and model (Marc 2026-10-07).

An HTTP error from an API the agent did call stays on that row with the API error (Mathilda). That is not a license to retry through SQL, JSONB, `custom_attributes`, drop, or delete. The transaction still rolls back in full.

---

## 5. Privilege

FB-7. A caller without `schema:edit` who reaches a schema mutate gets **403** and no writes.

Settings use the same `config:edit` gate. The copy for a caller who lacks it is “You can't change configuring-agent settings.”

Lab personnel input does not grant `schema:edit`. The agent does not grant it to itself. The agent never grants the user new privileges. A request that would need one is a stop (Marc 2026-10-07).

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

**Note under FB-7.** L-2 supersedes FB-7 for data tables only. Schema creation and alteration still need `schema:edit`.

The configuring-agent bars FB-1 to FB-10 still hold, except FB-7 as noted under L-2.

### Done bar: Step 1, configuring agent running for real (all must pass on the product tip)

Tobias 2026-10-07, Marc-approved. Spec only, no UAT stamp until there is a product tip.

D-1 Real lab input. Run CMDL-SOP2310 first, then Qubit 22975. Katinka and Marc sign off that each input is real. A fixture written to suit the agent fails.

D-2 Live call. Fresh seed DB and a live provider key. The call uses the stored agent_provider and agent_model. A stub, mock, or canned response fails. FB-1 to FB-4 still hold.

D-3 Change set before writes. The agent shows the full proposed change set before any write.

D-4 Apply through existing APIs. After confirm, every change goes through an existing NimbleLIMS API. Each change is verified in the real objects: information_schema, catalog rows, layouts, and privileges.

D-5 Usable on the bench. After apply, an operator accessions a sample and processes it on the new configuration, once for each input. If a written configuration can't be used, it fails.

D-6 Explicit stops. Anything the API can't express, and any self-escalation attempt, is logged as a stop with a reason. A silent drop fails.

D-7 Safe rerun. The same input run again gives a no-op or a clear diff. Duplicate tables, columns, or rows fail.

D-8 Audit. Each applied change logs the confirming user as actor, plus run id, provider, and model.

D-9 Survives restart. After compose down and up, the applied configuration and the run log are still there.

### Lock fail bars

Tobias 2026-10-07, Marc-approved. Spec only, no UAT stamp until there is a product tip.

L-1 Confirm. One confirm per change set, with an include control on each row.

- A second confirm is required before roles and privileges, schema changes, set-inactive, and amount → 0.
- Fail: any write before the required confirm.
- Fail: the applied set differs from the included rows. That covers an extra call, an excluded row that was applied, or a second-confirm item applied on the first confirm alone.
- Fail: cancel at either confirm writes anything.

L-2 Acts as the confirming user. The agent has exactly the confirming user's privileges.

- A table the user can write must be reachable.
- Fail: a refusal with no stated reason.
- A table the user can't write ends as a stop showing the 403.
- Fail: escalation through a system or service principal. A self-escalation attempt is a stop, never an apply.
- Schema creation and alteration still need schema:edit. That supersedes FB-7 for data tables only.

L-3 Drop banned, deprecate allowed.

- Fail: DROP TABLE, DROP COLUMN, TRUNCATE, or a destructive ALTER that loses data.
- Deprecate is allowed: mark the item inactive or hidden, keep the data, and keep it reversible.
- Scored from the API log and the Postgres statement log, not only the UI.

L-4 Plan equals effect. Fail: any side effect, write, or rule fire that is not in the confirmed change set.

FB-11 No delete. Fail: the agent issues DELETE or any delete endpoint on samples, containers, entries, users, or config rows. Removal is a status flag, or container amount → 0, and both need the L-1 second confirm.

FB-11 covers L-B (Marc 2026-10-04).

---

## 7. Katinka and Anton

Respect, refuse, links, and shapes are in the PRD §8 and §9. The spec adds only the contract:

- A proposal that mints tests at receive, treats a fitted number as a config param, puts a list on Schema, or grants `schema:edit` from personnel input fails FB-5, FB-7, FB-8, or FB-9 as applicable, and stops under §4 when the API cannot express it.
- Anton’s emit list is §3. Shapes are names for a later Brief. This packet has no fixtures and no new IDs.
- Instrument payload belongs on the existing results API as JSONB data. That sentence is not a config write and not a new importer.

---

## 8. Out of this spec

Chat. Lab-analysis assistant. Parser authoring. ELN authoring. Dose-response. Second results store. Workflow engine. 21 CFR package. Customer-specific scope. SQL. Code edits. Alembic from the agent. Vendor fallback. Fixed model catalog. Custom Fields. JSONB-as-config. Universal join table. Any delete or drop.

---

## 9. Step 1 slice

UI sketch (Mathilda 2026-10-07): [configuring-agent step 1](../../../review/ui-review/configuring-agent-step1.md) (lands with [PR #147](https://github.com/Marc02130/nimblelims/pull/147), tip `c2f2b46`). This spec does not copy the sketch.

Marc 2026-10-07: CMDL-SOP2310, then Qubit SOP 22975, on a fresh seed DB with a live provider key. TruSeq Nano is the second run.

Katinka 2026-10-07. Links only. No SOP body in this repo.

1. Whole-blood DNA extraction, CMDL-SOP2310 v1.0 (NCI Frederick, KingFisher Flex with the GenFind kit): https://frederick.cancer.gov/media/4402/download?ext=pdf
2. Qubit 4 dsDNA quantitation, SOP 22975 (NCI Frederick): https://frederick.cancer.gov/sites/default/files/2023-01/22975_Redacted.pdf

TruSeq Nano is held for run 2, and SureSelect stays parked.

Configure-first order, each step through existing APIs with confirm-before-apply:

1. Client/project and roles. Bench users can receive, run, and enter results. Review is a separate role. `schema:edit` stays with an admin, and the agent never grants it to itself.
2. Sample types and matrices: Whole Blood (parent) and Genomic DNA (derivative). The allowed pair is Whole Blood to Genomic DNA, recorded through `parent_sample_id`.
3. Container types: an EDTA blood tube for intake and a sample-numbered DNA tube for the eluate. Barcode identifies the vessel and Sample ID identifies the material. Each vessel holds an amount (volume).
4. Accession template: client/project, matrix (Whole Blood), barcode, volume, and first vessel. Receive ends at Available for Testing or Quarantine. No Tests are created at receive (WO-7).
5. Analyses. Extraction is a process step whose result is a new Genomic DNA material on a new tube. The SOP gives 600 µL of blood input per well, up to 24 samples per KingFisher run, and about 400 µL of eluate per sample. Qubit is a test on the DNA sample with the result as concentration in ng/µL. Its hints are the assay kit (HS or BR), the sample volume read, a dilution factor, and a standards check (pass/fail). The acceptance range is set per lab: the SOP only says to re-extract manually below the downstream requirement, so any minimum used in seed or UAT must be marked as example data, not attributed to the SOP. Params freeze at LimsRun start.
6. Statuses: Received, Available for Testing, Quarantine, and Spent when the amount reaches 0. Nothing is deleted, and RESTRICT stays on identity FKs.

Respect: identity plus first vessel at receive; DNA as a new material with `parent_sample_id`; the Qubit number on the DNA sample's test; links only.

Refuse: Tests at receive; JSONB or Custom Fields as config; deletes or CASCADE; an invented concentration cutoff presented as if it came from the SOP; a third ID scheme.

---

## 10. Needs build: where shipped PR #145 differs from the locks (Mathilda 2026-10-07)

Docs list only. Checked on `main` in `frontend/src/pages/admin/ConfiguringAgentRun.tsx`, `backend/app/services/configuring_agent_allow.py` (`_ALLOWED` and `schema_table_names`), `backend/app/services/configuring_agent_apply.py`, `start_run` and `clear_key` in `backend/app/services/configuring_agent_service.py`, and `clear_stored_key` in `backend/app/services/configuring_agent_crypto.py`. No code change in this fold.

Build order starts here:

1. **Drop and DELETE off `_ALLOWED` (first build item; L-B, answer 3, L-3, FB-11).** Remove these five from the agent's callable list. They are still in `_ALLOWED`, and `execute_step` still performs them: `POST /v1/schema/tables/{id}/drop`, `POST /v1/schema/columns/{id}/drop`, `DELETE /v1/schema/relations/{relation_id}`, `DELETE /lists/{list_id}`, `DELETE /lists/{list_name}/entries/{entry_id}`. `DELETE /roles/{role_id}` and `DELETE /v1/sample-type-transitions/{row_id}` are already absent from `_ALLOWED`, so only those five drop and delete routes remain callable.

- **Confirm (L-C, answer 5, L-1).** The run UI uses Accept, Skip, and Redo on each step, then “Apply accepted steps.” It does not show one change set with an include control on each row, and it has no second confirm. The claim matches the code.
- **Amount → 0 (L-B).** No contents-amount path is in `_ALLOWED`. `PATCH /containers/{container_id}/contents/{sample_id}` is not on the agent's callable list. The claim matches the code.
- **Agent scope (L-A).** `configuring_agent_allow.py` still limits schema names through `ui_schema_catalog.py` (`schema_table_names` returns `LAB_TABLES`, `SYSTEM_TABLES`, and `NOT_SCHEMA_TABLES`). Agent scope is the signed-in user's permissions, bounded by the API's own 422s (`_can_add_columns`, system tables, `ADD_COLUMN_OUT`). `manuals/api-endpoints.md` still says the proposal uses the Schema catalog. That wording updates when the L-A code lands. This fold does not edit the manual.
- **Clear key.** The PRD decision is that Clear also clears `agent_model` (§2). `clear_key()` calls `clear_stored_key`, which sets both `key_ciphertext` and `agent_model` to null. The code matches that decision. This is not a needs-build gap.
- **Halt at the first stop.** `start_run` breaks on the first stopped step, so later proposal rows are not kept. **Rolf 2026-10-07, CEO call, Marc may overrule.** This is not a Marc lock. The proposal keeps every row and shows each stop with its reason, so the user sees the full gap list in one run (D-6). Apply writes nothing while any included row is stopped. The user may exclude a stopped row only if no remaining included row depends on it. The first-stop `break` in `start_run` is therefore a needs-build item.

**Deferred, not in step 1:** confirm expiry, ordering of schema changes versus data changes, and undo.
