# Lab Ops Review (SVP): Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions** (L1 Met; L2 stands)  
**Reviewer persona:** SVP Lab Ops (Deiter)  
**Packet:** [tech-sketch/extract-hold-dest-type.md](../tech-sketch/extract-hold-dest-type.md) · [requirements/extract-hold-dest-type.md](../requirements/extract-hold-dest-type.md)  
**Related:** Architecture Accept · UI Accept (U6) · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)

## 1. Executive summary

Dest type on the aliquot/pool **plan entry** (beside Method), blank = Same as parent, execute writing `samples.sample_type` + `parent_sample_id` + `eln_process_samples` is the right bench shape. Template owns extract DNA; the tech under time pressure does **not** re-pick type on execute.

**L1 is Met** in the folded sketch: execute-minted dest joins this process instance after start (product of the step); arbitrary append stays refuse.

**L2 stands:** dest type only on the plan entry — no execute re-prompt, sample-ID box, wizard, or hop to sample detail.

Catalog is **many-to-many** (separate rows per dest). Seed **Blood × aliquot → DNA** with implement. Multi-hop (e.g. Blood → plasma → cfDNA) is **process steps**, not one chained catalog row.

**Verdict: Accept with conditions (L1 Met; L2).** Implement gate stays CLOSED until Günter stamps `config:edit` on the catalog. Not IC50.

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
| **L1** | Execute-minted dest for **this** process instance may join `eln_process_samples` even when the instance/step has already started (product of the step). Arbitrary append stays refuse. | **Met** (folded into sketch/AC) |
| **L2** | Dest type is set **only** on the plan entry (beside Method). Execute does **not** re-prompt type, open a sample-ID box, wizard, or hop to sample detail. | **Stands** — land with implement |

**With implement (not a Lab Ops revise):** seed at least **Blood × aliquot → DNA**. Additional many-to-many rows (plasma, RBC, WBC, buffy coat, …) are catalog config after Günter `config:edit`.

## 4. Risks / watch items (non-blocking)

- Matrix still copies parent until a later packet; eligibility/Qubit key off `sample_type` (C2).
- Multi-hop is process design, not a single catalog edge.
- Clearing this Hold unlocks Qubit on DNA; not TruSeq end-to-end.

## 5. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L1 Met; L2) |
| **Implement gate** | CLOSED until Günter stamps `config:edit` on the transition catalog; then OPEN for implement that lands L2 + seed Blood×aliquot→DNA |
| **Not in scope** | Matrix drop · TruSeq library · SOP+AI Apply · IC50 · Mixed container contents as pool |

```
LAB OPS REVIEW: Accept with conditions (L1 Met; L2)
```
