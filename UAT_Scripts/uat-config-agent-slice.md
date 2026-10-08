# UAT: configuring-agent slice input

**Stem:** config-agent-slice  
**Date:** 2026-10-08  
**Scope:** Opt-in seed plus the input packet. This does not run the configuring agent and does not need an LLM key.

## Setup

1. Migrate a fresh database (`alembic upgrade head` / backend startup).
2. Do not point `MIGRATE_DATABASE_URL` at a dogfood database unless you mean to load the slice there.
3. From `backend`: `python seed_config_agent_slice.py` writes nothing.
4. `python seed_config_agent_slice.py --apply`
5. `python seed_config_agent_slice.py --check`
6. Run `--apply` again. It refuses and does not change rows.

## Acceptance

1. `Project Alpha-01` exists, sample type Blood, matrix Whole Blood, status Available for Testing, one vessel `NBIO-EDTA-2310-001` of type `K2EDTA Tube (5mL)`, contents amount 600 µL.
2. `Project Alpha-02` exists, sample type DNA, matrix Genomic DNA, `parent_sample_id` is `Project Alpha-01`, vessel `NBIO-DNA-2310-001`, contents amount 400 µL. No tests were created at receive.
3. `results-reviewer` is Lab Manager, has `result:review`, and is not Administrator.
4. `schema-editor` is Schema Editor, has `schema:edit` and `config:edit`, and is not Administrator.
5. `alice-tech` is still Lab Technician on Project Alpha and mAb-2301 PK Study only. `admin` and `lab-tech` are unchanged. `mAb-2301-PK-T0` contents amount is still 50 µL.
6. Manifest names other than `NBIO-CMPD-001` resolve to those sample rows. `NBIO-CMPD-001` does not.
7. All 10 kinetic LAL CSVs parse with `UAT_Scripts/config-agent-slice/lal-parser-config.json` (8 valid, 2 edge).

## Fail bars for a later agent run

Recorded in `UAT_Scripts/config-agent-slice/README.md`. Confirm-before-apply. `schema-editor` may apply a schema change Alice cannot. No deletes. No Custom Fields. Missing LLM key is a clear error with no vendor fallback.
