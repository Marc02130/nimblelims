# Idea: Revisit workflows — accessioning (manifest + receive verification)

**Status:** Placeholder — **out of scope** for experiment entries / ELN tables work  
**Date:** 2026-08-10  
**Related:** [workflow-accessioning-to-reporting.md](../manuals/workflow-accessioning-to-reporting.md), [accessioning-workflow.md](../manuals/accessioning-workflow.md), [orders-and-projects.md](orders-and-projects.md); experiment start queue (select samples into experiment/run)

## One-liner

Accessioning is a **workflow** and must stay **configurable**. Revisit it end-to-end so labs can (1) **upload a sample manifest file**, and (2) **verify samples received** — supporting both **continuous** and **discontinuous** receive processes — without hard-coding a single intake path.

## Problem

| Gap | Why it matters |
|-----|----------------|
| Manifest-driven intake | Common: courier/cooler list or spreadsheet before/with physical samples |
| Verify received | Match physical receipt to expected list; handle missing/extra/damaged |
| Continuous vs discontinuous | Some labs receive in a stream; others in discrete batches/events |
| Configurability | Accessioning fields and steps differ by lab; should use Field Management + workflow patterns |

This is **adjacent** to experiment start (queue → select samples) but **not** the same surface: accessioning creates/registers samples; the experiment queue **selects already accessioned** (or otherwise ready) samples into a work unit.

## Non-goals (this idea doc)

- Implementing experiment_sample_data / experiment_data  
- Designing full ELN entry catalog beyond noting start-of-experiment header + samples entries  
- Merging accessioning UI into experiment start  

## Direction (for a later cycle)

1. Map current accessioning + workflow template capabilities.  
2. Define **manifest upload** contract (columns, validation, create vs match existing).  
3. Define **receive verification** states (expected / received / exception).  
4. Support continuous vs batch receive without two products.  
5. Keep identity fields (client sample id, client, subject, …) owned by accessioning — experiment entries only **display** them.

## Success sketch

- Lab configures accessioning workflow once.  
- Operator uploads manifest → system stages expected samples.  
- Operator verifies receipt (continuous or discontinuous) → samples ready for queue.  
- Experiment/run start picks from queue; no re-accessioning in the experiment entry.

## Open when we prioritize this

- Manifest formats and client-specific templates  
- Exception handling (partial cooler, relabel)  
- Tie-in to orders/projects rename idea  
- Permissions for verify vs register  
