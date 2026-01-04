# UAT Scripts: Help System

## Overview

This document contains User Acceptance Testing (UAT) scripts for the help system in NimbleLIMS. These scripts validate role-filtered help content, CRUD operations, and contextual help tooltips as defined in:

- **User Stories**: Implied in configs (help system for all roles)
- **UI Document**: `ui-accessioning-to-reporting.md` (HelpPage.tsx, role sections: ClientHelpSection, LabTechHelpSection, LabManagerHelpSection, AdminHelpSection)
- **API Document**: `api_endpoints.md` (GET `/help`, GET `/help/contextual`, POST/PATCH/DELETE `/help/admin/help`)
- **Navigation Document**: `navigation.md` (`/help` route)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Help entries for different roles:
    - At least 2 entries with `role_filter` = "client" (or "Client")
    - At least 2 entries with `role_filter` = NULL (public)
    - At least 1 entry with `role_filter` = "lab-technician" (not visible to Client)
    - At least 1 entry with `role_filter` = "lab-manager" (not visible to Client)
  - Roles: Client, Lab Technician, Lab Manager, Administrator
- Test user accounts:
  - Client user (for role-filtered view test)
  - Administrator with `config:edit` permission (for CRUD test)

---

## Test Case 1: Role-Filtered View - Client Accordion

### Test Case ID
TC-HELP-ROLE-FILTER-001

### Description
Verify that Client users see only Client-specific and public help entries in accordion format, with proper ARIA labels and accessibility features.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Client |
| **Help Entries Seeded** | At least 2 entries with `role_filter` = "client"<br>At least 2 entries with `role_filter` = NULL (public)<br>At least 1 entry with `role_filter` = "lab-technician" (should NOT be visible) |
| **User Logged In** | Client user successfully authenticated |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Client user | User authenticated |
| 2 | Navigate to `/help` route | Help page loads |
| 3 | **Verify Client Help Section Renders** | |
| 3.1 | Verify `ClientHelpSection` component renders | Component visible (not LabTechHelpSection or other role sections) |
| 3.2 | Verify heading displayed | Heading "Help & Support" visible |
| 3.3 | Verify description text | Description: "Find answers to common questions about using NimbleLIMS. Click on a topic below to learn more." |
| 4 | **Verify Help Entries Displayed** | |
| 4.1 | Verify accordion sections visible | Accordion components visible for each help entry |
| 4.2 | Count visible entries | At least 4 entries visible (2 Client + 2 public) |
| 4.3 | Verify Client-specific entries | Entries with sections like "Viewing Projects", "Understanding Statuses" visible |
| 4.4 | Verify public entries visible | Entries with `role_filter` = NULL visible |
| 4.5 | Verify Lab Technician entries NOT visible | Entries with `role_filter` = "lab-technician" NOT visible |
| 5 | **Test Accordion Interaction** | |
| 5.1 | Click on first accordion section | Accordion expands, content displayed |
| 5.2 | Verify content displayed | Help content text visible with proper formatting (line breaks preserved) |
| 5.3 | Click on same accordion section again | Accordion collapses |
| 5.4 | Click on second accordion section | Second accordion expands, first collapses (only one open at a time) |
| 6 | **Verify ARIA Labels** | |
| 6.1 | Inspect accordion elements | ARIA attributes present:<br>- `aria-controls` on AccordionSummary<br>- `aria-expanded` on Accordion<br>- `id` attributes on headers and content |
| 6.2 | Verify expand icon | ExpandMoreIcon has `aria-hidden="true"` |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | GET `/help` called (no role parameter):<br>- Backend automatically filters by current user's role<br>- Backend converts "Client" role name to "client" slug format<br>- Query filters: `role_filter = 'client' OR role_filter IS NULL` |
| **Backend Processing** | 1. **Role Filtering**:<br>   - Get current user's role: "Client"<br>   - Convert to slug: "client"<br>   - Query help entries:<br>     ```sql
     SELECT * FROM help_entries
     WHERE active = true
     AND (role_filter = 'client' OR role_filter IS NULL)
     ORDER BY section, created_at
     ```<br>2. **Response**:<br>   - Returns paginated list of filtered help entries |
| **Help Entries Returned** | - Only entries where:<br>  - `role_filter` = "client" (or "Client" normalized to "client")<br>  - OR `role_filter` IS NULL (public)<br>- Entries with `role_filter` = "lab-technician" NOT returned |
| **UI Display** | - `ClientHelpSection` component renders<br>- Accordion format with Material-UI Accordion components<br>- Each entry displayed as collapsible accordion<br>- Section name as accordion header<br>- Content in accordion details<br>- Only one accordion expanded at a time |
| **ARIA Accessibility** | - Navigation role: `role="navigation"` on container<br>- Labeled heading: `id="client-help-heading"` (if implemented)<br>- Accordion controls:<br>  - `aria-controls` = `"{section}-content"`<br>  - `id` = `"{section}-header"`<br>  - `aria-expanded` = true/false<br>  - `aria-label` = `"{section} help section"`<br>- Expand icon: `aria-hidden="true"` |

### Test Steps - Public Entry Visibility

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Verify Public Entries Visible** | |
| 7.1 | Locate entry with `role_filter` = NULL | Entry visible in accordion list |
| 7.2 | Expand public entry | Content displays correctly |
| 7.3 | Verify entry accessible | Entry accessible to Client user |

### Expected Results - Public Entries

| Category | Expected Outcome |
|----------|------------------|
| **Public Entry Access** | - Entries with `role_filter` = NULL visible to all roles<br>- Client user can access public entries |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| ClientHelpSection component renders | ✓ | ✗ |
| Only Client and public entries visible | ✓ | ✗ |
| Lab Technician entries NOT visible | ✓ | ✗ |
| Accordion format works correctly | ✓ | ✗ |
| Only one accordion expanded at a time | ✓ | ✗ |
| ARIA labels present and correct | ✓ | ✗ |
| Content displays with proper formatting | ✓ | ✗ |
| Backend filters by role correctly | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: CRUD as Admin - Create/Update/Delete Help Entry

### Test Case ID
TC-HELP-CRUD-002

### Description
Verify that administrators with `config:edit` permission can create, update, and delete help entries via the Help Management page.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Administrator |
| **Required Permission** | `config:edit` |
| **Help Management UI** | Help Management page accessible at `/admin/help` |
| **Roles Available** | At least one role exists (e.g., "Lab Technician", "Client") |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Administrator | User authenticated with `config:edit` permission |
| 2 | Navigate to Help Management page (e.g., `/admin/help`) | Help Management page loads |
| 3 | **Verify Page Loads** | |
| 3.1 | Verify DataGrid displays | DataGrid shows all help entries (users with config:edit see ALL entries by default) |
| 3.2 | Verify "Create Help Entry" button | Button visible and enabled |
| 3.3 | Verify search and filter controls | Search field and role filter dropdown visible |
| 4 | **Create Help Entry** | |
| 4.1 | Click "Create Help Entry" button | HelpEntryDialog opens |
| 4.2 | **Enter Help Entry Information** | |
| 4.2.1 | Enter Section: `Test Help Entry` | Field accepts input |
| 4.2.2 | Enter Content: `This is a test help entry for UAT testing. It contains step-by-step instructions.` | Multiline textarea accepts input |
| 4.2.3 | Select Role Filter: `Lab Technician` from dropdown | Role selected (options: Public (No Role), Lab Technician, Lab Manager, Administrator, Client) |
| 4.2.4 | Verify role filter validation | Role filter validated against existing roles |
| 4.3 | Click "Create" or "Save" button | Form submits, loading spinner shown |
| 4.4 | Wait for API response | Success message displayed, dialog closes |
| 4.5 | Verify entry in DataGrid | New entry appears in DataGrid with section "Test Help Entry" |
| 5 | **Update Help Entry** | |
| 5.1 | Click Edit icon on entry | HelpEntryDialog opens with pre-filled data |
| 5.2 | Verify form pre-filled | Section and content fields contain existing values |
| 5.3 | Update Content: `This is an updated test help entry with additional information.` | Field accepts input |
| 5.4 | Verify Active switch visible | Active switch visible (only in edit mode) |
| 5.5 | Click "Save" button | Form submits |
| 5.6 | Verify entry updated | Entry content updated in DataGrid |
| 6 | **Delete Help Entry** | |
| 6.1 | Click Delete icon on entry | Delete confirmation dialog opens |
| 6.2 | Verify confirmation message | Message: "Are you sure you want to delete this help entry?" |
| 6.3 | Click "Confirm" or "Delete" button | Dialog closes, entry soft-deleted |
| 6.4 | Verify entry removed from DataGrid | Entry no longer visible (or marked as inactive) |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call - Create** | POST `/help/admin/help` called with:<br>```json
{
  "section": "Test Help Entry",
  "content": "This is a test help entry for UAT testing. It contains step-by-step instructions.",
  "role_filter": "Lab Technician"
}
``` |
| **Backend Processing - Create** | 1. **Access Control**:<br>   - Verify user has `config:edit` permission<br>2. **Role Filter Validation**:<br>   - Validate `role_filter` against existing roles<br>   - Normalize to slug format: "Lab Technician" → "lab-technician"<br>   - Return 400 if role doesn't exist<br>3. **Help Entry Creation**:<br>   - Create `HelpEntry` record:<br>     - `name` = "Test Help Entry" (from section)<br>     - `section` = "Test Help Entry"<br>     - `content` = "This is a test help entry..."<br>     - `role_filter` = "lab-technician" (normalized)<br>     - `active` = true (default)<br>     - `description` = content summary (first 255 chars)<br>     - `created_by` = current user UUID<br>     - `modified_by` = current user UUID<br>4. **Commit**:<br>   - Commit to database<br>   - Return created entry |
| **Help Entry Record** | - Entry created in `help_entries` table:<br>  - `section` = "Test Help Entry"<br>  - `content` = "This is a test help entry..."<br>  - `role_filter` = "lab-technician" (normalized slug)<br>  - `active` = true<br>  - Audit fields set |
| **API Call - Update** | PATCH `/help/admin/help/{id}` called with:<br>```json
{
  "content": "This is an updated test help entry with additional information.",
  "active": true
}
``` |
| **Backend Processing - Update** | 1. **Access Control**:<br>   - Verify user has `config:edit` permission<br>2. **Entry Lookup**:<br>   - Find help entry by ID<br>   - Return 404 if not found<br>3. **Role Filter Validation** (if updated):<br>   - Validate against existing roles<br>   - Normalize to slug format<br>4. **Update Fields**:<br>   - Update provided fields (partial update)<br>   - Update `modified_by` and `modified_at`<br>5. **Commit**:<br>   - Commit to database<br>   - Return updated entry |
| **API Call - Delete** | DELETE `/help/admin/help/{id}` called |
| **Backend Processing - Delete** | 1. **Access Control**:<br>   - Verify user has `config:edit` permission<br>2. **Entry Lookup**:<br>   - Find help entry by ID<br>   - Return 404 if not found<br>3. **Soft Delete**:<br>   - Set `active` = false<br>   - Update `modified_by` and `modified_at`<br>4. **Commit**:<br>   - Commit to database<br>   - Return 204 No Content |
| **UI Feedback** | - Create: Success message, dialog closes, DataGrid refreshes<br>- Update: Success message, dialog closes, DataGrid refreshes<br>- Delete: Confirmation dialog, entry removed from view, DataGrid refreshes |

### Test Steps - Role Filter Validation (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Invalid Role Filter** | |
| 7.1 | Click "Create Help Entry" | Dialog opens |
| 7.2 | Enter Section: `Invalid Role Test` | Section entered |
| 7.3 | Enter Content: `Test content` | Content entered |
| 7.4 | Enter invalid role filter: `InvalidRole` (doesn't exist) | Role filter entered |
| 7.5 | Click "Create" | Form submits |
| 7.6 | Verify error response | HTTP 400 Bad Request:<br>- Error message: "Invalid role_filter. Must be one of: {list of available roles}"<br>- No entry created |

### Expected Results - Invalid Role Filter

| Category | Expected Outcome |
|----------|------------------|
| **Error Response** | - HTTP 400 Bad Request<br>- Error message lists available roles<br>- No entry created |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Help Management page accessible | ✓ | ✗ |
| All help entries visible (config:edit users) | ✓ | ✗ |
| Create help entry succeeds | ✓ | ✗ |
| Role filter normalized to slug format | ✓ | ✗ |
| Update help entry succeeds | ✓ | ✗ |
| Delete help entry (soft delete) succeeds | ✓ | ✗ |
| Invalid role filter rejected | ✓ | ✗ |
| Audit fields updated correctly | ✓ | ✗ |
| DataGrid refreshes after operations | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Contextual Help Tooltip Check

### Test Case ID
TC-HELP-CONTEXTUAL-003

### Description
Verify that contextual help tooltips display correctly in forms, fetching help content for specific sections via the contextual help endpoint.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Help Entry Exists** | At least one help entry with `section` = "Accessioning Workflow" and `role_filter` matching user's role |
| **Form with Help Icon** | At least one form page with contextual help icon/tooltip (e.g., AccessioningForm, ResultsEntryTable) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician | User authenticated |
| 2 | Navigate to form with contextual help (e.g., `/accessioning`) | Form loads |
| 3 | **Locate Help Icon** | |
| 3.1 | Locate help icon (InfoIcon or HelpOutlineIcon) | Icon visible in form (e.g., next to section heading or field label) |
| 3.2 | Verify icon placement | Icon positioned appropriately (e.g., next to "Accessioning Workflow" heading) |
| 4 | **Test Tooltip Display** | |
| 4.1 | Hover over help icon | Tooltip appears with help content |
| 4.2 | Verify tooltip content | Tooltip displays help content for the section (e.g., "Accessioning Workflow" help text) |
| 4.3 | Verify tooltip formatting | Content formatted correctly (line breaks, readable text) |
| 5 | **Test Contextual Help API** | |
| 5.1 | Inspect network requests (browser DevTools) | API call made: GET `/help/contextual?section=Accessioning Workflow` |
| 5.2 | Verify API response | Response contains help entry for section matching user's role |
| 6 | **Test Missing Help Entry** | |
| 6.1 | Navigate to form with section that has no help entry | Form loads |
| 6.2 | Locate help icon (if present) | Icon visible or not present (depending on implementation) |
| 6.3 | Hover over help icon (if present) | Tooltip shows default message or no tooltip (depending on implementation) |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | GET `/help/contextual?section=Accessioning Workflow` called:<br>- Backend automatically filters by current user's role<br>- Backend converts role name to slug format (e.g., "Lab Technician" → "lab-technician") |
| **Backend Processing** | 1. **Role Filtering**:<br>   - Get current user's role: "Lab Technician"<br>   - Convert to slug: "lab-technician"<br>   - Query help entry:<br>     ```sql
     SELECT * FROM help_entries
     WHERE active = true
     AND section = 'Accessioning Workflow'
     AND (role_filter = 'lab-technician' OR role_filter IS NULL)
     LIMIT 1
     ```<br>2. **Response**:<br>   - Returns help entry if found<br>   - Returns 404 if not found |
| **Help Entry Response** | ```json
{
  "id": "uuid",
  "section": "Accessioning Workflow",
  "content": "Step-by-step guide to sample accessioning:\n\n1. Enter sample details...",
  "role_filter": "lab-technician",
  "active": true
}
```<br>- HTTP 200 OK |
| **Tooltip Display** | - Material-UI Tooltip component displays help content<br>- Tooltip appears on hover<br>- Content formatted with line breaks (`whiteSpace: 'pre-line'`)<br>- Tooltip positioned appropriately (e.g., "top", "right") |
| **ARIA Labels** | - Help icon has `aria-label` attribute:<br>  - Example: `aria-label="Accessioning Workflow help"`<br>- Tooltip accessible to screen readers |

### Test Steps - Different Sections

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Different Sections** | |
| 7.1 | Navigate to Results Entry page | Page loads |
| 7.2 | Locate help icon for "Results Entry" section | Icon visible |
| 7.3 | Hover over icon | Tooltip displays "Results Entry" help content |
| 7.4 | Verify API call | GET `/help/contextual?section=Results Entry` called |

### Expected Results - Different Sections

| Category | Expected Outcome |
|----------|------------------|
| **Section-Specific Help** | - Each section can have its own help entry<br> - Contextual help fetches section-specific content<br> - Tooltip displays relevant content for that section |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Help icon visible in forms | ✓ | ✗ |
| Tooltip displays on hover | ✓ | ✗ |
| Tooltip content matches section | ✓ | ✗ |
| Contextual help API called correctly | ✓ | ✗ |
| Help content filtered by user role | ✓ | ✗ |
| ARIA labels present | ✓ | ✗ |
| Tooltip formatting correct | ✓ | ✗ |
| Missing help entry handled gracefully | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Stories (Implied in Configs)
- Help system provides role-filtered content for all user roles
- Administrators can manage help content via CRUD operations
- Contextual help available in forms for user guidance

### UI Document (HelpPage.tsx, Role Sections)
- **HelpPage.tsx**: Main help page component
  - Conditional rendering based on user role:
    - Client → `ClientHelpSection`
    - Lab Technician → `LabTechHelpSection`
    - Lab Manager → `LabManagerHelpSection`
    - Administrator → `AdminHelpSection`
  - "Manage Help" button visible for users with `config:edit` permission
- **ClientHelpSection.tsx**: Role-filtered help for Client users
  - Displays help entries in accordion format
  - Fetches via GET `/help` (backend auto-filters by role)
  - ARIA labels: `aria-controls`, `aria-expanded`, `id` attributes
- **LabTechHelpSection.tsx**: Role-filtered help for Lab Technician users
  - Accordion format with ARIA labels
  - Loading state: `aria-live="polite"`, `aria-label="Loading help content"`
  - Error handling: `role="alert"`, `aria-live="assertive"`
- **HelpManagement.tsx**: Admin page for CRUD operations
  - DataGrid with search and role filtering
  - Create/Edit/Delete dialogs
  - Role filter dropdown with validation

### API Document (GET /help, GET /help/contextual, CRUD /help/admin/help)
- **GET `/help`**: Get help entries filtered by current user's role
  - Query parameters: `role` (optional, for admins), `section` (optional), `page`, `size`
  - Access control: Users see entries where `role_filter` matches their role OR `role_filter` IS NULL (public)
  - Admins with `config:edit` see ALL entries when no `role` parameter provided
- **GET `/help/contextual`**: Get contextual help for specific section
  - Query parameter: `section` (required)
  - Returns help entry filtered by user's role
  - Returns 404 if no matching entry found
- **POST `/help/admin/help`**: Create help entry
  - Requires: `config:edit` permission
  - Request: `{section, content, role_filter}`
  - Role filter validated against existing roles and normalized to slug format
- **PATCH `/help/admin/help/{id}`**: Update help entry
  - Requires: `config:edit` permission
  - Request: Partial update (all fields optional)
- **DELETE `/help/admin/help/{id}`**: Soft delete help entry
  - Requires: `config:edit` permission
  - Sets `active` = false

### Navigation Document (/help route)
- **Route**: `/help`
- **Component**: `HelpPage`
- **Layout**: `MainLayout`
- **Visibility**: Always visible (no permission required)
- **Description**: Role-filtered help content and documentation

### Schema
- **`help_entries` table**:
  - `id`: UUID PK
  - `name`: String (NOT unique, set from section)
  - `section`: String (NOT NULL)
  - `content`: Text (NOT NULL)
  - `role_filter`: String (nullable, normalized to slug format: "lab-technician", "lab-manager", "administrator", "client")
  - `active`: Boolean (default true)
  - `description`: Text (nullable, summary from content)
  - Audit fields: `created_at`, `created_by`, `modified_at`, `modified_by`
- **Role Filter Values**:
  - NULL = Public (visible to all roles)
  - "client" = Client-specific
  - "lab-technician" = Lab Technician-specific
  - "lab-manager" = Lab Manager-specific
  - "administrator" = Administrator-specific

### Role Filter Normalization
- Backend converts role names to slug format:
  - "Lab Technician" → "lab-technician"
  - "Lab Manager" → "lab-manager"
  - "Administrator" → "administrator"
  - "Client" → "client"
- Case-insensitive matching
- Validated against existing roles in database

### ARIA Accessibility
- **Navigation**: `role="navigation"` on help section containers
- **Headings**: Labeled with `id` attributes (e.g., `id="lab-tech-help-heading"`)
- **Accordions**: 
  - `aria-controls` = `"{section}-content"`
  - `aria-expanded` = true/false
  - `aria-label` = `"{section} help section"`
  - `id` = `"{section}-header"` and `"{section}-content"`
- **Loading States**: `aria-live="polite"`, `aria-label="Loading help content"`
- **Error States**: `role="alert"`, `aria-live="assertive"`
- **Empty States**: `role="status"`, `aria-live="polite"`
- **Help Icons**: `aria-label` attributes for screen readers

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-HELP-ROLE-FILTER-001 | | | | |
| TC-HELP-CRUD-002 | | | | |
| TC-HELP-CONTEXTUAL-003 | | | | |

---

## Appendix: Sample Test Data

### Help Entries
- **Client Entries**:
  - Section: "Viewing Projects"
  - Section: "Understanding Statuses"
  - `role_filter`: "client"
- **Public Entries**:
  - Section: "Getting Started"
  - Section: "System Overview"
  - `role_filter`: NULL
- **Lab Technician Entries**:
  - Section: "Accessioning Workflow"
  - Section: "Results Entry"
  - `role_filter`: "lab-technician"
- **Lab Manager Entries**:
  - Section: "Results Review"
  - Section: "Batch Management"
  - `role_filter`: "lab-manager"

### Roles
- `Client` (role_filter: "client")
- `Lab Technician` (role_filter: "lab-technician")
- `Lab Manager` (role_filter: "lab-manager")
- `Administrator` (role_filter: "administrator")

### Sections
- "Viewing Projects" (Client)
- "Understanding Statuses" (Client)
- "Accessioning Workflow" (Lab Technician)
- "Results Entry" (Lab Technician)
- "Results Review" (Lab Manager)
- "Batch Management" (Lab Manager)
- "User Management" (Administrator)
- "EAV Configuration" (Administrator)

