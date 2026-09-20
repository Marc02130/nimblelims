# Product north star — Leadership lock

**Date:** 2026-09-20  
**Status:** Decided (Leadership / Core)  
**Source:** NimbleLIMS Core — Marc + Rolf; Spec fold Wilhelmina  
**Related:** [framework-stamps-2026-08-26](framework-stamps-2026-08-26.md) · [ai-sop-north-star](../review/requirements/ai-sop-north-star.md) · [ai-config-breadth](../review/open-questions/ai-config-breadth.md)

---

## Lock

NimbleLIMS is defined by **two goals**:

| # | Goal | Lock |
|---|------|------|
| **1** | **Framework first** | Flexible system that does **not** require re-coding when a laboratory adopts it. Adoption is **configuration** — rules, design, and page layouts stored in the DB. |
| **2** | **AI configuration from SOPs** | AI proposes that configuration from SOPs; humans edit and refine. |

A framework design (goal 1) enables AI-assisted configuration (goal 2) **throughout** the product — not only sample processing.

---

## Sequencing

1. **Finish sample processing** (living ISSUES: **E-10 Met**; Tobias honesty-check uniqueness **7.9 / 7.9b** — not a merge; then **E-14 / E-12**, then **E-6 / E-7**, remaining spine).  
2. **Then** look at AI to configure beyond sample processing (login, reporting, storage, etc.).  
3. Do **not** open those broader AI packets now.

---

## Docs folded

- Umbrella PRD §2.0.1 · sample-processing PRD / ISSUES · `ai-sop-north-star` · OQ `ai-config-breadth`
