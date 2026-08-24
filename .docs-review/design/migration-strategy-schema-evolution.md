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

## 2. High-Level Migration Phases (Focused MVP)

**MVP Focus (per CEO recommendation):**
- Prioritize adding list-backed columns and simple scalars to existing high-value tables (Samples and Experiments first).
- Deliver clean hard cutover from `custom_attributes` on these entities.
- Ensure new fields appear automatically in Entries and Processes.
- Defer "add table" capability.

### Phase 0 — Foundation
- FieldDefinition model + focused admin UI (list-backed + simple scalars).
- Safe migration generation and excellent migration UX (dry-run, impact preview, communication).
- Form/search integration for Entries and Processes.
- Basic backfill + validation tooling.

### Phase 1 — High-ROI Entities
- Add list-backed (e.g. `specimen_biotype`) and simple scalar fields on Samples and Experiments.
- Hard cutover from `custom_attributes` on these entities.
- Full integration into Entries and Processes.

### Phase 2 — Other Core Entities + Cleanup
- Extend to Projects, Batches, Results, etc.
- Remove legacy `custom_attributes` paths.
- Clean documentation and tests.

"Add table" and advanced capabilities remain out of scope for the initial release.

## 3. Data Migration Approach (Hard Cutover Model)

### 3.1 General Pattern for Moving Data Out of JSONB
1. **Add new storage** (real columns or dedicated `field_values` table) via migration.
2. **Backfill** existing data from `custom_attributes` JSONB into the new storage.
3. **Dual-read period** (short): code reads from new storage with fallback to JSONB.
4. **Cutover**: stop writing to old JSONB for this field, enforce reads from new storage.
5. **Cleanup**: drop the old data (after validation and backup).

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

- Detailed rollback playbook for a hard cutover.
- How template-scoped FieldDefinitions interact with global ones during migration.
- Whether we need a "schema version" per Process or Template during the transition.

**Storage model decision (2026-06-30):**

- **Top-level fields** on core entities (e.g. `specimen_biotype` on samples): Add column **directly** to the table (FK for lists, appropriate type otherwise).
- **Variable columns inside custom Entries** (sample data entries / experiment detail entries): Dedicated `entry_field_values` table (typed columns for value_text / value_number / value_list_entry_id, etc.).
- JSONB remains only for OOB unstructured data.
- This will be the basis for the hard cutover migrations.

## 8. Concrete Migration Strategy Example: Hard Cutover for specimen_biotype (Path 1 - focused MVP)

## 8. Concrete Migration Strategy Example: Hard Cutover for specimen_biotype (Path 1 - focused MVP)

**Scenario (from user story US-1):** Move "specimen_biotype" from legacy `custom_attributes` JSONB on Sample to a proper list-backed FieldDefinition + direct column (`specimen_biotype_id`).

**Guiding rules:**
- Hard cutover in one release (migrate + backfill + flip code).
- No long dual storage period.
- Top-level list/scalar fields use direct columns (Path 1).
- See deprecation plan comments in sample.py and experiment.py.
- Related: user-stories/schema-modification.md

**Prerequisites**
- List "specimen_biotypes" (or equivalent) with ListEntry rows exists.
- FieldDefinition created for the field (entity_type='sample', data_type='list', source_list_id=..., column_name='specimen_biotype_id', is_materialized_column=true).

### 1. Add the column (Alembic migration)
```python
def upgrade():
    op.add_column('samples', sa.Column(
        'specimen_biotype_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('list_entries.id'),
        nullable=True
    ))
    op.create_index('ix_samples_specimen_biotype_id', 'samples', ['specimen_biotype_id'])

def downgrade():
    op.drop_index('ix_samples_specimen_biotype_id', table_name='samples')
    op.drop_column('samples', 'specimen_biotype_id')
```

### 2. Backfill (batched, safe, with inline validation)
```python
def backfill_specimen_biotype(db, list_id):
    batch_size = 500
    updated = 0
    while True:
        batch = (db.query(Sample)
                   .filter(Sample.specimen_biotype_id.is_(None))
                   .filter(Sample.custom_attributes['specimen_biotype'].astext.isnot(None))
                   .limit(batch_size).all())
        if not batch: break
        for s in batch:
            val = s.custom_attributes.get('specimen_biotype')
            if val:
                le = db.query(ListEntry).filter(
                    ListEntry.list_id == list_id, ListEntry.name == val
                ).first()
                if le:
                    s.specimen_biotype_id = le.id
                    updated += 1
        db.commit()
    # Validation
    pending = db.execute(text(
        "SELECT COUNT(*) FROM samples WHERE custom_attributes->>'specimen_biotype' IS NOT NULL AND specimen_biotype_id IS NULL"
    )).scalar()
    if pending:
        raise RuntimeError(f"Backfill incomplete: {pending} rows")
    print(f"Backfilled {updated}")
```

### 3. Validation checklist (before cutover is "done")
- Before/after counts and value equality sampling.
- FK integrity + no orphan ids.
- RLS policies still enforce correctly on the new column.
- API + UI forms, Entry rendering, ProcessSample flows all use new path.
- Tests pass, including any that create experiments/entries.

### 4. Code flip (deployed together with the migration + backfill)
- Model: specimen_biotype_id + relationship already added to Sample; entries relationship added to Experiment.
- Change reads/writes to use the new attribute / relationship.
- Entry templates can now declare the field via FieldDefinition for sample_data entries.
- Deprecate (or delete) references to the old custom_attributes key for this field.
- Update any Process / sample execution code that needs the value.

### 5. Post-cutover (follow up)
- Strip the key from custom_attributes JSONB for cleaned rows (optional one-off UPDATE).
- Remove legacy code paths.
- FieldDefinition is now authoritative.

**Rollback (prepare this in advance)**
- Snapshot samples table (or custom_attributes) before the migration.
- On failure: code revert + `alembic downgrade` + optional script to copy values back into custom_attributes from the column (or restore snapshot).
- Communicate status; re-cut when fixed.

The same pattern (FieldDefinition + migration + backfill + flip + validation + rollback) applies for other top-level scalars and for columns inside EntryFieldValue for variable per-template entry fields.

See also the full design in .docs/design/schema-evolution.md and requirements.

---

**Related Documents**
- .docs/design/jsonb-usage-analysis.md (Recommended Refactor Order)
- .docs/requirements/schema-evolution.md
- .docs/design/schema-evolution.md
- .docs/user-stories/schema-modification.md
- .docs/manuals/processes.md
- .docs/manuals/experiments.md

       # Optional: add a comment or temporary column for safety
   ```

3. **Backfill script (run as part of migration or pre-deploy job)**
   ```python
   # Pseudocode for a safe, batched backfill
   def backfill_specimen_biotype():
       # Snapshot before
       # ...

       batch_size = 1000
       offset = 0
       while True:
           samples = db.query(Sample).filter(
               Sample.custom_attributes['specimen_biotype'].astext != None
           ).offset(offset).limit(batch_size).all()

           if not samples:
               break

           for s in samples:
               old_value = s.custom_attributes.get('specimen_biotype')
               if old_value:
                   list_entry = db.query(ListEntry).filter(
                       ListEntry.list_id == specimen_biotypes_list.id,
                       ListEntry.name == old_value
                   ).first()
                   if list_entry:
                       s.specimen_biotype_id = list_entry.id
                       # Optionally remove from JSONB here or after
                       # del s.custom_attributes['specimen_biotype']  # or mark

           db.commit()
           offset += batch_size
           # Progress logging, etc.

       # Validation
       # - Count of non-null before vs after
       # - Spot check random samples
       # - Ensure no invalid list_entry_ids
   ```

4. **Code changes (in the same release / hard cutover)**
   - Update Sample model (as sketched): add the real `specimen_biotype_id` column and relationship. Deprecate access via custom_attributes.
   - Update all read sites:
     - Old: `s.custom_attributes.get('specimen_biotype')`
     - New: `s.specimen_biotype.name if s.specimen_biotype else None`
   - Update write sites / forms: now use the FieldDefinition-driven form field.
   - In Entries: the new field becomes available for sample_data entries (template can reference the FieldDefinition).
   - In Processes: visible via ProcessSample + per-experiment data.
   - Remove or guard old custom_attributes access for this key.

5. **Post-cutover cleanup (follow-up migration)**
   - Remove the key from any remaining custom_attributes JSONB (or leave historical data).
   - Optionally drop support for the key in custom_attributes entirely.
   - Update any reports/queries that assumed the JSONB key.

6. **Validation & Testing**
   - Before/after row counts and value sampling.
   - Full test suite for the field in forms, Entries, Processes, search.
   - RLS tests: ensure the new column respects client/project isolation.
   - Dry-run the backfill on a staging copy of production data.

**Rollback plan (critical for hard cutover):**
- Pre-migration snapshot of the samples table (or at least the custom_attributes column).
- If issues: restore snapshot + revert code to read from custom_attributes.
- Alternative: have a "re-populate JSONB from new column" script as a quick fallback.
- Feature flag the new code paths if possible during the cutover window.

**Integration notes for this example:**
- Once the column exists, it can be pulled into sample_data Entries (via the template's FieldDefinitions).
- In a Process, samples carrying the biotype via ProcessSample will have the value available in the relevant experiment step's entries.

This pattern generalizes to other simple scalars and list-backed fields.
```

**Notes on this example:**
- It demonstrates the hard cutover: backfill + code flip in one go.
- Data from JSONB moves to the proper typed column.
- No long dual storage.
- The FieldDefinition provides the metadata (list source, validation, UI) going forward.
- Ties directly into Entries (columns defined in template) and Processes.

## 8. Concrete Migration Example: Hard Cutover for specimen_biotype

**Scenario (from user story):** Move "specimen_biotype" from legacy `custom_attributes` JSONB on Sample to a proper list-backed FieldDefinition + direct column (`specimen_biotype_id`).

**Assumptions:**
- We have (or create) a List "specimen_biotypes" with entries (name = the biotype value).
- Some existing samples have `custom_attributes['specimen_biotype'] = 'B-cell'` (string value matching a list entry name).
- Hard cutover: one deployment that does the migration + code flip. No long dual-write.

**Step-by-step:**

1. **Define the FieldDefinition (one-time, via admin UI or script)**
   ```python
   fd = FieldDefinition(
       entity_type='sample',
       name='specimen_biotype',
       display_name='Specimen Biotype',
       data_type='list',
       source_list_id=specimen_biotypes_list.id,
       is_required=False,
       is_materialized_column=True,
       column_name='specimen_biotype_id',
       # validation_rules, ui_hints etc.
   )
   db.add(fd)
   # This can be done before the migration.
   ```

2. **Migration (Alembic) - adds the column**
   ```python
   def upgrade():
       op.add_column('samples', sa.Column(
           'specimen_biotype_id',
           postgresql.UUID(as_uuid=True),
           sa.ForeignKey('list_entries.id'),
           nullable=True
       ))
       op.create_index('ix_samples_specimen_biotype_id', 'samples', ['specimen_biotype_id'])

       # Optional: add a comment or temporary column for safety
   ```

3. **Backfill script (run as part of migration or pre-deploy job)**
   ```python
   # Pseudocode for a safe, batched backfill
   def backfill_specimen_biotype():
       # Snapshot before
       # ...

       batch_size = 1000
       offset = 0
       while True:
           samples = db.query(Sample).filter(
               Sample.custom_attributes['specimen_biotype'].astext != None
           ).offset(offset).limit(batch_size).all()

           if not samples:
               break

           for s in samples:
               old_value = s.custom_attributes.get('specimen_biotype')
               if old_value:
                   list_entry = db.query(ListEntry).filter(
                       ListEntry.list_id == specimen_biotypes_list.id,
                       ListEntry.name == old_value
                   ).first()
                   if list_entry:
                       s.specimen_biotype_id = list_entry.id
                       # Optionally remove from JSONB here or after
                       # del s.custom_attributes['specimen_biotype']  # or mark

           db.commit()
           offset += batch_size
           # Progress logging, etc.

       # Validation
       # - Count of non-null before vs after
       # - Spot check random samples
       # - Ensure no invalid list_entry_ids
   ```

4. **Code changes (in the same release / hard cutover)**
   - Update Sample model (as sketched): add the real `specimen_biotype_id` column and relationship. Deprecate access via custom_attributes.
   - Update all read sites:
     - Old: `s.custom_attributes.get('specimen_biotype')`
     - New: `s.specimen_biotype.name if s.specimen_biotype else None`
   - Update write sites / forms: now use the FieldDefinition-driven form field.
   - In Entries: the new field becomes available for sample_data entries (template can reference the FieldDefinition).
   - In Processes: visible via ProcessSample + per-experiment data.
   - Remove or guard old custom_attributes access for this key.

5. **Post-cutover cleanup (follow-up migration)**
   - Remove the key from any remaining custom_attributes JSONB (or leave historical data).
   - Optionally drop support for the key in custom_attributes entirely.
   - Update any reports/queries that assumed the JSONB key.

6. **Validation & Testing**
   - Before/after row counts and value sampling.
   - Full test suite for the field in forms, Entries, Processes, search.
   - RLS tests: ensure the new column respects client/project isolation.
   - Dry-run the backfill on a staging copy of production data.

**Rollback plan (critical for hard cutover):**
- Pre-migration snapshot of the samples table (or at least the custom_attributes column).
- If issues: restore snapshot + revert code to read from custom_attributes.
- Alternative: have a "re-populate JSONB from new column" script as a quick fallback.
- Feature flag the new code paths if possible during the cutover window.

**Integration notes for this example:**
- Once the column exists, it can be pulled into sample_data Entries (via the template's FieldDefinitions).
- In a Process, samples carrying the biotype via ProcessSample will have the value available in the relevant experiment step's entries.

The same pattern applies to other top-level fields and to variable columns stored in entry_field_values.

See the FieldDefinition and Entry models for the supporting structures, and the deprecation comments in sample.py / experiment.py for the custom_attributes phase-out plan.