# UAT: Configuring agent

**Stem:** `configuring-agent`  
**PRD:** `.docs/internal/prd/configuring-agent/PRD.md`  
**Spec:** `.docs/internal/specs/configuring-agent/SPEC.md`  
**Design:** `.docs/internal/design/configuring-agent.md`  
**Manual:** `manuals/configuring-agent.md`  
**Migration:** `0083_configuring_agent`  
**Status:** UAT **failed**. Sections 1, 2, 3, 4, and 6 passed. Section 5 is **blocked** (schema:edit grant was not proposed). Do not treat this as a UAT Pass.

## Fail bars

1. A second provider is used in one run, or a missing key names a different vendor’s variable, or the key is shown again after save.
2. The model list is a fixed catalog, or it includes models from a provider other than the one selected.
3. Apply leaves any accepted step’s write in place after a later step fails or cannot be expressed.
4. A schema change is stored for a user who lacks `schema:edit`, or personnel input grants `schema:edit`.
5. `lists`, `list_entries`, or `units` are proposed as Schema tables, or many-to-many is applied.
6. A run calls the model with no ready lab file. A goal note alone counts as empty input.
7. Chunks are stored on the uploading user instead of the named configuration, or an applied table, column, relationship, or experiment template is missing from that configuration’s ledger.
8. The screen is a chat, a prompt box that runs without a proposal, or a SQL box.

## Logins

- Administrator seed has `config:edit`: `admin` / `***REMOVED***`
- Lab technician does not: `lab-tech` / `***REMOVED***`

Do not treat a failed documented password as a product failure of this script. Reset the local password if login is locked out, then continue. Do not grant `schema:edit` to the technician to make a step pass.

## 1. Gate

1. As lab technician, open `/admin/settings/configuring-agent` and `/admin/configuring-agent`. Both redirect away.
2. `GET /api/v1/configuring-agent/settings` as the technician returns **403** and the body says `You can't change configuring-agent settings.`
**Pass / Fail:** Pass. As lab-tech, both `/admin/settings/configuring-agent` and `/admin/configuring-agent` redirected to `/dashboard`. `GET /api/v1/configuring-agent/settings` returned 403 with `You can't change configuring-agent settings.`

## 2. Provider, model, key

1. As admin, open Configuring agent settings. The row name is Configuring agent and an id is shown.
2. Choose OpenAI. The model control says it is loading, then lists models from OpenAI only. Save a model.
3. Change the provider to xAI. The previous model is cleared and the OpenAI key, if one was stored, is not reused. The error or the list is xAI’s, not OpenAI’s.
4. Set a key. The field empties. The chip says **Key set**. Reload the page. The key is not in the page, the address bar, or a toast.
5. Clear the key and confirm. The chip says **No key** and the model is cleared. With no env fallback, starting a run names `XAI_API_KEY` (or whichever provider is selected) and does not mention another vendor.
**Pass / Fail:** Pass. Settings id `c0a16ae0-0000-4000-8000-000000000001`, provider xAI, chip Key set, saved model `grok-4.3`. The model control listed 14 models from `GET /models?provider=xai` (all `grok-*`, including `grok-4.3`; no `gpt-` or `claude` ids). Provider was not switched, because that clears the stored xAI key; the earlier run already saw clear-on-switch, the key field emptying with chip Key set, reload without the key, and Clear key showing No key.

## 3. Named configuration and files

1. Create a configuration named `Acme intake`. The page shows that name and an id.
2. Start a run before adding a file. The error says to add a lab file and does not call the model. A goal note without a file still refuses.
3. Upload a small text file that states one concrete change the lab files actually ask for (for example a list value). It becomes ready and shows a chunk count. The page does not show the file body.
4. Confirm in the database that `configuration_chunks` rows for that file have `configuration_id` of `Acme intake` and no user-owner column. `created_by` on the document may be the admin.
**Pass / Fail:** Pass. `POST /configurations` created Acme intake `309f0f8b-12be-4f7b-a8e9-6a4ea4673bed` (name and id on the page); `POST .../runs` before a file, with and without a goal note, returned 400 `Add a lab file before starting a run. Empty input does not call the model.` Upload returned 201 ready, `chunk_count` 1, the page showed `acme-intake.txt · ready · 1 chunks` and not the file body; `configuration_chunks` has no user-owner column, `configuration_id` is that id, and document `created_by` is admin `00000000-0000-0000-0000-000000000001`.

## 4. Proposal uses the Schema list

1. Start a run. Steps show target, action, and why.
2. List and unit steps, if any, are under **Other configuration**, not Schema tables or Schema columns.
3. A many-to-many proposal is **Stopped**, with banner `Can't apply this change through configuration APIs`, and it is not Accept. Nothing new is in Schema.
**Pass / Fail:** Pass. On UAT ledger pass the xAI run showed target, action, and why, and the list step’s group was `other` (screen heading Other configuration), not Schema tables. On UAT many to many the run status was stopped with banner `Can't apply this change through configuration APIs`; Accept returned 400 `This step cannot be accepted. Skip it or send feedback.` Schema table count stayed 29.

## 5. Apply is all or nothing

1. Accept two steps that the APIs can express, and Skip the rest. Apply. Status becomes done. The configuration ledger lists each stored object with a name and an id, including an experiment template when one was accepted. Schema, Lists, or Roles shows the same records.
2. Repeat with a second configuration. Accept one valid step and one step the signed-in user cannot perform (schema mutate without `schema:edit`, or a step the API rejects). Apply. The run is failed or stopped. The first step’s table, column, list, or template is **not** present. Ledger rows from this apply are absent.
3. Accept a step whose only action is granting a role `schema:edit` it does not already have. Apply stops, writes nothing, and does not add that permission.
**Pass / Fail:** Blocked. Two accepted steps on UAT ledger pass applied HTTP 200 status done (list `UAT intake source` `aaf58812-a35d-4bf0-b2ae-49ed3269f088` and experiment template `UAT intake plate` `69dd4d8c-ff8c-482a-ba93-198d63062b36` on the ledger and on Lists and experiment templates). A second run accepted a valid list plus `POST /v1/schema/columns` for a missing table; Apply returned status failed `Table not found`, applied 0, and neither the list nor a ledger row remained. A schema:edit-only grant was not proposed on two runs (400 `The model did not return any configuration steps.`), so Accept/Apply of that grant was not observed. `schema:edit` is still only on Administrator.

## 6. Out of scope

1. There is no chat transcript, no prompt playground, and no SQL entry on either page.
2. The agent does not offer Custom Fields, asked-for, routing, parsers, or ELN process definitions as places it will write.
**Pass / Fail:** Pass. Main content of both pages has no chat transcript, prompt playground, or SQL entry, and does not offer Custom Fields, asked-for, routing, parsers, or ELN process definitions as write targets. No proposal steps were returned, so this check is the screens, not a model step list.
