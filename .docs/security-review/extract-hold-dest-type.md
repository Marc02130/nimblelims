# Security Review: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Related:** [Lab Ops](../lab-ops-review/extract-hold-dest-type.md) · [UI](../ui-review/extract-hold-dest-type.md) · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)  
**Scope:** Feature packet (STRIDE). DEEP CSO: skipped.

## Executive summary

Optional dest `sample_type` on the aliquot/pool plan entry and execute writing `samples.sample_type` + `parent_sample_id` is not an AuthZ hole by itself. Existing columns only. Matrix drop stays out. Pool may set dest type ≠ parent as a **gate label** (pooled DNA, indexed DNA); material-class extract via pool remains Hans’s science refuse, not AuthZ.

The AuthZ hole is **process-sample insert after start**. The sketch inserts dest into `eln_process_samples` but must lock that path as execute-only. Without that lock, any caller who can touch process-samples can append after cohort lock — elevation past the started-instance refuse.

**Verdict: Accept with conditions (S1–S2).** Gate stays CLOSED until S1 is folded into the sketch. Not IC50.

## Surface delta

| Surface | Risk |
|---------|------|
| Plan line `dest_sample_type` (aliquot + pool) | Low — config on entry; not execute AuthZ |
| Execute dest create | Tampering if type can be re-prompted at execute (Lab Ops L2) |
| `eln_process_samples` insert after start | **High** — append-as-elevation if not execute-minted only |
| Step `accepted_sample_types` at start | Integrity gate; keys off `sample_type` |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | Existing JWT / RBAC; no change |
| Tampering | Dest type on plan entry only; execute does not re-prompt |
| Repudiation | Existing `modified_by` / execute audit; no new audit table this packet |
| Info disclosure | Dest inherits project/client of parent path; process membership must not expand client |
| DoS | Out of scope |
| Elevation | Process-sample after start only for execute-minted dest of this instance |

## Findings / conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **S1** | High | After start, `eln_process_samples` insert is allowed only for an **execute-minted** dest of **this** process instance. Same client. Caller has `experiment:manage` on this instance. Arbitrary sample-ID append stays **403/404**. Matches Lab Ops L1 as AuthZ. |
| **S2** | High | Client role cannot insert process-samples. *(Retracted 2026-08-23: aliquot-only dest type ≠ parent — pool gate labels are allowed; material-class refuse is science, not AuthZ.)* |

## Not in scope this review

- Matrix drop / catalog absorb
- TruSeq library dest-type
- SOP+AI Apply
- IC50
- Deep `/cso`

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (S1–S2) |
| **Date** | 2026-08-23 |
| **Implement gate** | CLOSED until S1 is in the sketch/AC |
| **Deep `/cso`** | skipped |

SECURITY REVIEW: Accept with conditions  
DEEP CSO: skipped
