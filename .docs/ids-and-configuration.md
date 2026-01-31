# IDs and Configuration: Sample, Project, and Related Entities

This document describes how identifiers (IDs) work for entities like samples and projects, where configuration data is stored, and how configuration drives behavior from setup through runtime use.

## Two Kinds of Identifiers

### 1. Primary key: `id` (UUID)

- **What it is**: A UUID primary key on every entity table (e.g. `samples.id`, `projects.id`).
- **Set where**: In the database/model layer. `BaseModel` uses `default=uuid.uuid4` (see `backend/models/base.py`), so the value is generated at insert time.
- **Used for**: API resource URLs (`/samples/{id}`), foreign keys (e.g. `samples.project_id` → `projects.id`), RLS policies, and internal references. It is **not** meant to be human-readable or configurable.
- **Storage**: Stored in the entity table’s `id` column. No configuration table drives it.

### 2. Human-readable name: `name`

- **What it is**: A unique, human-readable label (e.g. `SAMPLE-2024-001`, `PROJ-ACME-20240108-001`).
- **Set where**: Either supplied on create/update or **auto-generated from name templates** when omitted.
- **Used for**: Display in the UI, search, and user-facing identification. Must be unique per entity type (enforced by `name` column and, for generated names, by the name-generation logic).
- **Storage**: Stored in the entity table’s `name` column. **Which** name is generated is controlled by configuration (see below).

So for “IDs like sample and project”: the **id** is the UUID; the **name** is the configurable, human-facing identifier. Both are stored on the entity row; only the rules for generating `name` come from configuration.

---

## Where Configuration Data Is Stored

Configuration that depends on entity type (sample, project, etc.) is stored in a few places. The **entity type** (or list name) is what ties configuration to the right entity and thus to where data is stored.

### 1. Name generation: `name_templates` and sequences

**Purpose**: Define how auto-generated **names** (e.g. sample, project) are built.

| What | Where stored | How entity type is used |
| --- | --- | --- |
| Template string and metadata | Table `name_templates` | Column `entity_type` (e.g. `'sample'`, `'project'`, `'batch'`, `'analysis'`, `'container'`). Only **one active** template per `entity_type` (unique partial index). |
| Next sequence number for `{SEQ}` | PostgreSQL sequences | One sequence per entity type: `name_template_seq_sample`, `name_template_seq_project`, etc. (see migration `0021_configurable_names.py`). |
| Sequence starting value | PostgreSQL sequences (configurable via ALTER SEQUENCE) | Admins can set the starting value for each sequence (e.g., via SQL or admin tools). |
| Padding digits for `{SEQ}` | Table `name_templates` (new column: `seq_padding_digits`) | Defaults to 1 (no padding); e.g., 3 for zero-padding to 3 digits (001, 002, ...). |

So “where configuration is stored” for naming is:

- **name_templates**: one row per logical entity type (and only one active per type). The row’s `entity_type` selects which template (and thus which sequence) is used when generating a name for that kind of entity. Now includes `seq_padding_digits` for controlling {SEQ} formatting.
- **Sequences**: live in the DB; name generation uses the sequence whose name matches the entity type. Starting values can be set via ALTER SEQUENCE commands.

**Default templates** (seeded in migration 0021):

- **sample**: `SAMPLE-{YYYY}-{SEQ}`
- **project**: `PROJ-{CLIENT}-{YYYYMMDD}-{SEQ}`
- **batch**: `BATCH-{YYYYMMDD}-{SEQ}`
- **analysis**: `ANALYSIS-{SEQ}`
- **container**: `CONT-{YYYYMMDD}-{SEQ}`

Placeholders: `{SEQ}` (supports padding via `seq_padding_digits`, e.g., {SEQ} with 3 digits becomes 001), `{YYYY}`, `{YY}` (two-digit year), `{MM}`, `{DD}`, `{YYYYMMDD}`, `{CLIENT}` (see `backend/app/core/name_generation.py`).

**Resulting data**: The generated string is stored in the entity’s `name` column (e.g. `samples.name`, `projects.name`). So name **configuration** is in `name_templates` (+ sequences); name **data** is in the entity table.

### 2. Custom attributes: `custom_attributes_config`

**Purpose**: Define which custom attributes exist for which entity type and how they are validated (EAV-style).

| What | Where stored | How entity type is used |
| --- | --- | --- |
| Attribute definitions (name, type, validation) | Table `custom_attributes_config` | Column `entity_type` (e.g. `'samples'`, `'tests'`). All active rows with the same `entity_type` apply to that entity type. |

So “where configuration is stored” for custom attributes is **custom_attributes_config**, and **entity_type** selects which config applies (e.g. `entity_type = 'samples'` for samples).

**Resulting data**: Validated custom attribute **values** are stored on the entity in a JSONB column, e.g. `samples.custom_attributes`, `projects.custom_attributes` (see `backend/models/sample.py`, `backend/models/project.py`). So config is in `custom_attributes_config`; data is in the entity’s `custom_attributes` column.

### 3. List-based configuration (status, types, etc.)

**Purpose**: Allowed values for fields like sample status, sample type, matrix, project status (stored as FKs to `list_entries.id`).

| What | Where stored | How it’s scoped |
| --- | --- | --- |
| List definitions | Table `lists` | Each list has a unique `name` (e.g. `sample_status`, `sample_types`). |
| Allowed options | Table `list_entries` | `list_id` links to `lists.id`; which list is used for which field is defined in code/schema (e.g. sample status → `sample_status` list). |

So “where configuration is stored” for these dropdowns is **lists** and **list_entries**. The **list name** (and the FK from the entity to `list_entries.id`) effectively scopes which configuration applies to which field. Entity tables store only the chosen `list_entries.id` (e.g. `samples.status`, `samples.sample_type`).

---

## How It Works: Configuration Through Use

### Name generation (sample / project / batch / analysis / container)

1. **Configuration (admin)**

   - Admin creates or updates rows in **name_templates** (e.g. `entity_type = 'sample'`, `template = 'SAMPLE-{YYYY}-{SEQ}'`, `seq_padding_digits = 3`).
   - Only one active template per `entity_type`.
   - Sequences `name_template_seq_*` are created by migration and incremented when `{SEQ}` is used. Admins can set starting values (e.g., ALTER SEQUENCE name_template_seq_sample RESTART WITH 100;).
   - Padding is applied to {SEQ} (e.g., with seq_padding_digits=3, 1 becomes '001').

2. **At create time (e.g. accession)**

   - User or API creates a sample/project without supplying `name`, or bulk/API uses “auto name”.
   - Backend calls the appropriate generator (e.g. `generate_name_for_sample()`, `generate_name_for_project()`) in `backend/app/core/name_generation.py`.
   - Generator:
     - Loads the **active template** for that entity type from **name_templates`, including `seq_padding_digits`.
     - Gets the next **sequence** value for that entity type.
     - Resolves placeholders (e.g. year as {YYYY} or {YY}, date, client code) and formats {SEQ} with padding (e.g., str(seq).zfill(seq_padding_digits)).
     - Checks **uniqueness** against the entity table (e.g. `samples.name`, `projects.name`).
     - Returns the name; the row is inserted with this `name` and a new UUID `id`.

3. **Storage**

   - The generated value is written to the entity’s **name** column.
   - The entity’s **id** remains the UUID from `BaseModel`.
   - So: **name_templates + sequences** define *how* names are built (including padding and {YY}); **entity table** `name` is where that built value is stored.

4. **Usage**

   - APIs and UI use `id` for references and URLs; they use `name` for display and search.

### Custom attributes (e.g. samples, tests)

1. **Configuration (admin)**

   - Admin creates rows in **custom_attributes_config** with an **entity_type** (e.g. `'samples'`, `'tests'`) and attributes (attr_name, data_type, validation_rules).
   - This defines which keys are allowed and how they are validated for that entity type.

2. **At create/update time**

   - Request includes a `custom_attributes` object (e.g. on sample create/patch).
   - Backend calls `validate_custom_attributes()` in `backend/app/core/custom_attributes.py` with the appropriate **entity_type** (e.g. `'samples'`).
   - Validation loads active **custom_attributes_config** rows for that **entity_type** and validates the payload.
   - Validated dict is then written to the entity’s **custom_attributes** JSONB column (e.g. `samples.custom_attributes`).

3. **Storage**

   - **Configuration**: `custom_attributes_config` (keyed by **entity_type**).
   - **Data**: entity table’s **custom_attributes** column. So entity_type selects *which* config applies; the actual values are stored on the entity row.

4. **Usage**

   - APIs and UI read/write `custom_attributes` on the entity; validation and schema are driven by **entity_type** in **custom_attributes_config**.

### Summary table: configuration → storage → use

| Feature | Config table(s) | Entity type / scope | Where data is stored | Flow |
| --- | --- | --- | --- | --- |
| Human-readable name | `name_templates` + sequences | `entity_type` (sample, project, …) | Entity `name` column | Template + SEQ (with padding and {YY} support) → generate name → store in entity.`name` |
| Custom attributes | `custom_attributes_config` | `entity_type` (samples, tests, …) | Entity `custom_attributes` (JSONB) | Config defines allowed attrs → validate → store in entity.`custom_attributes` |
| Status / types / matrix | `lists`, `list_entries` | List name (e.g. sample_status) | Entity FK column (e.g. `samples.status`) | List entries define options → user picks → store list_entry.`id` on entity |

---

## Admin Pages for Configuring IDs

The "IDs" here primarily refer to the configurable human-readable `name` fields for entities like samples and projects, which are driven by name templates. Admin pages in the frontend UI should allow authorized users to manage these configurations. Assuming a React-based frontend with API calls to the backend (e.g., via FastAPI routers like `admin.py`), here's a proposed structure for the admin pages.

### 1. Name Templates Admin Page

- **Path**: `/admin/name-templates`
- **Purpose**: View, create, edit, and deactivate name templates for different entity types (e.g., sample, project).
- **Key Features**:
  - List view: Table showing all name templates with columns for `entity_type`, `template`, `seq_padding_digits`, `is_active`, `created_at`, `updated_at`.
  - Filters: By entity_type (dropdown with options like 'sample', 'project', 'batch', etc.).
  - Create/Edit form: Fields for `entity_type` (select from predefined types), `template` (text input with placeholder examples, including {YY} and {SEQ}), `seq_padding_digits` (number input, e.g., 3 for zero-padding), `description` (optional).
  - Validation: Ensure only one active template per entity_type; warn if activating a new one would deactivate others.
  - Actions: Activate/Deactivate, Delete (with confirmation, only if not active). Additional action: Set sequence starting value (e.g., input field to ALTER SEQUENCE).
- **API Integration**: Uses CRUD endpoints from `backend/app/routers/admin.py` (e.g., GET/POST/PATCH/DELETE `/admin/name-templates`). Add endpoint for setting sequence start (e.g., POST `/admin/sequences/{entity_type}/start`).
- **Permissions**: Restricted to admin roles; use auth checks in the frontend and backend.

### 2. Custom Attributes Config Admin Page

- **Path**: `/admin/custom-attributes`
- **Purpose**: Manage custom attribute definitions for entity types, which indirectly affect how entities (including their "IDs" via extended attributes) are configured.
- **Key Features**:
  - List view: Table with `entity_type`, `attr_name`, `data_type` (e.g., string, number, boolean), `validation_rules` (JSON editor), `is_required`, `is_active`.
  - Filters: By entity_type.
  - Create/Edit form: Select entity_type, input attr_name, choose data_type, define validation (e.g., min/max for numbers, regex for strings).
  - Actions: Activate/Deactivate, Delete.
- **API Integration**: CRUD on `/admin/custom-attributes-config`.
- **Permissions**: Admin-only.

### 3. Lists and List Entries Admin Page

- **Path**: `/admin/lists`
- **Purpose**: Configure dropdown lists (e.g., sample_status, sample_types) that affect entity fields, which can influence naming or identification indirectly.
- **Key Features**:
  - Two-level view: First, list of `lists` (e.g., sample_status, project_status).
  - For each list: Sub-view to manage `list_entries` (add/edit/delete options like 'Pending', 'Approved').
  - Create new lists if needed (though most are predefined).
- **API Integration**: CRUD on `/admin/lists` and `/admin/list-entries`.
- **Permissions**: Admin-only.

### General Admin Dashboard Integration

- **Navigation**: Add an "Admin" section in the main nav with sub-links to the above pages.
- **UI Components**: Use reusable components like DataTable for lists, FormModal for create/edit.
- **Error Handling**: Show toasts for API errors, e.g., "Only one active template per entity type."
- **Best Practices**:
  - Real-time updates: Use WebSockets or polling if configurations change frequently.
  - Preview: For name templates, add a preview generator showing example names (e.g., "SAMPLE-24-001" with {YY} and padding).
  - Audit Logging: Backend should log changes to configurations.

These pages build on the existing backend APIs. If the frontend framework is React, implement routes in `App.js`, components in `/components/admin`, and use hooks for API calls (e.g., via Axios or Fetch).

---

---

## Reference: Key Files

- **Base model (UUID** `id`**,** `name`**)**: `backend/models/base.py`
- **Name templates model**: `backend/models/name_template.py`
- **Name generation**: `backend/app/core/name_generation.py` — `get_active_template()`, `get_next_sequence()`, `generate_name()`, `generate_name_for_sample()`, `generate_name_for_project()`, etc.
- **Migration (name_templates + sequences + seeds)**: `backend/db/migrations/versions/0021_configurable_names.py`
- **Custom attributes config model**: `backend/models/custom_attributes_config.py`
- **Custom attributes validation**: `backend/app/core/custom_attributes.py` — `validate_custom_attributes()` with **entity_type**
- **Use in APIs**: e.g. `backend/app/routers/samples.py` (accession uses `generate_name_for_sample` / `generate_name_for_project`; custom attribute validation uses `entity_type='samples'`), `backend/app/routers/admin.py` (name template CRUD)