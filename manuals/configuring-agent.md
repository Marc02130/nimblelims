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

## A configuration

Create a configuration with a name. It has an id. Lab files are stored on that configuration, not on the person who uploaded them. `created_by` still records who uploaded or applied.

Supported files: PDF, DOCX, and text (TXT, CSV, MD, JSON). RTF is not accepted. Empty files and files over 10 MB are refused. Extracted text is not shown on the page and is not written to logs.

Embeddings match ragged: local `all-MiniLM-L6-v2`, 384 dimensions. `EMBEDDING_PROVIDER=local` in Compose. Tests use `stub`.

## A run

Add at least one ready file before starting. A goal note alone does not call the model.

Each proposed step shows a target, an action, and a one-line why. Groups are Schema tables, Schema columns, Layouts, Privileges, Relations, and other configuration. Lists and units are not in the Schema groups.

For each step: **Accept**, **Redo** with feedback, or **Skip**. Apply posts only the accepted steps, in order, through existing APIs, as the signed-in user. Schema changes still need that user’s `schema:edit`. Layouts need `layout:edit` or `schema:edit`.

Apply is one transaction. If a step cannot be expressed, or an API or permission error occurs, every change from that apply is undone. The screen then shows Stopped or Failed. The banner when a change cannot be expressed is: `Can't apply this change through configuration APIs`.

The agent uses the same Schema list as Admin → Schema. It does not add `lists`, `list_entries`, or `units` as Schema tables. Many-to-many stops. It does not grant `schema:edit`. It does not create users. It does not choose on-delete behavior.

## What was configured

After a successful apply, the configuration lists what was stored. Each row has a name and an id. Kinds include tables, columns, relationships, layouts, privileges, lists, list entries, experiment templates, container types, user roles, sample-type transitions, and role permissions.

Review those records on the existing Admin screens (Schema, Lists, Roles). This page does not edit them.

## What this is not

Not a chat. Not a parser editor. Not dose-response. Not ELN process definitions, asked-for, or routing. Not Custom Fields. A goal note is not a transcript.
