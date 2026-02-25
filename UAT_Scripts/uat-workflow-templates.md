# UAT: Workflow Templates

## Overview

This document defines 12 test cases for the Workflow Templates feature: template CRUD, execution with context (accessioning, batch, results entry), conditional behavior, permission denial, and transaction rollback. Run after `uat-security-rbac` (and optionally `uat-configurations-custom` for list data). Assumes admin user has `config:edit` and `workflow:execute`; test roles with reduced permissions where noted.

## Prerequisites

- Authentication: Valid admin (or user with config:edit and workflow:execute) session.
- At least one list entry for sample status (or use existing seed data) if templates reference status updates.
- Optional: One batch and one test for execution-on-batch and execution-on-results tests.

## Test Cases

### TC-WF-01: Create workflow template (success)

**Objective**: Verify that a user with config:edit can create a new workflow template with valid definition.

**Steps**:
1. Log in as admin (or user with config:edit).
2. Navigate to Admin → Workflow Templates.
3. Click "Add Template".
4. Enter name (e.g. "UAT Test Template"), description (optional), leave Active checked.
5. Set template definition JSON to: `{"steps":[{"action":"update_status","params":{}}]}`.
6. Click Create.

**Expected**:
- Template is created; list refreshes and shows the new template.
- Dialog closes. No error message.

---

### TC-WF-02: Create workflow template (duplicate name)

**Objective**: Verify that creating a template with an existing name returns an error.

**Steps**:
1. Ensure a template named "UAT Duplicate Test" exists (create via TC-WF-01 if not).
2. Click "Add Template".
3. Enter name "UAT Duplicate Test", valid template_definition (e.g. steps with update_status).
4. Click Create.

**Expected**:
- Error message indicating a template with that name already exists (400).
- Template list unchanged; dialog remains open or closes with error shown.

---

### TC-WF-03: Create workflow template (invalid definition)

**Objective**: Verify that template_definition validation rejects invalid actions.

**Steps**:
1. Click "Add Template".
2. Enter unique name; set template definition to `{"steps":[{"action":"invalid_action","params":{}}]}`.
3. Click Create.

**Expected**:
- Validation error (422 or inline error): action must be one of the valid list.
- Template is not created.

---

### TC-WF-04: List workflow templates and filter by active

**Objective**: Verify list and filter by active status.

**Steps**:
1. Create one active and one inactive template (or use existing).
2. Open Workflow Templates page.
3. Call API GET /admin/workflow-templates (or use UI that reflects it).
4. Call GET /admin/workflow-templates?active=true and ?active=false.

**Expected**:
- Unfiltered list includes both templates.
- active=true returns only active; active=false returns only inactive.

---

### TC-WF-05: Get workflow template by ID and 404

**Objective**: Verify get-by-ID and not-found behavior.

**Steps**:
1. Create a template and note its ID (or use first from list).
2. GET /admin/workflow-templates/{id} with valid ID.
3. GET /admin/workflow-templates/{id} with non-existent UUID.

**Expected**:
- Valid ID returns 200 and template body.
- Non-existent ID returns 404.

---

### TC-WF-06: Update workflow template

**Objective**: Verify partial update of template (description, active, template_definition).

**Steps**:
1. Create a template (e.g. name "UAT Update Test", description "Original", active true).
2. Open Edit for that template.
3. Change description to "Updated desc", set Active to false (or change one step in definition).
4. Save.

**Expected**:
- 200 with updated template; list shows new description and active state.

---

### TC-WF-07: Delete (soft-deactivate) workflow template

**Objective**: Verify that delete sets active=false and template is no longer available for execution.

**Steps**:
1. Create an active template.
2. Click Delete (Deactivate) and confirm.
3. Verify template still appears in full list but active=false (or filtered list ?active=false).
4. Attempt to execute that template (e.g. from Apply Template on Accessioning).

**Expected**:
- Template is soft-deactivated (active=false).
- Execute returns 404 or template not offered in active-only dropdown.

---

### TC-WF-08: Execute workflow from Accessioning (sample context)

**Objective**: Verify execution with empty context from Accessioning page and data refresh.

**Steps**:
1. Log in as user with workflow:execute.
2. Navigate to Accessioning.
3. Select a template from "Apply Template" dropdown; click Apply.
4. Wait for success.

**Expected**:
- Request: POST /workflows/execute/{template_id} with body context {} (or omitted).
- 201 with WorkflowInstanceRead; success message shown; lookup data (and optional custom attribute configs) refreshed.

---

### TC-WF-09: Execute workflow from Batch details (batch context)

**Objective**: Verify execution with batch_id context and batch refresh.

**Steps**:
1. Open Batches; open a batch (details view).
2. Select a template from "Apply Template" dropdown; click Apply.
3. Wait for success.

**Expected**:
- Request: POST /workflows/execute/{template_id} with body context { batch_id: selectedBatch.id }.
- 201 returned; success message; batch details re-fetched (e.g. handleViewBatch).

---

### TC-WF-10: Execute workflow from Results Entry (batch and test context)

**Objective**: Verify execution with batch_id and test_id context and parent data refresh.

**Steps**:
1. Open a batch and select a test so Results Entry is visible.
2. In Results Entry toolbar, select template from "Apply Template" and click Apply.
3. Wait for success.

**Expected**:
- Request: POST /workflows/execute/{template_id} with body context { batch_id, test_id }.
- 201 returned; success message; parent refreshes batch data (e.g. loadBatchData).

---

### TC-WF-11: Permission denial (template CRUD vs execute)

**Objective**: Verify RBAC: config:edit required for template list/create; workflow:execute required for execute.

**Steps**:
1. As user with workflow:execute but NOT config:edit: open Admin → Workflow Templates (or GET /admin/workflow-templates).
2. As user with config:edit but NOT workflow:execute: open Accessioning and check for Apply Template control; attempt execute via API POST /workflows/execute/{template_id}.

**Expected**:
- User without config:edit: 403 on template list/create or warning message on Workflow Templates page.
- User without workflow:execute: Apply Template not shown (or disabled); POST execute returns 403.

---

### TC-WF-12: Execute with invalid step (400) and transaction rollback on failure

**Objective**: Verify invalid step returns 400; step failure causes rollback (no workflow instance created).

**Steps**:
1. **Invalid step**: Create a template directly in DB (or via API) with one step action "not_valid_action". Execute it via API. Expect 400 "Invalid action".
2. **Rollback**: (Requires backend that throws in a step or use test_workflows.py.) Run backend test `test_transaction_rollback_on_step_failure`: patch _run_action to raise; POST execute; assert 500 and workflow_instances count unchanged for that template.

**Expected**:
- Invalid action in template → 400; no instance created.
- Step raises exception → 500; transaction rolled back; no new workflow_instance row.

---

## Dependency

| Depends On | Description |
|------------|-------------|
| uat-security-rbac | Permissions config:edit and workflow:execute; roles and auth |
| uat-configurations-custom | Optional; list entries if templates reference statuses |

## Completion Checklist

- [ ] TC-WF-01 Create success
- [ ] TC-WF-02 Duplicate name
- [ ] TC-WF-03 Invalid definition
- [ ] TC-WF-04 List and filter active
- [ ] TC-WF-05 Get by ID / 404
- [ ] TC-WF-06 Update template
- [ ] TC-WF-07 Delete (soft-deactivate)
- [ ] TC-WF-08 Execute from Accessioning
- [ ] TC-WF-09 Execute from Batch details
- [ ] TC-WF-10 Execute from Results Entry
- [ ] TC-WF-11 Permission denial
- [ ] TC-WF-12 Invalid step and rollback
