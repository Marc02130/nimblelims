# User stories — Platform (auth, config, audit)

User stories in Agile form: "As a [role], I want [feature] so that [benefit]."

**MVP Release Bar:** Stories labeled **[MVP]** are required for basic LIMS (sample tracking, test ordering, results entry). **[Shipped, Not MVP]** / **[Post-MVP]** are enhancements.

**Formal review SoT** stays under `.docs/review/`. These files are local working notes (`.docs/internal/`).

Cross-cutting stories that are not owned by containers / accessioning / processing.

---

- **US-12: User Authentication** **[MVP]**  
  As any user, I want to log in with username/password and verify email so that access is secure.  
  *Acceptance Criteria*:  
  - No default access; admin grants roles/permissions.  
  - JWT token on login; last_login tracked.  
  - API: POST /auth/login, /verify-email.  
  *Priority*: High | *Estimate*: 5 points

- **US-13: Role-Based Access Control** **[MVP]**  
  As an Administrator, I want to manage roles and granular permissions so that access is controlled.  
  *Acceptance Criteria*:  
  - 17 permissions (e.g., sample:create, result:review, batch:manage) via junctions.  
  - Roles: Admin (all), Lab Manager (review/manage), Technician (create/enter), Client (read own).  
  - API: CRUD /roles, /permissions (admin-only).  
  - Note: `test:configure` is referenced in code but not yet in database; endpoints use `config:edit` as fallback.  
  *Priority*: High | *Estimate*: 8 points

- **US-14: Project and Client Data Isolation** **[MVP]**  
  As a Client, I want to view only my projects/samples/results so that data privacy is maintained.  
  *Acceptance Criteria*:  
  - Project_users junction for access grants.  
  - Filters: client_id on users; RLS in DB.  
  - API: All queries scoped by user context.  
  *Priority*: High | *Estimate*: 5 points

- **US-15: Configurable Lists** **[MVP]**  
  As an Administrator, I want to manage lists for statuses, types, etc., so that the system is flexible.  
  *Acceptance Criteria*:  
  - Lists/list_entries tables; modifiable via UI/API.  
  - Used for sample_type, status, qc_type, units type (concentration, mass, volume, molar).  
  - API: CRUD /lists; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-16: Units Management** **[MVP]**  
  As an Administrator, I want to configure units with multipliers for conversions so that measurements are standardized.  
  *Acceptance Criteria*:  
  - Units table: name (e.g., µg/µL), multiplier (relative to base like g/L), type (from lists).  
  - Used in contents/containers for concentration/amount_units.  
  - Backend handles conversions in calculations.  
  - API: CRUD /units; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-17: Analyses Management** **[MVP]**  
  As an Administrator, I want to manage analyses (test methods) so that the system supports our laboratory's testing capabilities.  
  *Acceptance Criteria*:  
  - CRUD operations for analyses (name, method, turnaround_time, cost).  
  - Unique name validation.  
  - Cannot delete if referenced by tests.  
  - API: CRUD /analyses; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-18: Analytes Management** **[MVP]**  
  As an Administrator, I want to manage analytes (measurable components) so that they can be assigned to analyses.  
  *Acceptance Criteria*:  
  - CRUD operations for analytes (name, description).  
  - Unique name validation.  
  - Cannot delete if referenced by analyses.  
  - API: CRUD /analytes; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-19: Analysis-Analyte Configuration** **[MVP]**  
  As an Administrator, I want to configure validation rules for analytes within analyses so that results entry is properly validated.  
  *Acceptance Criteria*:  
  - Assign analytes to analyses.  
  - Configure per-analyte rules: data_type, high/low values, significant_figures, is_required, default_value, reported_name, display_order.  
  - Support for list-based analytes (qualifiers).  
  - Validation during results entry based on rules.  
  - API: CRUD /analyses/{id}/analyte-rules; RBAC: config:edit or test:configure.  
  *Priority*: Medium | *Estimate*: 5 points

- **US-20: Users Management** **[MVP]**  
  As an Administrator, I want to manage users so that access is properly controlled.  
  *Acceptance Criteria*:  
  - CRUD operations for users (username, email, role assignment, client assignment).  
  - Password management (admin can reset).  
  - Filter by role or client.  
  - API: CRUD /users; RBAC: user:manage or config:edit.  
  *Priority*: High | *Estimate*: 5 points

- **US-22: Test Batteries Management** **[MVP]**  
  As an Administrator, I want to create and manage test batteries (grouped analyses) so that common test combinations can be assigned efficiently during accessioning.  
  *Acceptance Criteria*:  
  - CRUD operations for test batteries (name, description).  
  - Add/remove analyses to/from batteries with sequence ordering (integer >= 1).  
  - Mark analyses as optional within batteries.  
  - Unique battery names; at least one analysis required.  
  - Cannot delete if referenced by tests (409 Conflict).  
  - API: CRUD /test-batteries and /test-batteries/{id}/analyses; RBAC: config:edit or test:configure.  
  - UI: Material-UI DataGrid with expandable rows, search/filter, sequence management.  
  *Priority*: Medium | *Estimate*: 8 points

### US-25: Client Project Management **[Shipped, Not MVP]**
As a Lab Manager, I want to group multiple NimbleLIMS projects under a client project so that ongoing submissions for the same client initiative can be tracked holistically.
Acceptance Criteria:
CRUD for client_projects (name, description, client_id, status).
Link NimbleLIMS projects via client_project_id FK.
Accessioning allows selection/creation of client project before NimbleLIMS project.
Reporting aggregates across linked projects.
API: CRUD /client-projects; RBAC: project:manage.
Priority: Medium | Estimate: 5 points

- **US-33: Append-Only Audit Events** **[MVP]**  
  As a Lab Manager or Administrator, I want an append-only audit trail for all critical changes so that compliance requirements are met and data integrity is ensured.  
  *Not in atomic-receive P0.* New audit tables/events are out of AR-01–AR-15 (no new tables this packet).  
  *Acceptance Criteria*:  
  - Audit events table: entity type, entity_id, event_type (created/updated/deleted/reviewed/reported), old_value, new_value, changed_by (user_id), changed_at (timestamp with time zone), reason (required once result is reviewed/reported).  
  - Events captured for: sample, order/test, result, spec/analysis, user account changes.  
  - Append-only: admin users **cannot edit or delete** audit log entries.  
  - Users cannot disable audit logging.  
  - Unique users required: no shared lab login accounts permitted.  
  - Disabled users remain in historical audit records (not deleted).  
  - Server-generated timestamps (not user-editable without creating a new audit event).  
  - Reason field required for changes to reviewed/reported results.  
  - API: GET /audit-events with filters; no DELETE or PATCH endpoints for audit events.  
  - Database: append-only constraint; admin role cannot bypass.  
  - **Important**: Do NOT claim "21 CFR Part 11 certified" compliance. E-signatures with meaning and re-authentication are post-MVP.  
  - UAT: Verify admin cannot edit audit log; verify reason required for post-review changes; verify disabled user still appears on historical actions.  
  *Priority*: High | *Estimate*: 13 points  
  *Related*: Issue #25

- **US-34: Audit Event Reconstruction for Compliance** **[MVP]**  
  As a Lab Manager or Auditor, I want to reconstruct the complete history of any sample, test, or result so that regulatory compliance (ISO 20387, GTEx, 21 CFR) is supported.  
  *Not in atomic-receive P0.* Out of AR-01–AR-15.  
  *Acceptance Criteria*:  
  - History view shows all audit events for an entity in chronological order.  
  - Display: timestamp (with timezone), user, action, old→new values, reason (if provided).  
  - Filterable by entity type, date range, user, event type.  
  - Export capability for audit trail (CSV/JSON).  
  - API: GET /samples/{id}/audit-trail, /tests/{id}/audit-trail, /results/{id}/audit-trail.  
  - UI: Audit History tab on detail views; admin Audit Log page with global search.  
  *Priority*: Medium | *Estimate*: 5 points  
  *Related*: Issue #25

### Custom Fields (EAV Model) **[Shipped, Not MVP]**  
  As an Administrator, I want to define custom attributes for samples, tests, results, projects, client_projects, and batches without schema changes so that the system can be customized for laboratory-specific requirements.  
  *Acceptance Criteria*:  
  - Admin interface for creating custom attribute configurations (entity_type, attr_name, data_type, validation_rules).  
  - Support for data types: text, number, date, boolean, select.  
  - Validation rules: min/max for numbers, length for text, options for select.  
  - Dynamic field rendering in forms based on configurations.  
  - Server-side validation against active configurations.  
  - Custom attributes stored in JSONB columns with GIN indexes for querying.  
  - List endpoints support filtering via `?custom.attr_name=value`.  
  - API: CRUD /admin/custom-attributes; RBAC: config:edit.  
  *Status*: Implemented (Post-MVP) | *Estimate*: 13 points

