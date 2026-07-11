# CEO Review: Docker Models for SOP → LIMS Configuration

**Date:** 2026-07-11  
**Branch:** `docker-model`  
**Reviewer:** CEO / Product Strategy  
**Context:** Idea to fine-tune a small open-weight model (Docker/Ollama stack) so labs can upload SOPs and have NimbleLIMS propose FieldDefinitions, Experiment Templates, Process Definitions, and LimsRuns as needed. Seed idea: [`.docs/ideas/model-fine-tune.md`](../ideas/model-fine-tune.md). Current product path uses cloud Claude via `/v1/sop-parse` for template extraction only.

## Executive Summary

**Verdict: Strategically right product direction; wrong first bet if “fine-tune a private model in Docker” is the launch strategy.**

Early-stage biotechs will pay for **time-to-structured-work**: “I drop in an SOP, review a proposed configuration, click Apply, and my Process/Template/Run scaffolding exists.” That is a 10-star wedge. It attacks configuration drag (the same pain FieldDefinitions and Process Definitions were built to solve) and differentiates NimbleLIMS from dumb form-builders and generic LIMS.

However, **fine-tuning and self-hosting a model is not the product**. The product is:

1. Reliable extraction of lab structure from SOPs (and optional instrument examples).
2. **Human-in-the-loop** apply into our first-class objects (FieldDefs, Experiment Templates, Process Definitions, LimsRun configs).
3. Trust, audit, and multi-tenant safety.

Cloud SOP parse already proves demand for (1)–(2) at template scope. Expanding that pipeline to Processes + Fields + Runs is the high-ROI path. Docker/Ollama fine-tunes are a **later** option for cost, air-gapped labs, and IP-sensitive customers—not the MVP.

**Bottom line:** Invest in **SOP → structured draft → review → apply** as a product capability. Treat fine-tuned Docker models as an **inference backend strategy**, not as the headline initiative.

## Market Fit (Early-Stage Biotech)

| Buyer pain | Why this idea helps | Risk if we overbuild |
|------------|---------------------|----------------------|
| Days/weeks configuring templates for a new assay | Minutes from SOP PDF/DOCX to draft config | Model invents wrong fields; scientists lose trust |
| Scientist = “LIMS admin” | Low-code path without DB literacy | Opaque AI that can’t be corrected |
| CRO / NGS / multi-step prep | Auto-propose **process definitions** with typed steps | Forces process when a single experiment would do |
| Instrument / plate work | Propose LimsRun + parser/worklist fragments | Dual SoT if we auto-create runs without intent |
| IP / data residency (some Series A+) | Local Docker model later | Premature GPU ops tax for majority of customers |

**What wins:** Reviewable drafts, strong defaults, one Apply that creates the right NimbleLIMS objects.  
**What loses:** “We fine-tuned Llama and it runs in Docker” as a sales story without accuracy and apply UX.

## Alignment with What We Just Built

This idea is **timed well** only because Phases 1–3 of experiments + FieldDefinitions exist:

| Capability | Role in AI pipeline |
|------------|---------------------|
| FieldDefinitions + lists | Propose columns / list-backed options for capture |
| Experiment Templates + Entries | Propose `template_definition` + entry blocks |
| Process Definitions (typed steps) | Multi-step SOPs → definition snapshot with `eln_experiment` / `lims_run` steps |
| LimsRun / parsers / worklists | Instrument SOPs → run config, not notebook experiments |
| Existing `/v1/sop-parse` | Proven job + poll + apply pattern to extend |

Without those entities, fine-tuning would dump JSON into a swamp. With them, the model’s job is **structured emission into a known schema**, which is the right AI problem.

## Product Opportunities (10-Star)

1. **“Configure from SOP” wizard** — single entry under Experiments/Admin: upload SOP (+ optional instrument file) → AI draft → side-by-side review → Apply creates objects with clear IDs and links.
2. **Intent classification** — Model decides *what is needed*: FieldDefs only / one Template / Process Definition / LimsRun scaffold / combination. Progressive: never create a Process when a single experiment template suffices.
3. **Diffable drafts** — Treat AI output as versioned draft jobs (like sop-parse jobs), not live mutations. Scientist owns Apply.
4. **Customer SOP memory (later)** — Fine-tune or RAG on *their* approved templates so the 5th assay is better than the 1st. That’s where private Docker models earn their keep.
5. **Air-gapped / no-cloud tier (later)** — Ollama in compose for customers who refuse Anthropic. Sell as enterprise option, not default.

## Scope Recommendations

### Do first (product MVP — provider-agnostic)

- Expand SOP job contract: emit a **structured plan**  
  `{ field_definitions?, experiment_templates?, process_definition?, lims_run_configs?, rationale[] }`
- UI: review each proposed object; accept/reject/edit before Apply.
- Apply uses existing services (no AI writes DB directly).
- Keep cloud model (or best available) as default inference; **no fine-tune required for v1**.
- Measure: time-to-first-template, edit rate on draft, Apply success rate, support tickets.

### Defer

- Fine-tuning Unsloth/QLoRA, custom GGUF, multi-GPU training ops.
- Fully automatic Apply without review.
- Auto-creating live LimsRuns or process **instances** (definitions/templates only until user starts work).
- Training on customer SOPs in a shared multi-tenant model (legal/privacy landmine).

### Explicit non-goals for v1

- Replacing Field Management UI or Process builder.
- General chat bot for LIMS.
- Guaranteeing 100% SOP fidelity without human review.

## Strategic Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Hallucinated fields / wrong step kinds** | High | Human review; schema validation; unit tests on sample SOPs |
| **Scope explosion** (AI product + GPU platform + training pipeline) | High | Ship apply pipeline first; Docker model as pluggable backend |
| **Trust / liability** for protocol errors | High | Copy: “draft for review”; never auto-start production runs |
| **Cost** of cloud tokens on large SOPs | Medium | Caching, chunking, later local model for heavy users |
| **Cannibalize existing builder UX** | Medium | AI is accelerator into same objects, not a second configuration system |
| **IP leakage** of SOP text to third-party LLM | Medium–High | Enterprise: local inference path; clear DPA; optional redact |

## Open Strategic Questions

1. Is the primary buyer motion “faster onboarding of a new assay” or “ongoing SOP change control”? (Affects whether we optimize first-upload or versioned re-parse.)
2. Do we ever auto-create process **instances** from a client order, or only definitions/templates for lab staff? (See open question #9: clients create orders; lab configures data.)
3. When is local Docker model a paid SKU vs default for all?
4. Who owns accuracy SLA—product, or “best effort draft”?

## Recommendations

1. **Rename the initiative in product language:** “SOP-assisted configuration” — not “Docker model fine-tune.”
2. **Build on `/v1/sop-parse` job lifecycle** rather than a parallel AI stack.
3. **Target objects in priority order:**  
   Experiment Template (+ entries) → FieldDefinitions/lists → Process Definition (typed steps) → LimsRun parser/worklist scaffold.  
   Only create process/run objects when the SOP clearly multi-steps or is instrument-shaped.
4. **Human Apply is non-negotiable** for v1.
5. **Revisit fine-tune + Ollama** after 20–50 real SOPs show systematic failure modes that prompt engineering can’t fix—or when a paying customer requires air-gap.

**CEO score:** Idea **8/10** for product impact if scoped as SOP→draft→apply. Idea **4/10** if scoped as “fine-tune and ship Docker model platform” first.

---

Related: [ideas/model-fine-tune.md](../ideas/model-fine-tune.md), [design/docker-model-sop-pipeline.md](../design/docker-model-sop-pipeline.md), [design-review/docker-model-sop-pipeline.md](../design-review/docker-model-sop-pipeline.md), [security-review/docker-model-sop-pipeline.md](../security-review/docker-model-sop-pipeline.md)
