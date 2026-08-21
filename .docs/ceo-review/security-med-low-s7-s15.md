# CEO Review: Med/Low security remediation (S7–S15)

**Date:** 2026-08-21  
**Status:** **Accept with conditions**  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)  
**Prerequisite:** High S1–S6 Met

## Ask

Should we invest in Med/Low findings now that High is Accept?

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Priority** | **P1 after High merge** — required for credible “production” language |
| **Ambition** | Right-sized: no cookie rewrite; phased quick wins first |

## Why

High closed the isolation/AuthN disasters. Remaining items are what questionnaires and pen-testers hit next: unauthenticated validate, upload bombs, published Postgres, catalog leakage, brute force. Shipping P1 quickly is high ROI.

## Conditions

| ID | Condition |
|----|-----------|
| **C1** | Do **not** expand into httpOnly JWT / BFF this cycle (OQ-S10 Decided No). |
| **C2** | Phase order P1→P2→P3→P4; P1 can ship/merge independently if reviews allow. |
| **C3** | Do not claim whole-product production-ready until P1+P2 Met and S12 prod profile exists. |
| **C4** | Keep High S1–S6 behavior unchanged. |
| **C5** | S14: prefer drop write-back for biotype/temperature unless Lab Ops objects. |

## Decision

**Proceed** to Arch · Security · QA; implement P1 after Accept.
