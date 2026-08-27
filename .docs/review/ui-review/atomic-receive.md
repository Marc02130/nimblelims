# UI / UX Review: Atomic receive CORE

**Date:** 2026-08-26  
**Status:** **Accept** (on CORE, **with conditions**)  
**Scope:** AR CORE receive loop — identity + **1..N** vessels; **no analysis-as-work-plan**  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Requirements:** [`.docs/review/requirements/atomic-receive.md`](../requirements/atomic-receive.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/atomic-receive.md) · [CEO](../ceo-review/atomic-receive.md) · [Architecture](../architecture-review/atomic-receive.md)

## Executive summary

Historical packet UI **Accept** still stands: **new receive loop**, not AccessioningForm / wizard.

This stamp is the **CORE fold**. Implement follows PRD **1..N**, not “first vessel.” Scan **primary** barcode + optional **additional** barcodes for the **same sample** (true extra vessels, not daughter Samples, not aliquot). Sticky project / type / matrix. Stay on `/receive`. No sample-ID field, no tube picker, no analysis-as-work-plan, no Received hop, no sample-detail redirect.

Collision → **409**, **stay on the scan well** (no partial commit).

CORE receive creates **zero Tests**. No analyses picker. Non-empty `analysis_ids` is a server **422** (refuse) — UI must not send a work-plan.

**Verdict: Accept** on CORE **with these conditions**. Coding stays Grok Build. **Hold merge** until UAT + dogfood. **PR 71 stays draft.** Not IC50.

## CORE loop (locked)

1. Scan (or type) **primary** barcode. **No sample-ID field.** Keyboard still works on the barcode field.
2. Optionally add more barcodes for the same sample before submit.
3. Sticky sample type, matrix, project. Temperature optional. **No analyses picker. No work-plan.**
4. Submit → toast → clear barcode field(s) → keep sticky → focus primary.
5. Next specimen. **Stay on the screen.**

Label extra barcodes as **additional tubes for this sample** — not aliquot / split / derivative. Duplicate barcode → **409** toast, **stay on the scan well**.

## Bounce (fails UI CORE Accept)

- Wizard revival / AccessioningForm as the forever receive path
- Sample-ID field / user-typed sample name / C1
- Single-vessel-only UI (no way to add extra barcodes)
- Tube picker on the scan loop
- Status picker / Received hop
- Project auto-create
- Analysis presented as “what’s next” / work plan
- Sample-detail redirect or aliquot dialog
- Results-entry UI as CORE ship
- Extract-hold / `work_order` surfaces on receive
- Method = dest
- IC50
- Leave the scan well on 409

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** (with conditions) |
| **Date** | 2026-08-26 |
| **Named scope** | AR CORE receive loop — primary + optional additional barcodes |
| **Merge** | Hold until UAT + dogfood. PR 71 stays draft. |
| **Product UI code** | Grok Build (this stamp is docs only) |

```
UI REVIEW: Accept
SCOPE: AR CORE (new receive loop, 1..N vessels)
CONDITIONS: hold merge until UAT + dogfood; PR 71 stays draft
```
