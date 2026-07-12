# Design Review: Field Management - OOB + Custom Fields Harmonization

**Date:** 2026-07-05
**Reviewer(s):** Architect + Eng
**Branch:** refactor/jsonb (continuing schema evolution)
**Related:** CustomFieldsManagement.tsx, CustomFieldDialog.tsx, FieldDefinition model, lists system, legacy CustomAttributeConfig

## 1. Problem Statement

The current "Custom Fields Management" only manages custom (EAV) attributes via CustomAttributeConfig. 

Out-of-the-box (OOB) select/list fields (sample_type, status, matrix, qc_type, specimen_biotype on samples; status on projects/tests/experiments, etc.) are implemented as direct FKs to list_entries. 

They are invisible in the field admin UI. Their "options" live in the separate Lists system.

This leads to:
- Inconsistent admin experience for "fields on an entity".
- No way for admins to see "what fields exist for samples" in one place (OOB + custom).
- No way to attach validation rules or manage "options" for OOB fields in the same way as custom 'select' fields (which use validation_rules.options).
- When adding a custom field, no context of what already exists on the entity → risk of duplication or poor naming.
- Entity type is not strongly front-and-center before defining a field.

User requirements:
- Harmonize OOB and custom in the field management UI.
- OOB fields denoted distinctly.
- Require entity_type selection before adding custom field.
- Provide "context" (existing fields on the entity) when defining/adding.
- Support "select require options" uniformly.
- Decide lists vs validation_rules.options.
- Validation rules (incl. options) should apply to OOB fields too.
- OOB select fields should be editable (for options/validation).
- All entities should support this.
- Keep legacy "Custom attributes" and "Name templates" UIs separate and available.

## 2. Options Considered (Architect Review)

### Option A: Continue/Extend "Lists" as the source of truth for all select fields (including harmonizing custom to lists)

- Custom 'select' would pick or create a List (source_list_id), similar to OOB.
- FieldDefinition would use data_type='list' + source_list_id (as originally sketched).
- OOB stay on lists.
- Field management UI would link to / manage lists for options.
- Editing OOB options = editing the List.

**Pros:**
- Strong data integrity (FK + shared controlled lists).
- Centralized list management.
- Re-use of values across fields/entities.
- Consistent with current DB schema for OOB columns.

**Cons:**
- Overhead: admin must manage lists separately even for simple one-off custom selects.
- When adding a field, two-step (create list first?).
- Less "self-documenting" in the field definition itself.
- For very field-specific options, lists feel heavyweight.
- If we want per-field options that don't pollute global lists, it doesn't fit well.

### Option B: Validation rules.options as the primary for "select" definitions (for both custom and OOB). Lists remain for legacy OOB storage if needed.

- For data_type='select', the allowed values live in validation_rules: { "options": ["A", "B", "C"], ... other rules }
- This is already how custom 'select' works.
- For the field management UI, register/hardcode OOB fields and allow editing their validation_rules (including options).
- Display/editing of options is done directly in the field definition.
- Under the hood for new custom fields: store options in the config/FieldDefinition; actual value storage can be in custom_attributes (string) or a generic value, or we can still map to list_entries for storage if we want.
- For existing OOB columns that use FKs: the UI definition shows/edits the options (we can seed the options from current list entries on first load). Editing options here documents the field; actual list data can stay or be synced manually.

**Pros:**
- Uniform experience: every "select field" definition has its options right in the validation rules.
- Easy to add/edit options directly when managing the field (no context switch to Lists).
- OOB fields become first-class citizens in field management (view + edit validation/options).
- Self-contained field definitions — good when using FieldDefinition for Entries or generated forms.
- "select require options" is enforced in one place.
- Validation rules become richer and available for OOB (required, other constraints).

**Cons:**
- Duplication risk if the same vocabulary is used in many places (mitigated by ability to still use shared lists elsewhere or copy).
- Loses some DB FK enforcement for purely custom fields (acceptable if they live in JSONB or a value table; for promoted OOB columns we keep the column + FK).
- If we "deprecate" heavy use of lists for field options, the Lists feature is still useful for other things (and can remain in UI).
- For true shared controlled vocab, admins may still want lists — we can support both (field can reference a list OR have inline options).

### Option C: Hybrid (recommended after review)

- Core data storage for high-value OOB list fields continues to use the lists + list_entries system (don't break existing columns/FKs).
- The **FieldDefinition / field management layer** uses validation_rules.options (or a first-class options list + optional source_list_id) to declare the allowed values for the field's admin definition, UI rendering, and validation.
- When defining/editing a select field (OOB or custom):
  - Prefer or default to inline options in validation_rules for simplicity and self-containment.
  - Advanced: allow choosing a source List (for shared/reusable).
- For OOB fields that have list-backed columns, the field definition can be "seeded" with current list entries as options, and editing options in field mgmt can be documented there (or we can later add a "sync to list" action).
- Custom fields for 'select' primarily use options (no mandatory list creation).
- FieldDefinition model can have both `source_list_id` (optional) **and** `validation_rules.options`.

This gives the best of both: data integrity where it matters (OOB columns), simple definition UX everywhere, and validation rules as the single place for rules + options.

**Why this over pure lists or pure options:**
- Matches the user's explicit direction: "OOB select fields should use options, not lists" in the context of field management / validation.
- "Validation rules can include options".
- Allows OOB fields to have editable validation rules.
- Doesn't require deprecating the Lists feature (ListsManagement stays, used for other controlled values and potentially reusable).
- Harmonizes the *admin definition experience* without a massive storage migration for all existing list-backed OOB data.

## 3. UI Requirements Implementation

- Rename/adapt "Custom Fields Management" conceptually toward unified "Field Management" (keep URL/nav for now or minor label change; don't remove legacy Custom Attributes page).
- Grid / list:
  - Combined view of OOB + Custom per entity.
  - Column or Chip: "OOB" (read-only name/data_type mostly, editable validation/desc) vs "Custom" (full CRUD).
  - Filter by entity_type still present.
- Add Custom Field flow:
  - Entity type selector is prominent and **required first**.
  - Other form fields disabled or hidden until entity_type chosen.
  - Immediately below or in a side/context panel: "Fields on this entity" — shows OOB + existing custom for the selected type (with notation). Helps avoid dups, gives naming ideas, shows structure.
- For select/list data_type:
  - "Options" handled via validation_rules (required for select).
  - Nice-to-have: small helper to edit options as a list of strings (but raw JSON still acceptable per current impl).
- Editing OOB: allowed for validation_rules, description, active. Name/entity/data_type locked.
- Expand ENTITY_TYPES to cover all relevant (samples, tests, results, projects, client_projects, batches, units, clients, experiments, analyses, containers, etc.).
- Validation rules fully supported for OOB.

## 4. Backend Considerations

- The current implementation uses legacy CustomAttributeConfig for customs.
- New FieldDefinition model exists for the broader refactor.
- For this feature, we can:
  - Continue using/enhancing CustomAttributeConfig (or a unified "field config") for the admin definitions of both OOB registration and customs.
  - Or introduce lightweight FieldDefinition CRUD endpoints that the UI can call.
- OOB "definitions" can be seeded on startup or via migration into the config table (with a flag is_oob=true or source='oob').
- No immediate change to the actual column storage for OOB (they keep their list FKs where present).
- When options are edited for an OOB field, it primarily affects the admin definition + any generated UIs/validation; the underlying list data can be managed separately or synced later.

## 5. Risks & Mitigations

- Confusion between "Lists" page and options inside fields: document that lists are for reusable/shared values; field options are per-field definition (can copy from list if desired).
- Data inconsistency if options edited but underlying list_entries not updated: for OOB, keep the list as source of truth for values; field options as "view" or allowed set. For MVP, document and allow admin to align.
- Scope creep: keep the change focused to the management UI + dialog. Don't rewrite storage yet.

## 6. Recommendations

- Adopt **Hybrid with emphasis on validation_rules.options** for the field definition/admin layer (as described).
- Update the two dialog/management files to meet the exact UX requirements.
- Seed a reasonable set of OOB fields in the frontend (or add a simple backend endpoint later to return "built-in fields per entity").
- Keep Custom Attributes (legacy) and Name Templates as separate entries in the UI per user instruction.
- After UI lands, we can evolve the backend to a FieldDefinition-based admin if desired.

## 7. Next Steps

1. Create CEO review (business justification + scope).
2. Implement UI changes (this PR).
3. Add tests / update existing CustomFieldsManagement.test.tsx.
4. Consider adding a small "register OOB" or seed mechanism if we want OOB definitions persisted rather than hardcoded in UI.
5. Later: wire more tightly to FieldDefinition model + support in form rendering (CustomAttributeField etc.).

This delivers the harmonized, contextual field management experience requested while respecting the current architecture and existing data storage.