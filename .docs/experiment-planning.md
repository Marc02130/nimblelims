# Experiment Management — Planning & Implementation

## Chunk 1 — Completed

**Status:** Completed and tested locally.

**Scope:** Backend and frontend for experiments and experiment templates; sidebar navigation refactor (Experiments as own accordion); sample↔experiment linking; workflow integration; lineage; My Experiments filter.

### Implementation Notes

- **Backend**
  - **Models:** `experiment_templates`, `experiments`, `experiment_details`, `experiment_sample_executions` (with role_in_experiment, processing_conditions JSONB, replicate_number, optional test_id/result_id). Migrations: `0036` (tables, RLS, audit triggers), `0037` (permission `experiment:manage` for Administrator, Lab Manager, Lab Technician), `0038` (seed list `experiment_status`).
  - **API:** `/v1/experiments` and `/v1/experiment-templates` (mounted under `/v1` so nginx proxy `/api/v1/*` → `/v1/*`). CRUD plus: `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `get_experiment_lineage`, `get_sample_experiments`. List experiments supports `mine=true` (filter by `created_by` = current user).
  - **Permissions:** `experiment:manage` required for all experiment/template endpoints. No separate `experiment_template:manage` yet; Templates sub-item in UI is gated by `config:edit` (admins only).
  - **Workflow:** Actions `create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `update_experiment_status`. Context carries `experiment_id` and `execution_id`; workflow execution uses `ExperimentService` with `auto_commit=False` in same transaction.

- **Frontend**
  - **Sidebar (refactor v2.1):** Experiments removed from Lab Mgmt. New top-level **Experiments** accordion (after Sample Mgmt) with sub-items: **All Experiments** (`/experiments`), **Experiment Templates** (`/experiments/templates`). Section visible with `experiment:manage`; Templates sub-item visible only with `experiment_template:manage` OR `config:edit`.
  - **Routes:** `/experiments`, `/experiments/:id`, `/experiments/templates` (MainLayout; list/detail protected by `experiment:manage`; templates by `experiment_template:manage` or `config:edit`).
  - **Pages:** ExperimentsManagement — list (filters, pagination, My Experiments chip via `?mine=true`), detail (tabs: Overview, Sample Executions, Details/Steps, Lineage, Linked Processes), create dialog. Sample detail shows "Participated in these Experiments"; experiment detail links to `/samples?highlight=<id>`; Samples list opens sample view when `?highlight=<id>` in URL.
  - **AppBar:** Titles "Experiments", "Experiment Detail", "Experiment Templates"; back button on experiment detail → `/experiments`.

- **Integration**
  - **Bidirectional linking:** Sample ↔ experiment via API and UI links; lineage view with loading/error states.
  - **Workflow builder:** Helper text in Workflow Templates admin lists experiment actions and context params.

### UAT

- **uat-experiments-navigation:** Sidebar Experiments section visibility and Experiment Templates gating (admin vs Lab Tech/Manager); permission redirects.
- **uat-experiment-management:** Experiment CRUD, list/filters (including My Experiments), sample↔experiment linking, lineage, workflow actions, back button and titles.

See `UAT_Scripts/uat-testing-log.md` for full UAT script steps.

---

## Chunk 2+ (Future)

- Optional: Add permission `experiment_template:manage` and assign to Lab Manager (or others) so Templates sub-item and `/experiments/templates` route can be granted without full `config:edit`.
- Dedicated Experiment Templates management page (e.g. CRUD for templates at `/experiments/templates`) if needed beyond current ExperimentsManagement reuse.
- Further workflow actions or reporting tied to experiments.

---

## Summary — Files Created/Modified (Experiment Planning)

**This file (`.docs/experiment-planning.md`):** Created. Contains Chunk 1 completion status and implementation notes.

**Related code/docs:** See `.docs/navigation.md` (navigation refactor summary), `README.md` (Experiment Management section and summary), `UAT_Scripts/uat-testing-log.md` (UAT scripts and dependency table).
