# UI / UX Review: Extract-hold dest sample type (PR 54 config-table fold)

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)

## Executive summary

Re-read after system-wide config table. Dest type select beside Method on aliquot and pool. Options come from the **lab-wide** catalog (`source × aliquot|pool × allowed dest`), not from the entry or template. Blank = “Same as parent.” always present. Start-time entry gate stays separate (`accepted_sample_types`). No free-text type. No receive / mid-entry type check.

**Verdict: Accept with conditions.** No product UI code in this packet.

## Flows reviewed

### A. Plan line

```
Method  |  Dest sample type
           Same as parent.  (always)
           + catalog rows for this source × this operation only
```

### B. Mixed-source pool (Hans / Heidi)

If UI shows one dest type for a multi-source pool, every source must have a catalog row for that op → dest, or execute refuses. Prefer disable Start / Execute with a clear message when the chosen dest is not allowed for all sources.

## Conditions

| ID | Condition |
|----|-----------|
| **U1** | Dest type beside Method on aliquot and pool. |
| **U2** | Blank placeholder **“Same as parent.”** always present / always allowed. |
| **U3** | Options = system-wide catalog for that source × operation only — not per-entry, not template JSON. |
| **U4** | No free-text type, sample-ID box, wizard, or hop to sample detail. |
| **U5** | Type **entry** gate is start only. Bounce receive gate or mid-entry type check. |
| **U6** | Mixed-source pool: do not present a dest type that is illegal for any source; or block execute with a lab-readable error. |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U6) |
| **Date** | 2026-08-23 |
| **Product UI code** | None until Leadership Accept + implement packet |

```
UI REVIEW: Accept with conditions
```
