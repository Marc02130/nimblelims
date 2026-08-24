# QA Review: Med/Low security remediation (S7–S15)

**Date:** 2026-08-21  
**Status:** **Accept with conditions**  
**Requirements:** [`.docs-review/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)  
**Tech sketch:** [`.docs-review/tech-sketch/security-med-low-s7-s15.md`](../tech-sketch/security-med-low-s7-s15.md)

## Testability

| Finding | Testable? | Notes |
|---------|-----------|-------|
| S7 | Yes | Two-client fixture; start with foreign sample → 404/403 |
| S8 | Yes | Oversized upload fixture |
| S9 | Yes | No token → 401 |
| S10 | Manual | Doc checklist |
| S11 | Yes | Query `pg_class.relforcerowsecurity`; RLS suite |
| S12 | Manual/CI | Compose file assert no ports on prod overlay |
| S13 | Yes | Client user GET /roles → 403 |
| S14 | Yes | Write-back forbidden column |
| S15 | Yes | Scripted failed logins → lock |

## Conditions

| ID | Condition |
|----|-----------|
| **Q1** | Create **`UAT_Scripts/uat-security-med-low-s7-s15.md`** with per-phase cases + negatives. |
| **Q2** | Pytest ≥1 automated case per finding that is code-backed (S10/S12 may be doc/compose checks). |
| **Q3** | Regression: High S1–S6 smoke (login must-change path, cohort upsert refuse) still green. |
| **Q4** | Implement prompts include manuals updates for S10/S12. |
| **Q5** | UAT personas: labtech, client A/B, admin; lockout tested with throwaway user. |

## Verdict

**Accept with conditions Q1–Q5.** Packet is testable by phase.

## Implement gate note

QA Accept = testability. Each phase needs UAT pass before claiming Met on codebase.md.
