# Design: Field Management - OOB + Custom Harmonization (Implementation Notes)

**Date:** 2026-07-05
**Status:** Ready for implementation

## Goals (this iteration)

- Single place (Field Management) shows **both** OOB fields and custom fields, clearly denoted.
- User **must** choose an entity type before defining a new custom field.
- Show **context** — the list of fields (OOB + custom) that already exist for the chosen entity.
- Harmonize how "select" / option-based fields are defined: use **validation_rules.options**.
- OOB select fields become editable for their validation rules / options / description.
- Validation rules are first-class for OOB fields.
- All reasonable entities supported.
- Do not remove or hide the existing "Custom Attributes" or "Name Templates" admin pages.

## Data Model / Source of Truth for Options (Decision)

After architect review:

**Primary for field definitions (admin + validation + UI generation): validation_rules.options**

- For data_type `select` (or future `list` in FieldDefinition), the allowed values are expressed as:
  ```json
  { "options": ["Plasma", "Serum", "Whole Blood"], "required": true }
  ```
- This is already implemented and validated for custom fields.
- We extend the same pattern to OOB fields.

**Lists system:**
- Remains available (ListsManagement, list entries for dropdowns in forms).
- Useful for reusable/shared vocabularies and cases where you want central management + potential future metadata on entries.
- **Not required** just to define a field's allowed options in Field Management.
- For existing OOB columns that are FK'd to list_entries, the field definition's options serve as the declared/validated set in admin and generated UIs. The actual runtime values for those columns can continue coming from list_entries. We can improve syncing in a follow-up.

This matches the explicit direction: OOB select fields in the context of field management should use options (via validation rules).

## UI Changes (CustomFieldsManagement + CustomFieldDialog)

1. **Entity Types**
   - Expand to a comprehensive list so "all entities are available":
     samples, tests, results, projects, client_projects, batches, units, clients, experiments, analyses, containers, workflows (and any others that make sense).
   - Keep the filter control.

2. **Combined Grid**
   - Define a static (or later API-driven) set of OOB fields per entity.
   - Each OOB entry includes at minimum: attr_name, data_type, description, typical validation_rules (with options where applicable).
   - Merge with custom configs for the current view/filter.
   - Add a "Source" / "Type" column or prominent Chip:
     - "OOB" (primary color or gray, "Built-in")
     - "Custom" (success or accent)
   - For OOB rows in actions:
     - Allow Edit (primarily for validation_rules, description, active).
     - Hide or disable Delete (or make it a "deprecate" that doesn't actually remove the column).
   - Columns stay similar (Entity, Name, Data Type, Description, Validation Rules, Status, Actions).

3. **Create Flow - Entity First + Context**
   - When opening the create dialog (not edit):
     - Entity Type select is the first / most prominent control.
     - All other controls (attr_name, data_type, validation rules, etc.) are disabled or shown in a collapsed state until a valid entity_type is chosen.
     - As soon as entity_type is selected (and valid), immediately render a **"Fields defined for this entity"** context section.
       - List or compact table/chips showing OOB + any loaded customs for that entity.
       - Notation: OOB vs Custom chips.
       - This gives immediate helpful context (avoid name collisions, see patterns, understand what "select" options look like on this entity).
   - The existing uniqueness check and Yup validation for entity_type remain / are enforced.

4. **Dialog Behavior for OOB vs Custom**
   - When editing an OOB config/row:
     - entity_type, attr_name, data_type are read-only / disabled.
     - validation_rules, description, active are fully editable.
     - Title: "Edit Built-in Field (OOB)" or similar.
   - When creating/editing custom: full editing as before.
   - For 'select' data_type (both OOB and custom): reinforce that options are required in validation_rules (existing Yup test + helper text).

5. **Validation Rules for Everyone**
   - The validation rules editor + helper notes are shown and functional for OOB edits.
   - This satisfies "Validation rules should be available for OOB fields".

6. **Other**
   - Update page title / header subtly toward "Field Management" while the route and nav can stay "Custom Fields" for now (or minor text change).
   - Keep the legacy Custom Attributes admin page and Name Templates completely untouched and navigable.
   - Search and filters continue to work across the combined set.

## OOB Fields Seed Data (Frontend for MVP)

We will maintain a const in the component or a small util:

```ts
const OOB_FIELDS_BY_ENTITY: Record<string, Array<{...}>> = {
  samples: [
    { attr_name: 'sample_type', data_type: 'select', description: 'Type of the sample material', validation_rules: { options: ['...'] }, is_oob: true },
    { attr_name: 'status', ... },
    { attr_name: 'matrix', ... },
    { attr_name: 'qc_type', ... },
    { attr_name: 'specimen_biotype', data_type: 'select', ... },  // the one from refactor
  ],
  projects: [ { attr_name: 'status', ... }, { attr_name: 'access_level', ... } ],
  // ... other entities
};
```

When merging for display or context, tag them with source: 'oob'.

Later this can be replaced/enhanced by a backend call that returns built-in + custom FieldDefinitions.

## Backend Notes (for awareness, not blocking this UI work)

- Current storage for customs = CustomAttributeConfig.
- OOB definitions can live alongside (with is_oob or source flag) or we can evolve toward FieldDefinition.
- No change required to existing list-backed columns for this UI iteration.
- When we later wire forms/Entries to consume these definitions, both OOB and custom will benefit from the same validation_rules.

## Success Criteria

- Admin opens Field Management → sees OOB + Custom mixed, clearly denoted.
- Filters by entity work on the combined set.
- Click "Create Custom Field" → entity selector first. Other fields disabled. Context panel appears with existing fields once entity chosen.
- Can edit an OOB field's validation rules / options / description (e.g. change the allowed options for specimen_biotype or matrix).
- Select data type still enforces options in validation rules.
- Legacy Custom Attributes and Name Templates pages remain fully functional and linked.
- No regression on creating/editing true custom fields.

This change delivers exactly the harmonized, contextual experience requested.