# UAT Experiment Results

**Run Date:** 2026-02-26 05:05:45
**Passed:** 31/31 ✅  **Failed:** 0 ❌

| TC | Description | Status | Details |
|-----|-------------|--------|--------|
| NAV-01 | Admin can list experiments | ✅ PASS | HTTP 200 |
| NAV-02 | Admin can list experiment templates | ✅ PASS | HTTP 200 |
| NAV-03 | Lab Tech can list experiments (has experiment:manage) | ✅ PASS | HTTP 200 |
| NAV-04 | Lab Tech experiment templates access | ✅ PASS | HTTP 200 |
| NAV-05 | Lab Manager can list experiments | ✅ PASS | HTTP 200 |
| NAV-06 | Client denied experiments (no experiment:manage) | ✅ PASS | HTTP 403 |
| NAV-ROUTE-/experiments | Frontend route /experiments returns 200 | ✅ PASS | HTTP 200 |
| NAV-ROUTE-/experiments/templates | Frontend route /experiments/templates returns 200 | ✅ PASS | HTTP 200 |
| EXP-TPL-01 | Create experiment template | ✅ PASS | id=dc7ee306-d491-4844-bee7-298e112be3ec |
| EXP-TPL-02 | List experiment templates | ✅ PASS | total=3 |
| EXP-TPL-03 | Get template by ID | ✅ PASS | HTTP 200 |
| EXP-TPL-04 | Update experiment template | ✅ PASS |  |
| EXP-01 | Create experiment | ✅ PASS | id=287c3ebb-d04a-47b6-89c0-1edef0191e89 |
| EXP-02 | List experiments | ✅ PASS | total=2 |
| EXP-03 | My Experiments filter (mine=true) | ✅ PASS | total=2 |
| EXP-04 | Get experiment by ID (detail) | ✅ PASS |  |
| EXP-05 | Update experiment | ✅ PASS |  |
| EXP-06 | Get non-existent experiment returns 404 | ✅ PASS | HTTP 404 |
| EXP-07 | Add experiment detail step | ✅ PASS |  |
| EXP-08 | Link sample to experiment | ✅ PASS |  |
| EXP-09 | Get sample's experiments (bidirectional link) | ✅ PASS | total=2 |
| EXP-10 | Link experiments together | ✅ PASS |  |
| EXP-11 | Get experiment lineage | ✅ PASS | linked_ids=['1150ac5e-0d0f-410a-a79f-d830378c8513'] |
| EXP-12 | Soft-delete experiment | ✅ PASS |  |
| EXP-TPL-05 | Soft-delete experiment template | ✅ PASS |  |
| EXP-WF-create_experiment | Workflow action 'create_experiment' accepted in template | ✅ PASS | HTTP 201 |
| EXP-WF-create_experiment_from_template | Workflow action 'create_experiment_from_template' accepted in template | ✅ PASS | HTTP 201 |
| EXP-WF-link_sample_to_experiment | Workflow action 'link_sample_to_experiment' accepted in template | ✅ PASS | HTTP 201 |
| EXP-WF-add_experiment_detail_step | Workflow action 'add_experiment_detail_step' accepted in template | ✅ PASS | HTTP 201 |
| EXP-WF-link_experiments | Workflow action 'link_experiments' accepted in template | ✅ PASS | HTTP 201 |
| EXP-WF-update_experiment_status | Workflow action 'update_experiment_status' accepted in template | ✅ PASS | HTTP 201 |
