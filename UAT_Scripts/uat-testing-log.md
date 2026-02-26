# UAT Testing Log

## Script Dependency Order

The UAT scripts should be run in the following order based on their dependencies:

| Order | Script | Dependencies | Description |
|-------|--------|--------------|-------------|
| 1 | `uat-security-rbac` | None | Foundation - authentication, permissions, RLS policies |
| 2 | `uat-navigation-ui` | uat-security-rbac | Sidebar navigation, permission gating, responsive design |
| 3 | `uat-configurations-custom` | uat-security-rbac | Lists management (full CRUD), custom fields configuration |
| 4 | `uat-help-system` | uat-security-rbac | Help system, role-based help content |
| 5 | `uat-analysis-analyte-management` | uat-security-rbac | Analyses/Analytes CRUD, expandable linked analytes grid, linking/unlinking |
| 6 | `uat-container-management` | uat-configurations-custom | Container types, hierarchical containers, pooling |
| 7 | `uat-sample-accessioning` | uat-configurations-custom, uat-container-management | Single sample accessioning with containers and tests |
| 8 | `uat-test-ordering` | uat-sample-accessioning, uat-analysis-analyte-management | Test assignment, test batteries, status management |
| 9 | `uat-sample-status-editing` | uat-sample-accessioning | Sample editing, status transitions |
| 10 | `uat-batch-management` | uat-sample-accessioning, uat-container-management | Batch creation, cross-project batching, QC generation, **sample prioritization** |
| 11 | `uat-aliquots-qc` | uat-sample-accessioning | Aliquot creation, QC sample workflows |
| 12 | `uat-results-entry-review` | uat-batch-management | Results entry, validation, review workflow |
| 13 | `uat-bulk-enhancements` | uat-sample-accessioning, uat-batch-management | Bulk accessioning, batch operations |
| 14 | `uat-reporting-projects` | uat-results-entry-review | Reporting, project management, client views |
| 15 | `uat-workflow-templates` | uat-security-rbac | Workflow template CRUD, execute (accessioning/batch/results), RBAC, rollback |
| 16 | `uat-experiments-navigation` | uat-security-rbac | Sidebar Experiments accordion visibility, Experiment Templates gating (admin vs Lab Tech/Manager) |
| 17 | `uat-experiment-management` | uat-security-rbac, uat-sample-accessioning (optional for link) | Experiment CRUD, list/detail, linking sample↔experiment, workflow integration, lineage, My Experiments filter |

## Dependency Diagram

```
uat-security-rbac (Foundation)
├── uat-navigation-ui
├── uat-help-system
├── uat-workflow-templates (Workflow template CRUD, execute, RBAC)
├── uat-analysis-analyte-management (Analyses/Analytes CRUD, linking)
│   └── uat-test-ordering (uses analyses for test assignment)
└── uat-configurations-custom (Lists, Custom Fields)
    ├── uat-container-management
    │   └── uat-sample-accessioning
    │       ├── uat-test-ordering
    │       ├── uat-sample-status-editing
    │       ├── uat-aliquots-qc
    │       └── uat-batch-management
    │           └── uat-results-entry-review
    │               └── uat-reporting-projects
    └── uat-bulk-enhancements (requires sample-accessioning + batch-management)
├── uat-experiments-navigation (Experiments accordion, Templates gating)
└── uat-experiment-management (Experiment CRUD, linking, workflow, lineage; optional: uat-sample-accessioning)
```

## Recommended Next Script

After completing `uat-configurations-custom`, the recommended next scripts are:
- **`uat-security-rbac`** - If not yet completed (foundational)
- **`uat-container-management`** - Builds on lists/configurations for container workflows
- **`uat-help-system`** - Can run in parallel (independent after security)

---

## Latest Run Summary

**Run date:** 2026-02-24  
**Total tests:** 65 | **Passed:** 64 ✅ | **Failed:** 0 ❌ | **Skipped:** 1 ⏭️  
*See `uat_results.md` for full detailed results.*

## Completion Log

| Date | Script | Status | Tester | Notes |
|------|--------|--------|--------|-------|
| 2026-02-24 | uat-security-rbac | ✅ Complete | | 14/14 passed; admin, lab-tech, lab-manager, client logins; RBAC & RLS |
| 2026-02-24 | uat-navigation-ui | ⚠️ Partial | | 5/5 run passed; 1 skipped (sidebar/permission gating – browser-only) |
| 2026-02-24 | uat-configurations-custom | ✅ Complete | | 8/8 passed; lists CRUD, custom fields, name templates |
| 2026-02-24 | uat-help-system | ✅ Complete | | 5/5 passed; help CRUD, contextual endpoint |
| 2026-02-24 | uat-analysis-analyte-management | ✅ Complete | | 6/6 passed; analyses/analytes, linked analytes |
| 2026-02-24 | uat-container-management | ✅ Complete | | 3/3 passed; container types, hierarchy, list |
| 2026-02-24 | uat-sample-accessioning | ✅ Complete | | 4/4 passed; sample create, detail, verify |
| 2026-02-24 | uat-test-ordering | ✅ Complete | | 3/3 passed; test assignment, batteries |
| 2026-02-24 | uat-sample-status-editing | ✅ Complete | | 2/2 passed; description & status update |
| 2026-02-24 | uat-batch-management | ✅ Complete | | 3/3 passed; batch create, list, detail |
| 2026-02-24 | uat-aliquots-qc | ✅ Complete | | 2/2 passed; aliquot create, endpoint |
| 2026-02-24 | uat-results-entry-review | ✅ Complete | | 2/2 passed; results list, entry endpoint |
| 2026-02-24 | uat-bulk-enhancements | ✅ Complete | | 1/1 passed; bulk endpoint |
| 2026-02-24 | uat-reporting-projects | ✅ Complete | | 6/6 passed; projects, client-projects, clients, units, roles, permissions |
| | uat-workflow-templates | ⬜ Pending | | Template CRUD, execute, RBAC, rollback (see UAT_Scripts/uat-workflow-templates.md) |
| | uat-experiments-navigation | ⬜ Pending | | Sidebar Experiments section visibility & Templates gating (see below) |
| | uat-experiment-management | ⬜ Pending | | Experiment CRUD, linking, workflow integration, lineage (see below) |

---

## UAT Script: Sidebar Navigation — Experiments Section Visibility & Templates Gating

**Prerequisites:** uat-security-rbac (roles and permissions). Default logins: admin/admin123, lab-tech/labtech123, lab-manager/labmanager123, client/client123.

**Objective:** Verify the Experiments accordion appears for the correct roles and that "Experiment Templates" is hidden from non-admins.

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as **Administrator** | Sidebar shows **Experiments** accordion (between Sample Mgmt and Lab Mgmt). |
| 2 | Expand Experiments | Sub-items: **All Experiments**, **Experiment Templates**. |
| 3 | Click "All Experiments" | Navigate to `/experiments`; list page loads; AppBar title "Experiments". |
| 4 | Click "Experiment Templates" | Navigate to `/experiments/templates`; AppBar title "Experiment Templates". |
| 5 | Log in as **Lab Manager** | Sidebar shows **Experiments** accordion. |
| 6 | Expand Experiments | Only **All Experiments** visible; **Experiment Templates** not shown. |
| 7 | Log in as **Lab Technician** | Same as Lab Manager: Experiments accordion with only "All Experiments". |
| 8 | Log in as **Client** | **Experiments** accordion not visible in sidebar. |
| 9 | As Client, navigate directly to `/experiments` | Redirect to `/dashboard` (permission redirect). |
| 10 | As Lab Tech, navigate to `/experiments/templates` | Redirect to `/dashboard` (no config:edit or experiment_template:manage). |

**Pass criteria:** Admins see both sub-items; Lab Manager and Lab Technician see only "All Experiments"; Client does not see Experiments section; direct URL access respects permission redirects.

---

## UAT Script: Experiment Management (CRUD, Linking, Workflow, Lineage)

**Prerequisites:** uat-security-rbac; optional uat-sample-accessioning (for linking samples to experiments). Log in as admin or lab-manager/lab-tech with experiment:manage.

**Objective:** Verify experiment list/detail, create/update, sample↔experiment linking, "My Experiments" filter, lineage view, and workflow actions (create_experiment, link_sample_to_experiment, etc.).

### List & filters

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Go to **Experiments** → All Experiments | List loads with pagination; Status and Type (Template) filters work. |
| 2 | Click **My Experiments** chip | URL gets `?mine=true`; list shows only experiments created by current user. |
| 3 | Click chip again | `mine` removed from URL; full list restored. |

### CRUD

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4 | Click **New Experiment** | Create dialog opens; name (required), description, template, status. |
| 5 | Submit with name only | Experiment created; redirect to `/experiments/:id` (detail view). |
| 6 | On detail, verify tabs | Overview, Sample Executions, Details/Steps, Lineage, Linked Processes. |
| 7 | Edit experiment (if UI exposed) | PATCH updates name/description/status/template. |

### Sample ↔ experiment linking

| Step | Action | Expected Result |
|------|--------|-----------------|
| 8 | From experiment detail, **Sample Executions** tab | Table of linked samples; link to sample opens `/samples?highlight=<sample_id>` (bidirectional). |
| 9 | Open a sample that is linked to an experiment | Sample detail shows "Participated in these Experiments" with link to `/experiments/:id`. |
| 10 | From Samples list, open URL `/samples?highlight=<id>` | Sample view dialog opens for that ID (bidirectional link from Experiments). |

### Lineage

| Step | Action | Expected Result |
|------|--------|-----------------|
| 11 | On experiment detail, open **Lineage** tab | Loading state then template (if any) and linked experiment IDs; expandable linked experiments. |
| 12 | Experiment with no template and no links | Message "No template or linked experiments." or equivalent. |

### Workflow integration

| Step | Action | Expected Result |
|------|--------|-----------------|
| 13 | In **Admin** → Workflow Templates, create or open a template | Steps JSON can include actions: `create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `update_experiment_status`. |
| 14 | Execute a template that includes `create_experiment_from_template` (with valid experiment_template_id in params) | Execution succeeds; context includes `experiment_id` for downstream steps. |
| 15 | Execute step `link_sample_to_experiment` (experiment_id from context, sample_id in params) | Sample linked to experiment; context includes `execution_id` (experiment_sample_execution id). |

### Back button & titles

| Step | Action | Expected Result |
|------|--------|-----------------|
| 16 | On experiment detail page | AppBar shows back button (←); click navigates to `/experiments`. |
| 17 | Page titles | List: "Experiments"; detail: "Experiment Detail"; templates route: "Experiment Templates". |

**Pass criteria:** List, filters, CRUD, bidirectional sample↔experiment links, lineage display, and workflow actions behave as above; no regression in Sample Mgmt, Lab Mgmt, or Admin sections.

---

## Notes

- Scripts can be run out of order if prerequisites are manually set up in the database
- Some scripts can run in parallel if they don't share dependencies (e.g., `uat-navigation-ui` and `uat-help-system`)
- Failed tests in foundational scripts (security, configurations) may cause cascading failures in dependent scripts

---

## Summary — Files Created/Modified (UAT log and scripts)

**This file (`UAT_Scripts/uat-testing-log.md`) modified:**
- Added script dependency rows for `uat-experiments-navigation` and `uat-experiment-management`.
- Updated dependency diagram to include both scripts.
- Added Completion Log rows (pending) for both.
- Added full **UAT Script: Sidebar Navigation — Experiments Section Visibility & Templates Gating** (steps 1–10).
- Added full **UAT Script: Experiment Management (CRUD, Linking, Workflow, Lineage)** (steps 1–17 across list/filters, CRUD, sample↔experiment linking, lineage, workflow integration, back button & titles).
- Added this Summary: the only file modified for the UAT log and script content is `UAT_Scripts/uat-testing-log.md`.
