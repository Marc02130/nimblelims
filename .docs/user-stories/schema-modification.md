# User Stories: Schema Modification (Focused MVP)

**Date:** 2026-06-30  
**Context:** High-ROI changes for early-stage biotechs: adding list-backed columns and simple scalars to existing tables (Samples/Experiments first), deprecation, and clean integration with Entries and Processes. Adding new tables is deferred.

## US-1: Add a List-Backed Column to an Existing Table

**Title:** As a Lab Administrator, I want to add a "Specimen Biotype" field (sourced from a controlled list) to the Sample table so that I can classify and filter samples by biological type without requiring a code change.

**As a** Lab Administrator  
**I want** to add a new column "specimen_biotype" to the Samples table  
**So that** samples can be categorized using a predefined list of biotypes, enabling better search, reporting, and workflow routing.

**Acceptance Criteria:**
- The new field appears as a selectable list (dropdown or autocomplete) sourced from an existing or new `list_entries` list called "specimen_biotypes".
- The column is added to the `samples` table as a nullable FK to `list_entries` (with proper index).
- Existing samples continue to function; the new field is optional until marked required.
- The field is automatically included in:
  - Sample list views and filters
  - Sample detail forms (editable)
  - Accessioning forms (if configured)
  - Custom attribute / search APIs
- Adding the field triggers or proposes a safe database migration (Alembic).
- Audit log records who added the field and when.
- RLS and permissions are respected (only users with appropriate roles see/edit the field).
- Data can be bulk-updated for existing samples via import or admin UI.
- Removing or deprecating the list entry does not break existing samples (soft handling).

**Notes:**
- This replaces or augments the previous pattern of putting such values in `custom_attributes` JSONB.
- The list itself can be managed under the existing Lists admin UI.

**Related Refactor:** Moves this data out of JSONB into a properly typed, queryable column while still allowing admin-driven addition.

## US-2: Remove a Column from an Existing Table

**Title:** As a Lab Administrator, I want to remove or deprecate an obsolete custom field from the Sample table so that the data model stays clean without losing historical information.

**As a** Lab Administrator  
**I want** to mark a column (or custom attribute) as deprecated / removed  
**So that** it no longer appears in new forms or reports, while preserving data for audits and historical queries.

**Acceptance Criteria:**
- Admin can select a field/column and choose "Deprecate" or "Remove".
- Deprecation:
  - Field is hidden from default UI forms and lists (but still queryable via advanced search or direct DB).
  - A deprecation warning/note is shown to users.
  - Data remains in the column (or migrated to archive JSONB if full removal).
- Full Removal:
  - Data is optionally migrated to an archive table or JSONB blob.
  - Column is dropped in a controlled migration.
  - All references in code, UI configs, and reports are flagged for cleanup.
- Audit trail of the removal action.
- Option to "restore" a deprecated field within a grace period.
- Existing workflows and results that referenced the field continue to work.
- Impact analysis report is generated before removal (what forms, reports, validations use it?).

**Notes:**
- Supports the goal of cleaning up after promoting fields out of JSONB or retiring unused custom fields.
- Should integrate with data retention policies.

## US-3: Add a New Table / Entity (Deferred)

**Status:** Explicitly out of MVP scope per focused recommendation.

Early value will come from adding fields to existing high-ROI tables (Samples, Experiments) rather than creating new top-level tables. This story is retained for future phases once the core field-addition + hard-cutover experience is proven.

## Cross-Cutting Requirements (implied by these stories)

- All schema changes must be auditable.
- Changes should support a review/approval workflow before being applied in production (especially for table additions).
- Backward compatibility during rollout (feature flags, dual storage).
- Integration with existing list management, custom attributes config, and workflow systems.
- Performance impact assessment (indexes, query plans).
- Support for both admin-driven and developer-driven schema evolution paths.

These user stories will drive the requirements, design, and implementation of schema evolution tooling as part of the JSONB refactor and broader experiment/process improvements.