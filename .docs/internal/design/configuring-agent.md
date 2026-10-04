# Design: Configuring agent

**Date:** 2026-10-03  
**Status:** Working draft. **Not an implement packet.**  
**Implement gate:** **CLOSED.**  
**PRD:** [../prd/configuring-agent/PRD.md](../prd/configuring-agent/PRD.md)  
**Spec:** [../specs/configuring-agent/SPEC.md](../specs/configuring-agent/SPEC.md)

Operator-facing shape of provider setup and of a configuration run. No chat transcript as the product. Routes below are proposed. They are not in `App.tsx` today.

Marc, explicit: an admin picks the provider (`openai`, `xai`, or `anthropic`) and picks the model from that provider’s live models endpoint. Store both as `agent_provider` and `agent_model`. No fixed catalog.

Mathilda’s confirm-before-apply flow is a **proposal and her preference**. It is not a Marc lock.

---

## 1. Settings

**Place:** Admin → Settings → Configuring agent.

Not lab-tech. No chat, no conversation UI, no prompt playground, no test message, no streaming panel.

A caller without the settings gate sees: “You can't change configuring-agent settings.” The permission name is open (`agent:configure` or the existing admin settings gate).

### Fields

| Field | Control | Stored as |
|-------|---------|-----------|
| Provider | Single select. Labels OpenAI / xAI / Anthropic. | `openai` / `xai` / `anthropic` |
| Model | Single select. Options from the live models endpoint of the selected provider. | `agent_model` |
| API key | Masked. Never echoed after save. | Encrypted. Not shown again. |

Changing provider clears the selected model and re-fetches models.

Model states:

- “Loading models…”
- “Couldn't load models — check key or try again”
- An empty list disables saving the model.

When the display name differs from the provider model id, show the model id as secondary text.

Status chip: **Key set** or **No key**.

### Actions

Separate save for provider and model. Separate key actions:

- Set or update key.
- Clear key. Confirm: “Clear the {provider} key? Configuring agent can't call that provider until a key is set again.”

Whether Clear also clears the model is open.

The key never appears in a URL, log, or toast. Mathilda recommends the models endpoint be server-proxied. Browser-direct is open. Either way the key stays off the wire the browser can read back, and off the URL.

### Missing key

Chip **No key**. The model control does not offer a saved model as if a call could succeed. A run start while the provider or the key is unset is refused, and the screen sends the admin to this Settings page.

The error names the missing key for the chosen provider: `OPENAI_API_KEY`, `XAI_API_KEY`, or `ANTHROPIC_API_KEY`. It does not offer another vendor.

### Bounce

Chat pane. Hard-coded model dropdown. Raw key after save. Lab-tech access to keys.

---

## 2. Run (proposal — Mathilda, not a lock)

**Place:** Admin → Configuring agent → New run.

Her default is Admin only. Whether a lab manager can start a run is open.

### Start

Attach SOPs, instrument output, CRO data, sample manifests, and personnel. Optional one-field goal note. The note is not a chat thread.

Start is refused when there are no inputs. Start is refused when provider or key is unset; send them to Settings. Empty input does not call the LLM (FB-10).

There is no transcript. The screen is the run, the proposal list, and the log.

### Statuses

Preparing → Reading inputs → Proposing changes → Applying → then one of Stopped, Failed, Done.

Stop run asks for confirm.

### Proposal list

Each step shows:

- target
- action
- one-line why

Group by Schema tables/columns, Layouts, Privileges, Relations, and other existing config APIs. Do not invent Schema chrome for lists. `lists` and `list_entries` do not appear in the Schema group. A list-entry write, if the list API is how a dropdown value is set, sits under other existing config APIs.

**Her preference, not a lock:** the admin Accepts or Skips each change, then Apply posts only the accepted ones through existing APIs. Auto-apply versus always-confirm is open. If auto-apply is later allowed, still show an Applied log.

Failures stay on the row with the API error. The run does not continue into later steps after a gap.

### Stopped

When an API cannot express the change:

- Status **Stopped**.
- Banner: “Can't apply this change through configuration APIs”
- The blocked step stays visible.
- The gap is in plain words (what was asked, which API cannot say it).

Example of the plain gap, not a script to ship: “Add a many-to-many between samples and projects. Relations accept one-to-many or one-to-one on an existing foreign key. There is no junction API.” The run writes nothing for that step.

### Done

Shows applied / skipped / stopped counts. Links go to existing Admin surfaces (Schema, Lists, Roles), not to a new editor. Run history is read-only.

### Bounce

Chat. Lab-analysis. JSONB or `custom_attributes` as config. Lists on Schema. A Schema table that is not configuration-usable. Apply that skips existing APIs. Silent continue after a gap.

---

## 3. What the operator does not get

A conversation. A dose-response plot. A parser editor. An ELN author. A SQL box. A model playground. A second results grid. Those products are out of this packet (Rolf, Marc).

---

## 4. Open on this screen

| Question | Note |
|----------|------|
| Permission that gates Settings | Open. |
| Clear key clears `agent_model`? | Open. |
| Server-proxied models vs browser-direct | Open. Recommendation: server-proxied. |
| Always confirm vs auto-apply | Open. Accept or Skip is the proposal on the page. |
| Lab manager may open New run? | Open. Default drawn here: Admin only. |
| How long uploads are kept, and PHI | Open. Do not draw a retention control until that is decided. |
