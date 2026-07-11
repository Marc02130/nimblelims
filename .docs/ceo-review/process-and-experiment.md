# CEO Review: Process and Experiment Plans

**Date:** 2026-07-09  
**Branch:** refactor/experiments  
**Reviewer:** CEO / Product Strategy  
**Context:** Review of experiment plans including `.docs/experiments.md`, `.docs/processes.md`, `.docs/gap-analysis-process-and-experiment.md`, `.docs/design-review-process-and-experiment.md`, and the consolidated requirements in `.docs/requirements/experiment-processes-entries.md`.

## Executive Summary

The direction to introduce first-class **Processes** (ordered collections of Experiments) and a structured **Entries** system (using FieldDefinitions) is strategically sound. It addresses a real pain point: labs doing complex, multi-step experimental work currently rely on informal linking via `ExperimentDetail` records, which doesn't scale for ordering, sample flow, or governance.

**Key Wins:**
- Aligns with the broader FieldDefinitions + lists hard cutover (avoids recreating custom attributes mess inside experiments).
- Separates ELN (flexible, process-oriented) from LIMS Runs (structured, publishable) — correct boundary.
- Opportunity to make "sample journey" a first-class, trustworthy view.

**Main Risks / Opportunities:**
- The ELN vs. LIMS split is useful today but could become a long-term fragmentation risk if not bridged with excellent visibility.
- Potential over-engineering: Not every lab needs formal Processes. Make them powerful but optional.
- Huge product leverage in reusable Process Templates and unified sample state across the platform.

## Strategic Assessment

### Strengths
- **Correct problem framing**: Current `experiment_link` is a linked-list hack. Processes + explicit ordering + `ProcessSample` is the right abstraction for "order matters" workflows (NGS prep, multi-stage protocols).
- **Leverages recent FieldDefs work**: Using FieldDefinitions for entry columns (list-backed for selects, validation rules for scalars) is the right long-term model.
- **Respect for domain differences**: Keeping ELN Experiments flexible (list-driven status) vs. Runs rigid (enum lifecycles) shows good product intuition.
- **Focus on sample flow**: `ProcessSample` as the assignment layer while keeping `ExperimentSampleExecution` for per-step detail is a smart separation.

### Weaknesses / Gaps in Thinking
- **Boundary with Runs is under-specified**. Many real processes end in instrument data or QC that lives in Runs today. If we pull QC into Entries/Experiments, we risk splitting the source of truth for sample state. A 10-star product needs a single "where is my sample in its journey?" experience.
- **Optional vs. mandatory**: The plan emphasizes rich Processes but doesn't strongly call out that many labs will continue with simple single-Experiment or ad-hoc flows. We must avoid forcing complexity.
- **Reusability is under-scoped**. Processes are treated mostly as instances. Reusable "Process Templates" (ordered list of Experiment Templates + default entries + sample requirements) would be a bigger lever than instance-only Processes.

## Product Opportunities (10-Star Thinking)

1. **Sample Journey as the Killer Feature**
   - Today: fragmented (participated in Experiments, this batch, this run).
   - Future: A Process view becomes the authoritative "this sample is in this workflow at this step, here's what happened, here's what's next."
   - This could differentiate NimbleLIMS significantly from generic LIMS + separate ELN tools.

2. **Process Templates**
   - Let labs define reusable multi-step protocols once (e.g., "Standard NGS Library Prep Process").
   - Instantiating a Process from a template should pre-populate steps, entries, and sample requirements.
   - This turns the system from "tracking what happened" into "orchestrating how we do work."

3. **Unified Visibility Layer**
   - Even if backend models stay separate (ELN vs. Runs), build a cross-cutting "Sample Journey" surface that aggregates Processes, Experiments, Runs, and Batches.
   - This reduces the pain of the split without forcing a full model unification (which may not be desirable).

4. **Progressive Disclosure**
   - Simple labs: just use Experiments directly.
   - Complex labs: unlock Processes, Entries, write-backs.
   - This respects the "flexible for most, structured where needed" philosophy already used for statuses and FieldDefs.

## Scope Recommendations

**Do First (Phase 1 Focus):**
- Minimal viable Process: create, order steps, assign samples via `ProcessSample`, explicit progression.
- Basic Entries for sample data and experiment detail using existing FieldDefinitions.
- Strong mental model documentation and UI labels to prevent confusion with Runs, Batches, and Workflows.
- RLS + audit for the new entities (non-negotiable).

**Defer or Phase 2:**
- Reusable Process Templates.
- Full write-back conflict resolution and governance.
- Deep integration between ELN Processes and LIMS Runs.
- Advanced visualization (pipeline diagrams) until core flows work.

**Watch for Scope Creep:**
- Don't try to solve every lineage/ordering use case in v1. Start linear and strict; add DAG support only if real demand appears.
- Avoid turning Processes into a general workflow engine (that's a separate concern).

## Risks

- **Fragmentation**: If ELN and LIMS experiment concepts diverge too far without good bridging, users will experience duplicated sample tracking and conflicting state.
- **Adoption**: If Processes feel mandatory or overly complex, adoption will be low. Emphasize optionality.
- **Data Integrity on Write-Backs**: This is both a product and security risk. Poor rules here will erode trust in sample data.

## Recommendations

1. **Prioritize sample state clarity** above almost everything else. Make `ProcessSample` the source of truth for "belongs to this workflow."
2. **Invest early in naming and mental model documentation**. "Process" is already overloaded in the codebase (LIMS `ExperimentProcess`). Fix this before code lands.
3. **Build a thin unified visibility layer** even in Phase 1 — e.g., "Sample Journey" tab or query that shows Processes + linked Runs.
4. **Treat reusable Process Templates as a high-value Phase 2** rather than deferring indefinitely.
5. **Validate with real lab managers**: Ask "Would you rather have a simple Experiment list or a Process builder?" before over-building the rich side.

## Open Strategic Questions

- How far should we push unification of the sample journey view vs. keeping clean domain separation?
- Should Processes ever be allowed to contain or reference LIMS Experiment Runs, or stay purely ELN?
- What is the minimum "10x" experience we want users to feel when they adopt Processes?

**Bottom line**: This is good product work. The FieldDefs foundation makes it timely. Execute the minimal model + strong visibility + clear mental models first, then expand into reusability and richer orchestration.

---
Related: `.docs/requirements/experiment-processes-entries.md`, `.docs/gap-analysis-process-and-experiment.md`