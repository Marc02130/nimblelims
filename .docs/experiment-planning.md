# Experiment Management — Planning & Implementation

## Chunk 1 — Completed

**Status:** Completed.

**Scope:** Backend and frontend for experiments and experiment templates API; sidebar navigation refactor (Experiments as own accordion); sample↔experiment linking; workflow integration; lineage; My Experiments filter.

### Implementation Notes (Chunk 1)

- **Backend**
  - **Models:** `experiment_templates`, `experiments`, `experiment_details`, `experiment_sample_executions` (with role_in_experiment, processing_conditions JSONB, replicate_number, optional test_id/result_id). Migrations through `0038`+; client RLS on experiment engine tables in `0041`/`0042`.
  - **API:** `/v1/experiments` and `/v1/experiment-templates`. CRUD plus: `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `get_experiment_lineage`, `get_sample_experiments`. List experiments supports `mine=true`.
  - **Permissions:** `experiment:manage` for experiment and template endpoints.
  - **Workflow:** Actions `create_experiment`, `create_experiment_from_template`, `link_sample_to_experiment`, `add_experiment_detail_step`, `link_experiments`, `update_experiment_status`. Context carries `experiment_id` and `execution_id`.

- **Frontend**
  - **Sidebar:** **Experiments** accordion after Sample Mgmt: **All Experiments** (`/experiments`), **Experiment Templates** (`/experiments/templates`). Section and both sub-items require `experiment:manage`.
  - **Routes:** `/experiments`, `/experiments/:id`, `/experiments/templates` — all `experiment:manage`.
  - **Pages:** `ExperimentsManagement` — list, detail, My Experiments (`?mine=true`), tabs, sample links, lineage. Sample detail “Participated in these Experiments”.

---

## Chunk 2 — Experiment Templates UI & SOP (AI) — Completed

**Status:** Shipped in app (`ExperimentTemplatesManagement.tsx`, `sop_parse` router).

**Scope:**

- Dedicated **Experiment Templates** page (not reused experiments list).
- Manual template authoring: MUI DataGrid + large dialog with tabs (basic info, protocol steps, transfer steps with “requires sign-off before activation”, result columns as key/value rows).
- **Upload SOP:** Two files (SOP + instrument CSV) → `POST /v1/sop-parse` → poll `GET /v1/sop-parse/{job_id}` → `POST /v1/sop-parse/{job_id}/apply`. UI shows progress, timeout handling, “fill in manually” escape hatch.
- **Sign-off:** For templates with `mandatory_review_count > 0`, chip opens stepper dialog; each mandatory transfer step confirmed individually (no “confirm all”); then PATCH clears `mandatory_review` flags and count.
- **Activation:** Active toggle disabled until sign-offs complete; tooltip explains why.
- **Delete:** `DELETE /v1/experiment-templates/{id}` wired in `apiService`.
- **SOP-filled fields:** Visual highlight + “from extraction” affordance in edit form after apply.

**Backend:** `backend/app/routers/sop_parse.py`, `SOPParseService` (Claude via `ANTHROPIC_API_KEY`), models `sop_parse_jobs` and related flexible experiment tables.

**Docs / plan:** See `.claude/plans/experiment-template-ui.md` for the original UI spec (implementation aligns with Phases 1–2; permission for templates is **`experiment:manage`** in code, not `config:edit`).

### UAT

- `UAT_Scripts/uat-experiment-templates.md` — template CRUD, SOP flow (with/without API key), sign-off, activation, RBAC.
- `UAT_Scripts/uat-testing-log.md` — dependency order and experiments navigation script (aligned with `experiment:manage` for templates).

---

## Future (optional)

- Permission `experiment_template:manage` for template-only access without full experiment workflows.
- Audit trail for sign-off (who/when).
- User manual generator from template schema (deferred).

---

## Summary — Files Touched (high level)

**Planning doc:** `.docs/experiment-planning.md` (this file).

**Related:** `.docs/navigation.md`, `.docs/api_endpoints.md`, `README.md`, `backend/README.md`, `frontend/README.md`, `.claude/plans/experiment-template-ui.md`, `UAT_Scripts/uat-experiment-templates.md`, `UAT_Scripts/uat-testing-log.md`.

**Frontend:** `frontend/src/pages/ExperimentTemplatesManagement.tsx`, `ExperimentsManagement.tsx`, `Sidebar.tsx`, `App.tsx`, `MainLayout.tsx`, `apiService.ts`.

**Backend:** `app/routers/experiments.py`, `app/routers/sop_parse.py`, `app/services/sop_parse_service.py`, `app/services/experiment_service.py`, flexible experiment models/migrations.
