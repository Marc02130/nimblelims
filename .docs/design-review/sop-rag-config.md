# Design Review: SOP → Config via RAG

**Date:** 2026-07-11 (revised: RAG-first)  
**Branch:** `sop-rag`  
**Reviewer:** Design / UX  
**Idea:** [`.docs/ideas/sop-rag-config.md`](../ideas/sop-rag-config.md)

## Executive Summary

Users should feel: **“The system remembers how we configure work like this.”**  
Not: “We trained a model.” Not: “Chat with AI about LIMS.”

RAG makes that story true in the UI: show **what was retrieved**, **what will be reused**, and **what is new**—then Apply.

**Strengths:** Plan-first review; native objects (templates, process defs, FieldDefs); trust via explicit memory sources.  
**Risks:** Opaque blob drafts; wrong object type (process vs template); no visibility into retrieval; rubber-stamp Apply.

## User jobs

| Persona | Job | Success |
|---------|-----|---------|
| Lab manager / scientist-admin | Stand up assay from SOP, consistent with lab standards | Draft reuses known fields/templates; Apply; start process later |
| Lab tech | Run processes/experiments | Unchanged—does not live in config AI |
| Lab client (sponsor) | Orders / own sample progress | **Never** this config flow (Decision #9) |

## UX principles

1. **Memory is visible** — “Similar SOPs / design docs used” panel (citations).  
2. **Reuse is first-class** — matched existing FieldDefs/templates shown as chips, not buried JSON.  
3. **Draft only** — production objects only after Apply.  
4. **Plan before detail** — checklist of proposed objects, then tabs.  
5. **Simpler default** — single template unless multi-step process is clear.  
6. **No fine-tune knobs** in main UI — optional “Inference: Cloud / Local” under admin later.

## Primary flow

```
[Configure from SOP]
   Upload SOP (+ optional instrument file)
   Optional: client context (if client-confidential method)
        ↓
[Processing] chunk / embed / retrieve / generate
        ↓
[Plan]
  • Sources: 2 similar SOPs, design doc “NGS Prep v3”, 5 catalog matches
  • Propose: 1 new field, 2 link existing fields, 1 process def (3 steps), …
        ↓
[Review tabs] Plan | Sources | Fields | Templates | Process | Runs | Raw
        ↓
[Accept selected] → confirm → Apply
        ↓
[Done] links to objects + “Start process from definition”
        + design doc saved (feeds next job)
```

### Sources tab (RAG-specific)

Critical for trust:

| Section | Content |
|---------|---------|
| Similar SOPs | Filename, score, snippet; open/preview |
| Design docs | Prior applied plans; “open process def created then” |
| Catalog hits | FieldDef/template/process name + id; linked vs new |

If retrieval is empty (first SOP): banner “No prior lab memory—review carefully.”

### Fields / templates / process

- **Link existing** rows: green “Matched” + disable duplicate create by default.  
- **New** rows: editable; warn if name collides.  
- Process steps: step_kind chips (ELN / LIMS Run); “Run config only—no live run yet.”  
- Show **rationale** one-liner per object when model provides it.

## Information architecture

- **Primary entry:** Experiments → Templates → **Configure from SOP** (evolve today’s upload).  
- **Secondary:** Processes → Definitions → **From SOP**.  
- **Admin (later):** Embedding/LLM provider health—not day-1 nav.

Avoid a standalone “AI” product island.

## Empty, error, and edge states

| State | UX |
|-------|-----|
| Job failed | Retry; no partial Apply; error message without dumping SOP to console logs in UI |
| Low retrieval | Explicit warning |
| Name collision | Rename or update existing (choose) |
| Partial accept | Apply only selected; leave rest in draft |
| Client-confidential SOP | Badge on job; retrieval limited accordingly |

## Anti-patterns

| Reject | Why |
|--------|-----|
| Chat-only config | Not auditable SoT |
| Auto-Apply | Trust destroyer |
| Hide retrieval sources | Users can’t validate “memory” |
| Fine-tune training UI in product | Ops, not lab workflow |
| Creating process **instances** from SOP | Protocol ≠ cohort |
| Client-facing config wizard | Decision #9 |

## Success metrics

- % jobs with ≥1 retrieval hit after lab has history  
- **link_existing** rate vs create rate  
- Median human edits before Apply  
- Abandon rate after Plan screen  
- Support: “AI invented duplicate field X”

## Design recommendations

1. **Sources panel is non-negotiable** for RAG credibility.  
2. **Match-or-create** FieldDefs/templates as default interaction.  
3. **Progressive complexity:** catalog injection UI copy even before vectors (“using your field list”).  
4. **After Apply:** celebrate reuse (“3 existing fields linked”) not only “created 12 things.”  
5. Keep visual language consistent with Process / Field Management chips.

**Design score (RAG-first UX): 8.5/10** if Sources + reuse are first-class.  
**Design score without visible retrieval: 5/10** (feels like random AI).

---

Related: [ceo](../ceo-review/sop-rag-config.md), [tech](../design/sop-rag-config.md), [security](../security-review/sop-rag-config.md)
