# CEO Review: High security remediation (S1–S6)

**Date:** 2026-08-20  
**Status:** **Accept with conditions**  
**Reviewer:** CEO / product (packet)  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Source audit:** [`.docs/security-review/codebase.md`](../security-review/codebase.md)

## Ask

Should we prioritize closing High findings S1–S6 before further ELN/feature expansion and before calling any environment “production”?

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Priority** | **P0 — blocks production** |
| **Scope** | High only (S1–S6); Med/Low deferred |

## Why this wins

Early-stage biotech buyers and partners will not tolerate:

- Forgeable JWTs / default secrets  
- Shared well-known admin passwords in a “real” deployment  
- Passwords in logs  
- Cross-client data if RLS is advertised but inactive  
- Silent wrong-sample write-back or partial aliquot mutations  

This packet is **trust infrastructure**, not a nice-to-have. Shipping more experiment UI on a stack that fails isolation is reputational debt.

## Scope discipline (CEO conditions)

| ID | Condition |
|----|-----------|
| **C1** | Do **not** expand this branch into S7–S15 or multi-tenant redesign. |
| **C2** | Preserve local/UAT dogfood with **explicit** insecure flags — do not make day-1 setup impossible. |
| **C3** | S5 refuse-null amount is acceptable product friction; document for lab techs. |
| **C4** | Production narrative: after merge + UAT, update README to stop claiming bcrypt/RLS until true. |
| **C5** | Implement order P0a→P0b→P0c→P0d; do not block S3/S4 on S1 open questions. |

## Non-goals affirmed

- Lab Ops / UI formal reviews skipped this cycle (eng fail-closed).  
- No new customer-facing feature marketing until High closed.

## Decision

**Proceed** through Architecture · Security · QA; implement P0a–P0c after those Accept; hold P0d on open questions Q1–Q2.
