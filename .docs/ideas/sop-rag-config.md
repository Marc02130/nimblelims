# Idea: SOP → LIMS config via RAG

**Status:** Exploratory + reviewed (RAG-first design)  
**Branch:** `sop-rag`  
**Date:** 2026-07-11  
**Supersedes:** Early “fine-tune Docker model” framing in prior notes

## Product intent

Help **lab personnel** turn SOPs (and optional instrument examples) into NimbleLIMS configuration by:

1. **Ingesting & vectorizing SOPs** (lab-owned and client-owned)
2. **Storing design docs** — applied ConfigurationPlans + links to live objects
3. **Retrieving** similar SOPs, design docs, and the lab catalog on each new upload
4. **Generating a draft** ConfigurationPlan (LLM + retrieved context)
5. **Human review → Apply** into FieldDefinitions, Experiment Templates, Process Definitions, LimsRun configs

**Core design: RAG (retrieval-augmented generation).**  
The system’s “memory” is the database (vectors + design docs + live config), not model weights. Fine-tuning a local model is **optional later** for JSON/schema quality—not how we learn from past SOPs.

## What gets created (draft → Apply)

| Object | When |
|--------|------|
| FieldDefinitions / lists | Capture columns the SOP requires |
| Experiment Templates (+ entries) | Single-unit protocol work |
| Process Definitions (typed steps) | Multi-step SOPs (`eln_experiment` \| `lims_run`) |
| LimsRun configs | Instrument-shaped steps — **lazy** run create at step start, not on parse |

## Actors & isolation

| Actor | SOP → config |
|-------|----------------|
| Lab personnel | Yes (RBAC `experiment:manage` or successor) |
| Lab **client** users (sponsors / customers of the lab) | **No** — Decision #9; may order work / see own journey later |

**Client** = customer of the lab (env client, CRO sponsor), not SaaS tenant.  
RAG retrieval: **lab catalog** + **client-tagged** confidential SOPs only when allowed. Client A never retrieves Client B’s SOPs.

## Reviews

| Review | Doc |
|--------|-----|
| CEO | [../ceo-review/sop-rag-config.md](../ceo-review/sop-rag-config.md) |
| Design | [../design-review/sop-rag-config.md](../design-review/sop-rag-config.md) |
| Tech | [../design/sop-rag-config.md](../design/sop-rag-config.md) |
| Security | [../security-review/sop-rag-config.md](../security-review/sop-rag-config.md) |

## RAG loop (summary)

```
Upload SOP → chunk + embed → store
          → retrieve similar SOPs + design docs + catalog
          → LLM(ConfigurationPlan)
          → human review
          → Apply → live objects + design doc (+ re-embed)
```

## Inference (pluggable)

- **Default:** cloud LLM (extend current `/v1/sop-parse` / Anthropic path)
- **Optional:** Docker **Ollama** (or OpenAI-compatible) for air-gap / local
- **Deferred:** LoRA/QLoRA fine-tune for structure only; always keep RAG for lab memory

## Phases (high level)

| Phase | Focus |
|-------|--------|
| R0 | ConfigurationPlan schema + Apply; persist design doc on apply |
| R1 | Plan review UI; partial accept; link_existing |
| R2 | Lab catalog injection (names/ids, no vectors yet) |
| R3 | pgvector SOPs + design docs; full RAG in job pipeline |
| R4 | Provider abstraction + optional Ollama |
| R5 | Optional fine-tune playbook (complements RAG) |

## Open questions

**Canonical decision log:** [../open-questions/sop-rag-config.md](../open-questions/sop-rag-config.md)

Do not implement R0+ until phase blockers in that doc are Decided (or stamped provisional).

## Related

- Multi-tenancy (lab–client vs multi-lab): [multi-tenancy.md](multi-tenancy.md)
- Current template-only SOP parse: `/v1/sop-parse`
