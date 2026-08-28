# Guidance PRD: AI SOP → live process (north star)

**Date:** 2026-08-28  
**Status:** **Guidance only. Implement gate CLOSED.** Placeholder so we do not lose the differentiator.  
**Stem:** `ai-sop-north-star`  
**Sketch:** [`.docs/review/tech-sketch/ai-sop-north-star.md`](../tech-sketch/ai-sop-north-star.md)  
**Leadership send:** [`.docs/discussions/2026-08-28-ai-sop-north-star.md`](../../discussions/2026-08-28-ai-sop-north-star.md)  
**Today’s lie (locked finding):** [`.docs/review/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md)  
**Not this packet:** [post-receive-work-spine](post-receive-work-spine.md) is how the lab **runs** (asked-for → map → work_order → steps). This document is how the lab **authors** that catalog from an SOP.

Do **not** treat post-receive P4/P5 as the AI product. P4 “Apply writes a process definition” is a **step on the way**. The north star is: SOP + example execution files → vector store → AI, via MCP, creates the process (experiments + LimsRuns) **and** the parser used to parse later files.

---

## 1. Why this exists

NimbleLIMS is a framework LIMS. Competitors have catalogs. The wedge is:

**Upload the SOP and files from actually running that SOP. The system turns that into a runnable process pack: experiment steps, LimsRuns, and a parser — without an engineer writing a parser or a BA cloning a template by hand.**

If we keep “admin configures parsers in a UI” as the success line, we are building a conventional LIMS. That is the stray.

## 2. Job to be done

| Actor | Job |
|-------|-----|
| Lab manager / scientist | I have an SOP and last week’s instrument/CRO files from executing it. I want Nimble to propose the process I will run next time. |
| Lab tech | I execute that process. I import the next file. I do **not** talk to an LLM at import. |
| Admin (`config:edit`) | I **review and activate** what AI drafted. I do not author JSON parsers from scratch. |

## 3. North-star flow

```text
1. Upload SOP (PDF/text) + example data from executing that SOP
2. Chunk + vectorize + store (lab-scoped, not git)
3. AI retrieves that content
4. AI, through an MCP server (new Docker container), drafts:
      - eln_process_definition (ordered steps)
      - experiment templates / entries for non-instrument steps
      - LimsRun bindings (analysis required)
      - data_parsers config for the example file shape  (framework engine, not new code)
5. Human reviews. Save = draft (inactive). Activate = config:edit
6. Day-to-day: routing_map points at that process pack; import uses the saved parser (no LLM)
```

## 4. Product locks (guidance — not implement)

| ID | Lock |
|----|------|
| **NS-1** | **Two legal jobs.** SOP-only may draft a **process skeleton** (no parser). **Parser draft requires** example execution files of the **same shape as production import**. Files-only (no SOP) is not the product. |
| **NS-2** | Files are **vectorized and stored**. AI is sent **retrieved chunks**, not a hope that the prompt remembers the PDF. |
| **NS-3** | AI **creates catalog objects** (process, experiment steps, LimsRuns, parsers). It does **not** invent result numbers or auto-publish. |
| **NS-4** | **Parser is a framework** (`data_parsers` JSON instructions + existing engine). AI fills that schema. No user-uploaded executable parsers. No second parse engine. |
| **NS-5** | **MCP server** is a **separate Docker container** on the LIMS network. Tools wrap existing **backend HTTP APIs**. No public host port. No `DATABASE_URL`. No LLM API key on the MCP container. |
| **NS-6** | Human **save/activate**. Drafts start inactive/unbound. Same as SOP Apply today, but the success path is process + parser, not ExperimentTemplate only. |
| **NS-7** | **Day-to-day import is deterministic** (existing G4). LLM is authoring-time, not every file. |
| **NS-8** | No SOP PDF bodies in git. Not IC50. Dest-type Hold (blood → DNA daughter) is **not** closed by a perfect parse. |
| **NS-9** | AuthZ: container identity ≠ data identity. MCP authenticates as a service; **every tool runs as the initiating user**. No god token. Client cannot author. `config:edit` **human** activate. Audit allow **and** deny. No SOP bytes in logs. |
| **NS-10** | **No MCP activate** (or routing_map, publish, receive, mint Test, write results). Server forces drafts `active=false` and parsers **unbound**. |
| **NS-11** | SOP text and example files are **untrusted** (prompt injection). Tool allowlist is the control, not the system prompt. |

## 5. Relationship to post-receive work spine

| Spine (run) | North star (author) |
|-------------|---------------------|
| Asked-for: analysis + TAT + params | AI may **propose** param defs from the SOP; human still confirms |
| `routing_map` → work_order | Map still needed. AI **does not replace** routing. It **fills** the process packs the map points at |
| Execute Process / Exp / LimsRun | Unchanged substrate |
| P4 Apply → process def | **Interim** if we ship it before vector store + MCP |
| P5 “admin parser UI” | **Not** the differentiator. Admin **reviews** AI-made parsers. A thin activate/dry-run UI remains |

Corrected success line for the spine: **Parser setup is an AI job at SOP time, not an engineering ticket.** Admin activates.

## 6. Non-goals (this guidance)

- Implement this quarter without Leadership restamp  
- LLM on every import  
- AI writing result values  
- Auto-activate live processes  
- Replacing `data_parsers` with generated Python  
- Closing extract-hold dest type  
- Materials, lots, multi-tenant  

## 7. Asks for Leadership (to make a better guidance doc)

Round 1 (2026-08-28 Leadership send) — **provisional answers**, not an implement stamp:

| Ask | Round 1 |
|-----|---------|
| 1. Vector store | **pgvector in our Postgres** (same RLS as SOP jobs / samples). No cloud vector SaaS. |
| 2. MCP activate? | **Draft-only.** Human `config:edit` activates. |
| 3. One SOP vs chain | **One SOP → one process definition** by default. A job with **two methods** may propose a **chain of defs**; AI does **not** write `routing_map`. |
| 4. Example files | **Required to draft a parser.** Same shape as production import. SOP-only → process skeleton only. |
| 5. Interim P4 | **Ship a tiny P4** to stop the template-only lie. **Do not** ship “admin authors parsers” as P5. P4 is not the differentiator. |

Full persona notes: [discussion](../../discussions/2026-08-28-ai-sop-north-star.md).  

## 8. Implement gate

**CLOSED.** This is a north-star placeholder. Coding the MCP container, vector pipeline, or replacing SopParse Apply is **out** until Leadership restamps and a real review packet runs.
