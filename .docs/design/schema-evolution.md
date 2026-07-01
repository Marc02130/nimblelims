# Design: Schema Evolution System

**Date:** 2026-06-30  
**Branch:** refactor/jsonb  
**Status:** Draft for design review

## 1. Goals

- Enable controlled, auditable extension of the data model by administrators (add list-backed columns, deprecate columns, add supporting tables).
- Reduce reliance on unstructured `JSONB` (especially `custom_attributes` and loose `content`/`processing_conditions`) for data that benefits from typing, querying, constraints, and reporting.
- Maintain safety: no runtime schema changes that bypass migrations, RLS, or upgrade paths.
- Integrate with existing mechanisms (Lists, custom attributes config, Alembic, RLS, audit).
- Support the evolving Experiment/Process/Entries model (template-driven columns, sample write-back).
- Provide a migration path from current JSONB-heavy patterns.

This design supports the user stories in `.docs/user-stories/schema-modification.md` and addresses gaps identified in the JSONB analysis.

## Glossary (Decided Direction)

- **FieldDefinition**: The canonical term for the metadata definition of an extensible, typed field (scalar or list-backed). Replaces the role previously played by custom attribute definitions. Used for deliberate schema extension.
- **FieldValue**: The actual value for a FieldDefinition on a specific record. Will live in a properly typed column (or a dedicated value table for complex cases) rather than JSONB.
- **Entry**: A richer, template-driven component inside an Experiment or Process step. Entries can be tables of data, actions, or structured blocks. Different from simple FieldDefinitions. Columns inside custom Entries are also defined via FieldDefinitions where appropriate.
- **ProcessSample**: Junction that records which samples are assigned to a Process (separate from per-experiment tracking).
- **JSONB (unstructured only)**: Strictly for opaque or highly variable data that is not used for modeled functionality. Examples: raw instrument rows (`row_data`), AI extraction results, external opaque payloads. JSONB will **not** be used to extend the data model or carry structured user fields.

**Custom attributes** concept is being retired for new extensibility work.

## 2. High-Level Architecture

### 2.1 Core Concepts

- **FieldDefinition**: Metadata for an extensible, typed field (the replacement for custom attribute definitions).
  - Belongs to an entity type (Sample, Experiment, etc.) or scoped to a Template/Process.
  - Properties: name, display_name, data_type (text, integer, list, reference, date, etc.), source_list_id (for list-backed fields), required, unique_scope, default_value, validation_rules, ui_hints.
  - Can be "core" (developer-defined) or "extended" (admin-defined via UI).
  - Will drive both database columns and UI generation.

- **SchemaChange** (audit + migration request): Records proposed and applied changes.
  - Type: ADD_COLUMN, DEPRECATE_COLUMN, DROP_COLUMN, ADD_TABLE, etc.
  - Status: proposed, reviewed, applied, rolled_back.
  - Stores before/after definition + impact report.

- **EntityExtension**: Runtime and migration support for the actual columns/tables.

For list-backed fields (e.g., `specimen_biotype`):
- Use existing `list_entries` system. The column will be a `list_entry_id` FK (or nullable reference) with a GIN or B-tree index as appropriate.

### 2.2 Storage Strategy (Hybrid)

- **Preferred for new/extended fields**: Real columns on the target table (or new junction/support table).
- **Fallback / transitional**: Small `custom_attributes` JSONB remains for truly ad-hoc data.
- **Promotion path**: Admin marks a JSONB key as "promotable" → system helps migrate to real column + updates queries/UI.

For new tables:
- Generated or manually reviewed model + migration.
- Basic dynamic access layer (or code generation) for CRUD until a developer provides custom logic.

### 2.3 Migration Approach

- Never perform raw `ALTER TABLE` at runtime from the app.
- Schema changes produce Alembic migration scripts (or fragments) that are reviewed and applied via the existing `run_migrations.py` / Docker startup flow.
- Support "soft" application: column is added as nullable, data is backfilled in a background job or admin-triggered batch, then NOT NULL constraint added in a follow-up migration if needed.
- Dual-write period for promoted fields: write to both JSONB and new column, read from new column with fallback.

### 2.4 UI Components

- **Schema Admin** (under Admin or Lab Mgmt):
  - Browse current fields per entity/table.
  - "Add Field" wizard: select type (including "List" → choose/create list), properties, scope (global or per-template/process).
  - Preview of affected forms/reports.
  - "Deprecate / Remove" flow with impact analysis.
  - "Add Table" flow (advanced).

- Generated forms: Use the same pattern as current custom fields but backed by real columns where possible. New fields appear in DataGrids, filters, and accessioning where the entity is used.

- Process/Experiment integration: When defining Entries in a template, admins can reference or promote fields defined at the entity level.

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

### 3.1 Add List-Backed Column (Specimen Biotype)

1. Admin selects "Samples" → "Add Field" → Type = List → Source = new or existing "specimen_biotypes" list.
2. System:
   - Creates `field_definition`.
   - Generates migration fragment: `add_column('samples', 'specimen_biotype_id', ...)`
   - Updates any dynamic form/rendering configs.
   - Records the change in `schema_changes`.
3. Admin reviews impact (forms, existing data, RLS).
4. Change is approved/applied → migration is run on next deploy or via admin action.
5. Field becomes available immediately in UI (after migration) for new and existing records (null for existing).

### 3.2 Remove / Deprecate Column

1. Admin selects field → Deprecate.
2. System hides from default UI, marks definition as deprecated.
3. Optional: migration to move data to `custom_attributes` archive or dedicated archive table.
4. Later: full drop migration after grace period.

### 3.3 Add Table

More involved; may be limited to advanced admins.
- Define table name, columns (via field_definitions), relationships.
- System proposes full migration + basic model skeleton.
- UI scaffolding is generated from definitions until custom code is written.

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