# Lab Ops Review (SVP): Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Reviewer persona:** SVP Lab Ops  
**Packet:** [tech-sketch/extract-hold-dest-type.md](../tech-sketch/extract-hold-dest-type.md) · [requirements/extract-hold-dest-type.md](../requirements/extract-hold-dest-type.md)  
**Related:** Architecture Accept · UI Accept with conditions · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)

## 1. Executive summary

Dest type on the aliquot/pool **entry** (beside Method), blank = Same as parent, execute writing `samples.sample_type` + `parent_sample_id` + `eln_process_samples` is the right bench shape. Template owns extract DNA; the tech under time pressure does not re-pick type on execute.

The sketch still has one hole that keeps Extract-then-Qubit fiction: after the extract step has started, cohort lock must treat an **execute-minted** dest as the product of that step, not a second batch. Without that lock written and honored, DNA can be created and still never appear for Qubit scan→start.

**Verdict: Accept with conditions (L1–L2).** Matrix drop stays later. TruSeq library is the same rule later. Not IC50.

## 2. Lab fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| Bench reality | 7 | Entry owns type; blank = parent is honest for aliquot. Extract DNA is not a checkbox at execute. |
| Material & sample integrity | 7 | New dest + `parent_sample_id` matches derivative identity. Type DNA on blood parent is the material story. |
| Chemistry / sequencing | 6 | Clears Qubit-on-DNA once L1 holds. TruSeq library is another daughter later. |
| Gating & compliance | 6 | Process membership is required; ad hoc skip is fine. Cohort exception must be explicit (L1). |
| Template → instance | 8 | Dest type beside Method on the plan line is reusable SOP setup. |
| Competitive floor | 7 | Enough for blood → DNA → quant without inventing a side spreadsheet. |
| Containers / amount | 8 | Reuses existing aliquot/pool amount/container execute. |
| Cohort / queue | 5 | Sketch inserts process-sample but does not lock started-instance exception. |
| Instrument boundary | 8 | Qubit stays a later LimsRun on the daughter’s Test; this packet does not invent Tests on blood. |

## 3. Conditions (must land with implement)

| ID | Condition | Why |
|----|-----------|-----|
| **L1** | Sketch + execute: an execute-minted dest for **this** process instance is allowed onto `eln_process_samples` even when the instance (or current step) has already started. It is the product of the step, not a second batch. Arbitrary sample-ID append stays refuse. | Without this, DNA is created then refused; Qubit scan→start has nothing honest. Same Hold hole as 2026-08-21. |
| **L2** | Dest type is set only on the plan entry (beside Method). Execute does not re-prompt type, open a sample-ID box, wizard, or hop to sample detail. | Under time pressure the tech will leave a second picker blank and dest stays blood. |

## 4. Risks / watch items (non-blocking)

- **Matrix still copies parent** until a later packet. Type DNA with matrix still blood is a residual lie if any path keys off matrix. Next-step eligibility and Qubit must key off `sample_type` (and process membership), not matrix. Do not reopen matrix drop in this packet.
- Pool dest type ≠ parent is rare on the bench; blank = parent remains the default path.
- Clearing this Hold unlocks Qubit on DNA. It does **not** unlock TruSeq end-to-end (library is another dest-type pass).

## 5. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L1–L2) |
| **Implement gate** | CLOSED until L1 is folded into the sketch/AC and Leadership Accept; then OPEN for implement that lands L1–L2 |
| **Not in scope** | Matrix drop · TruSeq library · SOP+AI Apply · IC50 · Atomic-receive |

```
LAB OPS REVIEW: Accept with conditions
```
