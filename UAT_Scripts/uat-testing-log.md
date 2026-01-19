# UAT Testing Log

## Script Dependency Order

The UAT scripts should be run in the following order based on their dependencies:

| Order | Script | Dependencies | Description |
|-------|--------|--------------|-------------|
| 1 | `uat-security-rbac` | None | Foundation - authentication, permissions, RLS policies |
| 2 | `uat-navigation-ui` | uat-security-rbac | Sidebar navigation, permission gating, responsive design |
| 3 | `uat-configurations-custom` | uat-security-rbac | Lists management (full CRUD), custom fields configuration |
| 4 | `uat-help-system` | uat-security-rbac | Help system, role-based help content |
| 5 | `uat-container-management` | uat-configurations-custom | Container types, hierarchical containers, pooling |
| 6 | `uat-sample-accessioning` | uat-configurations-custom, uat-container-management | Single sample accessioning with containers and tests |
| 7 | `uat-test-ordering` | uat-sample-accessioning | Test assignment, test batteries, status management |
| 8 | `uat-sample-status-editing` | uat-sample-accessioning | Sample editing, status transitions |
| 9 | `uat-batch-management` | uat-sample-accessioning, uat-container-management | Batch creation, cross-project batching, QC generation |
| 10 | `uat-aliquots-qc` | uat-sample-accessioning | Aliquot creation, QC sample workflows |
| 11 | `uat-results-entry-review` | uat-batch-management | Results entry, validation, review workflow |
| 12 | `uat-bulk-enhancements` | uat-sample-accessioning, uat-batch-management | Bulk accessioning, batch operations |
| 13 | `uat-reporting-projects` | uat-results-entry-review | Reporting, project management, client views |

## Dependency Diagram

```
uat-security-rbac (Foundation)
├── uat-navigation-ui
├── uat-help-system
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

## Completion Log

| Date | Script | Status | Tester | Notes |
|------|--------|--------|--------|-------|
| 2026-01-19 | uat-configurations-custom | ✅ Complete | | Lists CRUD, custom fields, list creation with empty list expand |
| | uat-security-rbac | ⬜ Pending | | |
| | uat-navigation-ui | ⬜ Pending | | |
| | uat-help-system | ⬜ Pending | | |
| | uat-container-management | ⬜ Pending | | |
| | uat-sample-accessioning | ⬜ Pending | | |
| | uat-test-ordering | ⬜ Pending | | |
| | uat-sample-status-editing | ⬜ Pending | | |
| | uat-batch-management | ⬜ Pending | | |
| | uat-aliquots-qc | ⬜ Pending | | |
| | uat-results-entry-review | ⬜ Pending | | |
| | uat-bulk-enhancements | ⬜ Pending | | |
| | uat-reporting-projects | ⬜ Pending | | |

---

## Notes

- Scripts can be run out of order if prerequisites are manually set up in the database
- Some scripts can run in parallel if they don't share dependencies (e.g., `uat-navigation-ui` and `uat-help-system`)
- Failed tests in foundational scripts (security, configurations) may cause cascading failures in dependent scripts
