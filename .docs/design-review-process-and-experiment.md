# Design Review: Process and Experiment

**Date:** 2026-06-30  
**Branch:** refactor/experiments  
**Scope:** ELN-side Experiments and the proposed Process construct that groups them. (LIMS Experiment Runs kept separate per prior decisions.)

## Executive Summary

The current ELN Experiment system provides flexible linking and sample association but lacks a first-class way to model ordered, multi-experiment workflows with process-level sample tracking. 

The proposed model introduces:
- **Process**: Ordered collection of Experiments.
- **ProcessSample**: Dedicated table for samples assigned to a Process.
- Rich **Entries** inside Experiments (predefined actions + custom data tables).

This review identifies structural issues, ambiguities, and risks that must be resolved before implementation.

## Current State (as of main + docs)

- Experiments linked via `ExperimentDetail(detail_type="experiment_link")` (JSONB content with ID). This is a linked list, not an ordered collection.
- Samples associated per-experiment via `ExperimentSampleExecution` (role, replicate, processing_conditions, optional test/result).
- No `Process` entity.
- No `ProcessSample`.
- Lineage is implicit and difficult to traverse or manage at scale.
- Existing `ExperimentProcess`/`ProcessStep` tables are exclusively for sub-processes *inside* LIMS `ExperimentRun`s (different domain).

## Proposed Target Model

- `Process` (new or first-class) owns an ordered list of Experiments (via junction with `sort_order`).
- `ProcessSample` tracks samples assigned at the *process* level.
- Within a Process step (Experiment), `ExperimentSampleExecution` provides fine-grained per-experiment data.
- Experiments use typed "Entries" for data capture and actions (columns defined in template for custom entries).
- Samples can write back from sample entries to core `Sample` attributes.

## Issues That Need to Be Addressed

### 1. Sample Tracking Split (ProcessSample vs ExperimentSampleExecution)

- **Issue**: Introducing `ProcessSample` creates a two-level sample model. It is unclear how consistency is maintained when a sample moves between steps.
- **Risks**:
  - Duplicate or conflicting data (e.g., concentration updated at process level vs per-experiment).
  - Query complexity for "where is this sample right now in the process?"
  - Race conditions when queuing/advancing samples.
- **Questions**:
  - Is `ProcessSample` only for assignment/queue state, while all mutable data lives in `ExperimentSampleExecution`?
  - Should `ProcessSample` have its own `processing_conditions` or delegate entirely?
  - Do we need a state machine on `ProcessSample` (queued / in_current_step / advanced)?

### 2. Experiment Linking vs Explicit Process Ordering

- Current `experiment_link` is stored as free-form detail content. It has no enforced ordering or integrity at the database level.
- A new `Process` + ordered junction would supersede this for many use cases.
- **Issue**: Migration path and coexistence strategy is undefined. Do we deprecate `experiment_link`? Support both? Dual-write?

### 3. Process as First-Class Entity vs. Implicit Grouping

- Is `Process` a database table with its own ID, name, status, etc., or a virtual view over ordered links?
- If first-class:
  - Ownership, permissions, and RLS must be defined.
  - Does a Process have its own `status_id` (list-driven like Experiment) or derive from its steps?
- Current docs suggest explicit UI for creation — this implies a real entity.

### 4. Interaction Between Process Steps and Experiment Entries

- Predefined entries (e.g., aliquoting, index assignment, flowcell loading) live in Experiments.
- When a sample is queued into a Process step, which entries are activated?
- **Gap**: Template-level configuration for "which entries are required/available for this step in this process type" is not specified.
- Risk of inconsistent behavior when the same Experiment Template is used in different Processes.

### 5. Write-Back Semantics and Data Ownership

- Sample entries writing back to the core `Sample` table (concentration, volume, etc.) is powerful.
- **Unresolved issues**:
  - Which step "wins" if multiple experiments in a process update the same attribute?
  - Audit trail for write-backs?
  - Concurrency when two users advance samples in parallel within a process?
  - Should write-backs be gated by experiment/process status?

### 6. Separation of Concerns (ELN Process vs LIMS Runs)

- User directive: "experiment runs will be kept separate."
- However, many real lab processes end in instrument data or QC that currently lives in the Run world (ExperimentData, dose-response, etc.).
- **Issue**: The boundary between "Process step produces data" and "that data lives in a Run" is fuzzy, especially for QC instruments (Tapestation, Qubit) now being pulled into Experiments.
- Risk of duplicated sample tracking or two competing "sources of truth" for the same physical sample's state.

### 7. Ordering, Lineage, and DAG Requirements

- User comment: "order is important."
- Current implementation is a simple linked list via details. It does not prevent cycles or enforce a total order across a Process.
- A proper Process model should probably enforce a linear order (or at least a DAG with clear execution semantics) at the process level.

### 8. Lifecycle and Status Interaction

- Experiments use flexible list-driven status.
- Processes will likely need some notion of "overall status" or "current step."
- How does advancing a sample in a process affect the status of the containing Experiment and the Process itself?
- Is there a "Process status" list or does it derive strictly from member experiments?

### 9. Template vs Instance Configuration

- Predefined entries are added to templates.
- Columns for sample/experiment detail entries are defined in the template.
- **Issue**: Once an Experiment is instantiated inside a Process, can the Process override or extend the entry configuration for that specific usage? Current design is unclear.

### 10. Workflow Integration Gaps

- Existing workflow actions include `link_experiments` (the old mechanism).
- New actions will likely be needed: `create_process`, `add_experiment_to_process`, `assign_sample_to_process`, `queue_sample_in_process_step`.
- No actions currently exist for the Process concept.

### 11. Permissions and Access Control

- Processes introduce a new authorization boundary.
- Does assignment to a Process grant implicit access to the contained Experiments?
- RLS impact: new policies needed for `Process` and `ProcessSample` tables.
- How does this interact with existing project-based sample access?

### 12. Naming and Mental Model Clarity

- "Process" is already used inside `ExperimentRun` (`ExperimentProcess`).
- This creates namespace collision in code and documentation.
- "ProcessSample" may be confused with sample processing in other contexts (e.g., processing_conditions on executions).

## Recommendations / Decisions Needed

1. **Define the ownership and lifecycle of `ProcessSample`** relative to `ExperimentSampleExecution` before any schema work.
2. Decide whether the new Process model *replaces* `experiment_link` or coexists.
3. Clarify the relationship (if any) between ELN Processes and LIMS Experiment Runs for end-to-end workflows.
4. Establish naming conventions to avoid collision with existing `experiment_process` / `process_step` tables.
5. Define a migration strategy for existing linked experiments.
6. Specify the exact data model (tables, columns, constraints) for `Process`, `process_experiments` junction, and `ProcessSample`.

## Next Steps

- Produce gap analysis (current implementation vs target).
- Prototype the minimal viable tables (`Process`, junction, `ProcessSample`).
- Define service/ router surface for Process management.
- Align Entries model inside Experiments with Process queuing semantics.

---

**Related Documents**
- `.docs/processes.md`
- `.docs/experiments.md`
- `.docs/experiment-runs.md`
- `.docs/experiment-rework-prerequisites.md`