# Open Questions — SOP → Config (RAG)

**Status:** Living decision log  
**Idea:** [`.docs/ideas/sop-rag-config.md`](../ideas/sop-rag-config.md)  
**Reviews:** [CEO](../ceo-review/sop-rag-config.md) · [Design](../design-review/sop-rag-config.md) · [Tech](../design/sop-rag-config.md) · [Security](../security-review/sop-rag-config.md)  
**Branch (docs):** `sop-rag`

## Gate rule

**Do not start a phase of SOP→config / RAG work until every open question marked as blocking that phase is Decided here.**

| Status | Meaning |
|--------|---------|
| **Open** | No decision — blocks related work |
| **Decided (provisional)** | Ship temporary rule; revisit before expansion |
| **Decided** | Locked for current roadmap |
| **Deferred** | Explicitly out of scope until named phase |

When resolving: fill **Decision**, **Date**, **Owner**, **Rationale**.

Related product decisions already locked elsewhere:

- **Experiments #9:** Lab personnel only edit lab/config data; lab **client** users do not. Clients may later create **orders**.  
- **Experiments #7:** Client users see journey for **their** samples only.

**Client** = customer of the **lab** (sponsor, env customer)—not NimbleLIMS SaaS tenant.

---

## Questions

| # | Question | Status | Blocks | Decision | Date | Owner | Rationale |
|---|----------|--------|--------|----------|------|-------|-----------|
| 1 | Architecture: RAG-first vs fine-tune-first for “learn from past SOPs”? | **Decided** | Whole initiative framing | **RAG-first.** Memory = vectorized SOPs + applied design docs + live catalog. Fine-tune optional later (schema/JSON quality only). | 2026-07-11 | Product/Eng | Reviews consensus; lab memory must update without retrain |
| 2 | Default inference: cloud LLM vs local (Ollama/Docker) for v1? | **Open** | R4 product packaging; R0–R3 can use cloud | — | | | |
| 3 | May AI Apply create process **instances** or only **definitions** (+ templates/fields/run configs)? | **Open** | Apply service scope (R0) | Reviews lean **definitions/configs only**—confirm | | | |
| 4 | Auto-Apply without human review ever allowed? | **Decided** | Safety / trust | **No** for v1 (and default policy). Draft → human review → Apply only. | 2026-07-11 | Product/CSO | Trust + protocol liability; security residual risk |
| 5 | Who can run SOP→config jobs and Apply? | **Decided** | AuthZ | **Lab personnel** with manage/config rights (today `experiment:manage` or successor). **Lab client users: never.** | 2026-07-11 | Product | Aligns Decision #9 |
| 6 | Ownership model: lab-owned vs client-owned SOPs—who sets the tag? Default? | **Open** | Ingest + RAG filters (R3); also R0 if tagging at upload | — | | | |
| 7 | Retrieval scope: always search full lab catalog, or constrain by client context / project? | **Open** | R2–R3 retrieval | — Lab-owned methods usually global to lab; client SOPs constrained | | | |
| 8 | What enters the searchable memory index? (applied only vs drafts) | **Decided (provisional)** | R3 index | **Applied, human-accepted design docs only** by default. Drafts not searchable (or lowest rank). | 2026-07-11 | Eng/CSO | Avoid poisoning memory with abandoned/bad drafts |
| 9 | Prefer `link_existing` vs create when catalog match is fuzzy? | **Open** | Matching UX + Apply (R1–R2) | — Thresholds, rename vs update existing | | | |
| 10 | Minimum human review checklist before Apply enabled? | **Open** | R1 UX / compliance messaging | — e.g. required open Sources tab, confirm step kinds | | | |
| 11 | SOP retention / deletion: vectors + blobs when SOP withdrawn? | **Open** | R3 ops + security retention | — | | | |
| 12 | Multi-lab shared DB later: does design assume single-lab deploy only? | **Deferred** | Multi-lab SaaS | **Single-lab deploy** assumed. Multi-lab = DB-per-lab or future `organization_id` ([multi-tenancy idea](../ideas/multi-tenancy.md)). | 2026-07-11 | Product | Not required for RAG v1 |
| 13 | Fine-tune phase (R5): allowed training corpus (lab-general only vs per-client)? | **Deferred** | R5 | Defer until R5 scheduled; default lean lab-general or isolated adapters—never mix client-confidential into one shared model | 2026-07-11 | | |
| 14 | Extend `/v1/sop-parse` vs new job API for full_plan + RAG? | **Open** | R0 API shape | Tech review suggests extend sop-parse with `mode=`—confirm | | | |
| 15 | Embeddings: pgvector in Postgres vs external vector store? | **Open** | R3 infra | Tech lean **pgvector**—confirm ops | | | |
| 16 | Success metrics that gate GA? | **Open** | Release | — e.g. link_existing rate, edit rate, isolation tests green | | | |

---

## Phase gate summary

| Phase | Scope (from tech review) | Open blockers before coding |
|-------|--------------------------|----------------------------|
| **R0** | ConfigurationPlan + Apply + design doc on apply | **#3** (definitions-only), **#14** (API shape). #1, #4, #5 Decided. |
| **R1** | Review UI, partial accept, link_existing | **#9**, **#10** (can provisional) |
| **R2** | Lab catalog injection | **#7** (provisional OK: full lab catalog for lab users) |
| **R3** | Full vector RAG | **#6**, **#7**, **#11**, **#15** |
| **R4** | Local LLM provider | **#2** |
| **R5** | Optional fine-tune | **#13** (Deferred until scheduled) |

**Do not start R0** until **#3** and **#14** are Decided (or explicitly provisional with written defaults below).

---

## Suggested provisional defaults (not decided until product confirms)

Use only if product stamps **Decided (provisional)**:

| # | Provisional default |
|---|---------------------|
| 3 | Apply creates **definitions/templates/fields/configs only**—never process instances or live LimsRuns |
| 6 | Default ownership **lab** on upload; optional “Client-confidential” + client picker for lab staff |
| 7 | Lab users: lab-owned SOPs + full lab catalog; client-owned SOPs only when job has matching `client_id` |
| 9 | Exact/normalized name match → `link_existing`; else create + warn on similarity |
| 10 | Apply requires at least one object selected + name non-empty; Sources tab recommended not forced in v1 |
| 14 | Extend `/v1/sop-parse` with `mode=template_only\|full_plan` |
| 15 | `pgvector` on primary Postgres |

---

## Decision #1 — RAG-first (not fine-tune-first)

**Status:** Decided  
**Date:** 2026-07-11

Institutional memory for SOP→config is:

1. Vectorized SOP chunks (lab- and client-owned as tagged)  
2. Applied **design docs** (ConfigurationPlan + links to live objects)  
3. Live **catalog** (FieldDefinitions, templates, process definitions)

Generation = retrieve → prompt → LLM → draft.  
Fine-tune may later improve JSON/schema compliance for small/local models; it does **not** store lab configuration memory.

---

## Decision #4 — No auto-Apply

**Status:** Decided  
**Date:** 2026-07-11

All production config creation goes through **human review and explicit Apply**. Auto-Apply is out of policy for v1.

---

## Decision #5 — Lab personnel only

**Status:** Decided  
**Date:** 2026-07-11

SOP upload, job view (including retrieval Sources), and Apply are **lab personnel** only. Lab **client** users do not configure assays via AI (Decision #9). They may still see sample journey for their samples (#7) and later create orders.

---

## Decision #8 — Applied design docs only (provisional index policy)

**Status:** Decided (provisional)  
**Date:** 2026-07-11

Default searchable memory excludes abandoned drafts. Only **applied** design docs (and their SOP documents) rank for retrieval unless product later enables “include drafts.”

---

## Decision #12 — Single-lab deploy assumption

**Status:** Deferred (multi-lab SaaS)  
**Date:** 2026-07-11

RAG v1 assumes one lab per deployment (on-prem or dedicated host). Multi-lab shared-DB tenancy is a separate initiative ([multi-tenancy](../ideas/multi-tenancy.md)).

---

## Related

| Doc | Role |
|-----|------|
| [ideas/sop-rag-config.md](../ideas/sop-rag-config.md) | Product idea summary |
| [design/sop-rag-config.md](../design/sop-rag-config.md) | Tech / RAG architecture |
| [open-questions/experiments.md](experiments.md) | #7 journey, #9 lab-only edit |
| [ideas/multi-tenancy.md](../ideas/multi-tenancy.md) | Lab–client vs multi-lab |
