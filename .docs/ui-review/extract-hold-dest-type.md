# UI / UX Review: Extract-hold dest sample type (PR 54 fold)

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Supersedes:** UI Accept on PR 52 (C3 aliquot-only void)

## Executive summary

Re-read after Marc C3 retract. Dest type beside Method on **aliquot and pool**. Blank = “Same as parent.” Start-time type gate only (experiment + LimsRun start). No receive gate. No mid-entry type check. No sample-ID box, wizard, or sample-detail hop.

**Verdict: Accept with conditions.** No product UI code in this packet.

## Flows reviewed

### A. Plan line (aliquot and pool)

```
Method  |  Dest sample type (optional)
           blank → Same as parent
```

Pool may set dest type ≠ parent (e.g. pooled DNA). Same control as aliquot.

### B. Start gate (not this packet’s UI chrome, contract only)

Refuse at experiment / LimsRun **start** when `accepted_sample_types` is non-empty and sample type ∉ list. Clear error. Not receive. Not mid-entry.

## Conditions

| ID | Condition |
|----|-----------|
| **U1** | Dest sample type sits **beside Method** on **aliquot and pool** plan lines. |
| **U2** | Blank shows placeholder **“Same as parent.”** |
| **U3** | No sample-ID field, no wizard, no post-execute hop to sample detail. |
| **U4** | Pool: one dest-type control per pool dest (same as aliquot). |
| **U5** | Type gate is **start only**. Bounce a receive gate or mid-entry type check. |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U5) |
| **Date** | 2026-08-23 |
| **Product UI code** | None until Leadership Accept + implement packet |

```
UI REVIEW: Accept with conditions
```
