# Security Review: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md) (folded on main)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Related:** [Lab Ops](../lab-ops-review/extract-hold-dest-type.md) · [UI](../ui-review/extract-hold-dest-type.md) · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)  
**Scope:** Feature packet (STRIDE). DEEP CSO: skipped.

## Executive summary

Folded sketch on main covers dest type on aliquot/pool, lab-wide transition catalog, L1 execute-minted process-sample join, step `accepted_sample_types` at start, pool one source type, blank = Same as parent always allowed.

**S1 Met** in sketch. Catalog mutate AuthZ (`config:edit` only) is locked in chat / Leadership but **not yet in the sketch text** — **S3** must fold before implement gate opens.

**Verdict: Accept with conditions (S2–S3).** Not IC50.

## Surface delta

| Surface | Risk |
|---------|------|
| Plan line `dest_sample_type` | Low — entry config |
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
| **S2** | High | **Met** (chat + sketch intent) | Client role cannot insert process-samples. *(Aliquot-only dest type ≠ parent retracted — pool gate labels allowed.)* |
| **S3** | High | **Open — fold into sketch** | `sample_type_transitions` mutate is **`config:edit` only**. Not writable via `experiment:manage` or Client. Execute refuse stays integrity. |

## Not in scope this review

- Matrix drop / TruSeq / SOP+AI Apply / IC50 / Deep `/cso`

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (S3 fold) |
| **Date** | 2026-08-23 |
| **Implement gate** | CLOSED until S3 is in the sketch; then OPEN with Lab Ops L2 + seed watch |
| **Deep `/cso`** | skipped |

SECURITY REVIEW: Accept with conditions  
DEEP CSO: skipped
