# Security Review (CSO): SOP → Config via RAG

**Date:** 2026-07-11 (revised: RAG-first)  
**Branch:** `sop-rag`  
**Reviewer:** CSO / Security  
**Idea:** [`.docs/ideas/sop-rag-config.md`](../ideas/sop-rag-config.md)  
**Tech:** [`.docs/design/sop-rag-config.md`](../design/sop-rag-config.md)

## Executive Summary

RAG increases **value** (lab memory) and **surface area** (stored SOP text, vectors, design docs, retrieval into prompts). Acceptable if:

1. LLM output is **untrusted**; only Apply mutates config.  
2. **Lab personnel** only for SOP→config (Decision #9)—not lab client users.  
3. **Lab-client isolation** on vectors and design docs (Client A ≠ Client B).  
4. No auto-Apply; no model DB access.  
5. Fine-tune (if ever) does not launder confidential SOPs across clients.

**P1 before production full RAG Apply**

| ID | Control |
|----|---------|
| S1 | Prompt injection → malicious field/step payloads sanitized/validated |
| S2 | Vector/search IDOR across lab clients |
| S3 | Job GET/Apply authorization (lab RBAC) |
| S4 | Index only applied design docs by default |
| S5 | Secrets never in prompts; Ollama not public |

## Trust boundaries

```
[Untrusted] SOP file/text (may include injection)
      │
      ▼
[Backend] extract, embed, store  ── ownership tags
      │
      ▼
[Retrieve] filtered by lab / client ownership
      │
      ▼
[Untrusted LLM] cloud or internal Ollama
      │
      ▼
[Backend] validate ConfigurationPlan (untrusted payload)
      │
      ▼
[Lab user] review/edit
      │
      ▼
[Apply] RBAC + RLS + domain services → DB + design doc
```

## STRIDE (RAG-focused)

### Spoofing
Stolen lab token runs jobs / Apply.  
**Mitigation:** Existing JWT + `experiment:manage` (or tighter); jobs bound to creator.

### Tampering
- Injection in SOP text influencing plan or future retrieval.  
- Poisoning lab-wide memory with a bad Apply.  
**Mitigation:** Output schema allowlists; human Apply; admin unindex; prefer applied docs only in index.

### Repudiation
Who applied which plan from which SOP/retrieval?  
**Mitigation:** Audit `job_id`, model id, retrieval ids, `applied_by`, SOP hash.

### Information disclosure
| Vector | Mitigation |
|--------|------------|
| Client-owned SOP in another client’s retrieval | Mandatory `ownership` + `client_id` filters; tests |
| Job UUID enumeration | 404; lab-only access |
| Logs | Hash/size only, not full SOP |
| Cloud LLM | DPA; local provider option for sensitive clients |
| Design doc links | Same visibility as underlying objects |

### Denial of service
Huge SOP / embed storms.  
**Mitigation:** Size/page limits, rate limits, top-k caps, timeouts.

### Elevation of privilege
Plan creates FieldDefs/entities beyond caller rights.  
**Mitigation:** Apply through same services as manual create; entity allowlist.

## Authorization

| Action | Lab admin | Lab manager/tech | Lab client user |
|--------|-----------|------------------|-----------------|
| Upload SOP / start job | Yes | Yes | **No** |
| View job + retrieval sources | Yes | Yes | **No** |
| Apply plan | Yes | Yes | **No** |
| Sample journey (own client) | Yes | Yes | **Yes** (#7) |
| Provider/embed admin | Yes | No | No |

**Client** = customer of the lab (CRO sponsor, env customer).

## RAG-specific requirements

1. **Ownership model** on `sop_documents`: `lab` | `client` + optional `client_id`.  
2. **Every** vector query applies the same filters in one repository function (no raw SQL in call sites).  
3. **Default index:** applied design docs only; drafts not searchable.  
4. **UUID hygiene:** reject `existing_id` not present in retrieval/catalog payload for that job.  
5. **Retention:** policy for SOP blobs/vectors; delete cascades.  
6. **Embed API:** same trust as LLM if external; prefer in-process/local for air-gap.

## Fine-tune (deferred) risks

- Mixing client-confidential SOPs into one model used lab-wide → treat as disclosure.  
- Prefer structure-only fine-tune on lab-general methods, or isolated adapters.  
- Training offline; opt-in; no production DB credentials on train boxes.

## Secure SDLC checklist

- [ ] Client isolation tests for retrieval  
- [ ] IDOR tests on jobs  
- [ ] Plan validator property tests  
- [ ] Upload limits  
- [ ] No secrets in prompt unit test  
- [ ] Apply audit event  
- [ ] Feature flag default off until golden + security suite  
- [ ] Ollama internal-only in compose  

## Residual risk

RAG/LLM may propose **scientifically wrong** protocol structure. Security cannot validate assay correctness. Product labels drafts as non-authoritative; lab remains responsible. **Accepted** with human Apply.

## Recommendations

1. Ship RAG pipeline (R0–R3) with isolation tests as release gates.  
2. Never client-user config Apply.  
3. Visible retrieval in UI aids security review culture (users spot wrong SOP context).  
4. Defer fine-tune; if added, data-classification review first.  
5. Auto-Apply remains **out of policy**.

**CSO verdict:** RAG-first design is **acceptable** with controls above. Fine-tune-first or auto-Apply is **not**.

---

Related: [ceo](../ceo-review/sop-rag-config.md), [design-review](../design-review/sop-rag-config.md), [tech](../design/sop-rag-config.md)
