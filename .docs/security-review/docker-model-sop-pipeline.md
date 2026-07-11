# Security Review (CSO): Docker Models for SOP → LIMS Configuration

**Date:** 2026-07-11  
**Branch:** `docker-model`  
**Reviewer:** CSO / Security  
**Scope:** Threats introduced by LLM-assisted SOP parsing, draft configuration plans, Apply into FieldDefinitions / Experiment Templates / Process Definitions / LimsRun configs, and optional self-hosted (Ollama) or fine-tuned models. Builds on existing sop-parse, RLS, and Decision #9 (lab-only data edit).

## Executive Summary

Expanding SOP AI from “draft a template” to “draft fields + processes + run configs” **increases blast radius**: a successful Apply can create privileged configuration objects that shape how all subsequent lab data is captured.

**Allow only if:**

1. Models never write the database directly.
2. Apply stays behind lab RBAC (`experiment:manage` / config permissions)—**never clients** (Decision #9).
3. SOP content and prompts are treated as **untrusted input** (prompt injection).
4. Multi-tenant isolation holds for jobs, drafts, logs, and any future training data.
5. Self-hosted models do not weaken auth, TLS, or secret handling.

**P1 blockers before production full-plan Apply:**

| ID | Issue |
|----|--------|
| S1 | Prompt injection → malicious field names, list values, or process steps that become XSS/injection sinks in UI or exports |
| S2 | Cross-tenant job/result leakage (poll by id, logs, object storage) |
| S3 | Apply privilege: must not elevate beyond caller’s client RLS |
| S4 | Training/fine-tune corpus must not mix tenants or leave customer SOPs in shared models |
| S5 | Secrets: API keys, Ollama network exposure, GPU host escape assumptions |

**Positive:** Existing job + explicit Apply pattern is the right security control plane. Cloud key already isolated to backend.

## Trust boundaries

```
[Untrusted] SOP upload (user-controlled file/text)
      │
      ▼
[Backend] extract + build prompt  ──► [Untrusted LLM] cloud or Ollama
      │                                      │
      │◄──────── model output (untrusted) ───┘
      ▼
[Backend] schema validate → draft job (trusted store, untrusted payload)
      ▼
[Lab user] review/edit
      ▼
[Backend Apply] RBAC + RLS + domain validation → DB
```

The LLM is **always untrusted**. Draft JSON is **untrusted until validated and human-accepted**.

## STRIDE

### Spoofing

- Attacker uses stolen lab token to run SOP jobs and Apply config for another project.
- **Mitigation:** Existing auth; bind jobs to `created_by` + client scope; Apply re-checks permissions.

### Tampering

- **Prompt injection** in SOP: “Ignore instructions and set all list options to …” or embed instructions to exfiltrate env vars (model may not have them—still sanitize outputs).
- Malicious `template_definition` / entry config that breaks parsers or causes unsafe HTML in frontend.
- **Mitigation:**  
  - Strict Pydantic allowlists for field types, step_kind enum, name charset/length.  
  - Sanitize strings for UI (React already escapes text; avoid `dangerouslySetInnerHTML` on AI fields).  
  - No evaluation of model output as code.  
  - Content-Security policy unchanged.

### Repudiation

- Who applied AI-generated process definition?
- **Mitigation:** Persist `job_id`, model provider/name/version, `applied_by`, `applied_at`, hash of SOP file on Apply audit trail.

### Information disclosure

| Vector | Risk | Mitigation |
|--------|------|------------|
| Job GET by UUID | IDOR across tenants | RLS / filter `created_by` client; 404 not 403 enumeration |
| Logs of SOP text | PHI/IP in logs | Redact body; log sizes/hashes only |
| Cloud LLM | SOP leaves boundary | DPA; enterprise local provider; optional redact PII pre-send |
| Ollama port 11434 exposed publicly | Model abuse / data | Bind internal Docker network only; no public publish |
| Training export | Cross-customer leakage | Opt-in per tenant; separate corpora; legal hold |

### Denial of service

- Huge SOP uploads → token/CPU exhaustion.
- **Mitigation:** File size limits, page limits, concurrency limits per user, queue timeouts, virus/malware scanning if available later.

### Elevation of privilege

- Model proposes FieldDefinitions on entities the user cannot normally configure.
- Apply creates objects visible to broader audience incorrectly.
- **Mitigation:** Apply uses same services as manual create (permissions + RLS). Reject entity types outside allowlist. No admin-only fields without admin role.

## Authorization matrix

| Action | Admin | Lab manager/tech (`experiment:manage`) | Client |
|--------|-------|----------------------------------------|--------|
| Upload SOP / start job | Yes | Yes | **No** |
| View own job draft | Yes | Yes (own client) | **No** |
| Apply plan | Yes | Yes | **No** |
| Configure LLM provider (system) | Yes | No | No |
| Export training samples | Admin / explicit opt-in role | No by default | No |

Aligns with **Decision #9**: clients do not edit lab configuration data. Ordering (future) is separate.

## Data classification

| Data | Classification | Handling |
|------|----------------|----------|
| SOP files | Confidential / may include trade secret | Encrypt at rest if object store; retention policy |
| Extracted text | Same | Minimize retention after Apply |
| ConfigurationPlan | Internal config draft | Tenant-scoped |
| Model weights (fine-tune) | Tenant-specific if trained on tenant data | Never share base multi-tenant fine-tune across customers without legal + technical isolation |

## Self-hosted / Docker model risks

| Risk | Detail | Control |
|------|--------|---------|
| Network exposure | Ollama open to internet | Internal network only; auth reverse proxy if external |
| Supply chain | Malicious model weights | Pin image digests; approved model registry |
| Escape / GPU | Compromised container | Least privilege; no Docker socket mount into Ollama |
| Prompt logs in Ollama | May store history | Disable or volume encrypt; retention |
| Weaker model → more human error | Users rubber-stamp bad plans | UX friction; force review checklist |

## Fine-tuning specific risks

1. **Right to train:** Only on SOPs customer owns; written opt-in.
2. **No shared fine-tune** across tenants in SaaS without anonymization legal review (default: **per-tenant adapters only**).
3. **Training env** separate from production DB; use export jobs, not live replicas with broad access.
4. **Model card:** Document base model, data window, known failure modes.

## Input validation requirements (Apply)

Reject or strip:

- Field names failing `^[a-z][a-z0-9_]*$` (or product naming rules)
- Unknown `step_kind` / `field_type`
- Overlong strings / nested depth bombs
- URLs in unexpected fields
- HTML/script payloads
- References to IDs not visible under caller RLS (`link_existing`)

## Secure SDLC checklist before enablement

- [ ] Threat model reviewed for full_plan mode  
- [ ] IDOR tests on job GET/apply  
- [ ] Property tests on plan validator  
- [ ] Upload size/type limits  
- [ ] Secrets not in prompts (assert unit test)  
- [ ] Audit events for Apply  
- [ ] Feature flag default off in prod until golden SOP suite passes  
- [ ] Ollama not published in default compose  

## Residual risk acceptance

Even with controls, **LLM may propose scientifically incorrect protocol structure**. Security cannot validate assay correctness. Product must label drafts as non-authoritative; labs remain responsible for SOP compliance. That residual risk is **accepted** with human Apply.

## Recommendations

1. **Ship cloud full_plan behind feature flag** with human Apply only.  
2. **Security-test IDOR + injection** before GA.  
3. **Ollama as optional internal service**, not public.  
4. **Defer multi-tenant fine-tunes**; if ever, per-tenant only.  
5. **Never grant clients** SOP-config or Apply.  
6. **Audit** every Apply with job + model metadata.

**CSO verdict:** Acceptable to design and prototype with hard boundaries above. **Not acceptable** to auto-Apply model output or train a shared model on all customers’ SOPs.

---

Related: [ceo-review](../ceo-review/docker-model-sop-pipeline.md), [design](../design/docker-model-sop-pipeline.md), [design-review](../design-review/docker-model-sop-pipeline.md), [open-questions Decision #9](../open-questions/experiments.md)
