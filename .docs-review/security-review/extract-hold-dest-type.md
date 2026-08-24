# Security Review: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions** — gate **OPEN**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Related:** [Lab Ops](../lab-ops-review/extract-hold-dest-type.md) · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)  
**Artifact:** [PR 55](https://github.com/Marc02130/nimblelims/pull/55)  
**Scope:** Feature packet (STRIDE). DEEP CSO: skipped.

## Executive summary

Folded sketch covers dest type on aliquot/pool, lab-wide many-to-many transition catalog, L1 execute-minted process-sample join, step `accepted_sample_types` at start, pool one source type, blank = Same as parent always allowed. Multi-hop = multiple process steps / multiple catalog rows.

**S1 Met.** **S3** (`config:edit` on catalog mutate) is an implement condition — folded into sketch/requirements. Gate **OPEN** for implement with S3 + Lab Ops L2 + seed.

**Verdict: Accept with conditions.** Not IC50.

## Surface delta

| Surface | Risk |
|---------|------|
| Plan line `dest_sample_type` | Low |
| `sample_type_transitions` catalog | Elevation if writable without `config:edit` |
| `eln_process_samples` after start | Met (S1) when implement honors sketch |
| Step `accepted_sample_types` at start | Integrity gate |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | Existing JWT / RBAC |
| Tampering | Dest type on plan entry only; execute does not re-prompt (L2) |
| Repudiation | Existing execute audit |
| Info disclosure | Process membership must not expand client |
| DoS | Out of scope |
| Elevation | S1 process-sample; S3 catalog `config:edit` |

## Findings / conditions

| ID | Severity | Status | Condition |
|----|----------|--------|-----------|
| **S1** | High | **Met** (sketch) | After start, `eln_process_samples` insert only for execute-minted dest of this instance. Same client. `experiment:manage`. Append 403/404. |
| **S2** | High | **Met** | Client cannot insert process-samples. Pool gate labels allowed (aliquot-only retracted). |
| **S3** | High | **Implement condition** | `sample_type_transitions` mutate is **`config:edit` only**. Not Client, not `experiment:manage` alone. Execute refuse stays integrity. |

## Not in scope this review

- Matrix drop / TruSeq / SOP+AI Apply / IC50 / Deep `/cso`

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (S3 + L2 + seed) |
| **Date** | 2026-08-23 |
| **Implement gate** | **OPEN** for implement that lands S3, Lab Ops L2, and Blood×aliquot→DNA seed |
| **Deep `/cso`** | skipped |

```
SECURITY REVIEW: Accept with conditions
DEEP CSO: skipped
```
