# Product Requirements Document (PRD) for LIMS MVP

## 1. Introduction

### 1.1 Purpose
This Product Requirements Document (PRD) outlines the requirements for the Minimum Viable Product (MVP) of an API-first Laboratory Information Management System (LIMS). The LIMS is designed to support core laboratory operations across various industries (e.g., clinical, research, environmental), focusing on sample tracking, test ordering, and results entry. This MVP emphasizes essential functionality, data security, and scalability, with configurable workflows for processes like aliquoting.

The system will be built using PostgreSQL as the database, Python (e.g., FastAPI with SQLAlchemy) for the backend, and React for the frontend. The API-first approach ensures all interactions occur via RESTful endpoints, enabling easy integration and frontend decoupling.

### 1.2 Project Overview
The LIMS MVP enables labs to manage samples from receipt to reporting, including tracking statuses, containers, aliquots/derivatives, and QC elements. It supports role-based access control (RBAC) to ensure data privacy, particularly for clients viewing only their own projects. Post-MVP expansions (e.g., instrument integration, result calculations) are noted but out of scope.

### 1.3 Stakeholders
- **Lab Technician**: Handles sample accessioning, test assignment, and results entry.
- **Lab Manager**: Oversees workflows, reviews tests/results, manages batches.
- **Administrator**: Manages users, roles, permissions, and system configurations.
- **Client**: Views their samples, tests, and results within assigned projects.

### 1.4 Version History
- Version 1.0: Initial draft based on planning discussions (October 21, 2025).
- Version 1.1: Added admin configuration features (analyses, analytes, users, roles management) - December 2025.
- Version 1.2: Added test batteries feature (grouped analyses with sequence ordering) - December 2025.

## 2. Goals and Objectives

### 2.1 Business Goals
- Streamline lab operations by automating sample tracking and results management.
- Ensure data security and compliance with role-based and project-based access.
- Provide a flexible, configurable system for common lab workflows.
- Enable quick MVP launch to validate core features before expansions.

### 2.2 User Goals
- Efficiently accession and track samples through their lifecycle.
- Order and assign tests seamlessly during sample intake.
- Enter and review results in batches/plates with validation.
- Securely access data based on roles and projects.

### 2.3 Success Metrics
- 100% coverage of MVP features: sample tracking, test ordering, results entry.
- User satisfaction: Measured via feedback on usability (e.g., <5 minutes for accessioning a sample).
- Performance: API responses <500ms; handle 1,000 samples/projects without degradation.
- Security: No unauthorized data access in testing.

## 3. Scope

### 3.1 In Scope (MVP Features)
- **Sample Tracking**:
  - Accessioning: Receive, inspect, note anomalies, double-entry option, assign tests from manifest, review/release.
  - Status management: Received, Available for Testing, Testing Complete, Reviewed, Reported.
  - Containers: Hierarchical (self-referential; types like tube, plate, well); contents linking samples with concentration/amount (volume calculated).
  - Aliquots/Derivatives: Linked via parent_sample_id; inheritance of project/client; created in workflows (e.g., DNA extraction).
  - QC Integration: qc_type field (e.g., Sample, Positive Control, Blank) from lists.
- **Test Ordering**:
  - Assign individual analyses or test batteries to samples at accessioning.
  - Test batteries automatically create sequenced tests for all analyses in the battery.
  - Test instances with status: In Process, In Analysis, Complete.
- **Results Entry**:
  - Batch/plate-based: Select batch (container collection), test; display analytes for entry.
  - Fields: raw_result, reported_result, qualifiers, calculated_result (post-MVP calculations).
  - Validation: Per analyte (data type, ranges, sig figs).
  - Review: Lab manager at test level; updates statuses.
- **Batches/Plates**:
  - Batches as container groups; statuses: Created, In Process, Completed.
  - Plates as containers with wells; support pooling via contents.
- **Security and Auth**:
  - RBAC with 17 permissions (e.g., sample:create, result:enter, batch:manage).
  - User auth: Username/password + email verification.
  - Client isolation: View own projects/samples only; project_users junction for access.
- **Configurable Elements**:
  - Lists for statuses, types, matrices, etc. (admin-editable via UI/API).
  - Container types: Pre-setup by administrators; instances created dynamically during workflows.
  - Analyses: Admin-configurable with methods, turnaround times, costs.
  - Analytes: Admin-configurable; linked to analyses via validation rules.
  - Analysis-Analyte Rules: Admin-configurable validation (data types, ranges, significant figures, required flags).
  - Test Batteries: Admin-configurable groups of analyses with sequence ordering and optional flags; assignable during accessioning.
  - Units: Admin-configurable with multipliers for conversions.
  - Workflows: Basic configurable for aliquoting/derivatives.
- **Data Model**: Normalized Postgres schema with standard fields (id UUID, name unique, description, active, audit timestamps/users).

### 3.2 Out of Scope
- Instrument integration (e.g., raw results import).
- Result calculations/formulas.
- Advanced reporting/export (e.g., PDF reports).
- Multi-factor auth or third-party OAuth.
- Mobile app; full internationalization.
- Performance optimizations for >10,000 samples.

## 4. User Roles and Permissions

| Role            | Description                                                                 | Key Permissions (Examples) |
|-----------------|-----------------------------------------------------------------------------|----------------------------|
| Administrator  | Manages system, users, and configs.                                        | All (17): user:manage, role:manage, config:edit, project:manage, sample:*, test:*, result:*, batch:*. |
| Lab Manager    | Oversees operations, reviews results.                                       | result:review, batch:manage, test:assign. |
| Lab Technician | Handles daily tasks like accessioning and entry.                            | sample:create, result:enter, test:assign. |
| Client         | Views own data.                                                             | sample:read (own), result:read (own). |

Permissions managed via roles, permissions, and role_permissions tables (17 total permissions: sample:create, sample:read, sample:update, test:assign, test:update, result:enter, result:review, result:update, result:delete, batch:manage, batch:read, batch:update, batch:delete, project:manage, user:manage, role:manage, config:edit).

**Note**: The code references `test:configure` permission in several places, but this permission is not currently created in the database. Endpoints that reference it use `require_any_permission(["config:edit", "test:configure"])`, which effectively requires `config:edit` permission.

## 5. Functional Requirements

### 5.1 Workflows
- **Sample Accessioning**:
  - Receive shipment; inspect/note anomalies; enter data (double-entry optional); assign tests; review/release.
  - Required fields: due_date, received_date (timestamp), sample_type, status, matrix, temperature.
- **Aliquots/Derivatives Creation**:
  - Workflow step: Select parent; create child with new container_id (aliquot) or sample_id/type (derivative).
  - Inherit project/client; update statuses.
- **Test Ordering**:
  - At accessioning: Assign analysis_id to sample → create test instance.
- **Results Entry**:
  - Select batch/container; choose test; enter per analyte with validation.
  - Update test/sample statuses on completion/review.
- **Batch Processing**:
  - Create batch; add containers; status flow: Created → In Process (analysis) → Completed (review).
- **Pooled Samples** (Pending Refinement): Add multiple contents to container; calculate concentration/amount (e.g., average/sum rules).

### 5.2 API Endpoints (High-Level)
- `/samples`: CRUD with filters (project_id, status).
- `/tests`: Assign to samples; update status.
- `/results`: Enter/review per test/analyte.
- `/batches`: Create/add containers; manage status.
- `/auth`: Login, verify email.
- `/analyses`: CRUD for analyses (admin: config:edit or test:configure).
- `/analytes`: CRUD for analytes (admin: config:edit or test:configure).
- `/analyses/{id}/analyte-rules`: Configure validation rules (admin).
- `/test-batteries`: CRUD for test batteries and battery-analyses junctions (admin: config:edit or test:configure).
- `/users`: CRUD for users (admin: user:manage or config:edit).
- `/roles`: CRUD for roles and permissions (admin: user:manage or config:edit).
- `/lists`: CRUD for lists and entries (admin: config:edit).
- `/containers/types`: CRUD for container types (admin: config:edit).
- All endpoints secured via JWT with RBAC checks.

## 6. Non-Functional Requirements

### 6.1 Security
- RBAC with granular permissions; RLS in Postgres for row-level access.
- Data isolation: Clients see only own projects (via client_id, project_users).
- Encryption: Password hashes (bcrypt); sensitive data at rest (Postgres defaults).

### 6.2 Performance
- Handle 500 concurrent users; <1s query times.
- Indexing on FKs (e.g., project_id, sample_id).

### 6.3 Usability
- React UI: Intuitive forms for workflows; real-time validation.
- Accessibility: WCAG 2.1 compliant.

### 6.4 Reliability
- Audit trails on all tables.
- Error handling: Graceful API failures with codes.

### 6.5 Scalability
- Normalized schema; UUIDs for distributed potential.

## 7. Data Model Overview

### 7.1 Key Tables and Fields
- **Samples**: id (UUID), name, description, active, audit fields, due_date, received_date, report_date, sample_type (FK list), status (FK), matrix (FK), temperature, parent_sample_id, project_id, qc_type (FK).
- **Containers**: id, name (barcode optional), row, column, concentration, amount, type_id (FK container_types), parent_container_id.
- **Contents**: container_id, sample_id, concentration, amount.
- **Analyses**: id, name, method, turnaround_time, cost.
- **Analysis_Analytes** (Junction): analysis_id, analyte_id, data_type, high/low, sig_figs, etc.
- **Test_Batteries**: id, name, description, active, audit fields.
- **Battery_Analyses** (Junction): battery_id, analysis_id, sequence (int >=1), optional (bool).
- **Tests**: id, sample_id, analysis_id, battery_id (nullable), status, review_date, test_date, technician_id.
- **Results**: id, test_id, analyte_id, raw_result, reported_result, qualifiers, etc.
- **Batches**: id, name, type, status, dates.
- **Batch_Containers** (Junction): batch_id, container_id.
- **Projects**: id, name, description, start_date, client_id, status.
- **Project_Users** (Junction): project_id, user_id, access_level.
- **Clients**: id, name, description, billing_info (JSONB), status; linked to locations, people, contacts.
- **Users**: id, username, password_hash, email, role_id, client_id, last_login.
- **Roles/Permissions**: As defined in Section 4.
- **Lists/List_Entries**: For configurable values.

Relationships: Normalized with FKs (e.g., samples → projects, tests → samples/analyses).

## 8. Assumptions and Dependencies
- Assumptions: Labs use standard workflows; no custom hardware needed for MVP.
- Dependencies: Postgres 15+, Python 3.10+, React 18+; libraries like FastAPI, SQLAlchemy, JWT.
- Risks: Schema changes post-MVP; ensure thorough testing for security.

## 9. Appendices
- Glossary: LIMS (Laboratory Information Management System), RBAC (Role-Based Access Control), etc.
- References: Discussions with Grok AI for schema/workflows.



# Post-MVP Product Requirements Document (PRD) for LIMS
## 1. Introduction
### 1.1 Purpose
This PRD outlines post-MVP enhancements for the LIMS, focusing on efficiency for high-volume workflows like bulk accessioning and batch results entry.
### 1.2 Project Overview
Extends MVP with bulk features, cross-project batching, and client project grouping for real-world scalability.
### 1.3 Stakeholders

Same as MVP, with emphasis on Lab Technicians for bulk efficiency.

### 1.4 Version History

Version 1.0: Initial post-MVP draft (December 28, 2025).

## 2. Goals and Objectives
### 2.1 Business Goals

Improve throughput for batch-heavy labs.
Enhance QC integration and validation.

### 2.2 User Goals

Reduce repetition in multi-sample workflows.
Group and process across projects efficiently.

### 2.3 Success Metrics

Reduced accessioning time for batches (<2 min for 5 samples).
100% QC coverage in batches.

## 3. Scope
### 3.1 In Scope

Bulk accessioning with common/uniques.
Client projects for grouping.
Cross-project batching with compatibility.
QC addition at batch.
Batch results entry with validation.

### 3.2 Out of Scope

Full automation (e.g., AI validation).
External integrations.

## 4. Functional Requirements
### 4.1 Bulk Accessioning

UI: Toggle, common fields, unique table.
Backend: Atomic multi-create.

### 4.2 Client Projects

Hierarchy: One client project → many LIMS projects.
Access: Inherited via RLS.

### 4.3 Advanced Batching

Cross-project: Compatible tests only.
QC: Auto-generate at creation.

### 4.4 Batch Results

Tabular entry; QC flags/blocks.

## 5. Non-Functional Requirements
### 5.1 Security

Extend RLS for client projects.

### 5.2 Performance

Handle 50-sample bulks <5s.

## 6. Data Model Enhancements

New: client_projects.
Updates: projects (client_project_id), samples (client_sample_id).

## 7. Assumptions and Dependencies

Builds on MVP; Alembic for migrations.