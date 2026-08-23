# UI / UX Review: Extract-hold dest sample type (PR 54)

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)

## Executive summary

Re-stamp after Marc same-type pool rule. Dest type beside Method. Options from system-wide catalog for source × aliquot|pool. Blank = “Same as parent.” always. Pool: enable dest select only when all sources share one type; mixed source types refuse. Start-time entry gate only. No free-text, receive gate, or mid-entry type check.

**Verdict: Accept with conditions.** No product UI code.

## Conditions

| ID | Condition |
|----|-----------|
| **U1** | Dest type beside Method on aliquot and pool. |
| **U2** | Blank placeholder **“Same as parent.”** always present / always allowed. |
| **U3** | Options = system-wide catalog for that source × operation only. |
| **U4** | No free-text type, sample-ID box, wizard, or hop to sample detail. |
| **U5** | Type entry gate is **start only**. Bounce receive gate or mid-entry type check. |
| **U6** | Pool: all sources must share one `sample_type`; mixed types refuse. Dest select enabled only after that; then one catalog row for that type × pool → dest. |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U6) |
| **Date** | 2026-08-23 |
| **Product UI code** | None until Leadership Accept + implement packet |

```
UI REVIEW: Accept with conditions
```
