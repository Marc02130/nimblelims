# Lab Ops Review (SVP): Atomic receive

**Date:** 2026-08-20  
**Status:** **Accept with conditions**  
**Reviewer persona:** SVP Lab Ops  
**Packet:** [tech-sketch/atomic-receive.md](../tech-sketch/atomic-receive.md) on PR 28  
**Related:** Leadership freeze 2026-08-20 (three-pillar MVP)

## 1. Executive summary

The sketch is the Hold packet. A tech can receive a rack under time pressure: one transaction, scan-first, stay on receive, system-managed status, optional tests, type-a-number results. Parked work (ELN, IC50, method-matrix, US-28, aliquot execute) stays parked.

**Verdict: Accept with conditions.** Conditions L1–L4 land in the same phase. L1–L4 are now folded into the sketch.

## 2. Lab fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| Bench reality | 8 | Stay-on-receive loop is the rack path. Sample.name is the barcode (L1). |
| Material & sample integrity | 8 | Unique container name, 409 on duplicate, no timestamp suffix. |
| Gating & compliance | 8 | System writes Received then Available for Testing. Tech does not pick status. |
| Containers / amount | 7 | Default tube off the form (L3). No new barcode table. |
| Instrument boundary | 9 | Classic result on a test. No lims_run, no IC50. |
| Scope discipline | 9 | Parked list is explicit. |
| Template → instance | n/a | Not this packet. |

## 3. Conditions (must land with implement)

| ID | Condition | Why |
|----|-----------|-----|
| **L1** | `Sample.name` = scanned barcode (same string as `Container.name`). Do not `generate_name_for_sample` a second ID. | The tube in hand is the identity. |
| **L2** | Project is required and session-sticky. Never auto-create a project per tube. | Auto-create dumps garbage projects into the queue. |
| **L3** | Container type is the lab default tube. Not a per-tube field. | Asking type on every scan breaks the loop. |
| **L4** | Test status at receive is assigned/pending, not In Process. DELETE test is refused if results exist. | In Process lies that work started. Deleting a resulted test breaks the audit trail. |

## 4. Locked (already in sketch — do not reopen)

- One POST, one DB transaction (sample + container + contents + optional tests)
- After success: stay on receive, toast, clear barcode, keep sticky type/matrix/project, focus barcode
- No sample-detail redirect, no aliquot dialog
- Tests optional at receive; add/remove from sample with no wizard
- System writes Received then Available for Testing; drop status from payload
- Duplicate `Container.name` → 409, no timestamp suffix
- Results: raw value, unit from `analytes.units_default`, optional qualifier (`<LOD`, `ND`)
- Existing tables only. Temperature optional. No ELN / IC50 / lims_run / US-28 / method-matrix

## 5. Few fields (closes open question)

Per-tube: barcode (required), optional `client_sample_id`.  
Session-sticky: sample type, matrix, project, optional analyses.  
Off the form: status, temperature, due_date, qc_type, description, container type, client_id, client_project_id.

## 6. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L1–L4) |
| **Date** | 2026-08-20 |
| **Implement gate** | OPEN for Heidi / Hans / CEO reviews. No product code until those pass. L1–L4 are in the sketch. |
