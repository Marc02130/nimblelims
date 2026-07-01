# Migration Strategy: Schema Evolution (Custom Attributes / JSONB to FieldDefinition)

**Date:** 2026-06-30  
**Branch:** refactor/jsonb  
**Status:** Initial draft — to be refined during design and implementation

## 1. Overview and Guiding Principles

This document outlines the migration strategy for moving from the current extensibility model (primarily `custom_attributes` JSONB + loose `content` / `processing_conditions` JSONB) to the new model based on **FieldDefinition** + properly typed storage.

**Key decisions driving this strategy:**
- We are using **FieldDefinition** as the single mechanism for modeled extensibility.
- We are retiring "custom attributes" as an extensibility pattern.
- **JSONB is restricted to Out-Of-Box (OOB) unstructured data only.** There will be no UI for users/admins to define new unstructured fields. JSONB remains appropriate for things like `template_definition`, `row_data`, `parser_config`, `worklist_config`, `runtime_state`, and `billing_info`.
- We will perform a **hard cutover** (not a long-running dual-write / dual-storage period).
- Processes use `ProcessSample` to track samples assigned at the process level.
- Experiments use a richer **Entries** model whose columns are driven by FieldDefinitions (where appropriate).

**Core principles:**
- Safety first — no data loss, no broken workflows during transition.
- Audit everything.
- Minimize long-term technical debt.
- Leverage existing infrastructure where possible (Lists system for list-backed fields, Alembic for migrations, RLS policies).
- Prioritize high-value, high-usage entities first.

## 2. High-Level Migration Phases

### Phase 0 — Foundation (Pre-Migration)
- Implement the `FieldDefinition` model and supporting tables.
- Build admin UI for defining FieldDefinitions (with support for list-backed fields using `list_entries`).
- Implement safe migration generation (Alembic fragments or scripts).
- Add basic form generation and search/filter support for new fields.
- Define and implement `ProcessSample` model.
- Establish the Entries model inside Experiments/Processes.
- Create migration tooling (backfill jobs, validation, dry-run capabilities).
- Build impact analysis tooling (what will be affected by a given change?).

### Phase 1 — Core Schema Registry + New Fields
- Enable creation of new fields via FieldDefinition (e.g. adding `specimen_biotype` as a list-backed column to `samples`).
- Support adding simple columns to existing tables.
- Begin using FieldDefinitions for new work in Experiments (columns inside custom Entries) and Processes.
- Deprecate direct writes to `custom_attributes` for new features.

### Phase 2 — Per-Entity Hard Cutovers (High-Impact Entities First)
Target order (subject to refinement):
1. **Samples** (very high usage, frequently extended, ties into Processes/Entries)
2. **Projects** and **Batches**
3. **Experiments** and **ExperimentSampleExecution** (move relevant data out of `processing_conditions` and `custom_attributes`)
4. **Results**, **Tests**, **Analyses**, etc.

For each entity:
- Define the set of FieldDefinitions that will replace the old custom attributes.
- Generate and apply migration(s) to add real columns (or typed value tables).
- Write one-time data migration scripts to move data from `custom_attributes` JSONB into the new FieldValue storage.
- Update all read paths to prefer the new structured storage.
- Hard cutover: remove or restrict the old JSONB path for that entity.
- Update UI, APIs, reports, and workflows.

### Phase 3 — Deprecation and Cleanup
- Remove or archive remaining `custom_attributes` columns after all major entities are migrated.
- Clean up dual-read code paths.
- Remove legacy `custom_attributes_config` usage where replaced.
- Update all documentation, tests, and example data.

### Phase 4 — Advanced Capabilities
- Full support for adding new tables via the schema UI (with appropriate guardrails).
- Deeper integration of FieldDefinitions with template-driven Entries.
- More sophisticated validation, computed fields, or cross-entity rules (if needed).

## 3. Data Migration Approach (Hard Cutover Model)

### 3.1 General Pattern for Moving Data Out of JSONB
1. **Add new storage** (real columns or dedicated `field_values` table) via migration.
2. **Backfill** existing data from `custom_attributes` JSONB into the new storage.
3. **Dual-read period** (short): code reads from new storage with fallback to JSONB.
4. **Cutover**: stop writing to old JSONB for this field, enforce reads from new storage.
5. **Cleanup**: drop or archive the old data (after validation and backup).

For a **hard cutover** we compress steps 3–5 into a single deployment window where possible:
- Run the backfill as part of the deployment or as a prerequisite job.
- Flip all reads/writes in the same release.
- Have a rollback plan that can restore from the old JSONB if needed.

### 3.2 Example: Adding `specimen_biotype` (List Column) to Samples
1. Create the list "specimen_biotypes" (if it doesn't exist) via the Lists admin UI.
2. Define a FieldDefinition for `specimen_biotype` (data_type = list, source_list_id = ...).
3. Generate migration: `ALTER TABLE samples ADD COLUMN specimen_biotype_id UUID REFERENCES list_entries(id);` + index.
4. Backfill: for any existing samples that had a matching value in `custom_attributes`, set the new FK (script can use list entry name matching or manual mapping).
5. Update the Sample model, schemas, forms, filters, and APIs to use the new column.
6. Hard cutover: stop reading/writing that key from `custom_attributes` for the `specimen_biotype` concept.
7. (Optional later) Remove the key from any remaining JSONB or leave historical noise.

### 3.3 Removing a Column
1. Mark the FieldDefinition (or legacy custom attribute) as deprecated.
2. Run impact analysis.
3. Optionally migrate data to an archive JSONB blob or archive table.
4. Generate migration to drop the column (or set it aside).
5. Update all code/UI paths that referenced it.
6. Hard remove in a subsequent release after validation.

### 3.4 Adding a New Table
1. Define the new table and its columns via FieldDefinitions in the schema admin.
2. Generate full migration (CREATE TABLE + constraints + indexes + RLS policy skeleton).
3. Generate basic model scaffolding (or use dynamic access).
4. Generate initial UI (list + detail forms).
5. Backfill or seed any initial data if required.
6. Wire integration points (e.g., linking from Sample, use in Processes) manually or via configuration.

## 4. Tooling and Automation Needs

- **Schema change planner** — preview impact, generate migration fragments, estimate data volume and backfill time.
- **Backfill framework** — safe, batched, resumable jobs with progress tracking and validation.
- **Validation suite** — before/after data integrity checks, RLS regression tests.
- **Rollback tooling** — ability to restore previous state from archived JSONB or previous schema version.
- **Audit + change log** — every FieldDefinition change and every bulk data migration must be recorded.

## 5. Risks and Mitigations

| Risk                              | Mitigation |
|-----------------------------------|----------|
| Data loss during hard cutover     | Thorough backfill + validation jobs + pre-cutover data snapshots |
| Performance regression on large tables | Index strategy, phased rollout, query plan review |
| Breaking existing reports / exports | Impact analysis step + parallel support period for consumers |
| RLS policy gaps on new columns/tables | Automated policy inheritance + explicit review gate |
| Confusion during transition       | Clear deprecation messages in UI + good documentation |
| Long-running backfills blocking deployments | Asynchronous backfill jobs with status dashboard |

## 6. Interaction with Other Work

- **Processes**: Use `ProcessSample` for process-level assignment. Per-experiment detail lives in `ExperimentSampleExecution`. FieldDefinitions feed into both.
- **Entries (Experiments/Processes)**: Columns inside custom Sample and Experiment detail entries are defined and migrated via the same FieldDefinition system.
- **Existing JSONB that stays**: `row_data`, `template_definition`, etc. — these are out of scope for this migration except for any normalization that makes sense independently.

## 7. Open Questions & Next Steps

- Exact storage model for FieldValue (dedicated `field_values` table vs. adding columns directly to entity tables).
- Detailed rollback playbook for a hard cutover.
- How template-scoped FieldDefinitions interact with global ones during migration.
- Whether we need a "schema version" per Process or Template during the transition.

---

**Related Documents**
- `.docs/jsonb-usage-analysis.md` (with recommended refactor order)
- `.docs/requirements/schema-evolution.md`
- `.docs/design/schema-evolution.md`
- `.docs/design-review/schema-evolution.md`
- `.docs/user-stories/schema-modification.md`
- `.docs/processes.md`
- `.docs/experiments.md`

This is a starting point. It will be expanded with concrete migration scripts, checklists, and timelines as implementation progresses.