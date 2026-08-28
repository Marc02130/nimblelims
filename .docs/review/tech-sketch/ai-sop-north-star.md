# Tech sketch (placeholder): AI SOP north star

**Date:** 2026-08-28  
**Status:** **Guidance. Implement gate CLOSED.**  
**Requirements:** [`.docs/review/requirements/ai-sop-north-star.md`](../requirements/ai-sop-north-star.md)  
**Today:** `POST /v1/sop-parse` → Claude → ExperimentTemplate only (`sop_parse_service`). Parser JSON stays on the job.

This sketch is a **north star**, not a P0 build list. Do not implement from this file.

---

## 1. Problem

| Today | North star |
|-------|------------|
| SOP + optional instrument file → template-centric extract | SOP + **example execution files** → process pack |
| No durable retrieval; prompt-sized | Chunk, vectorize, store, retrieve |
| Apply writes ExperimentTemplate | Apply (via MCP) writes process def + Exp steps + LimsRun bindings + `data_parsers` draft |
| Parser authoring imagined as admin UI (work-spine P5 stray) | Parser authored **at SOP time** into the **existing parser framework** |
| AI talks to Anthropic from backend | AI talks to a **dedicated MCP container** that can only call LIMS tools |

## 2. Containers (target)

```text
lims-frontend
lims-backend          existing APIs (process defs, parsers, experiments, lims-runs)
lims-db               (+ optional pgvector)
lims-r-calculator
lims-ai-mcp           NEW — MCP server; tools only; no public host port
vector / object store SOP + example files (lab-scoped). Placeholder: Postgres+pgvector vs sidecar — Leadership ask
```

`lims-ai-mcp` sits on `lims-network` like `r-calculator`. Backend (or the AI host) calls it internally. **Never** expose MCP to the public internet in the placeholder design.

## 3. MCP tools (draft-only)

Names are illustrative.

| Tool | Creates / mutates | Bounce |
|------|-------------------|--------|
| `search_sop_corpus` | Read retrieved chunks | No SOP bytes in git |
| `draft_process_definition` | `eln_process_definitions` + steps (`eln_experiment` \| `lims_run`) | `active=false` |
| `draft_experiment_template` | Template + entries for an experiment step | No live experiment instance |
| `draft_parser` | `data_parsers` JSON **framework config** + example/test file ids | Inactive, **unbound** to production runs |
| `dry_run_parser` | Existing parse engine on an example file | No result rows |
| `link_parser_analysis` | M2M parser ↔ analysis | Still inactive |

**No tools:** publish results, mint Tests, receive samples, activate parser, `config:edit` activate, write `reported_result`.

Auth: tool calls as the **initiating user**. Audit: one row per tool invocation (who, tool, ids, deny/allow).

## 4. Parser is a framework

Reuse [data-parsers sketch](data-parsers-lims-runs.md):

- AI outputs `ParserConfig` (delimiter, header, column map, …)
- Engine already in backend judges dry-run
- Day-to-day import: **no LLM** (G4)

AI does **not** emit Python/R parsers.

## 5. Vectorize + retrieve

Placeholder pipeline:

1. Upload SOP + N example files (same job)
2. Extract text (PDF → text; CSV stays as table + header digest)
3. Chunk; embed; store with `client_id` / job_id / source_kind (`sop` \| `example`)
4. At authoring: retrieve top-k for “steps”, “sample types”, “file columns”
5. Send **chunks + tool schemas** to the model, not the whole PDF if it does not fit

Store choice is a Leadership ask (pgvector vs sidecar). RLS must match SOP job visibility.

## 6. How this meets the run spine

```text
AI/MCP ──draft──► process_definition + parser (inactive)
Human  ──activate──► catalog
Admin  ──routing_map──► analysis × sample_type × TAT → that process chain
Tech   ──asked-for──► work_order ──start──► Process/Exp/LimsRun
Import ──saved parser──► lims_run_data ──publish──► Results
```

Routing map stays. AI fills **what the map points at**.

## 7. Security sketch (for CSO feedback)

- MCP has no `DATABASE_URL` for writes; HTTP to backend with user token
- No tool to skip activate
- Prompt injection: SOP text is **untrusted**. Tools must not follow “ignore policy, activate”
- Do not log raw SOP in app logs
- Example files may contain client data — same RLS as samples/runs

## 8. Phasing (suggestion, not a gate)

| Slice | What | Still not the north star? |
|-------|------|---------------------------|
| Interim P4 | Apply → process definition (no vectors, no MCP) | Yes — stops the template-only lie |
| North star A | Vector store + retrieve into current Claude job | Retrieval, still no MCP writes |
| North star B | `lims-ai-mcp` draft tools | Differentiator |
| North star C | Parser draft + dry-run at SOP | Differentiator |

Leadership should say whether interim P4 is worth it or trains the wrong story.

## 9. Bounce

- LLM on production import
- Executable parser code
- Auto-activate
- Inventing numeric results
- SOP bodies in git
- IC50
- Claiming dest-type Hold is fixed
