# Tech Review: Docker Models for SOP → LIMS Configuration

**Date:** 2026-07-11  
**Branch:** `docker-model`  
**Reviewer:** Engineering / Architecture  
**Status:** Design only — not approved for implementation until open questions gated  
**Inputs:** [ideas/model-fine-tune.md](../ideas/model-fine-tune.md), existing `/v1/sop-parse`, FieldDefinitions, ELN process definitions (0051), LimsRun/parser/worklist stack

## 1. Problem statement

Labs need to turn **unstructured SOPs** (and optional instrument files) into **correct NimbleLIMS configuration**:

| Target object | Purpose |
|---------------|---------|
| FieldDefinitions (+ lists) | Columns required to capture protocol data |
| Experiment Templates (+ entries) | Single-unit protocol structure |
| Process Definitions (typed steps) | Multi-step SOPs (`eln_experiment` \| `lims_run`) |
| LimsRun-related config | Parser/worklist/result fragments for instrument steps |

Today: Claude cloud extraction creates **experiment template-oriented** drafts via job + apply. Gap: no first-class plan for fields, process definitions, or typed lims_run steps in one pipeline; no pluggable local model.

## 2. Current architecture (baseline)

```
Client → POST /v1/sop-parse (multipart SOP + instrument file)
       → SopParseJob (pending)
       → background: Claude API (ANTHROPIC_API_KEY)
       → job.result JSON
       → POST /v1/sop-parse/{id}/apply → ExperimentTemplate (+ related)
```

Strengths: async job, connection pool release during LLM call, apply is explicit, permission `experiment:manage`.

Limits: single-vendor cloud; output schema not aligned to Process Definitions / FieldDefinitions create APIs; no draft review model beyond template form.

## 3. Target architecture

### 3.1 Separation of concerns

| Layer | Responsibility |
|-------|----------------|
| **Ingestion** | Extract text from PDF/DOCX/images; chunk + **vectorize** SOP text into DB |
| **Configuration memory** | Store approved **design docs** (ConfigurationPlans + links to live objects); embed for retrieval |
| **Retrieval (RAG)** | On new SOP: search similar SOPs + design docs + existing FieldDefs/templates/process defs (tenant-scoped) |
| **Inference provider** | Pluggable: `anthropic` \| `openai_compat` \| `ollama` (Docker) |
| **Extraction service** | Prompt = new SOP + retrieved context → schema-validated **ConfigurationPlan** |
| **Draft store** | Persist plan JSON + status (extend SopParseJob or new `config_from_sop_jobs`) |
| **Apply service** | Transactional creation via existing domain services only; on success, **index design doc** for future jobs |
| **Optional training** | Offline LoRA/QLoRA (Unsloth) → GGUF → Ollama — **not in request path**; RAG is the default “memory” |

**Hard rule:** Models never receive DB credentials or call SQL. Apply path uses repositories/services with RLS + RBAC.  
**Hard rule:** Retrieval is **tenant/client-scoped** (same isolation as samples/templates)—never cross-customer SOP memory.

### 3.2 ConfigurationPlan (proposed schema)

Logical JSON shape (versioned):

```json
{
  "schema_version": "1",
  "summary": "string",
  "confidence": 0.0,
  "field_definitions": [
    {
      "action": "create|link_existing",
      "existing_id": null,
      "name": "rna_integrity_number",
      "field_type": "number",
      "entity": "sample|entry|...",
      "source_list_name": null,
      "rationale": "..."
    }
  ],
  "experiment_templates": [ { "name", "template_definition", "lifecycle_type", "entries": [] } ],
  "process_definitions": [
    {
      "name": "NGS Prep",
      "steps": [
        {
          "name": "Extraction",
          "step_kind": "eln_experiment",
          "execution_mode": "eln_experiment",
          "template_ref": "by_name_or_index"
        },
        {
          "name": "Plate QC",
          "step_kind": "lims_run",
          "execution_mode": "lims_run",
          "template_ref": "..."
        }
      ]
    }
  ],
  "lims_run_configs": [
    {
      "name": "Optional standalone run scaffold",
      "parser_config": {},
      "worklist_config": {},
      "result_columns": []
    }
  ],
  "warnings": [],
  "source_spans": []
}
```

Validate with Pydantic before job marked `complete`. Reject/partial-fail on schema errors.

### 3.3 Provider abstraction

```text
LLMProvider.complete(system, user, files_meta) -> str
  AnthropicProvider  # current
  OpenAICompatibleProvider  # vLLM, etc.
  OllamaProvider  # http://ollama:11434
```

Docker Compose (optional profile):

```yaml
# profile: local-llm
ollama:
  image: ollama/ollama
  volumes: [ollama_data:/root/.ollama]
  ports: ["11434:11434"]
  # deploy.resources reservations devices nvidia.com/gpu (optional)
```

Backend env:

- `LLM_PROVIDER=anthropic|ollama|openai_compat`
- `OLLAMA_BASE_URL=http://ollama:11434`
- `OLLAMA_MODEL=llama3.2:3b` (or fine-tuned tag)
- Keep `ANTHROPIC_API_KEY` for default cloud path

### 3.4 Apply pipeline (transactional)

Order of apply (dependency-aware):

1. Lists (if new list names proposed)  
2. FieldDefinitions (link_existing first)  
3. Experiment Templates (entries referencing field defs)  
4. Process Definitions (steps reference templates by id after create)  
5. LimsRun-related rows (parser/worklist) **as config only** — do not create active LimsRun instances unless explicitly requested in a later product decision  

Use existing services: `FieldDefinitionService`, `ExperimentService`, `ELNProcessService.create_definition`, lims run template helpers. Single DB transaction where possible; record created IDs on job for UI.

### 3.5 Fine-tuning path (offline, deferred)

From ideas doc — engineering notes only:

| Component | Use |
|-----------|-----|
| Unsloth / TRL + PEFT | QLoRA on 1B–9B models |
| Dataset | JSONL: `{ sop_text, configuration_plan }` from **approved** Applies (opt-in per tenant) |
| Export | GGUF → `ollama create` |
| Runtime | Ollama container; no training in API workers |

**Do not** put GPU training in the FastAPI container. Separate job image / CI / offline notebook.

### 3.6 Model selection guidance

| Model class | Fit |
|-------------|-----|
| Llama 3.2 3B / Qwen small | Local latency, weak long-SOP fidelity — OK for drafts with heavy review |
| Cloud Sonnet/Opus-class | Better structure adherence for v1 |
| Fine-tuned domain adapter | After ≥ dozens labeled plans; improves schema compliance |

Structured output: prefer constrained decoding / JSON schema mode where provider supports it; else repair loop (parse → validate → one repair call).

### 3.7 Configuration memory & RAG (using existing config)

**Yes — the model should use existing configuration.** Prefer **retrieval-augmented generation (RAG)** over fine-tuning for “learn from our SOPs.” Fine-tune remains optional for style/schema compliance; **memory of past work is RAG + DB**.

This matches the product loop:

| # | Store in DB | Role |
|---|-------------|------|
| **1** | **SOPs vectorized** | Chunks of source protocol text + embeddings + metadata (filename, version, client, applied_job_id) |
| **2** | **Design docs** | The model’s (and human-edited) **ConfigurationPlan** after Apply — the “how we implemented this SOP in NimbleLIMS” artifact, with FKs to created FieldDefs / templates / process definitions / lims configs |
| **3** | **Live config** | Existing FieldDefinitions, lists, Experiment Templates, Process Definitions, LimsRun parser/worklist rows — either embedded summaries or structured lookup by name/type |

#### On new SOP upload

```
new SOP → extract + chunk + embed
       → retrieve top-k similar SOP chunks (same tenant)
       → retrieve linked design docs for those SOPs
       → retrieve / rank candidate existing objects
            (FieldDefinitions by name similarity, templates, process defs)
       → build prompt:
            system: schema + rules (link_existing preferred)
            user: new SOP text
            context: similar SOPs + design docs + candidate IDs/names
       → LLM → ConfigurationPlan
            (prefer action=link_existing over create)
       → validate → human review → Apply
       → write: SOP vectors (if not already), design doc, embeddings for design doc
```

#### Why this works better than “only fine-tune”

| Approach | Learns | Risks |
|----------|--------|-------|
| **RAG over SOPs + design docs** | This tenant’s protocols and *how they mapped to NimbleLIMS* | Must enforce tenant scope; bad past Applies can reinforce mistakes (prefer **applied + human-edited** design docs only) |
| **Fine-tune** | Generic extraction style / JSON shape | Expensive; stale; cross-tenant leakage if shared; doesn’t auto-see new FieldDefs |
| **Both** | Fine-tune for structure; RAG for tenant memory | Best long-term; more ops |

#### Suggested tables (illustrative)

```
sop_documents          id, client_id, filename, raw_uri, text_hash, created_by, ...
sop_chunks             id, document_id, chunk_index, text, embedding vector, ...
sop_design_docs        id, document_id, job_id, plan_json, applied_at, applied_by, ...
sop_design_links       design_doc_id, object_type, object_id
                       -- experiment_template | process_definition | field_definition | ...
```

Embeddings: `pgvector` on Postgres (fits existing stack) or external vector store with **mandatory client_id filter** on every query.

#### Design-doc content

A **design doc** is not free-form narrative only. It is:

1. Final **ConfigurationPlan** JSON (post human edit, as applied)  
2. Optional short **rationale** (model + human notes)  
3. **Links** to live object UUIDs after Apply  
4. Optional “diff from nearest prior design doc” for versioned SOP revisions  

When a **new version of the same SOP** is uploaded, retrieve prior design doc for that lineage and prompt: “update configuration; prefer patching existing templates/process over duplicates.”

#### Retrieval policy (product + eng)

| Include in context | Exclude |
|--------------------|---------|
| Same client (RLS) SOPs and design docs | Other clients’ SOPs |
| Applied, human-accepted design docs | Failed / abandoned drafts (or mark low weight) |
| Active FieldDefinitions / templates / process defs | Soft-deleted / inactive unless user opts in |
| Top-k by embedding similarity + optional keyword (assay name) | Dump of entire catalog (token bloat, noise) |

#### Prompt contract (guidance to the model)

- Prefer **`link_existing`** when a retrieved FieldDefinition or template matches.  
- Prefer **extending** a retrieved process definition pattern over inventing new step kinds.  
- Cite which prior design doc influenced each major choice (for UI “inspired by …”).  
- Never invent UUIDs; only use IDs present in the retrieval payload.

#### Phasing relative to T0–T5

| Phase | Memory capability |
|-------|-------------------|
| **T0–T1** | No vectors required; Apply stores design doc JSON on job for audit |
| **T1.5** | Structured catalog injection: list existing FieldDef/template/process **names** for the client into the prompt (no vectors yet) |
| **T3.5** | `pgvector` SOP chunks + design-doc embeddings; retrieval in job pipeline |
| **T4–T5** | Optional fine-tune **plus** RAG (RAG remains source of tenant-specific truth) |

**Recommendation:** Implement **T1.5 catalog injection early** (cheap, high value). Full vector RAG when SOP volume justifies it.

## 4. Data flow diagram

```
SOP file ──► text extract ──► chunk + embed ──► store sop_documents / sop_chunks
                     │
                     ▼
              retrieve (tenant-scoped)
              • similar SOP chunks
              • linked design docs
              • candidate FieldDefs / templates / process defs
                     │
                     ▼
         prompt(schema_v1 + retrieved context) ──► LLM provider
                     │
                     ▼
             ConfigurationPlan JSON
                     │
             Pydantic validate
                     │
             job.status = complete
                     │
            human review (frontend)
                     │
             Apply (RBAC + RLS)
                     │
     ┌───────────────┼───────────────┬────────────────┐
     ▼               ▼               ▼                ▼
FieldDefinitions  Templates   ProcessDefinitions  Lims configs
     │               │               │                │
     └───────────────┴───────────────┴────────────────┘
                     │
                     ▼
         sop_design_docs + links + embed design doc
         (memory for next SOP)
```

## 5. API sketch (evolutionary)

Prefer extending sop-parse rather than greenfield:

| Endpoint | Change |
|----------|--------|
| `POST /v1/sop-parse` | Accept optional `mode=template_only\|full_plan` (default template_only for back-compat) |
| `GET /v1/sop-parse/{id}` | `result` may be ConfigurationPlan v1 |
| `POST /v1/sop-parse/{id}/apply` | Body: `{ accept: { fields: [], templates: [], processes: [], lims: [] } }` partial apply |
| `GET /v1/llm/health` | Provider reachability (admin) |

## 6. Performance & ops

- Continue **two-session background pattern** (no long-held DB connections during LLM).
- Timeouts: 2–10 min for large SOPs; chunk long documents by section headings.
- Token cost controls: max pages, truncate appendix tables.
- Observability: job duration, token usage, validation failure rate, apply success rate.
- GPU: optional; CPU Ollama acceptable for demo, not for 100-page SOPs.

## 7. Testing strategy

| Layer | Tests |
|-------|-------|
| Unit | Pydantic plan validation; apply service with mocked plan |
| Integration | Apply creates definition + templates with FK integrity |
| Golden files | 5–10 redacted SOPs → expected plan snapshots (diff intentionally) |
| Provider contract | Mock HTTP for Ollama/Anthropic |
| Regression | Existing template-only sop-parse tests stay green |

## 8. Migration / compatibility

- `schema_version` on plan; old jobs remain template-shaped.
- Feature flag: `SOP_FULL_PLAN_ENABLED`.
- No change to production templates until Apply.

## 9. Implementation phases (eng)

| Phase | Deliverable | Depends on fine-tune? |
|-------|-------------|----------------------|
| **T0** | ConfigurationPlan schema + validator + extended apply (cloud model); store applied plan as design doc on job | No |
| **T1** | UI plan review + partial accept; show “link existing” matches | No |
| **T1.5** | Inject tenant catalog (FieldDef/template/process names+ids) into prompt | No |
| **T2** | `LLMProvider` + Ollama compose profile | No |
| **T3** | Telemetry + golden SOP suite | No |
| **T3.5** | Vectorize SOPs + design docs (`pgvector`); RAG retrieval in job pipeline | No |
| **T4** | Opt-in dataset export from approved design docs | No |
| **T5** | Offline fine-tune playbook + private model tag (**complements** RAG, does not replace it) | Yes |

## 10. Tech risks

| Risk | Mitigation |
|------|------------|
| Unstable JSON from small models | Schema repair; prefer cloud for T0–T1 |
| Duplicate FieldDefinitions | link_existing + name similarity match |
| Process step template_ref orphans | Apply creates templates first; resolve refs in-memory |
| Prompt injection via SOP content | See security review; treat SOP as untrusted |
| Compose complexity | Optional profile; default cloud |
| Fine-tune data leakage across tenants | Per-tenant training only; never mix |

## 11. Recommendation

**Proceed with T0–T3 as engineering plan.**  
**Park T4–T5** until product commits to local-model SKU and labeled data volume exists.

Fine-tuning is an **optimization of the inference provider**, not a prerequisite for the SOP configuration product.

---

Related: [ceo-review](../ceo-review/docker-model-sop-pipeline.md), [design-review](../design-review/docker-model-sop-pipeline.md), [security-review](../security-review/docker-model-sop-pipeline.md), [ideas/model-fine-tune.md](../ideas/model-fine-tune.md)
