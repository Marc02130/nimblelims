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

---

## Notes

- Scripts can be run out of order if prerequisites are manually set up in the database
- Some scripts can run in parallel if they don't share dependencies (e.g., `uat-navigation-ui` and `uat-help-system`)
- Failed tests in foundational scripts (security, configurations) may cause cascading failures in dependent scripts
