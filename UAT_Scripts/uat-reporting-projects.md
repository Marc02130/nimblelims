# UAT Scripts: Reporting and Project Management

## Overview

This document contains User Acceptance Testing (UAT) scripts for reporting and project management in NimbleLIMS. These scripts validate the reporting workflow and project access mechanisms as defined in:

- **User Stories**: US-2 (Sample Status Management), US-13 (Role-Based Access Control), US-25 (Client Project Management)
- **PRD**: Section 3.1 (Reporting)
- **Workflow Document**: `workflow-accessioning-to-reporting.md` (Stage 5: Reporting)
- **Schema**: `projects` table with `client_project_id` FK, `project_users` junction table, `samples.report_date` field

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Database seeded with:
  - Sample status list entries: "Received", "Available for Testing", "Testing Complete", "Reviewed", "Reported"
  - At least one sample with status "Reviewed" (all tests complete)
  - At least one client project with multiple linked projects
  - At least one project with samples
  - At least one user with project access via `project_users` junction
- Test user accounts:
  - Lab Manager with `sample:update` permission and project access
  - Lab Technician with project access via `project_users` junction
  - Lab Technician without project access (for RLS test)

---

## Test Case 1: Sample Reporting - Mark Sample as 'Reported'

### Test Case ID
TC-REPORTING-001

### Description
Mark a sample as "Reported" after all tests are reviewed, setting the report_date timestamp.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Manager or Administrator |
| **Required Permission** | `sample:update` |
| **Project Access** | User has access to sample's project |
| **Sample Exists** | At least one sample with status "Reviewed" exists |
| **Sample Readiness** | All tests for sample have status "Complete" |
| **Status Available** | "Reported" status exists in `sample_status` list |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `/samples` route | Samples Management page loads with DataGrid showing accessible samples |
| 2 | **Locate Reviewed Sample** | |
| 2.1 | Filter samples by status: "Reviewed" | DataGrid shows only samples with "Reviewed" status |
| 2.2 | Select sample: `SAMPLE-REVIEWED-001` | Sample row selected |
| 2.3 | Verify sample details | Sample status = "Reviewed", all tests = "Complete" |
| 3 | **Update Status to Reported** | |
| 3.1 | Click "Edit" button or status dropdown | Sample edit dialog opens or status dropdown appears |
| 3.2 | Select status: "Reported" from dropdown | Status "Reported" selected |
| 3.3 | Click "Save" or "Update Status" | Form submits, loading spinner shown |
| 4 | Wait for API response | Success message displayed or sample details view updates |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **API Call** | PATCH `/samples/{sample_id}/status?status_id={reported_status_uuid}` called with:<br>- `sample_id`: UUID of SAMPLE-REVIEWED-001<br>- `status_id`: UUID of "Reported" status |
| **Backend Processing** | 1. Verify sample exists and is active<br>2. Verify status exists in `list_entries`<br>3. Check project access (RLS enforced)<br>4. Update sample status to "Reported"<br>5. **Set report_date**: Current timestamp (datetime.utcnow())<br>6. Update audit fields: `modified_by`, `modified_at`<br>7. Commit transaction |
| **Sample Record** | - Sample updated with:<br>  - `status` = UUID of "Reported" status<br>  - `report_date` = current timestamp (not null)<br>  - `modified_by` = current user UUID<br>  - `modified_at` = current timestamp |
| **UI Feedback** | - Success message displayed<br>- Sample status updated in DataGrid to "Reported"<br>- report_date visible in sample details view<br>- Sample no longer appears in "Reviewed" filter |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Sample status updated to "Reported" | ✓ | ✗ |
| report_date set to current timestamp | ✓ | ✗ |
| report_date is not null | ✓ | ✗ |
| Audit fields updated (modified_by, modified_at) | ✓ | ✗ |
| Sample visible in "Reported" status filter | ✓ | ✗ |
| Sample no longer visible in "Reviewed" filter | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Client Project Grouping - Reporting Aggregation

### Test Case ID
TC-PROJECT-GROUPING-002

### Description
Verify that multiple projects linked to a client project can be aggregated for reporting purposes.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Manager or Administrator |
| **Required Permission** | `sample:read`, `project:manage` |
| **Client Project Exists** | At least one client project exists (e.g., "Client Project Alpha") |
| **Linked Projects** | At least two projects linked to client project via `client_project_id` FK |
| **Samples in Projects** | Each linked project has at least one sample (some with status "Reported") |
| **Project Access** | User has access to all linked projects |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to client projects page (e.g., `/client-projects`) | Client projects list loads |
| 2 | **Select Client Project** | |
| 2.1 | Locate client project: `CLIENT-PROJECT-ALPHA` | Client project visible in list |
| 2.2 | Click on client project or "View Details" | Client project details view opens |
| 3 | **View Linked Projects** | |
| 3.1 | Navigate to "Linked Projects" section | Section displays list of projects with `client_project_id` = CLIENT-PROJECT-ALPHA |
| 3.2 | Verify projects listed | At least two projects displayed (e.g., "Project Alpha-1", "Project Alpha-2") |
| 4 | **Verify Reporting Aggregation** | |
| 4.1 | Navigate to reporting/dashboard view (if available) | Reporting view loads |
| 4.2 | Filter by client project: `CLIENT-PROJECT-ALPHA` | Filter applied |
| 4.3 | View aggregated statistics | Statistics show:<br>- Total samples across all linked projects<br>- Samples by status (including "Reported")<br>- Total reported samples aggregated |
| 4.4 | Verify sample list | Sample list shows samples from all linked projects |
| 5 | **Verify Project-Level Access** | |
| 5.1 | Navigate to `/samples` route | Samples Management page loads |
| 5.2 | Filter by client project (if available) or by individual projects | Samples from all linked projects visible |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Client Project Structure** | - Client project exists with `id`, `name`, `client_id`<br>- Multiple projects have `client_project_id` = client project UUID<br>- Projects linked via FK relationship |
| **Database Query** | Query for samples across client project:<br>```sql
SELECT s.* FROM samples s
JOIN projects p ON s.project_id = p.id
WHERE p.client_project_id = '{client_project_uuid}'
AND s.active = true
```<br>Returns samples from all linked projects |
| **Aggregation Results** | - Total samples: Sum of samples from all linked projects<br>- Reported samples: Count of samples with status "Reported" across all projects<br>- Status breakdown: Aggregated counts per status |
| **RLS Access** | - User can access samples from all linked projects<br>  - Via `has_project_access()` function checking `client_project_id`<br>  - Or via direct `project_users` access to each project |
| **UI Display** | - Client project details show linked projects count<br>- Reporting view aggregates data across linked projects<br>- Sample list includes samples from all linked projects when filtered by client project |

### Test Steps - Create Client Project Link (Optional)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Link Additional Project** (if testing creation) | |
| 6.1 | Navigate to project edit page | Project edit form loads |
| 6.2 | Select client project: `CLIENT-PROJECT-ALPHA` from dropdown | Client project selected |
| 6.3 | Click "Save" | Project updated with `client_project_id` set |
| 6.4 | Verify link created | Project now appears in client project's linked projects list |

### Expected Results - Project Linking

| Category | Expected Outcome |
|----------|------------------|
| **Project Update** | - Project `client_project_id` updated to client project UUID<br>- Audit fields updated |
| **Access Control** | - Users with access to client project can now access linked project<br>  - Via `has_project_access()` function logic |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Client project exists with linked projects | ✓ | ✗ |
| Multiple projects linked via client_project_id FK | ✓ | ✗ |
| Reporting aggregates samples across linked projects | ✓ | ✗ |
| Sample list shows samples from all linked projects | ✓ | ✗ |
| RLS allows access to samples from linked projects | ✓ | ✗ |
| Project can be linked to client project via edit | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Project Access via project_users Junction

### Test Case ID
TC-PROJECT-ACCESS-003

### Description
Verify that lab users can access projects and their data via the `project_users` junction table, with RLS enforcement.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician or Lab Manager |
| **Required Permission** | `sample:read` (or appropriate read permission) |
| **Project Exists** | At least one project exists (e.g., "Project Beta") |
| **Project Access Granted** | User has entry in `project_users` junction table:<br>- `project_id` = Project Beta UUID<br>- `user_id` = test user UUID |
| **Samples in Project** | Project Beta has at least one sample |
| **No Direct Client Access** | User does not have `client_id` matching project's client (for lab user test) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician with project access | User authenticated, dashboard loads |
| 2 | **Verify Project Access** | |
| 2.1 | Navigate to `/projects` route | Projects list page loads |
| 2.2 | Verify project visible | "Project Beta" visible in projects list |
| 2.3 | Click on "Project Beta" | Project details view opens |
| 3 | **Verify Sample Access** | |
| 3.1 | Navigate to `/samples` route | Samples Management page loads |
| 3.2 | Filter by project: "Project Beta" | Filter applied |
| 3.3 | Verify samples visible | Samples from Project Beta visible in DataGrid |
| 3.4 | Click on a sample | Sample details view opens |
| 4 | **Verify RLS Enforcement** | |
| 4.1 | Navigate to `/samples` route | Samples Management page loads |
| 4.2 | Verify no samples from inaccessible projects | Samples from projects without `project_users` entry not visible |
| 5 | **Test API Access** | |
| 5.1 | Make API call: GET `/samples?project_id={project_beta_uuid}` | API returns samples from Project Beta only |
| 5.2 | Verify response | Response contains only samples from accessible projects |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **project_users Junction** | - Entry exists in `project_users` table:<br>  - `project_id` = Project Beta UUID<br>  - `user_id` = test user UUID<br>  - `access_level` = optional (nullable)<br>  - `granted_at` = timestamp<br>  - `granted_by` = optional (nullable) |
| **RLS Function** | `has_project_access(project_uuid)` function:<br>1. Checks if user is Administrator → return TRUE<br>2. If project has `client_project_id`, checks client access<br>3. **Falls back to `project_users` check**:<br>   ```sql
   RETURN EXISTS (
       SELECT 1 FROM project_users pu
       WHERE pu.project_id = project_uuid
       AND pu.user_id = current_user_id()
   );
   ```<br>Returns TRUE if entry exists |
| **Database Queries** | - Projects query filtered by RLS:<br>  - Lab users see projects where `has_project_access(project.id)` = TRUE<br>  - Samples query filtered by accessible projects:<br>  - Lab users see samples where `has_project_access(sample.project_id)` = TRUE |
| **API Responses** | - GET `/projects`: Returns only accessible projects<br>- GET `/samples?project_id={uuid}`: Returns samples if project accessible<br>- GET `/samples`: Returns samples from all accessible projects |
| **UI Display** | - Projects list shows only accessible projects<br>- Samples list shows only samples from accessible projects<br>- Project details view accessible<br>- Sample details view accessible |

### Test Steps - Access Denial (Negative Test)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6 | **Test Inaccessible Project** | |
| 6.1 | Log in as Lab Technician without project access | User authenticated |
| 6.2 | Navigate to `/projects` route | Projects list loads |
| 6.3 | Verify inaccessible project not visible | Project without `project_users` entry not in list |
| 6.4 | Attempt API call: GET `/samples?project_id={inaccessible_project_uuid}` | API call made |
| 6.5 | Verify response | Response returns empty list or 403 Forbidden (depending on implementation) |
| 6.6 | Attempt direct sample access: GET `/samples/{sample_id}` (from inaccessible project) | API call made |
| 6.7 | Verify response | HTTP 403 Forbidden or 404 Not Found (RLS enforced) |

### Expected Results - Access Denial

| Category | Expected Outcome |
|----------|------------------|
| **RLS Enforcement** | - `has_project_access()` returns FALSE for inaccessible project<br>- Database queries filtered by RLS return no rows<br>- API endpoints return 403 or empty results |
| **Error Response** | - HTTP 403 Forbidden with message: "Access denied: insufficient project permissions"<br>- Or HTTP 404 Not Found (if RLS hides record) |
| **UI Behavior** | - Inaccessible projects not visible in UI<br>- Inaccessible samples not visible in UI<br>- Error message displayed if direct access attempted |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| project_users entry exists | ✓ | ✗ |
| User can access project via project_users | ✓ | ✗ |
| User can view samples from accessible project | ✓ | ✗ |
| RLS function checks project_users correctly | ✓ | ✗ |
| Inaccessible projects not visible | ✓ | ✗ |
| API returns 403 for inaccessible data | ✓ | ✗ |
| Database queries filtered by RLS | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### User Story US-2 (Sample Status Management)
- **As a** Lab Technician or Lab Manager
- **I want** to update sample statuses throughout the lifecycle
- **So that** progress is tracked accurately
- **Acceptance Criteria**:
  - Statuses: Received, Available for Testing, Testing Complete, Reviewed, Reported (from lists)
  - Updates trigger audit logs
  - Filtered views by status/project
  - API: PATCH `/samples/{id}/status`; RBAC: `sample:update`

### User Story US-13 (Role-Based Access Control)
- **As an** Administrator
- **I want** to manage roles and granular permissions
- **So that** access is controlled
- **Acceptance Criteria**:
  - 17 permissions (e.g., sample:create, result:review, batch:manage) via junctions
  - Roles: Admin (all), Lab Manager (review/manage), Technician (create/enter), Client (read own)
  - API: CRUD /roles, /permissions (admin-only)
  - Project access via `project_users` junction

### User Story US-25 (Client Project Management)
- **As a** Lab Manager
- **I want** to group multiple NimbleLIMS projects under a client project
- **So that** ongoing submissions for the same client initiative can be tracked holistically
- **Acceptance Criteria**:
  - CRUD for client_projects (name, description, client_id, status)
  - Link NimbleLIMS projects via `client_project_id` FK
  - Accessioning allows selection/creation of client project before NimbleLIMS project
  - **Reporting aggregates across linked projects**
  - API: CRUD `/client-projects`; RBAC: `project:manage`

### PRD Section 3.1 (Reporting)
- **Sample Tracking**: Status management includes "Reported" status
- **Reporting**: Mark sample as reported to client; set `report_date` timestamp
- **Data Model**: Samples table includes `report_date` field (DateTime, nullable)

### Workflow Document (Stage 5: Reporting)
- **Purpose**: Mark sample as reported to client
- **Actors**: Lab Manager, Administrator
- **Steps**:
  1. Verify sample readiness (status "Reviewed", all tests "Complete")
  2. Mark as Reported:
     - Update sample status to "Reported"
     - Set `report_date` (current timestamp)
     - Optionally generate report (post-MVP)
- **Status Transitions**: Sample: "Reviewed" → "Reported"
- **Final State**: Sample lifecycle complete, all tests complete and reviewed, results available for client viewing

### Technical Document (PATCH /samples/{id}/status)
- **Purpose**: Update sample status (e.g., to "Reported")
- **Request**: Query parameter `status_id: UUID`
- **Response**: `SampleResponse`
- **Implementation**: `backend/app/routers/samples.py::update_sample_status()`
- **Processing Steps**:
  1. Verify sample exists
  2. Verify status exists in `list_entries`
  3. Update sample status
  4. **Set report_date if status is "Reported"** (implementation detail)
  5. Update audit fields
  6. Return updated sample

### Schema
- **`projects` table**:
  - `client_project_id`: UUID FK to `client_projects.id` (nullable)
  - Links multiple projects to a client project for aggregation
- **`project_users` junction table**:
  - `project_id`: UUID FK to `projects.id` (primary key)
  - `user_id`: UUID FK to `users.id` (primary key)
  - `access_level`: UUID FK to `list_entries.id` (nullable)
  - `granted_at`: DateTime
  - `granted_by`: UUID FK to `users.id` (nullable)
  - Composite primary key: (project_id, user_id)
- **`samples` table**:
  - `report_date`: DateTime (nullable)
  - Set when sample status changes to "Reported"
- **`client_projects` table**:
  - `id`: UUID (primary key)
  - `name`: String (unique)
  - `description`: Text (nullable)
  - `client_id`: UUID FK to `clients.id`
  - `active`: Boolean
  - Audit fields: `created_at`, `created_by`, `modified_at`, `modified_by`

### RLS Function: has_project_access()
```sql
CREATE OR REPLACE FUNCTION has_project_access(project_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    project_client_project_id UUID;
    project_client_id UUID;
    user_client_id UUID;
BEGIN
    -- Admin users can access all projects
    IF is_admin() THEN
        RETURN TRUE;
    END IF;
    
    -- Get the project's client_project_id and client_id
    SELECT p.client_project_id, p.client_id INTO project_client_project_id, project_client_id
    FROM projects p
    WHERE p.id = project_uuid;
    
    -- If project has a client_project_id, check access via client_projects
    IF project_client_project_id IS NOT NULL THEN
        -- Get user's client_id
        SELECT u.client_id INTO user_client_id
        FROM users u
        WHERE u.id = current_user_id();
        
        -- Check if user's client_id matches the client_project's client_id
        IF user_client_id IS NOT NULL THEN
            IF EXISTS (
                SELECT 1 FROM client_projects cp
                WHERE cp.id = project_client_project_id
                AND cp.client_id = user_client_id
            ) THEN
                RETURN TRUE;
            END IF;
        END IF;
    END IF;
    
    -- Fall back to direct project access check (for lab technicians or direct grants)
    RETURN EXISTS (
        SELECT 1 FROM project_users pu
        WHERE pu.project_id = project_uuid
        AND pu.user_id = current_user_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-REPORTING-001 | | | | |
| TC-PROJECT-GROUPING-002 | | | | |
| TC-PROJECT-ACCESS-003 | | | | |

---

## Appendix: Sample Test Data

### Sample Names
- `SAMPLE-REVIEWED-001` (status "Reviewed", ready for reporting)

### Client Projects
- `CLIENT-PROJECT-ALPHA` (client project with multiple linked projects)

### Projects
- `Project Alpha-1` (linked to CLIENT-PROJECT-ALPHA)
- `Project Alpha-2` (linked to CLIENT-PROJECT-ALPHA)
- `Project Beta` (accessible via project_users junction)

### Sample Statuses
- `Reviewed` (prerequisite for reporting)
- `Reported` (final status after reporting)

### Users
- Lab Manager (with `sample:update` permission)
- Lab Technician with project access (via project_users)
- Lab Technician without project access (for negative test)

