# Lab Ops Review (SVP): Atomic receive

**Date:** 2026-08-20  
**Status:** **Accept with conditions** (L1 retracted)  
**Reviewer persona:** SVP Lab Ops  
**Packet:** [tech-sketch/atomic-receive.md](../tech-sketch/atomic-receive.md)  
**Related:** Leadership freeze 2026-08-20 (three-pillar MVP)

## 1. Executive summary

The packet is the wedge: scan receive, one transaction, type a number on a test. Two identities are correct lab practice. Barcode is the tube. Sample ID is the material.

**L1 is retracted.** Sample ID is not the tube barcode.

**Verdict: Accept with conditions** (L2–L4). No aliquot or derivative UI this packet.

## 2. Identities (locked)

| Identity | Field | Receive |
|----------|--------|---------|
| Tube | `containers.name` | Scanned barcode. Duplicate scan → 409 on container only. |
| Material | `samples.name` | System-assigned from the existing name template. Tech does not type it. 409 only if that sample ID collides. |

Receive screen has **no sample-ID field**. Lookup is scan the tube. P0 creates one sample plus its first tube.

Aliquot later: same sample, another container + contents row.  
Derivative later (DNA from blood): new sample with `parent_sample_id`.  
Not this packet.

## 3. Conditions (same phase)

| ID | Condition | Why |
|----|-----------|-----|
| **L1** | **Retracted.** | Two IDs. Barcode is the tube. |
| **L2** | Project required and session-sticky. Never auto-create a project per tube. | Auto-create dumps garbage projects. |
| **L3** | Container type is the lab default tube. Not a per-tube field. | Asking type on every scan breaks the loop. |
| **L4** | Test status at receive is assigned/pending, not In Process. DELETE refused if results exist. | In Process lies that work started. Deleting a resulted test breaks the audit. |

## 4. Locked (do not reopen)

- One POST, one DB transaction (sample + first container + contents + optional tests)
- After success: stay on receive, toast, clear barcode, sticky type/matrix/project, focus barcode
- No sample-detail redirect, no aliquot dialog
- Tests optional at receive; add/remove from sample with no wizard
- One status on commit: Available for Testing. Receipt is `received_date`. No status_history. Techs do not pick status.
- Results: `reported_result` + `qualifiers`. Unit from `analytes.units_default`; missing → 422. No `results.unit_id`.
- Existing tables only. Temperature optional.

## 5. Few fields

Per-tube: barcode (required), optional `client_sample_id`.  
Session-sticky: sample type, matrix, project, optional analyses.  
Off the form: sample ID, status, container type, due_date, qc_type, client_id.

## 6. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L2–L4; L1 retracted) |
| **Date** | 2026-08-20 |
| **Implement gate** | Packet signed on docs. No new Lab Ops packet. |
