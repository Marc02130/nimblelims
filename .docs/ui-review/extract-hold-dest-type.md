# UI / UX Review: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Requirements:** [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md)  
**Related:** Architecture Accept (Heidi, PR 52) · Hold [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md)

## Executive summary

Entry setup for optional dest sample type is enough. One select next to Method, blank = “Same as parent,” same control on aliquot and pool. No new screen, no sample-ID field, no wizard.

**Verdict: Accept with conditions.** No product UI code in this packet.

## Flows reviewed

### A. Plan line (aliquot and pool)

```
Method  |  Dest sample type (optional)
           blank → Same as parent
```

### B. After execute (expectation only)

Dest appears with chosen/parent type and on the process queue when under a process. This packet does not redesign the queue.

## Conditions

| ID | Condition |
|----|-----------|
| **U1** | Dest sample type sits **beside Method** on both aliquot and pool plan lines (same control cluster). |
| **U2** | Blank shows placeholder **“Same as parent”** — not an empty unlabeled select. |
| **U3** | Do **not** add a sample-ID field, a wizard step, or a post-execute redirect to sample detail. |
| **U4** | Pool: one dest-type control per pool dest sample (not per source). |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U4) |
| **Date** | 2026-08-23 |
| **Product UI code** | None until Leadership Accept + implement packet |

```
UI REVIEW: Accept with conditions
```
