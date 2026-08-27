# UI / UX Review: Atomic receive CORE

**Date:** 2026-08-26  
**Status:** **Accept**  
**Scope:** AR CORE receive loop — identity + **1..N vessels**  
**Tech sketch:** [`.docs/review/tech-sketch/atomic-receive.md`](../tech-sketch/atomic-receive.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/atomic-receive.md) · [CEO](../ceo-review/atomic-receive.md) · [Architecture](../architecture-review/atomic-receive.md)

## Executive summary

Historical packet UI **Accept** still stands: new receive loop, not AccessioningForm / wizard.

This stamp is the **CORE fold**. Implement follows PRD **1..N**, not “first vessel.” Scan **primary** barcode + optional **additional** barcodes for the **same sample** (true extra vessels, not daughter Samples, not aliquot). Sticky project / type / matrix. Stay on `/receive`. No sample-ID field, no status picker, no tube picker, no Received hop, no sample-detail redirect.

**Verdict: Accept** on CORE. Coding stays Grok Build. Not IC50.

## CORE loop (locked)

1. Scan (or type) **primary** barcode. **No sample-ID field.** Keyboard still works on the barcode field.
2. Optionally add more barcodes for the same sample before submit.
3. Sticky sample type, matrix, project. Temperature optional. Prefer no test assignment on the default path.
4. Submit → toast → clear barcode field(s) → keep sticky → focus primary.
5. Next specimen. **Stay on the screen.**

Label extra barcodes as **additional tubes for this sample** — not aliquot / split / derivative. Duplicate barcode → 409 toast, stay on screen (no partial commit).

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
- IC50

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** |
| **Date** | 2026-08-26 |
| **Named scope** | AR CORE receive loop — primary + optional additional barcodes |
| **Product UI code** | Grok Build (this stamp is docs only) |

```
UI REVIEW: Accept
SCOPE: AR CORE (new receive loop, 1..N vessels)
```
