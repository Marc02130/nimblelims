# Idea: AI-assisted analyte resolution (when aliases miss)

**Status:** Exploratory follow-on to run→results  
**Branch:** `run-results`  
**Date:** 2026-07-11  
**Related:** [run-results.md](run-results.md), [open-questions/run-results.md](../open-questions/run-results.md)

## Problem

Instrument/CRO column names for the **same** analyte are arbitrary strings with **no reliable pattern**:

| Canonical (DB) | Aliases people actually send |
|----------------|------------------------------|
| Ethanol | `ethanol`, `EtOH`, `C2H5OH`, `Ethyl alcohol`, … |

A **maintained alias list on the analyte** (v1) is the right primary fix—same approach labs already use offline. Matching remains:

1. Exact / normalized name  
2. Alias list hit  
3. Else **unresolved**

AI is **not** a substitute for the list; it is a **helper when the list fails**.

## Idea

When promote (or a pre-publish preview) finds:

- A JSONB column that does **not** match any analyte name/alias, **and/or**  
- An expected analyte on the run’s **analysis** with **no** corresponding column/result from the run  

…offer an **AI-assisted suggestion** path (lab user reviews before apply):

| Case | AI help |
|------|---------|
| **Unmatched column** | Propose which catalog analyte it is (or “not an analyte / skip”) |
| **Missing analyte on run vs analysis** | Flag “analysis expects Lead; no column found” — AI may suggest alternate column names to map, not invent data |

### Guardrails (must)

- **Human confirm** before writing aliases or results (align Decision #9 lab-only).  
- Suggestions may **propose adding an alias** to the analyte’s maintained list—not silent auto-alias.  
- Prefer **lab catalog** context (analyte names + existing aliases) in the prompt; optional RAG over past successful maps later.  
- Never invent numeric **values**—only **identity** of columns ↔ analytes.  
- Client isolation if any SOP/history is used for context.

### Non-goals (this idea)

- Replacing the maintained alias list as SoT  
- Auto-promote without publish  
- Chemical structure inference as v1 requirement (nice later)

## Fit with run→results v1

| Phase | Approach |
|-------|----------|
| **v1 (implement now)** | **Maintained alias list on analyte** only; unresolved → error/skip in preview |
| **Later** | This idea: AI assist on unresolved + gap detection vs analysis analytes |

## Open questions (for when this idea is reviewed)

1. Inline on promote preview vs separate “map columns” wizard?  
2. Does accepting a suggestion auto-append to analyte.aliases?  
3. Cloud vs local LLM (see sop-rag provider work)?  

## Success metric

Reduction in publish failures / manual remaps after first CRO file for a given analysis; growth of alias list quality over time.
