# Schema changes: data-parsers-lims-runs

**Feature / cycle:** Data parsers, instruments/CRO sources, LimsRun lineage  
**Phases covered:** **P0 + P1** (P2 AI = no schema required unless setup-file persistence chosen)  
**Status:** Schema **verified** by architecture (2026-07-18); full architecture review still in progress  
**Alembic revisions:** _(none yet)_  
**Requirements:** [../requirements/data-parsers-lims-runs.md](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [../tech-sketch/data-parsers-lims-runs.md](../tech-sketch/data-parsers-lims-runs.md)  
**Architecture review:** [../architecture-review/data-parsers-lims-runs.md](../architecture-review/data-parsers-lims-runs.md)  
**Open questions:** [../open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md)

> **This is the authoritative schema delta for this cycle.** Architecture review of “what changes in the DB” should use **this file**, not a full read of the packet.

## 1. Summary

Add light **instrument** and **CRO source** catalogs; re-scope **instrument_parsers** to **analysis × instrument|CRO only**; **remove `experiment_template_id`** from parsers (no template-linked parsers); add **lims_runs** FKs for instrument, CRO source, and parser used. No change to `results` / promote schema (already shipped).

## 2. Delta (authoritative list)

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| **`instruments`** | Lab data-source catalog (not full asset CMMS) | `id`, `name`, `vendor` NULL, `model` NULL, `description` NULL, `active`, audit cols |
| **`cro_sources`** | External/CRO export-source catalog | `id`, `name`, `description` NULL, `client_id` NULL → `clients`, `active`, audit cols |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| **`instrument_parsers`** | **DROP `experiment_template_id`** (column + FK + related indexes) | **Decided:** parsers are not template-scoped. Pre-migration data handling: §4 |
| **`instrument_parsers`** | ADD `analysis_id` UUID **NOT NULL** → `analyses(id)` | Required for every parser |
| **`instrument_parsers`** | ADD `instrument_id` UUID NULL → `instruments(id)` | Lab path |
| **`instrument_parsers`** | ADD `cro_source_id` UUID NULL → `cro_sources(id)` | CRO path |
| **`instrument_parsers`** | ADD `is_default` BOOLEAN NOT NULL DEFAULT false | Default among siblings |
| **`instrument_parsers`** | ADD `active` BOOLEAN NOT NULL DEFAULT true | Soft deactivate |
| **`instrument_parsers`** | `parser_config` JSONB | **No structural change** — content must match ParserConfig v1 (app validation) |
| **`lims_runs`** | ADD `instrument_id` UUID NULL → `instruments` ON DELETE SET NULL | XOR with cro |
| **`lims_runs`** | ADD `cro_source_id` UUID NULL → `cro_sources` ON DELETE SET NULL | XOR with instrument |
| **`lims_runs`** | ADD `parser_id` UUID NULL → `instrument_parsers` ON DELETE SET NULL | Stored default/override |

`lims_runs.analysis_id` — **already exists** (run-results); no change.  
`lims_runs.experiment_template_id` — **unchanged** (protocol/lifecycle still on the run).

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| **`instrument_parsers` source CHECK** | Exactly one of `instrument_id` / `cro_source_id` is non-null | Lab XOR CRO scope |
| **`instrument_parsers` analysis** | `analysis_id` NOT NULL | Every parser belongs to an analysis |
| **`lims_runs` source CHECK** | NOT (instrument_id AND cro_source_id both non-null) | One source type per run |
| **`uq_parser_default_instrument`** | UNIQUE (`analysis_id`, `instrument_id`) WHERE `is_default AND active AND instrument_id IS NOT NULL` | One default per analysis×instrument |
| **`uq_parser_default_cro`** | UNIQUE (`analysis_id`, `cro_source_id`) WHERE `is_default AND active AND cro_source_id IS NOT NULL` | One default per analysis×CRO |
| Drop indexes/FKs | Any index/FK solely on `instrument_parsers.experiment_template_id` | With column drop |
| Indexes on FKs | `analysis_id`, `instrument_id`, `cro_source_id`, `parser_id` as needed | Lookup performance |

Exact CHECK SQL may be refined at implement time; intent is fixed.

### 2.4 Enums / types

| Type | Change |
|------|--------|
| — | **None** this cycle |

### 2.5 Optional / not MVP (P2–P3 — do not implement in P0/P1 unless decided)

| Object | Notes |
|--------|-------|
| **`parser_setup_files`** | Only if product chooses persistent examples/tests (open #10a). Default P1: ephemeral upload for dry-run. |
| Snapshot column on `lims_runs` (e.g. `parser_config_snapshot` JSONB) | Open Q5 — lean defer |

## 3. RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| `instruments` | **TBD implement** | Lab-config tables: typically all lab users with config:edit can manage; readable by lab roles that import. **Not** client-user writable. Confirm with security. |
| `cro_sources` | **TBD implement** | Same as instruments |
| `instrument_parsers` | **Review existing** + extend for new rows | Ensure client roles cannot mutate parsers |
| `lims_runs` new FKs | No new table | Existing lims_runs RLS continues; FKs do not expand client write surface |

Architecture + security must approve RLS approach before merge; document final policies here when implemented.

## 4. Data migration / backfill

- [x] **No backfill required** for new catalogs (empty at start)  
- [ ] **Existing `instrument_parsers` rows** (template-scoped): before DROP `experiment_template_id`:
  1. **Preferred:** migrate each row to analysis×instrument|CRO if mapping is known, **or**  
  2. **Acceptable for early envs:** **delete** template-only parser rows (dev/UAT with disposable data) after confirming no critical production dependence, **or**  
  3. One-time script: export configs for re-entry via new admin UI  
- [x] **No dual-write** to template-scoped parsers after cutover  
- [x] **Import** no longer resolves parser via `experiment_template_id`  

**SOP parse impact (app, not only DB):** stop creating parsers with template FK; either create analysis×source parsers when context exists, or create template protocol only and leave parser setup to the new flow (product choice at implement).

## 5. Rollback

- Forward migrations preferred.  
- Re-adding `experiment_template_id` after drop is painful if data was deleted—prefer staging validation.  
- Soft-delete via `active=false` preferred over DROP of catalog/parser rows in production.

## 6. Explicitly out of scope (this cycle)

Do **not** change as part of data-parsers P0/P1:

| Area | Why |
|------|-----|
| `results`, `tests`, promote columns | Shipped in run-results |
| `analyte_aliases` | Shipped |
| Field Management / dynamic schema product (`design/schema-evolution.md`) | Separate workstream |
| `experiment_templates` structure | Unchanged (still used for protocol/lifecycle on the **run**) |
| Parser ↔ template link | **Removed** — not “nullable legacy” |
| Executable parser storage | Forbidden |

## 7. Open schema blockers

| ID | Topic | Blocks |
|----|--------|--------|
| Q2 | Instrument grain (name + vendor/model sufficient?) | P0 column set |
| Q7 | Lab-global vs client-scoped catalogs | RLS design |
| Q9 | Keep table name `instrument_parsers` | Naming only |
| #10a | Persist setup files table? | Optional table |
| Q5 | parser_config snapshot on run | P3 |

Product: CEO locked analysis×instrument/CRO scope (Decision #11). Architecture to approve this delta list.

## 8. Implementation checklist

- [ ] Migration(s) match this doc  
- [ ] SQLAlchemy models match migration  
- [ ] RLS policies documented and tested  
- [ ] ParserConfig v1 validated in app (not a DB constraint)  
- [ ] This file updated with Alembic revision id(s)  
- [ ] Import resolution uses `lims_runs.parser_id`  

## 9. App-level contract (not DB, but schema-adjacent)

Stored in `instrument_parsers.parser_config` JSONB; **validated by Pydantic**, not CHECK JSON:

- `schema_version`, `delimiter`, `encoding`, `skip_rows`, `header_row`, `columns[]`, `well_col`, `sample_col`  
- See tech sketch §5 and open-questions Decision #1  

DB does not enforce JSON shape beyond JSONB type.
