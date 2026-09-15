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

## 6. Deiter Lab Ops Confirm — Marc E-10 fold (2026-09-14)

**Deiter Lab Ops Confirm** of Marc’s UAT punch (7.3b / 7.6b / 7.7b / 7.8). Formal **§7 Result: Pass** (Tobias QA, 2026-09-14 22:28 ET, `dc7ee92`) — **7.1–7.8 Pass** on `e5a8fdd` (not rescored) + Deiter **double-Add Pass** on `dc7ee92` (**409** `wrapper_at_capacity`). Prior overall **Fail** on `e5a8fdd` is **history**. **Lab Ops: Deiter Met** on double-Add 2026-09-14. Living uniqueness: **409** `wrapper_at_capacity` (not a blocker). **Rolf Confirm: Hold merge lifted**. **E-10 Met**. Product on `main` @ `e56a89f` (PR **129**). **Tobias dogfood Ready=Yes** on **`dc7ee92`** (`/workspace/dogfood-e10-dc7ee92/READY.md`). Ready=Yes on **`e5a8fdd`** and Ready=No on **`9312c54`** stay history. Evidence: `/workspace/uat-e10-section7-overall-dc7ee92/RESULT.md`, `/workspace/uat-e10-section7-overall-dc7ee92/stamp.json`, `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`, `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`, `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`, `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`, `/workspace/dogfood-e10-dc7ee92/READY.md`. Prior Fail history: `/workspace/uat-e10-section7-e5a8fdd/`. §§1–6 stay `008baf2`. Does **not** rewrite the 2026-08-23 Accept-with-conditions verdict above. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

## 7. Deiter Met — double-Add (2026-09-14)

**Lab Ops: Deiter Met** on the EXTRA double-Add bar on product **`dc7ee92`**. Sequential second plan POST → **409** `wrapper_at_capacity`; second dest POST → **409**; GET still **1 plan + 1 dest** (no half). Concurrent double POST → statuses **201 + 409**; after counts **1 plan + 1 dest**. Prior Fail on `e5a8fdd` is history. Does **not** rewrite the 2026-08-23 Accept-with-conditions verdict. Not IC50.
