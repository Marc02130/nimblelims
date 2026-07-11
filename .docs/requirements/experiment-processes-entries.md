# Requirements: Experiment Processes, Entries, and Sample Flow

**Date:** 2026-07-09  
**Branch:** refactor/experiments  
**Status:** Draft for review  
**Derived from:** CEO Review, Security (CSO) Review, and Design Review of the Experiment Plans (see `.docs/manuals/experiments.md`, `.docs/manuals/processes.md`, `.docs/design/gap-analysis-process-and-experiment.md`, `.docs/design/experiment-planning.md`)

## 1. Purpose and Context

NimbleLIMS currently supports ELN-style Experiments using loose mechanisms (`ExperimentDetail` with `detail_type="experiment_link"`, JSONB content, and `ExperimentSampleExecution`). This works for simple cases but fails to model ordered, multi-step experimental workflows where:

- Order matters.
- Samples are assigned at a process level and progressed through steps.
- Data capture needs to be template-driven and structured (using FieldDefinitions + lists rather than free-form JSONB).

The goal is to introduce first-class **Processes** and a rich **Entries** system while maintaining clear separation from LIMS Experiment Runs (see `.docs/manuals/lims-runs.md`).

This requirements doc consolidates feedback from CEO, Security, and Design reviews to drive implementation.

## 2. Goals

- Make complex, ordered experimental work (e.g., NGS library prep pipelines) first-class and explicit.
- Provide strong template control over data capture via **Entries** backed by FieldDefinitions (list-backed where appropriate).
- Enable sample assignment at the Process level with clear progression through steps.
- Deliver a coherent mental model and UI that feels like a natural extension of the existing Field Management experience.
- Preserve (and improve) the existing flexibility of ELN Experiments while adding structure where it adds value.
- Maintain clean separation from LIMS Experiment Runs, Batches, and Workflows, while enabling end-to-end sample journey visibility.
- Ensure security, auditability, and data integrity (especially for write-backs and sample state).

## 3. Non-Goals (for initial scope)

- Full unification of ELN Experiments and LIMS Experiment Runs into a single model (keep separate for now; improve visibility instead).
- Reusable Process Templates (defer to Phase 2; focus on instance-level Processes first).
- Support for non-linear DAGs in Processes (start with strict linear order; evaluate DAGs later).
- Overhauling existing Experiment Runs, dose-response, or flexible experiment engine in this effort.
- Automatic promotion of data from Entries into Runs/Results (explicit integration points only).

## 4. Functional Requirements

### 4.1 Processes (ELN Layer)

- A **Process** is a first-class entity representing an ordered collection of Experiments (or references to Experiment Templates).
- Processes support:
  - Name, description, status (list-driven, similar to Experiments), owner, timestamps.
  - Explicit ordered membership of steps (Experiments) via a junction with `sort_order`.
  - Assignment of samples at the process level (via `ProcessSample`).
- Sample flow through a Process:
  - Samples are assigned to a Process (`assign_samples_to_process`).
  - Samples can be queued into specific steps (`queue_sample_in_process_step`).
  - As work completes, samples can be advanced to the next step (`advance_sample_to_next_step`).
  - Per-step details remain in `ExperimentSampleExecution`.
- Processes are distinct from:
  - Existing `experiment_processes` / `process_steps` (LIMS Runs side).
  - Workflow Templates (general automation).
  - Batches (operational grouping for testing).

**Priority:** P1

### 4.2 ProcessSample

- Dedicated table for tracking samples assigned to a Process.
- Stores process-level state (e.g., assigned, in_progress, completed) and `assigned_at`.
- `ProcessSample` is the authoritative source for "this sample belongs to this workflow."
- Must clearly document and enforce consistency rules with `ExperimentSampleExecution` (no silent divergence).

**Priority:** P1

### 4.3 Entries (Data Capture inside Experiments)

- Experiments are composed of **Entries** (replacing or augmenting loose `ExperimentDetail`).
- Entry types (initial):
  - `predefined_action`: OOB behaviors (aliquoting, pooling, index assignment, flowcell loading, QC review pass/fail).
  - `sample_data`: Per-sample structured data tables (columns defined via FieldDefinitions in the template).
  - `experiment_detail`: Experiment-level notes/conditions (columns via FieldDefinitions).
  - `display_table`: Read-only structured display.
- Custom entries (`sample_data`, `experiment_detail`) use FieldDefinitions for columns (supporting `data_type='list'` with `source_list_id`, scalars with validation rules, etc.).
- Sample data entries must support write-back to core Sample attributes (e.g., concentration, volume_ml, received_date) with:
  - Clear rules for conflicts when multiple steps update the same attribute.
  - Audit trail.
  - Authorization checks.
- Entries are declared/configured at the ExperimentTemplate level (predefined entries + custom column definitions).
- When instantiating an Experiment (especially inside a Process), entries are created from the template.
- Process steps can influence which entries are active/required (details to be specified).

**Priority:** P1 for model + basic sample_data/experiment_detail; P2 for full predefined actions and write-back.

### 4.4 Integration with Existing Concepts

- Experiment Templates declare entries (predefined + custom via FieldDefinitions).
- When creating Experiments from templates (inside or outside Processes), entries are instantiated.
- Lineage: New Process ordering should supersede or clearly coexist with legacy `experiment_link` (via `ExperimentDetail`).
- Status: Experiments retain flexible list-based status; Processes may derive or have their own.
- `lifecycle_type` on templates influences reviews/approvals in both Experiments and (future) Processes.
- Sample visibility: Processes should contribute to "Participated in these Experiments" and provide process-level journey views.

## 5. Data Model Requirements

- New or promoted tables (with proper naming to avoid collision with LIMS `experiment_processes`):
  - `processes` (or `experiment_processes` renamed/distinguished for ELN).
  - Junction table for ordered steps (e.g., `process_experiments` with `sort_order`, FKs to processes and experiments/templates).
  - `process_samples`.
  - `entries`.
  - `entry_field_definitions` (junction).
  - `entry_field_values` (typed values: text, number, list_entry_id, date, boolean, json).
- `Experiment` gains (or strengthens) `entries` relationship.
- `Process` references Experiments (instances) or Templates + instantiation rules.
- All new tables follow existing patterns: UUID PKs, audit fields, RLS enablement, list-driven statuses where appropriate.
- Migration strategy required for existing `experiment_link` records and sample executions (coexistence or one-time migration).

**Naming rule:** Use distinct ELN prefixes (e.g., `eln_process_*`) or clear module separation if needed.

**Priority:** P1

## 6. API / Service / Workflow Requirements

- CRUD for Processes + ordering operations (add/remove/reorder steps).
- Sample assignment: `assign_samples_to_process`, `remove_samples_from_process`.
- Queuing/advancing: `queue_sample_in_process_step`, `advance_sample_to_next_step`.
- Entry-related actions: instantiate entries from template, create/update entry values.
- Workflow actions: `create_process`, `add_experiment_to_process`, etc. (replace or deprecate `link_experiments`).
- Queries: Efficient process-level lineage/status, "samples currently in step X of process Y".
- Existing experiment endpoints remain backward compatible during transition.

**Priority:** P1 for basic Process + sample assignment; P2 for full workflow integration.

## 7. UI / UX Requirements

- Dedicated Process management:
  - Create/edit Processes.
  - Builder to select and order Experiments (or templates).
  - Assign samples to Process.
  - Visual or list-based view of steps with sample queues and status.
  - "Queue samples into this step" actions.
- Process overview showing progress across steps.
- Within Experiments (especially in process context):
  - Entry-based data capture UI (forms/tables driven by FieldDefinitions).
  - Predefined entries surfaced as actions.
  - Clear indication of write-back effects.
- Consistency with Field Management UI (OOB + custom fields, lists for selects, validation rules for scalars).
- Sample detail pages and "My Experiments" should surface process context and current step.
- Mental model clarity: Explicit documentation and UI labels distinguishing ELN Process vs. Experiment vs. LIMS Run vs. Workflow Template vs. Batch.
- Progressive disclosure: Start with simple single-experiment flows; unlock rich process features.

**Priority:** P1 for basic CRUD + assignment + overview; P2 for advanced visualization and entry UIs.

## 8. Security Requirements

- RLS policies for all new tables (`processes`, `process_*`, `entries`, `entry_*`):
  - Align with existing client/project scoping.
  - Process membership should grant appropriate visibility to contained Experiments and Samples.
  - Policies must be defined and tested before schema migration.
- Authorization: `experiment:manage` (or refined `process:manage` / `entry:manage`) for new operations.
- Write-back security:
  - Gated by experiment/process status.
  - Full audit trail (who, when, from which entry/step/process).
  - Conflict resolution rules documented and enforced.
- Audit for: sample assignment, step advancement, entry value changes, write-backs.
- No new attack surfaces from ordering (enforce integrity at DB level where possible).
- Address naming to prevent accidental policy or query errors across ELN vs. LIMS "Process" concepts.
- Review existing `experiment_link` usage for any exposure during migration.

**Priority:** P1 (policies + audit before any data model changes).

## 9. Cross-Cutting and Quality Requirements

- Clear documentation of:
  - Relationship and consistency rules between `ProcessSample` and `ExperimentSampleExecution`.
  - How Processes interact with Entries (activation, configuration inheritance/override).
  - Migration/coexistence path from `experiment_link`.
  - Boundary with LIMS Experiment Runs (when a process step produces instrument data).
- Testing: Ordered multi-step flows, sample progression, consistency invariants, write-back conflicts, RLS.
- Performance: Efficient queries for process status and sample location in long processes.
- Flexibility: Support simple labs (optional Processes) while enabling rich pipelines.
- Deprecation path for legacy mechanisms (with clear user guidance).

## 10. Open Questions (to resolve in review)

1. Should Processes be able to reference LIMS Experiment Runs, or stay strictly ELN?
2. Does a Process need its own status list, or is it strictly derived?
3. Can a Process override or extend entry configuration from its member templates?
4. Exact conflict resolution and "last write wins" rules for write-backs across steps.
5. Level of integration with existing Workflows (new actions only, or deeper orchestration)?
6. Reusable Process definitions (templates) — Phase 1 or Phase 2?
7. How should overall process progress/status be surfaced to non-admin users?

## 11. Phasing Recommendations (from reviews)

**Phase 1 (Minimal Viable):**
- Data model: `Process`, ordered junction, `ProcessSample`.
- Basic CRUD + sample assignment + explicit ordering.
- RLS policies + basic audit.
- Migration strategy for links.
- Resolve naming.
- Update docs and mental model.

**Phase 2:**
- Entries implementation (model + instantiation from templates).
- Write-back (with rules and audit).
- Process-aware UI (builder, queues, overview).
- Workflow actions.

**Phase 3:**
- Reusable Process Templates.
- Deeper integration / visibility across ELN + Runs.
- Advanced visualization and reporting.

## 12. References

- [`.docs/manuals/experiments.md`](../manuals/experiments.md)
- [`.docs/manuals/processes.md`](../manuals/processes.md)
- [`.docs/design/gap-analysis-process-and-experiment.md`](../design/gap-analysis-process-and-experiment.md)
- [`.docs/design/experiment-planning.md`](../design/experiment-planning.md)
- [`.docs/design-review/process-and-experiment.md`](../design-review/process-and-experiment.md)
- [`.docs/manuals/lims-runs.md`](../manuals/lims-runs.md)
- [`.docs/checklist/experiment-rework-prerequisites.md`](../checklist/experiment-rework-prerequisites.md)
- FieldDefinitions work (unified OOB + custom fields via lists)

---

**Next:** Review this document, resolve open questions, and prioritize for implementation on the `refactor/experiments` branch.