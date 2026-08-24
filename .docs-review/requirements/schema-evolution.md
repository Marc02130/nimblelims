# Requirements: Schema Evolution and Management

**Date:** 2026-06-30  
**Status:** Draft for review  
**Related:** User Stories for schema modification, JSONB usage analysis, design docs for Experiments/Processes.

## 1. Introduction

This document captures the functional and non-functional requirements for a **focused, controlled schema evolution system**. The goal is to reduce reliance on unstructured `custom_attributes` JSONB for user-defined data by enabling lab administrators to add simple, high-value fields (especially list-backed columns and basic scalars) to existing entities in a safe, auditable way with minimal developer involvement.

**MVP Scope (per CEO recommendation):**
- Prioritize adding list-backed columns (e.g. `specimen_biotype`) and simple scalars (text, number, date, boolean) to core existing tables (Samples and Experiments first).
- Clean integration so new fields appear in Entries and Processes.
- Solid hard cutover from `custom_attributes` on high-usage entities.
- Easy deprecation/removal of fields.
- Excellent migration experience.

Full "add arbitrary table" capability and broad dynamic schema editing are explicitly deferred.

It must integrate with the existing architecture (Lists system, Alembic migrations, RLS, audit, UI generation, Experiments/Processes/Entries model).

## 2. Functional Requirements

### FR-1: Define and Add New Columns/Fields
- Administrators (with `config:edit` or equivalent) can define new fields on existing tables via UI.
- Supported field types: text, number, date, boolean, list (FK to list_entries), reference (to other entities), JSON (for complex but rare cases).
- For list fields: must integrate with the existing Lists system (select or create a list source).
- Field properties: display name, description, required, unique (scoped), default value, validation rules (min/max, regex, allowed values).
- New fields must be added as proper database columns (not just JSONB) when possible.
- System proposes or generates a safe Alembic migration.
- Fields can be marked as "UI-only" initially or hidden from certain forms.

### FR-2: Deprecate and Remove Columns
- Administrators can deprecate existing columns (including those previously added via this system or legacy custom_attributes).
- Deprecation hides the field from default UI while preserving data.
- Full removal requires data migration (to archive table or JSONB fallback) and generates a migration script.
- Impact analysis: show where the column is used (forms, reports, workflows, queries).
- Grace period / approval workflow before destructive removal.
- Audit of deprecation/removal actions.

### FR-3: Add New Tables (Deferred beyond MVP)
- This capability is explicitly out of scope for the initial focused release.
- Future consideration only after the core "add field to existing entities + hard cutover" is proven with real customers.

### FR-4: Integration with Existing Systems
- New fields/tables must be usable in:
  - Accessioning and data entry forms.
  - Search/filters and reports.
  - Workflow templates and actions.
  - Experiment/Process Entries (template-driven columns).
  - Sample write-back scenarios (e.g., updating concentration from a sample entry).
- Must support the existing `custom_attributes` as a fallback/legacy path during transition.
- List-backed fields must use the same `list_entries` mechanism as other configurable values (e.g., statuses, roles).

### FR-5: Template and Process Awareness
- When adding fields to entities used in Experiments or Processes (e.g., Samples, or new experiment-specific tables), admins can scope the field to specific templates or process types.
- Fields defined in templates (for Entries) should be promotable to real columns via this system.

### FR-6: Data Migration and Backfill
- For column additions: support backfilling existing records (null, default, or bulk import).
- For removals: optional archival migration.
- For new tables: initial data population options.
- Dual-write / dual-read support during transition periods (JSONB ↔ structured column).

### FR-7: UI Generation and Consistency
- Forms for new fields are automatically generated or configurable.
- Display order, grouping (tabs/sections), and visibility rules can be defined.
- Must integrate with existing UI patterns (DataGrid, forms, dialogs).

### FR-8: Audit and History
- All schema changes (add/deprecate/remove column, add table) are audited (who, when, what changed).
- Changes to field definitions are versioned where practical.

## 3. Non-Functional Requirements

### NFR-1: Safety and Reliability
- Schema changes must be reviewable and produce controlled Alembic migrations (no raw runtime ALTER TABLE from the app).
- Every schema change must explicitly address RLS policy impact.
- Hard cutover migrations must include validation, audit, and rollback paths.
- Prevent schema changes that would break critical workflows, RLS isolation, or data integrity.

### NFR-2: Performance
- New columns must be properly indexed (system suggests indexes based on type and usage).
- Adding a column or table must not degrade performance of existing high-volume queries without warning.
- Query plans and index recommendations should be part of the change review.

### NFR-3: Security and Access Control
- Schema modification requires explicit permission (recommended: elevated or separate from general `config:edit`).
- Every schema change must surface and require confirmation of RLS policy impact.
- New columns and any supporting tables must have RLS policies applied (or explicitly inherit from parent entity).
- All schema changes are fully audited (who, what, when, impact).
- Data in new fields must respect existing RLS/client/project isolation.

### NFR-4: Maintainability and Upgrade Safety
- Schema changes must not prevent future application upgrades or require per-client custom migrations.
- Generated code/migrations must follow project conventions (Alembic, naming, BaseModel patterns where applicable).
- Clear separation between admin-driven extensions and core developer schema.

### NFR-5: Usability
- Impact analysis and preview of changes (affected forms, reports, data volume) before applying.
- Clear messaging for end users when fields are added/deprecated.
- Support for bulk operations on new fields (import, update).

### NFR-6: Auditability and Compliance
- Full history of schema definitions and changes.
- Ability to report on which fields were used when for compliance/audit purposes.
- Support for data lineage when moving values between JSONB and structured columns.

### NFR-7: Extensibility
- The system should support future evolution toward more advanced features (e.g., computed fields, validation across multiple tables, versioning of entire entity schemas).

## 4. Out of Scope (for initial version)

- Full low-code application builder (arbitrary business logic).
- User-defined tables with complex triggers or stored procedures.
- Real-time collaborative schema editing.
- Automatic generation of API endpoints beyond basic CRUD.
- Support for all possible PostgreSQL column types or advanced features (arrays of arrays, etc.).

## 5. Success Metrics

- Reduction in ad-hoc `custom_attributes` JSONB usage over time.
- Time to add a common list-backed field drops from developer task (days) to admin task (minutes).
- No production incidents caused by schema changes performed via the new system.
- High adoption of the new fields in reporting and workflows.
- Clean migration paths when retiring JSONB-heavy patterns.

### Additional Constraints from Current Direction

- **Hard cutover**: When moving from custom_attributes to FieldDefinition-based storage, we will do a hard cutover (with migration), not a long-running dual-write period.
- **JSONB restriction**: JSONB may only be used for Out-Of-Box (OOB) unstructured data. There will be no UI allowing users or admins to define new unstructured fields for extensibility. JSONB examples that remain allowed: `template_definition`, `row_data`, `parser_config`, certain OOB result blobs.

---

This requirements document will guide the design and implementation of schema evolution features as part of the JSONB refactor and broader experiment/process improvements.