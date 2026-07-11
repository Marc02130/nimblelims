# Tech Review: SOP → Config via RAG

**Date:** 2026-07-11 (revised: RAG-first architecture)  
**Branch:** `docker-model`  
**Reviewer:** Engineering / Architecture  
**Status:** Design only — gate open questions before implementation  
**Idea:** [`.docs/ideas/sop-rag-config.md`](../ideas/sop-rag-config.md)

## 1. Problem statement

Labs need **SOP → structured NimbleLIMS configuration** that **improves with use**:

| Target | Purpose |
|--------|---------|
| FieldDefinitions (+ lists) | Capture columns |
| Experiment Templates (+ entries) | Single protocol units |
| Process Definitions (typed steps) | Multi-step (`eln_experiment` \| `lims_run`) |
| LimsRun configs | Parser/worklist scaffolds; **lazy** run instances |

**Architecture choice: RAG-first.**

1. Vectorize and store SOPs  
2. Store **design docs** (applied ConfigurationPlans + object links)  
3. On new SOP, retrieve SOPs + design docs + live catalog, then generate a draft  

Fine-tuning is **out of the critical path** (optional R5 for local model JSON quality).

Today: `/v1/sop-parse` → Claude → template-oriented JSON → Apply template. No retrieval memory, no process/field plan.

## 2. Terminology

| Term | Meaning |
|------|---------|
| **Lab** | Org running NimbleLIMS |
| **Lab personnel** | System-client / lab roles |
| **Client** | Customer of the lab (sponsor, env customer)—not vendor SaaS tenant |
| **Lab-owned SOP** | Shared methods; searchable for lab config jobs |
| **Client-owned SOP** | Confidential to one lab client; retrieval restricted |
| **Design doc** | Applied ConfigurationPlan + links to created/linked object IDs |
| **Catalog** | Live FieldDefs, lists, templates, process definitions |

## 3. Architecture (RAG-centered)

### 3.1 Layers

| Layer | Responsibility |
|-------|----------------|
| **Ingest** | Extract text; chunk; embed; persist `sop_documents` / `sop_chunks` |
| **Memory** | Design docs + embeddings; links to live objects |
| **Catalog index** | Queryable summaries/ids of FieldDefs, templates, process defs (structured + optional embed) |
| **Retrieve** | Top-k SOPs + design docs + catalog candidates (ownership filters) |
| **Generate** | LLM(provider) → ConfigurationPlan JSON |
| **Validate** | Pydantic / schema_version; reject bad enums, names, fake UUIDs |
| **Draft job** | Extend SopParseJob or `config_from_sop_jobs` |
| **Apply** | Domain services only; write design doc + re-embed; RBAC/RLS |
| **Provider** | `anthropic` \| `ollama` \| `openai_compat` — pluggable |

**Hard rules**

- Model never gets DB credentials or runs SQL.  
- Apply uses existing services (FieldDefinition, Experiment, ELNProcess definition, lims config helpers).  
- Retrieval never returns Client B’s client-owned SOP chunks to a Client A–scoped job.  
- Prefer `link_existing` when retrieved IDs/names match.

### 3.2 End-to-end data flow

```
SOP upload
    │
    ├─► extract text
    ├─► chunk + embed ──► sop_documents / sop_chunks
    │
    ▼
retrieve (lab personnel job)
    • similar SOP chunks (lab-owned + allowed client-owned)
    • design docs for those SOPs
    • catalog candidates (FieldDefs, templates, process defs)
    │
    ▼
prompt = system(schema + rules) + user(new SOP) + context(retrieval)
    │
    ▼
LLM ──► ConfigurationPlan ──► validate ──► job complete
    │
    ▼
human review (partial accept)
    │
    ▼
Apply (transaction)
    │
    ├─► lists / FieldDefinitions (link or create)
    ├─► Experiment Templates
    ├─► Process Definitions
    ├─► LimsRun configs (not live runs)
    │
    └─► sop_design_docs + sop_design_links + embed design doc
```

### 3.3 ConfigurationPlan (v1 sketch)

```json
{
  "schema_version": "1",
  "summary": "string",
  "confidence": 0.0,
  "retrieval": {
    "sop_chunk_ids": [],
    "design_doc_ids": [],
    "catalog_refs": []
  },
  "field_definitions": [
    {
      "action": "create|link_existing",
      "existing_id": null,
      "name": "string",
      "field_type": "string",
      "entity": "string",
      "source_list_name": null,
      "rationale": "string"
    }
  ],
  "experiment_templates": [],
  "process_definitions": [
    {
      "name": "string",
      "steps": [
        {
          "name": "string",
          "step_kind": "eln_experiment|lims_run",
          "execution_mode": "eln_experiment|lims_run",
          "template_ref": "name_or_index"
        }
      ]
    }
  ],
  "lims_run_configs": [],
  "warnings": []
}
```

Model may only put UUIDs in `existing_id` / catalog refs that appeared in the retrieval payload.

### 3.4 Persistence (illustrative)

```
sop_documents
  id, ownership ('lab'|'client'), client_id NULL,
  filename, storage_uri, text_hash, created_by, created_at, ...

sop_chunks
  id, document_id, chunk_index, text, embedding vector(n), ...

sop_design_docs
  id, document_id, job_id, plan_json, applied_at, applied_by, ...

sop_design_links
  design_doc_id, object_type, object_id
  -- field_definition | experiment_template | process_definition | ...
```

**Embeddings:** `pgvector` on Postgres preferred (one stack, RLS-friendly).  
**Alternative:** external vector DB with mandatory ownership filters on every query.

### 3.5 Retrieval policy

| Include | Exclude |
|---------|---------|
| Lab-owned SOPs + design docs | Other clients’ client-owned SOPs |
| Client-owned SOPs if job `client_id` matches (lab staff working that client) | Abandoned drafts as high-rank memory |
| Active catalog objects | Soft-deleted unless opted in |
| Top-k by similarity (+ optional keyword) | Entire catalog dump (token noise) |

**First SOP / empty memory:** generation still works; `retrieval` empty; UI warns.

### 3.6 Apply order

1. Lists (if needed)  
2. FieldDefinitions (`link_existing` first)  
3. Experiment Templates (+ entries)  
4. Process Definitions (resolve template refs to ids)  
5. LimsRun config rows  
6. Design doc + links + embed  

Single transaction where practical; record created/linked IDs on job.

### 3.7 LLM providers

| Provider | Role |
|----------|------|
| Anthropic (current) | Default quality for R0–R3 |
| Ollama (Docker) | Optional local; internal network only |
| OpenAI-compatible | vLLM / other |

Env: `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `ANTHROPIC_API_KEY`, embed model settings.

Background jobs: keep **two-session** pattern (no DB hold during LLM/embed HTTP).

### 3.8 Fine-tuning (explicitly secondary)

| | RAG | Fine-tune |
|---|-----|-----------|
| Lab memory | **Yes** | No |
| Schema/JSON habit | Partial (prompt) | Optional improve |
| Ops cost | Embed + retrieve | GPU train/deploy |
| Client isolation | Query filters | Risk if mixed corpora |

**R5 only:** offline LoRA on approved plans for **structure**; never replace design-doc retrieval. Prefer lab-general methods; avoid mixing client-confidential SOPs into one broadly served model.

## 4. API evolution

| Endpoint | Behavior |
|----------|----------|
| `POST /v1/sop-parse` | `mode=template_only\|full_plan` (default template_only) |
| Job pipeline | ingest → retrieve → generate → validate |
| `GET /v1/sop-parse/{id}` | plan + retrieval metadata for Sources UI |
| `POST .../apply` | `{ accept: { fields, templates, processes, lims } }` partial |
| `GET /v1/llm/health` | provider + embed reachability (admin) |

## 5. Implementation phases

| Phase | Deliverable | RAG depth |
|-------|-------------|-----------|
| **R0** | ConfigurationPlan + validate + Apply; save design doc JSON on job | Write path only |
| **R1** | Review UI + partial accept + link_existing | — |
| **R2** | Inject lab catalog names/ids into prompt | Structured RAG-lite |
| **R3** | pgvector chunks + design docs; retrieval in pipeline; Sources API | Full RAG |
| **R4** | Provider abstraction + optional Ollama | — |
| **R5** | Optional fine-tune playbook | Complements RAG |

## 6. Testing

| Layer | Coverage |
|-------|----------|
| Unit | Plan schema; retrieval filter (client isolation); apply link vs create |
| Integration | Apply creates FKs; design doc links; second SOP job returns prior design doc in retrieval |
| Security | Client A job cannot retrieve Client B SOP chunks |
| Golden | Fixed SOPs → plan snapshots (allow intentional diffs) |
| Regression | `template_only` sop-parse remains green |

## 7. Performance & ops

- Chunk size / overlap policy; max pages; top-k cap (e.g. 5–15 chunks)  
- Embed batching on ingest  
- Job timeouts; queue concurrency per user  
- Metrics: retrieval hit rate, link_existing rate, token usage, apply success  

## 8. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Bad Applies poison memory | Index applied+accepted only; admin unindex |
| Duplicate objects | Catalog + link_existing + name collision UI |
| Small model bad JSON | Schema repair loop; prefer cloud until R4 |
| Vector/RLS mistakes | Integration tests; FORCE filters in repository layer |
| Prompt injection via SOP | Treat output untrusted; allowlist types; no code exec |

## 9. Recommendation

**Implement R0→R3 as the core product.**  
R4 for local inference SKUs.  
R5 only if metrics demand it.

RAG is the architecture; Docker/Ollama is an optional runtime; fine-tune is optional polish.

---

Related: [ceo](../ceo-review/docker-model-sop-pipeline.md), [design-review](../design-review/docker-model-sop-pipeline.md), [security](../security-review/docker-model-sop-pipeline.md), [ideas](../ideas/sop-rag-config.md)
