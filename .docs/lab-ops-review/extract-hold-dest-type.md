# Lab Ops Review (SVP): Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions** (L1 Met; L2 stands)  
**Reviewer persona:** SVP Lab Ops (Deiter)  
**Packet:** [tech-sketch/extract-hold-dest-type.md](../tech-sketch/extract-hold-dest-type.md) · [requirements/extract-hold-dest-type.md](../requirements/extract-hold-dest-type.md)  
**Related:** Architecture Accept · UI Accept (U6) · Security/CSO [PR 55](https://github.com/Marc02130/nimblelims/pull/55) · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)

## 1. Executive summary

Dest type on the aliquot/pool **plan entry** (beside Method), blank = Same as parent, execute writing `samples.sample_type` + `parent_sample_id` + `eln_process_samples` is the right bench shape. Template owns extract DNA; the tech under time pressure does **not** re-pick type on execute.

**L1 is Met.** **L2 stands** (land with implement). Catalog is many-to-many. Seed Blood × aliquot → DNA with implement.

**Verdict: Accept with conditions (L1 Met; L2).** Leadership opened the implement gate (Günter PR 55) for S3 + L2 + seed. Not IC50.

## 2. Lab fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| Bench reality | 8 | Entry owns type; blank = parent; no execute re-prompt (L2). |
| Material & sample integrity | 8 | New dest + `parent_sample_id`; many-to-many catalog matches blood fractions. |
| Chemistry / sequencing | 7 | Clears Qubit-on-DNA once L1 holds. TruSeq later. |
| Gating & compliance | 7 | Process membership + start entry allow-list; catalog is config not code. |
| Template → instance | 8 | Dest type beside Method on the plan line. |
| Competitive floor | 7 | Blood → DNA → quant without a side spreadsheet. |
| Containers / amount | 8 | Reuses existing aliquot/pool execute. |
| Cohort / queue | 8 | L1 Met: execute-minted dest joins after start. |
| Instrument boundary | 8 | Qubit stays a later LimsRun on the daughter. |

## 3. Conditions

| ID | Condition | Status |
|----|-----------|--------|
| **L1** | Execute-minted dest for **this** process instance may join `eln_process_samples` even when the instance/step has already started. Arbitrary append stays refuse. | **Met** |
| **L2** | Dest type set **only** on the plan entry. Execute does **not** re-prompt type. | **Stands** — land with implement |

**With implement:** seed at least **Blood × aliquot → DNA**.

## 4. Risks / watch items (non-blocking)

- Matrix still copies parent; eligibility/Qubit key off `sample_type` (C2).
- Multi-hop is process design, not a single catalog edge.

## 5. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L1 Met; L2) |
| **Implement gate** | **OPEN** (Leadership / Günter PR 55) — implement lands L2 + S3 + Blood×aliquot→DNA seed |
| **Not in scope** | Matrix drop · TruSeq · SOP+AI Apply · IC50 · Mixed container contents as pool |

```
LAB OPS REVIEW: Accept with conditions (L1 Met; L2)
```
