# CEO Review: SOP → Config via RAG

**Date:** 2026-07-11 (revised: RAG-first)  
**Branch:** `docker-model`  
**Reviewer:** CEO / Product Strategy  
**Idea:** [`.docs/ideas/sop-rag-config.md`](../ideas/sop-rag-config.md)

## Executive Summary

**Verdict: Pursue as “SOP-assisted configuration with institutional memory.” RAG is the product strategy; fine-tuning is not.**

Early-stage biotechs, environmental labs, and CROs will pay for **time-to-correct structure**: drop in an SOP, get a reviewable draft that reuses how *this lab* already configures similar work, Apply, start real work. That compounds every time a lab configures another assay—the 5th NGS-like SOP should be faster than the 1st because **design docs and SOPs live in the DB**.

**RAG** (vectorized SOPs + applied design docs + live FieldDefs/templates/process defs) is how we deliver that compounding. **Fine-tuning** does not replace it; at best it makes small/local models emit cleaner JSON.

**Bottom line:** Invest in **ingest → retrieve → draft → review → Apply → store design doc**. Treat cloud or Docker LLMs as interchangeable engines. Do **not** center the roadmap on Unsloth/fine-tune platforms.

## Market fit

| Buyer | Why RAG-shaped SOP config wins |
|-------|--------------------------------|
| Scientist-led biotech | Less config thrash; reuse fields/templates they already trust |
| Env lab (many clients) | Lab-owned methods shared; client-confidential methods isolated |
| CRO (sponsors) | Lab staff configure once; sponsors never touch config (Decision #9); data still client-separated |

**What wins:** Reviewable drafts, “inspired by prior design doc X,” prefer link existing objects, clear Apply.  
**What loses:** Opaque auto-config; AI that invents duplicate fields every time; fine-tune story without accuracy.

## Alignment with shipped product

| Asset | Role in RAG design |
|-------|---------------------|
| FieldDefinitions + lists | Catalog retrieval + link_existing |
| Experiment Templates + entries | Primary draft object |
| Process Definitions (typed steps) | Multi-step SOP → definition, not ad hoc links |
| LimsRun configs | Instrument steps; lazy instance create |
| `/v1/sop-parse` job + Apply | Lifecycle to extend (template-only → full plan + RAG) |
| client_id / RLS | Client-owned SOP vectors never cross sponsors |

Without FieldDefs + process definitions, RAG would dump unstructured JSON. With them, retrieval has real targets.

## Product principles (locked for this initiative)

1. **Memory in the database** — SOPs, design docs, live config—not only in model weights.  
2. **Human Apply** — drafts never mutate production without lab review.  
3. **Lab configures; clients don’t** — Decision #9. Clients may order / view their samples (#7).  
4. **Prefer reuse** — link existing FieldDefs/templates/process defs over create.  
5. **Lab-owned vs client-owned SOPs** — shared methods vs sponsor-confidential retrieval rules.  
6. **Definitions not instances** — AI proposes process **definitions** and run **configs**, not live cohorts/runs.

## Scope

### Do (RAG product)

- ConfigurationPlan schema (fields, templates, process defs, lims configs)
- On Apply: create objects **and** persist **design doc** + links
- Vectorize SOPs; embed design docs; retrieve on new upload
- Early win: inject **lab catalog** (names/ids) even before full vectors
- Plan-first UI: summary → tabs → partial Accept → Apply
- Extend sop-parse job pattern; feature-flag full plan

### Defer

- Fine-tune / LoRA pipelines
- Auto-Apply, auto process **instances**, auto LimsRun start
- Client-user SOP upload for configuration
- Multi-lab SaaS org layer (see [multi-tenancy idea](../ideas/multi-tenancy.md))

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Hallucinated / wrong step kinds | High | Review UI; schema validation; golden SOPs |
| Duplicated FieldDefs every time | High | RAG + catalog + link_existing |
| Bad past Applies poison retrieval | Medium | Index only **applied** human-accepted design docs |
| Client SOP leakage (CRO/env) | High | Ownership tags + RLS on vector search |
| Scope = “build AI platform” | High | RAG pipeline only; pluggable LLM |
| Trust / protocol liability | High | “Draft for review” copy; lab remains SoT |

## Open strategic questions

1. Is success measured as **time-to-first Apply** or **% reuse of existing templates**? (Both; weight reuse for CROs.)  
2. Cloud default forever, or paid local LLM for sensitive labs?  
3. When a client provides a confidential SOP, is design doc client-tagged always?

## Recommendations

1. **Rename the initiative in sales/docs language:** “Configure from SOP (learns from your lab)” — not “fine-tuned Docker model.”  
2. **Ship R0–R3** (plan + design docs + catalog + vectors) before any fine-tune.  
3. **Measure** edit-rate, link_existing rate, Apply success, cross-client retrieval tests.  
4. **Revisit fine-tune only** if local small models fail schema compliance after RAG is solid.

**CEO score (RAG-first): 9/10** strategic fit.  
**CEO score (fine-tune-first): 4/10** — wrong sequencing.

---

Related: [design](../design/docker-model-sop-pipeline.md), [design-review](../design-review/docker-model-sop-pipeline.md), [security](../security-review/docker-model-sop-pipeline.md)
