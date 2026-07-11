# Gap Analysis: Process and Experiment

**Date:** 2026-06-30  
**Branch:** refactor/experiments  
**Focus:** ELN Experiments + proposed Process construct

## Purpose

This document identifies the concrete gaps between the **current implementation** and the **target design** described in the documentation and recent feedback.

Gaps are categorized by area and prioritized (P1 = blocking for basic Process functionality, P2 = important for usability, P3 = nice-to-have or future).

## 1. Data Model Gaps

| Gap | Current State | Target State | Priority | Notes |
|-----|---------------|--------------|----------|-------|
| First-class `Process` entity | Does not exist. Linking via `ExperimentDetail` only. | Explicit `Process` table with metadata and ordered children. | P1 | Core of the refactor. |
| Ordered membership of experiments in a process | Implicit linked-list via `detail_type="experiment_link"`. No enforced order or integrity. | Dedicated junction table (e.g. `process_experiments`) with `sort_order` and FK constraints. | P1 | Prevents cycles and guarantees ordering. |
| Process-level sample tracking | Samples only tracked per-experiment via `ExperimentSampleExecution`. | `ProcessSample` table for samples assigned to a Process. | P1 | User directive: "use processsample to track samples assigned to processes." |
| Relationship between `ProcessSample` and `ExperimentSampleExecution` | N/A | Must be defined (composition vs. separate concerns). | P1 | Critical ambiguity. |
| Experiment-specific tables for data entries | All custom data lives in `custom_attributes` JSONB or generic `ExperimentDetail`. | Per-entry typed tables whose columns are defined in the template. | P2 | Required for points 4 and 8 from review comments. |
| Write-back capability from sample entries | No supported path. | Sample entries can update core `Sample` attributes (concentration, volume, etc.). | P2 | Needs audit, authorization, and conflict resolution rules. |
| Predefined entry configuration on templates | No concept of "entries" on templates. | Templates can declare which predefined entries are active for instances created from them. | P2 |  |

**Current tables that are related but in the wrong domain:**
- `experiment_processes` and `process_steps` exist but are attached to `experiment_runs` (LIMS side only).

## 2. API / Service Layer Gaps

| Gap | Current | Target | Priority |
|-----|---------|--------|----------|
| Process CRUD | None | Full CRUD + ordering operations for experiments inside a process. | P1 |
| Sample assignment to process | Only per-experiment via `link_sample_to_experiment`. | `assign_samples_to_process`, `remove_samples_from_process`. | P1 |
| Queuing / advancing samples within a process | No concept. | `queue_sample_in_process_step`, `advance_sample_to_next_step`. | P1 |
| Process-level lineage queries | `get_experiment_lineage` only follows `experiment_link` details. | Efficient queries across an entire ordered process. | P1 |
| Workflow actions for processes | Only `link_experiments` (old mechanism). | New actions: `create_process`, `add_experiment_to_process`, `assign_sample_to_process`, `queue_sample_in_process_step`. | P2 |
| Process templates / reusable definitions | None | Ability to define reusable process structures (ordered list of experiment templates + default entries). | P3 |

## 3. UI Gaps

| Gap | Current | Target | Priority |
|-----|---------|--------|----------|
| Process creation and editing | No UI. | Dedicated process builder (select/ order experiments). | P1 |
| Sample assignment to processes | Samples assigned directly to experiments. | UI to assign samples to a Process, then see them flow through steps. | P1 |
| Queuing / worklist view per process step | No support. | "Queue samples into this experiment" from within a process context. | P1 |
| Process overview / progress | None. | Dashboard showing all steps and sample status across the process. | P2 |
| Entry configuration in templates | Templates have loose `template_definition`. | UI to add/remove predefined entries and define columns for custom sample/experiment detail entries. | P2 |

## 4. Behavior and Consistency Gaps

- **Ordering guarantees**: Current links provide no total order. A Process must enforce one.
- **Sample state visibility**: Today you can only see which experiment(s) a sample has participated in. No notion of "current step in process".
- **Duplicate sample tracking risk**: Once `ProcessSample` exists, we must prevent (or clearly document) divergence from `ExperimentSampleExecution`.
- **Entry activation**: When a sample is queued into an experiment via a process, it is unclear which entries from the template should be active vs. the experiment's own configuration.
- **Write-back conflicts**: No rules for what happens when two different steps in the same process attempt to update the same sample attribute.
- **Lineage vs. Process**: Existing `get_experiment_lineage` and `link_experiments` will need to be reconciled with Process membership.

## 5. Cross-Cutting Concerns

| Area | Gap | Priority |
|------|-----|----------|
| **Permissions / RLS** | No policies for new `Process` or `ProcessSample` tables. Unclear how process membership affects visibility of contained experiments/samples. | P1 |
| **Audit** | Write-backs from entries and process-level sample movements have no dedicated audit path today. | P2 |
| **Name collisions** | `experiment_process` / `process_step` already exist for Runs. New ELN Process concept needs distinct naming in code and DB. | P1 |
| **Migration** | Existing `experiment_link` records and sample executions need a path to new Process model (or coexistence strategy). | P1 |
| **Workflow integration** | No actions for the new Process model. Existing `link_experiments` will become legacy. | P2 |
| **Search / Reporting** | No way to query "all samples currently in step X of process Y". | P2 |

## 6. Documentation & Mental Model Gaps

- The distinction between:
  - Loose `experiment_link` lineage
  - Explicit Process ordering
  - Sub-processes inside Runs
  is not yet clear to developers or users.
- "Process" term is overloaded.
- The role of `lifecycle_type` on templates when applied to Processes (vs. individual Experiments) is not defined.
- How Processes interact with the "Entries" model (especially predefined entries) needs a dedicated design section.

## 7. Testing & Validation Gaps

- No tests for ordered multi-experiment workflows with sample progression.
- No tests for `ProcessSample` consistency with per-experiment executions.
- No tests exercising template-defined entry columns + write-back.

## Summary of Highest Priority Gaps (P1)

1. Define and implement `Process`, ordered junction, and `ProcessSample` tables.
2. Decide and document the relationship and consistency rules between `ProcessSample` and `ExperimentSampleExecution`.
3. Resolve naming collision with existing Run-side `ExperimentProcess`.
4. Define migration/coexistence strategy for `experiment_link`.
5. Add basic Process CRUD + sample assignment APIs.
6. Add RLS policies for new tables.
7. Clarify boundary between ELN Processes and LIMS Runs for data-producing steps.

## Recommendations

- Treat `ProcessSample` as the authoritative source for "this sample belongs to this process" while `ExperimentSampleExecution` remains the detailed execution record for a specific step.
- Make the ordered membership explicit and enforced (junction table) rather than relying on detail ordering.
- Produce a small data model diagram + sequence diagram for sample flow through a Process before implementation.
- Decide early whether Processes can ever reference LIMS Runs or remain strictly ELN.

---

**Related Documents**
- `.docs/manuals/processes.md`
- `.docs/design-review/process-and-experiment.md`
- `.docs/manuals/experiments.md`
- `.docs/manuals/lims-runs.md`
- `.docs/checklist/experiment-rework-prerequisites.md`