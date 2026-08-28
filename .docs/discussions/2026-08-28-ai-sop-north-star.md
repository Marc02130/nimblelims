# Leadership send: AI SOP north star (guidance)

**Date:** 2026-08-28  
**Team:** Leadership (Lab Ops, CEO, Security CSO, Scientific CSO)  
**Ask:** Thoughts and feedback to **improve this guidance**. Not an implement vote.  
**Implement gate:** **CLOSED**

**PRD (placeholder):** [`.docs/review/requirements/ai-sop-north-star.md`](../review/requirements/ai-sop-north-star.md)  
**Sketch (placeholder):** [`.docs/review/tech-sketch/ai-sop-north-star.md`](../review/tech-sketch/ai-sop-north-star.md)  
**Today’s finding:** [sop-ai-to-process](../review/open-questions/sop-ai-to-process.md) — Apply writes a template; SOP+AI → live process is a lie.

---

## The stray

Post-receive work spine success currently reads like a conventional LIMS:

- receive tubes  
- record asked-for  
- **admin** sets up parsers  

That last line is wrong for the product we said we were building. **Parser setup is an AI job at SOP time.** Admin activates. The run spine (asked-for → routing map → work_order → Process/Exp/LimsRun) stays. This north star **authors** the catalog that spine consumes.

## One paragraph

Scientist uploads the SOP and files produced by **executing** that SOP. We vectorize and store them. An AI, talking only through a **new MCP Docker container**, drafts a process (experiment steps + LimsRuns) and a **parser config** for the existing parser **framework**. Human reviews. Later imports do not call an LLM. Routing still turns “ELISA, plasma, 5-day TAT” into a work_order.

## Asks (please answer)

1. pgvector in our Postgres vs a sidecar for embeddings?  
2. MCP tools draft-only, or may they activate? (PRD recommends draft-only.)  
3. One SOP → one process definition, or AI may emit a **chain** (extract then assay) that routing/WO already knows how to snapshot?  
4. Are example execution files **required** to author a parser (PRD NS-1)?  
5. Ship interim P4 (Apply → process def, no MCP/vectors) or wait so we do not teach “template+admin parser UI”?  

## Feedback (Leadership) — round 1

**Not an implement stamp.** Gate stays **CLOSED**.

### Roll-up

| Ask | Lab Ops | CEO | Security CSO | Sci CSO |
|-----|---------|-----|----------------|---------|
| 1. Store | pgvector if it keeps client RLS | **pgvector in our Postgres.** No cloud vector SaaS | **pgvector + FORCE RLS.** No sidecar AuthZ plane | Store is not scientific; RLS must match samples |
| 2. Activate | **Draft-only.** Non-negotiable | **Draft-only. Hard lock** | **Draft-only. Locked.** No god token | Draft-only (analyte remap risk) |
| 3. One vs chain | Default one SOP → one def; two SOPs may be a chain; mashed extract+assay is a reject | One SOP → one def; job **pack** may emit a chain of defs; AI does not write the map | Chain of **drafts** OK; **no MCP routing_map tool** | One method → one def; split only when two methods are in the job |
| 4. Example files | Required for parser; same production shape; SOP-only = no parser | Required to **author a parser**; not required to draft a process | Required to author a parser; SOP-only must not invent columns | **Hard gate.** SOP-only → process skeleton only |
| 5. Interim P4 | **Ship P4.** Do not ship P5 as success line | **Tiny P4 lie-closer.** Do not wait for MCP to stop the template lie. Do not sell P4 as the product | P4 OK if drafts stay inactive/unbound | P4 OK with L5 copy; no parser from SOP-only |

**Consensus:** Parser setup is an **AI job at SOP time**. Admin activates. Run spine stays asked-for → map → WO. Dest-type Hold is unchanged. No LLM on import. MCP has no activate tool and no DB URL.

### Lab Ops (Deiter)

Authoring job, not a run path. Do not sell “upload SOP and tubes move.” NCI extract → Qubit still **cannot execute** until dest-type writes a DNA daughter. SOP-only drafts process skeleton; parser needs production-shaped files. Activate UI must show steps, types, and dry-run columns — not JSON. Two SOPs (23113 + 22975) stay two definitions. Example files are client data.

### CEO / Product

Wedge is 10-star; do not inflate with a lab chatbot. Kill “admin authors parsers.” Ship brutal tiny P4 to close today’s template lie; do not ship a parser IDE. Dry-run pass before parser activate. AI may propose param defs; human confirms. Do not let P5 eat this document.

### Security CSO

MCP: no host port, no `DATABASE_URL`, no LLM key, tools = backend HTTP as **the user** (not a lab-wide service account). Split network so MCP cannot reach Postgres. SOP text is untrusted; allowlist is the control. pgvector in the same DB with FORCE RLS; ANN in the same query, not retrieve-then-filter. Audit allow **and** deny; never log SOP bytes. No “fallback to AI if parse fails.”

### Scientific CSO

Parser draft refuses without an import-shaped example. Cross-reference in an SOP is not a second method. Process fields ≠ params ≠ results (no fitted IC50 in param JSON). Dest-type Hold: parser quality ≠ dest mint. Not IC50; not PR 48 files as this path.
