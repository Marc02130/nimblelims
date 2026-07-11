# Design Review: Process and Experiment Plans

**Date:** 2026-07-09  
**Branch:** refactor/experiments  
**Reviewer:** Design / UX  
**Scope:** UX, mental models, interface patterns, and product design implications of the experiment + process + entries work. Based on `.docs/experiments.md`, `.docs/processes.md`, `.docs/gap-analysis-process-and-experiment.md`, `.docs/design-review-process-and-experiment.md`, `.docs/requirements/experiment-processes-entries.md`, and related Field Management work.

## Executive Summary

The plans correctly identify that the current loose `ExperimentDetail` + `experiment_link` model is insufficient for ordered, multi-step experimental work. Introducing explicit **Processes** and template-driven **Entries** (powered by the new FieldDefinitions system) is a strong direction.

**Strengths:**
- Good alignment with the FieldDefinitions + lists philosophy (consistency win).
- Clear recognition that "order matters" and that sample flow needs to be first-class.
- Sensible separation of ELN (flexible) vs. LIMS Runs (structured).

**Key Design Risks:**
- Severe mental model overload around the word "Process".
- Ambiguity in how lineage, ordering, and sample state will be presented to users.
- Under-specified interaction between Processes and the new Entries system.
- Risk of building a powerful but confusing system if UI doesn't make the hierarchy and flow extremely clear.

## Current State Problems (from a Design Perspective)

- Lineage is hidden in JSONB details (`experiment_link`) — not visible or editable in any structured way.
- Sample participation is only visible per-experiment; there is no "this sample is currently progressing through this multi-step workflow" view.
- Data capture inside experiments is inconsistent (mix of predefined UI, free-form details, and JSONB).
- No visual or navigational support for ordered work.

## Proposed Model from a UX Viewpoint

### Processes
- Should feel like a **pipeline or worklist**, not just another CRUD entity.
- Users need to see:
  - The sequence of steps at a glance.
  - Which samples are at which step.
  - Overall progress and blockers.
- Key interactions: create process, define order, assign samples, queue/advance samples through steps.

### Entries
- The move to FieldDefinition-backed entries is excellent from a design consistency standpoint.
- Should feel like an extension of the new Custom Fields / Field Management UI.
- Predefined entries should surface as clear actions (not buried in forms).
- Custom sample/experiment detail entries should provide structured forms/tables with good validation.

### Sample Flow
- Assignment at Process level + progression through steps is the right abstraction.
- UI must make the "current step" and "next action" obvious.

## Critical Design Issues & Recommendations

### 1. Mental Model Clarity (Highest Priority)

**Problem**: "Process" is already used inside LIMS Experiment Runs (`ExperimentProcess`, `ProcessStep`). We also have Workflows, Batches, and now ELN Processes.

**Recommendations**:
- Use distinct, clear naming in the UI (e.g., "ELN Process", "Experiment Workflow", or "Protocol Process").
- Create a short "Concepts" page or in-app help that explicitly distinguishes:
  - ELN Experiment
  - ELN Process
  - LIMS Experiment Run
  - Workflow Template
  - Batch
- In navigation and labels, be explicit: "Processes (ELN)" vs. sub-processes in Runs.

### 2. Hierarchy and Navigation

Current sidebar has "Experiments" accordion. We will need to decide:
- Do Processes live under Experiments, or get their own top-level section?
- Recommended: Processes as a peer or sub-section under Experiments, with clear entry points.

Inside a Process:
- Overview (pipeline view or ordered list)
- Samples tab (with current step indicator)
- Steps (drill into individual Experiments)
- Progress / status roll-up

### 3. Consistency with Field Management

This is one of the strongest parts of the plan.

- Defining columns for sample data entries and experiment detail entries should use the same patterns as the new `/admin/custom-fields` experience (entity type, data type, list-backed vs. scalar, validation rules, etc.).
- Reuse components where possible (List selector, validation rule editors, etc.).
- Predefined entries should be presented similarly to OOB fields.

**Recommendation**: Treat Entries configuration as "Field Definitions scoped to an Experiment Template."

### 4. Lineage vs. Explicit Process Ordering

Current `experiment_link` is a free-form linked list.

**Design impact**:
- Users currently rely on lineage views. We must not break that during transition.
- New Process ordering should be the preferred way going forward.
- UI should offer a clear migration or "convert linked experiments into a Process" flow if possible.
- Avoid showing two competing lineage systems.

### 5. Entry Activation and Configuration in Context of Processes

When a sample is queued into a Process step:
- Which entries from the template are active?
- Can the specific Process usage customize or require certain entries?

**Current gap**: Not specified.

**Recommendation**:
- Start simple: entries are activated exactly as defined on the Experiment Template.
- Later, allow Process-level overrides or requirements (P2).
- Make it visually obvious in the UI which entries are coming from the template vs. any process-specific configuration.

### 6. Write-Back UX

Write-back from sample entries to core Sample fields is powerful but potentially confusing.

**Recommendations**:
- Always show clear "This will update the sample record" messaging.
- Provide an audit / history view of what was written back and from which step.
- Consider making write-backs opt-in per entry or per field.
- Show the effect immediately in the sample detail view.

### 7. Visualization and Feedback

- Processes should support at least a simple visual or card-based pipeline representation.
- Status aggregation (step status → process status) needs good defaults and user control.
- "My Work" or queue views per user would be high value (samples waiting for me in a process step).

### 8. Progressive Disclosure & Optionality

- Many users will continue to use simple Experiments without Processes.
- Don't force users into the Process model.
- Make creating a simple ad-hoc Experiment still easy and prominent.
- Reveal Process features progressively (e.g., "Turn this into a multi-step Process").

## Alignment with Existing Design Work

- **Field Management (OOB + custom)**: Strong alignment. Entries should feel native to this system.
- **Lists preference**: Excellent. Use lists for any selectable values inside entries.
- **Hard cutover philosophy**: Good. The move away from loose JSONB in experiments is consistent with the broader cleanup.

## Open Design Questions

1. What is the primary navigation model for Processes? (Own accordion? Under Experiments? Searchable entity?)
2. How should we represent "current step" for a sample across the whole system (sample detail page, lists, dashboards)?
3. Should there be a visual difference between Experiments created inside a Process vs. standalone?
4. What is the minimal delightful first experience for a user creating their first Process?

## Recommendations Summary

1. **Invest heavily in mental model clarity** before building UI — naming, help text, diagrams, and consistent labels.
2. **Make Processes feel like pipelines**, not just another list of things.
3. **Reuse the Field Management patterns** aggressively for entry configuration and data entry.
4. **Plan the transition from `experiment_link`** explicitly in the UI (don't just hide the old mechanism).
5. **Design write-back feedback** as a first-class experience, not an implementation detail.
6. **Keep simple paths simple** — Processes should be an upgrade, not a requirement.

## References

- `.docs/requirements/experiment-processes-entries.md`
- `.docs/gap-analysis-process-and-experiment.md`
- `.docs/experiments.md` and `.docs/processes.md`
- Field Management design docs (unified OOB + custom via lists)
- Existing ExperimentsManagement and ExperimentTemplatesManagement UI patterns

---
**Next**: Review this alongside the requirements document and decide on navigation hierarchy and mental model communication strategy before detailed UI design.