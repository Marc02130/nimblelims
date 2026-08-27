# Lab Ops Review (SVP): Atomic receive CORE

**Date:** 2026-08-20  
**Updated:** 2026-08-26 (CORE re-review — **1..N** vessels; L4 Test-at-receive **superseded**)  
**Status:** **Accept with conditions** (L2–L3; L1 retracted; L4 Test-at-receive superseded)  
**Reviewer persona:** SVP Lab Ops  
**Scope of this stamp:** **AR CORE only** — identity + **1..N vessels**; **refuse `analysis_ids`**; docs/UAT/dogfood  
**Packet:** [tech-sketch/atomic-receive.md](../tech-sketch/atomic-receive.md) · [requirements/atomic-receive.md](../requirements/atomic-receive.md)  
**Related:** [Leadership gate](../../discussions/2026-08-26-ar-core-plan-leadership.md) · [WO-7](../../decision-logs/framework-stamps-2026-08-26.md)

## 1. Executive summary

CORE is bench-real for high-volume receive: scan a **primary** barcode, optionally add **additional** barcodes for the same material, keep sticky type/matrix/project, commit once, stay on the form. Extra tubes are extra vessels on the **same** Sample — not daughters, not aliquot.

**Two identities remain correct (L1 stays retracted):**

| Identity | Field | Receive |
|----------|--------|---------|
| Tube / vessel | `containers.name` | Scanned barcode. Any duplicate (request or DB) → **409** and full rollback. Stay on the scan well. |
| Material | `samples.name` | System-assigned from the existing name template. Tech does **not** type it. **No sample-ID field.** |

**L4 Test-at-receive is superseded.** CORE creates **zero Tests**. **Refuse:** if `analysis_ids` is present and non-empty → **422**. Empty or omitted only. `_create_asked_for_tests` is a fail. Ignore is not the pick. DELETE-with-results still stands for independently created tests. Classic Test+Result with no LimsRun still exists — not this packet. Test at LimsRun start is WO-7, later.

**Language:** Prefer **primary + additional barcodes** / **1..N vessels**. Do **not** use “first tube / first vessel only.”

**Verdict: Accept with conditions** (L2–L3). Merge hold until UAT + dogfood. PR 71 stays draft.

## 2. Conditions (must land with CORE implement)

| ID | Condition | Why |
|----|-----------|-----|
| **L1** | **Retracted.** Barcode ≠ sample ID. Two identities. | Sample ID is material; barcode is the tube. |
| **L2** | Project **required** and **session-sticky**. Never auto-create a project per tube. | Auto-create dumps garbage projects. |
| **L3** | Container type = **lab default tube**, applied to **all** vessels on the call, **off the form**. No tube picker. | Asking type on every scan breaks the loop. |
| **L4** | **Superseded.** CORE receive creates **zero Tests**. **Refuse** present non-empty `analysis_ids` → **422**. **DELETE** remains refused if an independently created test has results. | Receive does not imply an order or work plan. A-15 parked. WO-7 later. |

## 3. Locked for CORE (do not reopen)

- One `POST /api/samples/receive`, one DB transaction: sample + **1..N** 1×1 containers + contents each; **zero Tests**
- Extra barcodes = more 1×1 Contents on the **same** Sample, not daughter Samples
- UX: **primary barcode required** + **optional additional barcodes** on the same commit
- After success: stay on receive; toast; clear barcode field(s); sticky type/matrix/project; focus **primary**
- Collision → **409**, stay on the scan well; no partial commit
- No sample-detail redirect; no aliquot dialog; no sample-ID field; no status picker; no tube picker; no analyses picker / work-plan
- Status on commit: **Available for Testing** only; receipt = `received_date`
- AuthZ identical to sample create + project RLS on the **whole txn**
- Existing tables only
- **OUT:** results-entry as ship blocker; aliquot/derivative UI; intake-profile engine; work_order; wizard as forever receive path; IC50

## 4. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L2–L3; L1 retracted; L4 Test-at-receive superseded) |
| **CORE scope** | Identity + **1..N vessels** + refuse `analysis_ids` |
| **Results-entry** | **OUT of CORE** |
| **Merge** | Hold until UAT + dogfood. PR 71 stays draft. |
| **Date** | 2026-08-26 |
