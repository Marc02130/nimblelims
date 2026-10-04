# PRD: Configuring agent

**Domain:** How an admin turns lab inputs into NimbleLIMS configuration  
**Date:** 2026-10-03  
**Status:** Working draft. Marc locked the open build questions on 2026-10-03 (below). The branch `configuring-agent` implements those locks.  
**Implement gate:** Those locks are the green light for this branch. This file still has **no** review Accept and **no** UAT Pass.  
**Spec:** [../../specs/configuring-agent/SPEC.md](../../specs/configuring-agent/SPEC.md)  
**Design:** [../../design/configuring-agent.md](../../design/configuring-agent.md)  
**History (leave standing):** [configuration PRD](../configuration/PRD.md) · [configuration spec](../../specs/configuration/SPEC.md) · [AI SOP north star](../ai-sop-north-star/PRD.md)  
**Team:** Marc locks below. Rolf product locks. Mathilda surfaces (preference labeled). Tobias fail bars live in the spec. Katinka names public SOPs. Anton names dataset shapes. No fixtures in this packet.

No Accept, Confirm, or UAT Pass is recorded here. August 2026 files stay history. This packet does not reopen them and does not open their implement gates.

## Decisions locked 2026-10-03

- The gate is existing `config:edit`, not a new `agent:configure`. Anyone with `config:edit` may open settings and start a run. The agent calls existing APIs as that user and does not grant itself `schema:edit`.
- Chunks stay on the named configuration (name and id), not on the person who uploaded them. `created_by` still records who did it. A new process is one such configuration. The same name-and-id rule applies to settings, documents, runs, and each ledger row.
- The ledger stores configuration that was actually applied: tables, columns, relationships, experiment templates, and the other allowed kinds. Each row has a name and an id.
- Vectorization matches ragged: local `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, `fastembed`, batch 32. Tests use `EMBEDDING_PROVIDER=stub` (`[[0.01] * 384]`). Chunking is heading-aware, 1000 characters, 200 overlap.
- Apply is one transaction. If any accepted step cannot be expressed or the API errors, every write from that apply is rolled back, including earlier steps in the same apply. The failure is recorded after the rollback. A partial configuration is not left behind.
- The agent uses the Schema screen’s allow-list (`ui_schema_catalog.py`). It does not keep a second list. OQ-1 is not restamped here. OQ-5b stays open; the agent does not choose CASCADE.
- Changing provider clears the stored key and the model, then models are loaded from that provider only. Clearing the key also clears the model. Models are fetched on the server. Accept, feedback-and-redo, or Skip, then Apply only the accepted steps.

---

## 0. Why this exists

A startup lab brings SOPs, instrument files, CRO sheets, manifests, and a staff list. The configuring agent reads those inputs and proposes NimbleLIMS configuration. NimbleLIMS changes only when an existing API can express the change.

One chosen LLM proposes. The product applies by calling APIs that already exist.

---

## 1. Who it is for

Startup biotech/pharma LIMS only (Rolf). Anyone with `config:edit` may set the provider and start a run. Today the Administrator seed role has that permission. Lab Manager does not, unless it is granted.

Lab techs do not see API keys. A caller without `config:edit` sees: “You can't change configuring-agent settings.”

`schema:edit` stays Admin-only (Rolf). The agent does not mint that permission, does not add a Schema-admin role, and lab personnel input does not grant `schema:edit`.

---

## 2. What it does

The agent configures a lab’s NimbleLIMS from lab inputs (Marc, 2026-10-03): SOPs, instrument output, CRO data, sample manifests, lab personnel, and similar.

Rolf narrows the write surface. The agent configures accession, sample processing, schema, layouts, and privileges **that existing APIs already express**. It is not a CRM, not an ERP, and not an enterprise suite.

An admin picks the provider and the model (Marc, explicit):

- Provider is one of `openai`, `xai`, `anthropic`.
- The model list comes from that provider’s live models endpoint. There is no fixed catalog.
- Both values are stored as `agent_provider` and `agent_model`.

The LLM proposes. Each proposed step names a target, an action, and a one-line why (Mathilda). Grouping she asks for: Schema tables/columns, Layouts, Privileges, Relations, and other existing config APIs.

---

## 3. Inputs

| Input | What a run uses it for |
|-------|------------------------|
| SOP | Public links and names only. No SOP body in git. Katinka’s list is §8. |
| Instrument output | Payload shape. Not a schema design. Anton’s row shape is §9. |
| CRO data | Same manifest row plus a sponsor project that is not the home client. |
| Sample manifest | Existing catalog names and the row shape in §9. |
| Lab personnel | Existing users only. Shape is user × role × project. |
| Goal note | Optional one field on New run. Not a chat thread (Mathilda). |

Empty or missing lab input means no LLM call and a clear error (Tobias FB-10). Start is refused with no inputs (Mathilda).

---

## 4. What it does not do

- Chat product. Lab-analysis assistant. Prompt playground. Test message. Streaming panel. Conversation UI.
- IC50, dose-response fitting, parsers, ELN, and a second results store (Rolf). Classic results stay as they are. Asked-for and routing stay as built. This packet does not reconfigure those paths.
- SQL, code edits, Alembic, direct Postgres, or any new write path that bypasses existing APIs (Marc, Rolf).
- A second vendor in the same run, or a silent fallback when the chosen provider has no key (Marc).
- Revival of Custom Fields, `custom_attributes`, or JSONB-as-fields (Rolf). A field is a real column. A link is a real FK.
- Lists and list items as Schema tables. Dropdown values may still be set through the existing list-editor APIs. The agent does not add columns on `lists` or `list_entries`.
- Many-to-many as an operator sheet. There is no universal join table. Junctions, when the product has them, stay behind the scenes: operators link and unlink only (Rolf; product intent already stated). The relations API today does not create a junction. See the spec.
- 21 CFR validation package, a workflow engine, or customer-specific scope as P1 (Rolf).
- A later lab chat. It may reuse the same LLM client someday. This packet does not design that chat (Marc).

---

## 5. Stop when the API cannot express the change

If an existing API cannot express the change, the agent stops and says so in plain language (Marc). It does not invent a workaround. It does not silently drop the step. It does not partially apply and continue (Rolf). Tobias FB-6: write nothing for that blocked change.

Mathilda’s stop chrome: status **Stopped**, banner “Can't apply this change through configuration APIs,” plus the blocked step and the gap in plain words.

Her confirm-before-apply flow is a **preference, not a Marc lock**: propose, then human Accept or Skip per change, then Apply accepted changes. Auto-apply versus always-confirm stays **open**. If a later lock allows auto-apply, the run still shows an Applied log (Mathilda).

Two sentences sit side by side and are **not frozen** into one rule:

- Rolf / FB-6: cannot-express stops the run and writes nothing for that change.
- Mathilda: an API error during Apply stays on that row; Done can show applied / skipped / stopped counts.

Reading that keeps them apart: a gap found while proposing writes nothing. An error returned by an API during Apply stays on the row and the run does not continue into later steps. The stricter reading (roll back rows already posted) is not decided here.

---

## 6. Provider, model, and key

Marc, 2026-10-03, explicit:

- One chosen provider: `openai`, `xai`, or `anthropic`.
- Admin picks the model from that provider’s live models endpoint.
- Store `agent_provider` and `agent_model`.
- No fixed catalog.
- API keys are stored encrypted.
- Env fallback names, and only these: `OPENAI_API_KEY`, `XAI_API_KEY`, `ANTHROPIC_API_KEY`.
- No key for the chosen provider is a clear error. The error names that provider’s key. No silent fallback to another vendor. No config writes before the key check (FB-4).

Nothing in the repo today stores `agent_provider`, `agent_model`, or an encrypted provider key. Those are contracts for a later build. This packet does not name a new table.

---

## 7. Schema display rule

Marc, 2026-10-03:

A table appears on Schema only when a change can be made and then used through configuration. If the app would ignore the change until code is refactored, the table stays off Schema.

`lists` and `list_entries` stay off Schema. Do not document them as schema tables. The agent may still call the list-editor APIs when those APIs are how dropdown values are set. It must not treat lists as Schema tables and must not add columns on them.

Custom Fields is not a place to work. Many-to-many is deferred. There is no universal join table.

Current catalog code (`ui_schema_catalog.py`) also keeps `units` off Schema: a new column there is unused until conversion code changes. That matches the display rule. This packet does not document `units` as a schema table.

**OQ-1 (Schema Tables allow-list) is not frozen here.** The tables-cleanup open-questions file already carries a Decided label on an allow-list. Rolf: that question stays Marc’s until he answers. This packet does not restamp it and does not treat the label as a new Accept.

**OQ-5b (on-delete) is not frozen here.** Katinka’s position is RESTRICT on identity links (sample, barcode vessel). Rolf: OQ-5b stays open until Marc answers. Both sentences stay. This packet does not pick one.

---

## 8. Katinka — respect and refuse

Links and names only. No SOP body in git. Propose from these public links only.

### Respect

- Receive is identity plus first vessel only. Do not mint tests at accession. Tests appear at LimsRun start.
- Barcode is the vessel. Sample ID is the material.
- A result stays on the sample’s test.
- A derivative is a new material with `parent_sample_id`.
- Locked path to name: blood → DNA → TruSeq Nano. Capture and SureSelect stay parked.
- Relations the product already intends: 1:N FK on the child, 1:1 unique FK, M:N junction behind the scenes.
- Config is real columns and real FKs.
- Instrument files are payload, not schema. JSONB is allowed for instrument or result payload, not for config.
- Analysis params freeze at LimsRun start. Fitted IC50, Hill, CLint, and fu are results, not config params.

### Public methods (name + link)

| Name | Link |
|------|------|
| NCI Best Practices for Biospecimen Resources (2016) — identity, receipt | https://dctd.cancer.gov/data-tools-biospecimens/biospecimens-biobanks/resources/best-practices/best-practices-2016.pdf |
| NCI GTEx BBRB-OP-0011 — chain of custody | https://dctd.cancer.gov/data-tools-biospecimens/biospecimens-biobanks/resources/sops/gtex/bbrb-op-0011.pdf |
| NCI-60 submitting-compounds SOP — dose-response | https://dctd.cancer.gov/drug-discovery-development/assays/high-throughput-screening-services/nci60/submitting-compounds/sop.pdf |
| SOP 23103 — HEK 293 HCP ELISA (Cygnus) | https://frederick.cancer.gov/sites/default/files/2022-04/Quantitation_of_HEK_293_Host_Cell_Protein_Using_Cygnus_Inc._ELISA_Kit.pdf |
| SOP 22135 — kinetic chromogenic LAL (Charles River) | https://frederick.cancer.gov/sites/default/files/2022-03/Endotoxin_Determination_by_Kinetic_Chromogenic_Testing_Using_Charles_River_LAL_System.pdf |
| CMDL-SOP2310 — KingFisher whole blood | https://frederick.cancer.gov/media/4402/download?ext=pdf |
| SOP 23113 — QIAamp Mini | https://frederick.cancer.gov/media/1962/download?ext=pdf |
| SOP 22975 — Qubit 4 | https://frederick.cancer.gov/sites/default/files/2023-01/22975_Redacted.pdf |
| MCCRD-SOP0002 — tissue AllPrep | https://dctd.cancer.gov/drug-discovery-development/reagents-materials/pdmr/using-pdmr/sops/mccrd-sop0002.pdf |
| CMDL-SOP2308 — FFPE | https://frederick.cancer.gov/media/4400/download?ext=pdf |
| TruSeq Nano DNA Library Prep Reference Guide (15041110 D) | https://support.illumina.com/downloads/truseq-nano-dna-library-prep-guide-15041110.html |
| MCCRD-SOP0005 — SureSelectXT capture (**parked**) | Listed on https://dctd.cancer.gov/drug-discovery-development/reagents-materials/pdmr/using-pdmr/sops |

Param families only, not full SOPs: AGM, ICH, OECD, NCI — for safety, DMPK/ADME, cell-based, biochemical, and dose-response. AGM entry already recorded: https://www.ncbi.nlm.nih.gov/books/NBK144065/ . ICH example already recorded (safety, not a DMPK SOP): https://database.ich.org/sites/default/files/S7B_Guideline.pdf . OECD is the test-guideline family. **No titled public DMPK SOP was found. Do not invent one.**

### Refuse

JSONB or `custom_attributes` as fields, tables, or related ids. Custom Fields chrome. Dropdown lists on Schema. CASCADE or silent wipe of a sample or barcode vessel (her position; OQ-5b is not frozen — §7). A junction table as an operator data-entry sheet. Tests or an analysis queue at receive. Treating IC50 or any fitted number as configuration. Inventing a DMPK SOP or a third sample-ID scheme. Granting itself `schema:edit`. Any change the current API cannot make.

---

## 9. Anton — shapes only

He is not seeding until a Brief opens. No new IDs, no SOP prose, no fixtures in this PR.

**SOP packet.** SOP number and source URL only. Ordered steps. Each step: input matrix, output matrix, field-name hints (barcode, sample ID, vessel, parent link, matrix/type). Concrete bind: CMDL-SOP2310 KingFisher whole blood, then SOP 22975 Qubit 4, then TruSeq Nano. Capture stays parked.

**Manifest row.** Existing name, sample type, nullable parent (1:N on the child), project, container barcode, matrix. Bind existing catalog names only:

| Name | Bind |
|------|------|
| `CAR-T-Batch-001` | PBMC. HCP ELISA and kinetic LAL. |
| `Plasmid-Lot-2025-001` | Already DNA. LAL, including plasmid PPC. |
| `mAb-2301-PK-T0` → `T0-Aliq` | Plasma PK. |
| `NBIO-CMPD-001` / A549 | NCI-60 CellTiter-Glo. `EX_CTG` / `EX_NCI60`. |

Gap he names, do not mint it: no whole-blood intake and no DNA daughter with `parent_sample_id`. Blood × aliquot → DNA already exists (0068).

**Instrument export.** Payload, not config. One importable result per row: `example_id`, `example_class` valid or edge, `plate_id`, existing sample or compound name, assay columns. The three CSVs are the bind (NCI-60, HCP ELISA on `CAR-T-Batch-001`, kinetic LAL on CAR-T and plasmid), including SOP edge rows (NCI-60 C ≤ Tz and missing dose; HCP percent CV over 25 and above ULOQ; LAL PPC inhibition and contaminated blank). Lands as JSONB payload through the results API. Never a schema or config write. This packet does not add a results importer. Classic results stay as they are (Rolf).

**CRO inbound.** Same manifest row plus a sponsor project that is not the home client. 0059 has no such sample. Name the gap. Do not invent a sponsor name or a third ID scheme.

**Personnel.** Existing user only. Alice is the 0058 seed user (mAb PK and Alpha only; same-client deny on `CAR-T-Batch-001`). Shape is user × role × project. `schema:edit` defines an FK and a junction; an operator links and unlinks only. Enterer versus reviewer is US-10, no new columns. No new staff names.

**Config the agent may emit,** only through an API that already exists: allow-listed table or column (real DDL), role layout, role privileges, 1:N FK, 1:1 unique FK, and an M:N junction only if that API already exists. Many-to-many is still deferred and `POST /v1/schema/relations` refuses `many_to_many`. The run stops and says so. It does not invent the junction.

---

## 10. How this differs from the August 2026 docs

The [configuration PRD](../configuration/PRD.md) (2026-08-30) and the [AI SOP north star](../ai-sop-north-star/PRD.md) describe MCP draft-only process and parser authoring, Field Management custom fields, and lists as configuration homes. Those files stay history. Their implement gates stay **CLOSED**. This packet does not claim signed UAT is overturned.

This packet:

- Configuration goes through existing APIs and stops when an API cannot express the change.
- Custom fields are not a place to work. The agent does not call `/admin/fields` or `/admin/custom-attributes` to invent fields. `/admin/custom-fields` already redirects to Schema tables.
- Lists are not Schema tables. List-editor APIs remain the way to set dropdown values.

Asked-for, routing, parsers, and ELN authoring stay on the older packets. Rolf keeps them out of this one. If a proposal needs a parser, an ELN process definition, or a change to asked-for or routing, the run stops and says that path is not this packet. Those HTTP routes exist; this packet does not assign them to the agent. That overlap (Katinka’s blood → DNA → TruSeq path versus Rolf’s ELN exclusion) is **not frozen**: the path is what a proposal must respect; ELN and parser writes are not in this packet’s job.

---

## 11. Mathilda

Two surfaces. Detail is in the [design](../../design/configuring-agent.md). Settings: Admin → Configuring agent settings (`/admin/settings/configuring-agent`). Run: Admin → Configuring agent (`/admin/configuring-agent`).

Accept, feedback-and-redo, or Skip, then Apply. Apply does not leave a partial configuration.

---

## 12. Success (behavior, not a shipped claim)

A later build matches this draft when an admin can:

- Store one provider and one model from that provider’s live list, and see a clear error when that provider’s key is missing, with no call to another vendor.
- Start a run only with lab input attached, and get a proposal whose steps name target, action, and why.
- Watch the run stop, with the banner and the gap in plain words, when no existing API can express a step, and see that the agent did not invent a workaround.
- Land list values through the list APIs while `lists` and `list_entries` stay off Schema.
- Finish without a chat transcript, a lab-analysis answer, a SQL write, or a code edit.

This draft does not claim that behavior ships.

---

## 13. Open (do not freeze)

| Item | Who | State |
|------|-----|--------|
| OQ-1 Schema Tables allow-list | Marc | Open for him. Not frozen by this packet. |
| OQ-5b on-delete | Marc | Open for him. Katinka’s RESTRICT on identity links is her position only. |
| Settings permission name | Marc | **Decided.** `config:edit`. |
| Clearing the key also clears `agent_model` | Marc | **Decided.** Yes. Changing provider clears the key and the model. |
| Models fetched server-side or in the browser | Marc | **Decided.** Server-side, chosen provider only. |
| Auto-apply vs always-confirm | Marc | **Decided.** Accept, feedback-and-redo, or Skip. Apply accepted steps as one transaction. |
| Who may start a run | Marc | **Decided.** Anyone with `config:edit`, not a new permission. |
| Where chunks live | Marc | **Decided.** On the named configuration, with a ledger of what was stored. |
| Failed apply | Marc | **Decided.** Roll back the whole apply. No partial configuration. |
| Which Schema list | Marc | **Decided.** The Schema screen list. No second list. |
| Input retention and PHI on uploads | Mathilda | Open. No retention control in this build. |
| What else a startup LIMS must refuse | Rolf | His locks in §4 and §7 are in this draft. He did not add a further list. |
| Dataset fixtures | Anton | Out. No Brief, no seed. |
