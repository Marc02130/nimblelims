# UAT Workflow Templates Results

**Run Date:** 2026-02-25 03:29:29
**Passed:** 16/16 ✅  **Failed:** 0 ❌

| Test Case | Description | Status | Details |
|-----------|-------------|--------|--------|
| TC-WF-01 | Create workflow template (success) | ✅ PASS | id=6f0e0289-1e46-4991-9aab-a0f6dc5c7ad1 |
| TC-WF-02 | Create template (duplicate name) rejected | ✅ PASS |  |
| TC-WF-03 | Create template (invalid definition) rejected | ✅ PASS | HTTP 422 |
| TC-WF-04 | List and filter by active | ✅ PASS | all=7, active=2, inactive=5 |
| TC-WF-05a | Get template by valid ID | ✅ PASS |  |
| TC-WF-05b | Get template by non-existent ID returns 404 | ✅ PASS |  |
| TC-WF-06 | Update template (description + active) | ✅ PASS |  |
| TC-WF-07 | Delete (soft-deactivate) template | ✅ PASS |  |
| TC-WF-08 | Execute workflow (accessioning context) | ✅ PASS | instance=46752465-f54a-4742-89b6-8d849c2a115c |
| TC-WF-09 | Execute workflow (batch context) | ✅ PASS |  |
| TC-WF-10 | Execute workflow (batch + test context) | ✅ PASS |  |
| TC-WF-11a | Lab Tech denied template CRUD (no config:edit) | ✅ PASS |  |
| TC-WF-11b | Lab Tech can execute workflow (has workflow:execute) | ✅ PASS |  |
| TC-WF-11c | Client denied workflow execute (no workflow:execute) | ✅ PASS |  |
| TC-WF-12a | Invalid action rejected at creation (400/422) | ✅ PASS | HTTP 422 — validation at create time |
| TC-WF-12b | Execute deactivated template returns 404 | ✅ PASS |  |
