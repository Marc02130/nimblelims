# Idea: Local / fine-tuned models for SOP-assisted configuration

**Status:** Exploratory + reviewed (not scheduled for implementation)  
**Branch:** `docker-model`  
**Date:** 2026-07-11

## Product intent

Fine-tune or run a small open-weight model (Docker-friendly) so labs can:

1. **Read SOPs** (and optional instrument example files)
2. **Propose FieldDefinitions / lists** needed to capture protocol data
3. **Create Experiment Templates** (+ entries) when appropriate
4. **Create Process Definitions** (typed steps: `eln_experiment` \| `lims_run`) when the SOP is multi-step
5. **Propose LimsRun config** (parser/worklist scaffolds) when instrument-shaped — **lazy run create**, not live runs on parse

All proposals are **drafts**. Humans **review and Apply** via existing domain services (RBAC/RLS). Clients do **not** use this path (lab-only config; Decision #9).

## Reviews (read these first)

| Review | Doc |
|--------|-----|
| CEO / product | [../ceo-review/docker-model-sop-pipeline.md](../ceo-review/docker-model-sop-pipeline.md) |
| Design / UX | [../design-review/docker-model-sop-pipeline.md](../design-review/docker-model-sop-pipeline.md) |
| Tech / architecture | [../design/docker-model-sop-pipeline.md](../design/docker-model-sop-pipeline.md) |
| Security (CSO) | [../security-review/docker-model-sop-pipeline.md](../security-review/docker-model-sop-pipeline.md) |

**Consensus:** Build **SOP → structured ConfigurationPlan → review → Apply** first (extend `/v1/sop-parse`). Treat Docker/Ollama + fine-tune as a **pluggable inference backend** (later), not the MVP.

## Baseline infrastructure notes (inference & fine-tune)

There are several open-source AIs available as Docker containers for small-scale deployment and fine-tuning.

The ecosystem is usually split into two phases: **Inference** (running the model) and **Fine-Tuning** (training on your data).

### 1. Small models (under ~10B)

For consumer hardware or a single container:

* **Llama 3.2 (1B or 3B):** Fast, small footprint; LoRA/QLoRA friendly.
* **Qwen3 (1.7B or 4B):** Strong structured/tool-style outputs; good candidate for JSON plans.
* **Gemma 2 (2B or 9B):** Strong general quality for size.

### 2. Docker inference — Ollama

**CPU:**

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

**NVIDIA GPU:**

```bash
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

Pull/run a model:

```bash
docker exec -it ollama ollama run llama3.2:3b
```

**NimbleLIMS note:** Prefer attaching Ollama on an **internal** compose network (not public `11434`) when integrated. See security review.

### 3. Fine-tune inside Docker

#### Unsloth + Ollama

**Unsloth** is a strong low-memory option for LoRA/QLoRA on Llama/Qwen-class models.

* Community stacks bundle Unsloth + Ollama + OpenWebUI.
* Or: PyTorch CUDA image + `unsloth`, train on JSONL `(sop_text → configuration_plan)`, export **GGUF**, load into Ollama.

#### Custom Hugging Face / Axolotl-style container

```dockerfile
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-devel
RUN pip install transformers datasets trl peft accelerate bitsandbytes
# Add training script and data here
```

**NimbleLIMS note:** Training must be **offline / separate** from the FastAPI app container. Dataset only from **opt-in approved Applies**, ideally **per tenant** — never a shared multi-tenant fine-tune without legal + isolation review.

## Configuration memory (RAG) — preferred “learning” path

Yes: new SOPs should be guided by **existing** tenant configuration.

1. **Vectorize SOPs** into the DB (chunks + embeddings, tenant-scoped).  
2. **Store design docs** — applied ConfigurationPlans + links to created FieldDefs / templates / process defs / lims configs.  
3. **On new upload** — retrieve similar SOPs + design docs + catalog candidates; prompt the model to prefer `link_existing` and consistent patterns.

RAG is the default memory mechanism; fine-tune is optional for JSON/schema skill. Details: [tech review §3.7](../design/docker-model-sop-pipeline.md).

## Suggested eng phases (from tech review)

| Phase | What | Fine-tune? |
|-------|------|------------|
| T0 | `ConfigurationPlan` + Apply; store applied design doc | No |
| T1 | Plan review UI + partial accept | No |
| T1.5 | Inject tenant catalog names/ids into prompt | No |
| T2 | `LLMProvider` + optional Ollama compose profile | No |
| T3 | Golden SOP tests + telemetry | No |
| T3.5 | Vector SOPs + design docs; RAG retrieval | No |
| T4–T5 | Opt-in export + offline fine-tune (**plus** RAG) | Yes |

## Open product questions

1. Default inference: cloud forever vs paid local-model SKU?
2. Auto-create process **definitions** only, or ever instances from AI?
3. Minimum human review checklist before Apply is enabled?

Add blockers to [open-questions](../open-questions/) before implementation.
