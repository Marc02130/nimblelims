# Plan: ExperimentTemplatesManagement UI (Phase 1 + 2)

**Branch:** experiment-template-ui-docs
**Repo:** Marc02730/nimblelims
**Design doc:** ~/.gstack/projects/garrytan-gstack/marcbreneiser-main-design-20260331-210433.md (APPROVED)
**CEO review:** APPROVED 8.5/10
**Design review:** NEEDS_CHANGES 6.5/10 — addressed below
**Eng review:** NEEDS_CHANGES 6/10 — critical schema fixes applied below

---

## Problem

`/experiments/templates` renders `<ExperimentsManagement />` (the experiments list) because
`ExperimentTemplatesManagement.tsx` does not exist. The backend API at `/v1/experiment-templates`
is fully implemented with CRUD + SOP extraction (`SOPParseService` via Claude). Scientists have
no way to create or manage experiment templates without writing raw JSON.

Secondary bugs:
- `App.tsx:192` — wrong component + wrong permission (`experiment_template:manage` doesn't exist; backend uses `experiment:manage`)
- `Sidebar.tsx` — nav item gated on nonexistent `experiment_template:manage`

---

## Actual Backend API Schema (corrected)

**`ExperimentTemplateRead`** (what the API returns):
```typescript
interface ExperimentTemplateRow {
  id: number;
  name: string;                        // outer field — NOT inside template_definition
  description: string | null;
  active: boolean;                     // NOT is_active
  template_definition: TemplateDefinition;  // JSONB — all the rich fields live here
  custom_attributes: Record<string, unknown> | null;
  created_at: string;
  created_by: string | null;
  modified_at: string;
  modified_by: string | null;
}

interface TemplateDefinition {
  experiment_name: string;
  description?: string;
  protocol_steps: string[];
  plate_layout?: '96-well' | '384-well' | null;
  transfer_steps: TransferStep[];
  result_columns: Record<string, unknown>[];
  acceptance_criteria?: string;
  mandatory_review_count: number;
}

interface TransferStep {
  step: number;
  source_plate?: string;
  source_well?: string;
  dest_plate?: string;
  dest_well?: string;
  volume_ul?: number;
  mandatory_review: boolean;
}
```

**`ExperimentTemplateCreate`** (what POST/PATCH send):
```typescript
{ name: string; description?: string; template_definition: TemplateDefinition; custom_attributes?: Record<string, unknown> }
```

Note: `active` uses PATCH separately — `updateExperimentTemplate(id, { active: true })`.
Note: `is_active` does not exist anywhere in the API. Always use `active`.

**Form → API serialization:** The form collects `experiment_name`, `protocol_steps`, etc. as top-level fields for UX clarity, but the create/update payload must nest them under `template_definition`. The outer `name` field maps to `template_definition.experiment_name`.

---

## Implementation Plan

### Phase 0: Restore point
```bash
cd ~/Code/nimblelims && git stash
```

### Phase 1: Foundation (list + create/edit form)

**1a. Create `ExperimentTemplatesManagement.tsx`**

File: `frontend/src/pages/ExperimentTemplatesManagement.tsx`

Structure mirrors `WorkflowTemplatesManagement.tsx` (MUI DataGrid + Dialog pattern).

**DataGrid columns:**
- `name` (outer field) — template name
- `description` (outer field)
- `plate_layout` → `row.template_definition?.plate_layout` — "96-well", "384-well", or "—"
- Status chip column → `row.template_definition?.mandatory_review_count`:
  - > 0: amber Chip "N pending sign-offs"
  - = 0: green Chip "Ready"
  - (this replaces both the column and the Phase 2 row badge — they are the same element)
- `active` (outer field) — toggle switch (disabled + tooltip "Sign-off required" when `mandatory_review_count > 0`)
- `modified_at` (outer field) — "Last modified" (more useful than `created_at`)
- `modified_by` (outer field) — "Modified by"
- Actions: Edit icon, Delete icon (with confirmation dialog)

**Form validation:**
- Save button disabled until `name` (outer form field, required) is filled
- On Save click, validate all tabs; auto-navigate to first tab with an error
- Tab headers show red dot indicator when their tab has validation errors
- Error summary bar below tabs lists which tabs have issues (one line per tab)

**Create/Edit Dialog — `maxWidth="lg"`, 4 tabs:**

- **Tab 1: Basic Info** — `name` (required, maps to outer `name`), `description`, plate_layout selector (96-well / 384-well / none), `acceptance_criteria`, `experiment_name` (internal experiment identifier inside template_definition)
- **Tab 2: Protocol Steps** — ordered list of text steps, add/remove/reorder
- **Tab 3: Transfer Steps** — table of `TransferStep` rows: step, source_plate, source_well, dest_plate, dest_well, volume_ul, toggle labeled **"Requires sign-off before activation"** (with helper text: "When checked, a lab manager must review this step before the template can be activated.")
- **Tab 4: Result Columns** — key/value pairs for result column definitions

**API calls (existing `apiService` methods + one addition):**
- `getExperimentTemplates()` → list
- `getExperimentTemplate(id)` → detail
- `createExperimentTemplate({ name, description, template_definition })` → create
- `updateExperimentTemplate(id, { name?, description?, template_definition?, active? })` → update
- `deleteExperimentTemplate(id)` → DELETE /v1/experiment-templates/{id} (ADD THIS to apiService — method is missing)

**1b. Fix `App.tsx:192`**

```tsx
// Add import:
import ExperimentTemplatesManagement from './pages/ExperimentTemplatesManagement';

// Fix route (was rendering ExperimentsManagement with wrong permission):
<Route
  path="/experiments/templates"
  element={
    hasPermission('experiment:manage') ? (
      <ExperimentTemplatesManagement />
    ) : (
      <Navigate to="/dashboard" replace />
    )
  }
/>
```

**1c. Fix `Sidebar.tsx`**

```tsx
// Update hasExperimentTemplatesAccess variable (around line 280):
const hasExperimentTemplatesAccess = hasPermission('experiment:manage');
// Also check line 523 and any other usage site — grep for hasExperimentTemplatesAccess
```

Also confirm: `experiment_name` is editable on edit (unlike WorkflowTemplates pattern where name is disabled). Experiment templates can legitimately be renamed (e.g., "PCR v1" → "PCR v2"). If made non-editable, show tooltip: "Name cannot be changed after creation."

### Phase 2: SOP Upload + Sign-off (SOP-First flow)

**2a. SOP Upload UI**

**Note:** The backend `POST /v1/sop-parse` requires TWO files:
- `sop_file: UploadFile` (required) — the SOP document
- `instrument_file: UploadFile` (required) — instrument CSV

The upload dialog must have two file inputs. If the product decision is to make `instrument_file` optional, that requires a backend change first. For now, require both.

Upload flow:
- Two file inputs: "SOP Document (PDF/DOCX/TXT)" and "Instrument CSV"
- POST as multipart/form-data to `/v1/sop-parse`
- Poll GET `/v1/sop-parse/{job_id}` every 2s
  - `SopParseJobStatus` values: `pending`, `running`, `complete`, `failed`
  - Show spinner + elapsed time counter while polling
  - Max 120s — after timeout: "This is taking longer than expected" with "Keep Waiting" and "Fill in Manually" buttons
  - On `failed`: show error message with "Fill in Manually" button
- On `complete`: use `POST /v1/sop-parse/{job_id}/apply` to create the template record atomically
  - The `/apply` endpoint creates ExperimentTemplate, InstrumentParser, and RobotWorklistConfig in one transaction
  - Returns 409 if already applied — disable Apply button after first success
  - Retry is safe (idempotent)
- After apply: reload the list, open the new template's edit dialog for review

**SOP-extracted field highlighting:**
Fields pre-filled from SOP extraction get `sx={{ backgroundColor: 'action.hover' }}` and a small "Filled by SOP" chip on the field label. Scientists need to see what was auto-filled vs what they still need to enter.

**Upload button placement:** "Upload SOP" is the primary action (prominent), "New Template" is secondary. Both in top-right of the list page header.

If parse fails and user retries: preserve the uploaded filenames so they don't re-select files from scratch.

**2b. Mandatory Review Sign-off Screen**

Triggered by clicking the amber "N pending sign-offs" chip in the DataGrid.

Opens a stepper dialog:
- Each step = one `TransferStep` where `mandatory_review = True`
- Display formatted (not raw field names): "Source: Plate A, Well B3 → Destination: Plate B, Well C4 — 10 µL"
- "Confirm" button per step
- **NO "Confirm All" button** — it defeats the safety purpose of mandatory review
- Partial sign-off: state is kept local (not PATCHed) until all steps confirmed
  - On dialog close with partial progress: warn "You have N unconfirmed steps. Progress will not be saved."
- On all steps confirmed: PATCH template with updated `transfer_steps` (mandatory_review=False each) and `mandatory_review_count=0`
  - Use `updateExperimentTemplate(id, { template_definition: updatedDefinition })`
  - `active` field is NOT changed here — lab manager activates separately after sign-off

**Post-sign-off transition:**
- Success toast: "Sign-off complete. Template is now ready to activate."
- DataGrid row updates in-place (chip flips from amber to green) without full page reload
- No page redirect

**2c. Template Activation Guard**

- `active` toggle in DataGrid is disabled when `template_definition.mandatory_review_count > 0`
- Tooltip on disabled toggle: "Sign-off required before activating this template"
- When enabled (count = 0), toggle calls `updateExperimentTemplate(id, { active: !row.active })`

---

## Files to Create/Modify

| File | Action | What |
|------|--------|------|
| `frontend/src/pages/ExperimentTemplatesManagement.tsx` | CREATE | Main page (Phase 1 + Phase 2) |
| `frontend/src/services/apiService.ts` | MODIFY | Add `deleteExperimentTemplate(id)` method |
| `frontend/src/App.tsx` | MODIFY | Fix route (line 192) + import |
| `frontend/src/components/Sidebar.tsx` | MODIFY | Fix permission check (line ~280 + any other usage sites) |

No backend changes needed for Phase 1. Phase 2 requires both files at SOP upload — if `instrument_file` needs to be optional, that's a backend task.

---

## Success Criteria

- Lab manager can create an experiment template using a form (no JSON required)
- Lab manager can upload a SOP PDF + instrument CSV and get a pre-filled template (with highlighted fields)
- Robot-affecting fields (transfer steps) require explicit per-step sign-off before template activates
- Template list shows sign-off status chip; templates with pending review cannot be activated
- Route `/experiments/templates` renders the template management page (not the experiments list)
- Delete works (requires `deleteExperimentTemplate` added to apiService)

---

## What's Out of Scope (Phase 3)

- User manual generator (writes to HelpPage from template schema) — deferred until real templates exist
- Visual plate editor (96/384 well grid UI for assigning conditions) — XL effort, premature
- Audit trail for sign-off (who confirmed, when) — check if backend models support it before Phase 2 ships; may be required for regulated environments
