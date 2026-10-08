# Configuring-agent slice (step 1 input)

Lab input for one configuring-agent run against a fresh seed database. This folder is testdata. It is not an SOP pack and it does not contain SOP body text.

No open docs pull request was found on 2026-10-08 that folds Wilhelmina's newer locks. This packet follows `main` (configuring-agent PRD/spec/design from PR 143, and the provisional experiment entries/event rules from PR 146) plus the Brief approved 2026-10-07 and the SOP owner's note of 2026-10-08. On `main`, confirm-before-apply is still written as a preference. The fail bars below treat the Brief as the rule for this slice.

## How to load the database slice

The slice is opt-in. It is not an Alembic revision, so `alembic upgrade` and a dogfood database stay unchanged until someone runs the loader.

```bash
cd backend
# MIGRATE_DATABASE_URL = migrator owner, same as create_uat_users.py
python seed_config_agent_slice.py            # prints usage, writes nothing
python seed_config_agent_slice.py --apply    # one fresh database
python seed_config_agent_slice.py --check    # re-read rows and parse the LAL CSVs
```

A second `--apply` refuses and writes nothing. Passwords follow the 0058 pattern (bcrypt, short dev password, `must_change_password` false). They are not printed here.

| Username | Role | Why |
|----------|------|-----|
| `alice-tech` | Lab Technician | Existing 0058 user. Not modified. mAb PK and Project Alpha only. Same-client deny on CAR-T. |
| `results-reviewer` | Lab Manager | Reviewer for enterer vs reviewer. Holds `result:review`. Also holds `result:enter`, because no existing role is review-only. Not Administrator. |
| `schema-editor` | Schema Editor | No existing non-admin user holds `schema:edit` (0080 grants it to Administrator only). This role holds `schema:edit` and `config:edit` and is not Administrator. |

`admin` and `lab-tech` are not touched.

## Samples the loader adds

Both names come from the active sample template `{PROJECT}-{SEQ}` (padding 2) on existing project `Project Alpha`.

| Name | Sample type | Matrix | Parent | Vessel | Amount |
|------|-------------|--------|--------|--------|--------|
| `Project Alpha-01` | Blood | Whole Blood | | `NBIO-EDTA-2310-001`, existing type `K2EDTA Tube (5mL)` | 600 µL |
| `Project Alpha-02` | DNA | Genomic DNA | `Project Alpha-01` | `NBIO-DNA-2310-001`, existing type `Microcentrifuge Tube (1.5mL)` | 400 µL |

`Whole Blood` and `Genomic DNA` are matrix list entries from 0058. They are not sample types. The 0068 transition is Blood × aliquot → DNA.

The daughter is created by `AliquotPlanService.execute` (`aliquot_by_target_amount`, destination type DNA) so the 0068 row is the gate. Execute copies the parent matrix and moves the same amount (600 µL) onto a product name `{parent}-ALQ-{hex}`. The loader then sets matrix `Genomic DNA`, renames the daughter with the sample template, sets the eluate to 400 µL, and restores the blood vessel to 600 µL. The product path cannot express a 600 µL input and a 400 µL eluate in one transfer. A scaffolding experiment `config-agent-slice-blood-dna` remains so the execute row is visible. It is not a KingFisher process and not a Qubit run.

Receive is atomic receive: status `Available for Testing`, no tests. The blood vessel amount is set after receive because receive leaves contents amount null, and execute refuses a null amount.

## Files

| File | What it is |
|------|------------|
| `sops.md` | CMDL-SOP2310 then SOP 22975. Number, public URL, ordered steps, matrices, field-name hints. |
| `manifest.csv` | Catalog rows. Only `Project Alpha-01` and `Project Alpha-02` are `sop_path=yes`. |
| `personnel.csv` | `alice-tech`, `schema-editor`, `results-reviewer` only. |
| `lal-parser-config.json` | `InstrumentDataService` config for the kinetic LAL CSVs. |
| `../instrument-exports/lal-kinetic-chromogenic/` | The 10-file LAL pack (8 valid, 2 edge). Referenced, not copied. |

`NBIO-CMPD-001` is the compound id on the NCI-60 CSV (A549). It is not a `samples` row. The manifest says so.

The depleted row is `mAb-2301-PK-T0`. Amount is 0. Status is `Testing Complete`, the closest existing sample status. `Spent`, `Discarded`, and `Quarantine` are not on the Sample Status list. The live 0059 contents row is still 50 µL. This seed does not change it. Nothing is deleted.

## Configure-first order

What the configuring agent should set up, in order. Existing rows are named. Gaps are not seeded.

1. Client, project, and roles. Client `NovaBio Therapeutics` and project `Project Alpha` exist. Bench is role `Lab Technician` (`result:enter`, no `result:review`). Review is role `Lab Manager` (`result:review`, and also `result:enter`). An administrator who holds `schema:edit` already exists: user `admin`, role `Administrator`. The slice also has `schema-editor` so a non-admin caller can be allowed a schema change that is refused for Alice. The agent does not grant itself `schema:edit`.
2. Sample types and matrices. `Blood` and `DNA` exist (0068 allows Blood × aliquot → DNA). Matrices `Whole Blood` and `Genomic DNA` exist. The link is `samples.parent_sample_id` (1:N on the child).
3. Container types. Intake vessel type `K2EDTA Tube (5mL)` exists (1×1, preservative K2EDTA). There is no container type whose name is a sample-numbered DNA tube. The eluate in this seed uses existing `Microcentrifuge Tube (1.5mL)`. A separately named DNA-tube type is a gap for the agent, through the container-type API, if the proposal needs that name. Barcode is `containers.name`. Sample ID is `samples.name`. Each vessel holds `contents.amount` (and `containers.amount`).
4. Accession template. Active sample template `{PROJECT}-{SEQ}` exists. Receive is `POST /samples/receive`: client/project, sample type, barcode, first vessel. Status becomes `Available for Testing`. Non-empty `analysis_ids` is refused. No tests are created at receive. Matrix is not written by receive (the column is nullable). This seed sets matrix after receive so the SOP path has `Whole Blood`.
5. Analyses. No extraction analysis and no Qubit analysis exist. Do not pre-seed them. The agent creates them through the existing analysis APIs if it can. Extraction quantities to capture: 600 µL blood input, up to 24 samples per run, about 400 µL DNA eluate per sample. Qubit fields: concentration (ng/µL), HS or BR kit, sample volume, dilution factor, standards pass/fail. If an API cannot express one of those, the run stops with the gap. It does not use Custom Fields or JSONB-as-fields.
6. Statuses. `Received`, `Available for Testing` exist. `Quarantine` does not. `Spent` does not. A vessel at amount 0 stays in the database. The closest existing status used on the depleted manifest row is `Testing Complete`. Creating `Spent` (and `Quarantine` if the proposal needs it) is the agent's job, through the list API. Lists stay off Schema.

## Expected agent behavior (fail bars)

- Every write is confirm-before-apply. Propose, then a person accepts or skips, then apply.
- The agent may change only what the acting user can change. The same schema change applies for `schema-editor` and is refused for `alice-tech` (`Permission 'schema:edit' required`, no write). The user is responsible for the apply.
- No deletes. A used-up vessel is a status flag or contents amount 0. Amounts never go below 0.
- Config is real DDL or catalog rows the APIs already allow: allow-listed table or column, role layout, role privileges, 1:N foreign key, 1:1 unique foreign key, M:N junction behind the scenes. `POST /v1/schema/relations` still refuses `many_to_many` and does not create a junction. The run stops and says so.
- Not Custom Fields. Not JSONB-as-fields. JSONB is allowed only as an instrument or result payload.
- A change the APIs cannot express stops with a clear error and writes nothing for that change.
- A missing LLM key names that provider's key (`OPENAI_API_KEY`, `XAI_API_KEY`, or `ANTHROPIC_API_KEY`). No vendor fallback. No config write before the key check.

## Edge cases (no new result fixtures)

- A DNA concentration below an example minimum is flagged for re-extraction. Example cutoff: 10 ng/µL. That number is example data. The SOP says low samples are re-extracted manually and does not set this cutoff.
- A failed Qubit standards check blocks or flags the run.
- Blood amount decrements after extraction, never goes below 0, and is Spent at 0. `Spent` is not seeded. Until it exists, amount 0 is the expression, and the sample and vessel remain.

## Instrument payload

Kinetic LAL, 10 CSVs under `UAT_Scripts/instrument-exports/lal-kinetic-chromogenic/` (PR 48 / PR 49): 8 valid and 2 edge, covering `CAR-T-Batch-001` and `Plasmid-Lot-2025-001`. `lal-parser-config.json` is the `InstrumentDataService` column map. `dilution` is a string because the pack writes ratios such as `1:10`. Empty numeric cells stay null. Parsed rows are a JSON payload (`row_data`) for the LIMS-run import path. They are not a schema write. This packet does not add a parser row and does not post results.

`--check` parses all 10 files with that config and checks manifest names against the database.
