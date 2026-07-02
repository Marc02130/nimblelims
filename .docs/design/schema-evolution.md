# Design: Schema Evolution System

**Date:** 2026-06-30  
**Branch:** refactor/jsonb  
**Status:** Draft for design review

## 1. Goals (Focused MVP)

- Enable controlled, auditable addition of high-value fields to existing entities: primarily list-backed columns (e.g. `specimen_biotype` on Samples) and simple scalars (text, number, date, boolean).
- Perform a clean hard cutover from `custom_attributes` JSONB on key entities (Samples and Experiments first).
- Make it easy for administrators to deprecate or remove fields.
- Ensure new fields automatically appear in Entries (sample data entries / experiment detail entries) and Processes.
- Maintain safety: no runtime schema changes that bypass migrations, RLS, or upgrade paths.
- Integrate with existing mechanisms (Lists system, Alembic, RLS, audit).
- Reduce long-term technical debt while keeping the system simple for early-stage biotech teams.

This design supports the user stories in `.docs/user-stories/schema-modification.md` and addresses gaps identified in the JSONB analysis.

## Glossary (Decided Direction)

- **FieldDefinition**: The canonical term for the metadata definition of an extensible, typed field (scalar or list-backed). This replaces the old "custom attributes" mechanism for deliberate schema extension. All modeled, user-extensible fields go through FieldDefinition.

  **Important distinction (per design direction):**
  - A **lookup table (foreign key)** is good when metadata about the record is needed (richer entity with its own attributes, relationships, etc.).
  - A **list** is used when you just need a value (simple controlled vocabulary from the existing `lists` + `list_entries` system).

- **FieldValue**: The stored value for a FieldDefinition on a concrete record. Lives in a real database column (preferred) or a properly typed mechanism. Not stored in generic JSONB when used for extensibility.

- **Entry**: A richer, composable component that lives inside an Experiment or inside a step of a Process.
  - **Predefined Entries** (Out-Of-Box): Built-in behaviors such as aliquoting, pooling, index assignment, flowcell loading, QC review (pass/fail).
  - **Custom Entries**:
    - Sample data entries: per-sample data tables.
    - Experiment detail entries: experiment-level data.
  - The **columns** inside custom Entries are defined using FieldDefinitions (declared in the template).
  - Relationship: FieldDefinitions are the building blocks (atoms). Entries are higher-level constructs (molecules) that can be built from FieldDefinitions + behavior. A FieldDefinition can also stand alone as a top-level extension on an entity (e.g. adding `specimen_biotype` directly to the Sample table).

- **ProcessSample**: Junction table recording which samples are assigned to a Process (at the process level).

- **JSONB (restricted to OOB only)**: Only for Out-Of-Box (OOB) unstructured or highly variable data. There is **no UI** for administrators to define new unstructured fields.
  - Allowed examples: `template_definition`, `row_data` (raw instrument output), `parser_config`, `worklist_config`, `result` (from SopParseJob), `runtime_state`, `billing_info`.
  - JSONB is **explicitly not used** to extend functionality or carry user-modeled data.

For list-backed fields (e.g. `specimen_biotype`):
- This is a "list" (just a value), not a full lookup table.
- Implemented as a direct column on the target table: `specimen_biotype_id UUID REFERENCES list_entries(id)`.
- The FieldDefinition will have `data_type = 'list'` and reference the appropriate List.

**Custom attributes** as an extensibility pattern is being retired. We are planning a **hard cutover** (not a long dual-write period). Existing `custom_attributes` data will be migrated to FieldValue storage as part of the cutover.

## 2. High-Level Architecture

### 2.1 Core Concepts

- **FieldDefinition**: Metadata for an extensible, typed field. This is the replacement for the old custom attributes mechanism.
  - Can be scoped globally to an entity type or more narrowly to a Template or Process.
  - Properties include: name, display_name, data_type, source_list_id (for list types), required, validation rules, etc.
  - Drives real columns + UI generation.
  - Used for both top-level entity extensions (e.g. adding `specimen_biotype` to Sample) and for defining columns inside custom Entries.

- **SchemaChange** (audit + migration request): Records proposed and applied changes.
  - Type: ADD_COLUMN, DEPRECATE_COLUMN, DROP_COLUMN, ADD_TABLE, etc.
  - Status: proposed, reviewed, applied, rolled_back.
  - Stores before/after definition + impact report.

- **EntityExtension**: Runtime and migration support for the actual columns/tables.

For list-backed fields (e.g., `specimen_biotype`):
- Use existing `list_entries` system. The column will be a `list_entry_id` FK (or nullable reference) with a GIN or B-tree index as appropriate.

### 2.2 Storage Strategy for FieldValue (Focused MVP)

**Yes, the "lists" you are referring to are the existing `lists` + `list_entries` system.**  
This is the right mechanism for list-backed fields (e.g. `specimen_biotype` will be a FK column to `list_entries`, exactly like `sample.matrix`, `sample.qc_type`, `sample.status`, etc.).

**Recommended storage model for MVP:**

- **Top-level extensions on core entities** (Samples, Experiments, etc.):
  - **Add the column directly** to the entity table when the FieldDefinition is activated.
  - Use a controlled Alembic migration.
  - List types: `xxx_id UUID REFERENCES list_entries(id)`.
  - Simple scalars: native types (`TEXT`, `NUMERIC`, `TIMESTAMPTZ`, `BOOLEAN`, etc.).
  - This gives the best performance and is what scientists expect.

- **Columns inside custom Entries** (for now):
  - Use the same direct-column approach where the parent table allows it.
  - For highly variable per-template data, we can initially lean on FieldDefinitions + direct columns on the relevant junction or use a lightweight `entry_field_values` table only if table width becomes a problem. Keep it simple first.

- **JSONB restriction**: Strictly for OOB unstructured data (template_definition, row_data, etc.). No JSONB for new modeled user fields.

This hybrid avoids the downsides of pure EAV (bad performance) and pure "add column to everything" (table bloat for highly variable data).

See:
- `backend/models/field_definition.py` (FieldDefinition + EntryFieldValue)
- `backend/models/entry.py` (fuller Entry model and relationships)

Key relationships (updated to match design):

Processes are composed of experiments (templates)
Experiments are composed of entries

This does make sense
 Processes:
  An Entry can be linked to a process step via process_step_id.
  ProcessSample tracks which samples are assigned to the overall process; the per-step data lives in the Entry + EntryFieldValue layer.

Predefined Entries use `predefined_entry_key` + config.
Custom entries (sample_data / experiment_detail) have columns defined by attached FieldDefinitions (from the template).

This supports:
- Process-level assignment via ProcessSample.
- Per-step (per-Experiment) data capture via Entry + EntryFieldValue.
- Template-driven structure for columns in entries.

Hard cutover means: when migrating an existing custom_attributes field, we move the data into the appropriate storage (direct column or entry_field_values) and stop using the old JSONB path.

### 2.3 Migration Approach

- Never perform raw `ALTER TABLE` at runtime from the app.
- Schema changes produce Alembic migration scripts (or fragments) that are reviewed and applied via the existing `run_migrations.py` / Docker startup flow.
- Support "soft" application: column is added as nullable, data is backfilled in a background job or admin-triggered batch, then NOT NULL constraint added in a follow-up migration if needed.
- Dual-write period for promoted fields: write to both JSONB and new column, read from new column with fallback.

### 2.4 UI Components (MVP Scope)

- **Schema Admin** (under Admin or Lab Mgmt):
  - Browse current fields per entity (focus on Samples and Experiments first).
  - "Add Field" wizard focused on:
    - List-backed fields (using existing Lists system)
    - Simple scalars (text, number, date, boolean)
  - Clear impact preview (which forms, Entries, Processes, and reports will be affected).
  - "Deprecate / Remove" flow with impact analysis.

- New fields must automatically appear in:
  - Standard entity forms and filters
  - Custom Entries (sample data entries and experiment detail entries)
  - Processes

- No "Add Table" wizard in MVP.

### 2.5 Data Model Sketch (New/Extended Tables)

```sql
-- Core addition for managed definitions
CREATE TABLE field_definitions (
    id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,           -- 'sample', 'experiment', etc.
    name TEXT NOT NULL,
    display_name TEXT,
    data_type TEXT NOT NULL,             -- 'list', 'text', 'number', 'date', ...
    source_list_id UUID REFERENCES lists(id),
    is_required BOOLEAN DEFAULT false,
    unique_scope TEXT,                   -- null, 'global', 'project', etc.
    validation_rules JSONB,
    ui_hints JSONB,
    scope_type TEXT,                     -- 'global', 'template', 'process'
    scope_id UUID,
    is_core BOOLEAN DEFAULT false,       -- true if added by developers
    deprecated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    created_by UUID
);

-- For new supporting tables (example)
-- Admins define columns in field_definitions with entity_type = 'new_table_name'
-- System generates:
-- CREATE TABLE new_supporting_table (...);
-- With appropriate FKs and indexes.
```

For the concrete "add specimenbiotype to samples":
- Create a list "specimen_biotypes" (or reuse).
- Add column: `specimen_biotype_id UUID REFERENCES list_entries(id)`
- Register in `field_definitions`.
- Update Sample model + schemas + UI (or rely on dynamic generation).

## 3. Key Flows

### 3.1 Add Field to Existing Table (List-backed or Simple Scalar)

The "Add list-backed columns + simple scalars" capability covers:

- **List-backed fields** (e.g. `specimen_biotype`): Uses the existing `lists` + `list_entries` system. Stored as a direct FK column (`specimen_biotype_id UUID REFERENCES list_entries(id)`).
- **Simple scalars**: text, numeric, date, boolean, etc. Stored as native column types (e.g. `TEXT`, `NUMERIC`, `TIMESTAMPTZ`, `BOOLEAN`).

Example flow for adding either type to Samples:

1. Admin selects "Samples" → "Add Field".
2. Chooses data type:
   - "List" → selects or creates a source list (e.g. "specimen_biotypes").
   - "Text", "Number", "Date", "Boolean", etc.
3. System:
   - Creates `field_definition`.
   - Generates migration fragment to add the appropriate column directly to the `samples` table.
   - Updates dynamic form/rendering/search configs.
4. Admin reviews impact.
5. Migration applied → field available in UI, Entries, Processes, etc.

This directly supports adding a text column or numeric column to an existing table as a first-class, queryable, typed field.

### 3.2 Remove / Deprecate Column

1. Admin selects field → Deprecate.
2. System hides from default UI, marks definition as deprecated.
3. Optional: migration to move data to `custom_attributes` archive or dedicated archive table.
4. Later: full drop migration after grace period.

### 3.3 Add Table

Deferred beyond MVP (see CEO recommendation). Focus first on adding fields to existing high-value tables.

## 4. Integration Points

- **Lists**: First-class use for "list" data_type.
- **Custom Attributes**: Gradual migration target. New fields are structured; legacy JSONB remains for ad-hoc.
- **Experiments / Processes / Entries**: Template can declare required/available fields or entry types. Columns defined here can be referenced in entry column definitions.
- **Workflows**: New fields are usable in workflow actions/conditions.
- **RLS**: New columns/tables must have policies (inherit from parent entity or explicit).
- **Audit**: All schema changes + data changes to new fields go through existing audit mechanisms.
- **Reporting/Search**: New columns are automatically indexed (system recommends) and exposed to query builders.

## 5. Risks and Mitigations

- **Migration safety**: Use nullable-first + backfill jobs. Provide dry-run and impact reports.
- **Performance**: System suggests indexes. Monitor slow queries after changes.
- **RLS / multi-tenancy breakage**: All new columns/tables default to inheriting parent RLS. Explicit review required for exceptions.
- **Code / ORM drift**: Prefer dynamic form generation + explicit model updates for core entities. Use views or generated code where possible.
- **Over-flexibility**: Gate advanced features (new tables) behind stricter roles and review processes.
- **JSONB lock-in**: Provide clear deprecation path and tooling to promote fields out of JSONB.

## 6. Phased Implementation

**Phase 1 (Foundation)**
- FieldDefinition model + admin UI for adding list-backed and simple columns.
- Migration generation for column adds on existing tables.
- Basic form generation for new fields.
- Support for the specimenbiotype example.

**Phase 2 (Deprecation + New Tables)**
- Deprecate/remove flows.
- Initial support for adding simple supporting tables.
- Data migration tooling (JSONB ↔ column).

**Phase 3 (Advanced)**
- Deeper integration with Entries / Processes.
- Template-scoped field definitions.
- Advanced validation and cross-entity constraints.
- Better reporting surface for custom fields.

## 7. Open Design Questions

- How much of the form/UI generation should be fully dynamic vs. generated code that developers can customize?
- Should we support "computed" or "derived" fields at the schema level?
- Versioning of field definitions vs. simple deprecation.
- Handling of required fields on existing data (backfill strategy).
- Interaction with the "add table" feature and the overall experiment/process model (e.g., can users define new tables that participate in Processes?).

---

This design aims to give controlled flexibility while preserving the safety, performance, and maintainability required for a production LIMS. It directly supports the move away from suboptimal JSONB patterns identified earlier.