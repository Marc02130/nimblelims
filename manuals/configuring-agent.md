# Configuring agent

An admin with `config:edit` turns lab files into NimbleLIMS configuration. There is no chat on this screen.

## Where

| Screen | Route |
|--------|--------|
| Settings | Admin → Configuring agent settings (`/admin/settings/configuring-agent`) |
| Run | Admin → Configuring agent (`/admin/configuring-agent`) |

A person without `config:edit` gets: “You can't change configuring-agent settings.”

## Settings

Pick one provider: OpenAI, xAI, or Anthropic. The model list is that provider’s live list, loaded by the server. Changing the provider clears the stored key and the model. Set the key after the provider is chosen. The key is encrypted and is not shown again. Clearing the key also clears the model.

If no key is stored, the server uses only that provider’s environment variable: `OPENAI_API_KEY`, `XAI_API_KEY`, or `ANTHROPIC_API_KEY`. It does not call another vendor. The error names the missing variable.

The settings row is named **Configuring agent** and has an id.

The model call runs in the background: **Start** returns at once (HTTP 202, status *reading inputs*) and the page checks every 3 seconds until the proposal is stored. The server waits up to 300 seconds for the model; set `CONFIGURING_AGENT_TIMEOUT_S` to change it. A run still reading inputs well after that (for example after a server restart) is shown as failed: start a new run. `CONFIGURING_AGENT_ASYNC=0` turns the background call off.

## A configuration

Create a configuration with a name. It has an id. Lab files are stored on that configuration, not on the person who uploaded them. `created_by` still records who uploaded or applied.

Supported files: PDF, DOCX, and text (TXT, CSV, MD, JSON). RTF is not accepted. Empty files and files over 10 MB are refused. Extracted text is not shown on the page and is not written to logs.

Embeddings match ragged: local `all-MiniLM-L6-v2`, 384 dimensions. `EMBEDDING_PROVIDER=local` in Compose. Tests use `stub`.

## A run

Add at least one ready file before starting. A goal note alone does not call the model.

Each proposed step shows a target, an action, and a one-line why. Groups are Schema tables, Schema columns, Layouts, Privileges, Relations, and other configuration. Lists and units are not in the Schema groups.

The proposal is one change set. Every row stays on screen, including stops, each with its reason. Each row has an **Include** checkbox; **Redo** with feedback still replaces one row. A row you lack the permission for is greyed out with `Needs {permission}` and can't be included. **Apply N changes** asks you to confirm once. If the included rows contain roles or privileges, schema changes, **Set inactive**, or **Amount → 0**, a second dialog, **You are responsible for these changes**, needs its checkbox before Confirm. Cancel at either dialog writes nothing. Apply writes nothing while an included row is stopped, or while an included row depends on an excluded stopped row. Apply posts only the included rows, in order, in one transaction, through existing APIs, as you (the confirming user). The agent never drops or deletes, and never grants privileges. Every row shows **Before → After** against the live configuration. Running the same file again shows rows that already exist, or already have the proposed values, as **Already there, nothing to change** and **No change**; they start excluded, and even if included, Apply writes nothing and records nothing for them.

The model is given this lab's catalog with ids (Schema tables and columns, lists and their entries, roles, container types, layout screen keys) and the exact routes and body formats, generated from the real API schemas. Names it still sends (a table by name, `name` instead of `display_name`, a role by name, a list entry `value`) are turned into the real ids and fields when the row is proposed and again at Apply, so a column can be added to a table created by an earlier row. Sample types and matrices are entries in the existing `sample_types` and `matrix_types` lists; a new table for them (or for container types) is a stop. Lot numbers, expiry dates and serials are recorded per run and are never configured; a list for them is a stop.

Only tables marked as taking new columns get them (Samples and lab tables you create). Experiments, tests, results and containers do not: a field there is a stop that says where it belongs. A measured result, such as a Qubit concentration in ng/µL, is an **analyte** on an **analysis** and is recorded on the sample's test (POST `/analytes`, POST `/analyses`, POST `/analyses/{analysis}/analytes`). The experiment template is the process, not the result fields.

Duplicates are matched on content, not only the name: a template whose name has the same content words (for example *Qubit dsDNA HS Assay* and *Qubit 4 dsDNA HS quantitation*), or the same definition, is **No change**. Re-adding a column that already exists is **No change**, not a stop. A new row whose name is close to an existing one (for example *EDTA Tube* when *K2EDTA Tube (5mL)* exists) shows **Already exists with a similar name** and starts excluded; include it only if it really is different.

The tables the agent may change are registered in the Schema catalog up front, by migration 0089: every existing table the Schema screen shows (never lists, list entries or units), with its columns and default table privileges. Starting a run writes nothing but the run and its proposed steps. Apply re-checks the catalog idempotently inside its transaction only as a safety net for tables or clients created after the migration.

Apply is one transaction. If a step cannot be expressed, or an API or permission error occurs, every change from that apply is undone. The screen then shows Stopped or Failed. The banner when a change cannot be expressed is: `Can't apply this change through configuration APIs`. The banner and the stopped count include rows that are stops only for you (for example, a permission you don't hold).

The agent uses the same Schema list as Admin → Schema. It does not add `lists`, `list_entries`, or `units` as Schema tables. Many-to-many stops. It does not grant `schema:edit`. It does not create users. It does not choose on-delete behavior.

## What was configured

After a successful apply, the configuration lists what was stored. Each row has a name and an id. Kinds include tables, columns, relationships, layouts, privileges, lists, list entries, experiment templates, container types, user roles, sample-type transitions, and role permissions.

Review those records on the existing Admin screens (Schema, Lists, Roles). This page does not edit them.

## What this is not

Not a chat. Not a parser editor. Not dose-response. Not ELN process definitions, asked-for, or routing. Not Custom Fields. A goal note is not a transcript.

## Slice input

The first lab packet for a real run is `UAT_Scripts/config-agent-slice/`. Load the matching database rows only with `backend/seed_config_agent_slice.py --apply` on a fresh database. That loader is not a migration.

Kit or reagent lot numbers, part numbers, expiry dates and serials are per-run facts. The agent does not propose columns, lists or entries for them; any such proposal is stopped, at proposal and again at Apply, with a reason pointing to reagent tracking, a future feature.
