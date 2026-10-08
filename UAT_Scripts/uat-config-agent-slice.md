# UAT: configuring-agent slice input

**Stem:** config-agent-slice  
**Date:** 2026-10-08  
**Scope:** Opt-in seed plus the input packet. This does not run the configuring agent and does not need an LLM key.  
**Locks:** [PR #148](https://github.com/Marc02130/nimblelims/pull/148). The follow-up named tip `686f926`. The PR head used here is `47b3a52`. Bars are SPEC §6: FB-1–FB-11, D-1–D-9, L-1–L-4. #148 records no UAT Pass. This script does not stamp one.

## Setup

1. Migrate a fresh database (`alembic upgrade head` / backend startup).
   **D-2** asks for a fresh seed DB before the live call. Expected: migrations only. No slice users and no `Project Alpha-01` yet. This step does not make the live provider call. A stub or canned LLM response still fails D-2 when that run happens.
2. Do not point `MIGRATE_DATABASE_URL` at a dogfood database unless you mean to load the slice there.
   Expected: dogfood rows are unchanged when the URL points at a fresh database. This is the loader rule. It is not an agent bar.
3. From `backend`: `python seed_config_agent_slice.py` writes nothing.
   Expected: exit 0, usage text, no new users, samples, or vessels. **L-1** fails any agent write before confirm. This command is the loader with no `--apply`. It is not the agent confirm.
4. `python seed_config_agent_slice.py --apply`
   Expected: the rows in Acceptance. This is the lab input **D-1** will run against (CMDL-SOP2310, then SOP 22975). Loading the seed is not the agent apply in **D-4**. Set `SLICE_REVIEWER_PASSWORD` and `SLICE_SCHEMA_EDITOR_PASSWORD` first. If either is unset, that password is generated and printed once on this command's stdout. Do not copy it into this script's results. `--check` does not print a password.
5. `python seed_config_agent_slice.py --check`
   Expected: manifest names resolve as in Acceptance 6, and all 10 kinetic LAL CSVs parse (8 valid, 2 edge). LAL rows are JSON payload, not a config write (**FB-5**, PRD §9, SPEC §7).
6. Run `--apply` again.
   Expected: exit 2, message that the slice is already present, and the same row counts as after step 4. That refusal is the loader. **D-7** is the later agent bar: the same lab input run again gives a no-op or a clear diff, and duplicate tables, columns, or rows fail. This step does not score D-7.

## Acceptance

1. `Project Alpha-01` exists, sample type Blood, matrix Whole Blood, status Available for Testing, one vessel `NBIO-EDTA-2310-001` of type `K2EDTA Tube (5mL)`, contents amount 600 µL.
   **SPEC §9.3–§9.4.** Barcode is the vessel. Sample ID is the material. The vessel holds an amount. Receive ends at Available for Testing. `Quarantine` is not on the Sample Status list, so this row does not use it. Creating `Quarantine` is a later agent gap (SPEC §9.6), through the list API, with lists kept off Schema (**FB-9**).
2. `Project Alpha-02` exists, sample type DNA, matrix Genomic DNA, `parent_sample_id` is `Project Alpha-01`, vessel `NBIO-DNA-2310-001`, contents amount 400 µL. No tests were created at receive.
   **SPEC §9.2 and §9.4**, PRD §8. The derivative is a new material with `parent_sample_id`. No Tests are created at receive (WO-7). The catalog sample types are Blood and DNA. The matrices are Whole Blood and Genomic DNA.
3. `results-reviewer` is Lab Manager, has `result:review`, and is not Administrator.
   **SPEC §9.1 and §3.3.** Review is a separate role. `result:enter` and `result:review` already exist. No new columns. Lab Manager also holds `result:enter`. #148 does not require a review-only role.
4. `schema-editor` is Schema Editor, has `schema:edit` and `config:edit`, and is not Administrator.
   **L-2** and **FB-7**. Schema creation and alteration still need `schema:edit`. L-2 supersedes FB-7 for data tables only. Expected on a later agent run: the same schema change applies for `schema-editor` and is refused for `alice-tech` with 403 `Permission 'schema:edit' required` and no write. The agent does not mint `schema:edit` and does not grant a privilege the user lacks (PRD §1, answer 6). A self-escalation attempt is a stop, never an apply (**L-2**, **D-6**).
5. `alice-tech` is still Lab Technician on Project Alpha and mAb-2301 PK Study only. `admin` and `lab-tech` are unchanged. `mAb-2301-PK-T0` contents amount is still 50 µL.
   Personnel shape is user × role × project (PRD §9). The manifest's depleted row is amount 0 plus status Testing Complete, the closest existing status. **L-B** and **FB-11**: the live sample and vessel stay. The seed does not delete them and does not change the 50 µL contents row. `Spent` is not seeded.
6. Manifest names other than `NBIO-CMPD-001` resolve to those sample rows. `NBIO-CMPD-001` does not.
   **PRD §9** manifest shape, existing names only. `NBIO-CMPD-001` is the NCI-60 compound id (A549), not a sample. Plasma PK and plasmid rows stay off the blood → DNA SOP path.
7. All 10 kinetic LAL CSVs parse with `UAT_Scripts/config-agent-slice/lal-parser-config.json` (8 valid, 2 edge).
   **FB-5.** Parsed `row_data` is instrument payload. It is not a schema write and not `custom_attributes`. This script does not post results and does not add a parser row (SPEC §3.4).

## Later agent run (not executed here)

Expected results match SPEC §6. #148 has no UAT stamp until there is a product tip.

| Bar | Expected |
|-----|----------|
| **D-1** | The run uses CMDL-SOP2310, then SOP 22975, from this packet's links. TruSeq Nano is run 2. SureSelect stays parked. A fixture written to suit the agent fails. |
| **D-2** | Fresh database from this seed, live provider key, stored `agent_provider` and `agent_model`. A stub, mock, or canned response fails. |
| **D-3** | The full proposed change set is shown before any write. |
| **D-4** | After confirm, every change goes through an existing API and is visible in the real objects. |
| **D-5** | After apply, an operator can accession and process on that configuration, once for each input. A configuration that cannot be used fails. |
| **D-6** | A change the API cannot express, and any self-escalation, is a stop with a reason. A silent drop fails. Banner text, exact: `Can't apply this change through configuration APIs`. |
| **D-7** | The same input again is a no-op or a clear diff. Duplicate tables, columns, or rows fail. |
| **D-8** | Each applied change logs the confirming user, flagged agent-assisted, plus run id, provider, and model (answer 7). |
| **D-9** | After compose down and up, the applied configuration and the run log are still there. |
| **L-1** | One confirm per change set, include control on each row. A second confirm before roles and privileges, schema changes, set-inactive, and amount → 0. Any write before the required confirm fails. Cancel writes nothing. The applied set matches the included rows. |
| **L-2** | The agent has exactly the confirming user's privileges. `schema-editor` can reach a schema change. `alice-tech` stops with the 403. Escalation through a system or service principal fails. |
| **L-3** | DROP TABLE, DROP COLUMN, TRUNCATE, or a destructive ALTER that loses data fails. Deprecate (inactive or hidden, data kept, reversible) is allowed. |
| **L-4** | No side effect outside the confirmed change set. |
| **FB-1–FB-4** | One of `openai`, `xai`, `anthropic`. Live models for that provider. Stored provider and model are what the call uses. Missing key names `OPENAI_API_KEY`, `XAI_API_KEY`, or `ANTHROPIC_API_KEY`, with no config write and no vendor fallback. |
| **FB-5** | Existing APIs only. JSONB or `custom_attributes` as config fails. Instrument JSON payload is allowed and is not config. |
| **FB-6** | Stop, say so, write nothing for the blocked change. Silent drop, partial apply, or a workaround fails. Apply is one transaction with full rollback. |
| **FB-7** | Schema mutate without `schema:edit` is 403 and no write. L-2 supersedes FB-7 for data tables only. |
| **FB-8** | No chat and no lab-analysis assistant. |
| **FB-9** | `lists` and `list_entries` stay off Schema. Dropdown values go through the list API. |
| **FB-10** | No lab input means no LLM call and a clear error. |
| **FB-11** | No DELETE on samples, containers, entries, users, or config rows. Removal is a status flag or container amount → 0, and both need the L-1 second confirm. |

**Provisional, not scored as a Marc lock.** At `47b3a52`, SPEC §4 and §10 say the proposal keeps every row and shows each stop, and apply writes nothing while any included row is stopped (Rolf 2026-10-07, Marc may overrule). At `686f926` the same section said not to continue into later steps. The design file on `47b3a52` still says the run does not continue after a gap. This script does not pick one. PRD §10 leaves the blood → DNA path versus ELN and parser writes unfrozen: respect the path, and do not assign those routes to the agent.
