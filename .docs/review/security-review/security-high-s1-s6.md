# Security Review: High remediation packet (S1–S6)

**Date:** 2026-08-21  
**Status:** **Accept**  
**Packet:** Remediation of [codebase.md](codebase.md) High findings  
**Requirements:** [`.docs-review/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Tech sketch:** [`.docs-review/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)  
**UAT:** [`UAT_Scripts/uat-security-high-s1-s6.md`](../../UAT_Scripts/uat-security-high-s1-s6.md)  
**Scope:** `security/high-s1-s6` @ `1d3762a` (0062 + live TC-S5-004). Not a product-wide production sign-off. DEEP CSO: skipped.

## Relationship to codebase audit

| Doc | Role |
|-----|------|
| [codebase.md](codebase.md) | Finding list; whole-product still Revise (S7–S15) |
| **This packet** | High S1–S6 closed |

## UAT status

| ID | Theme | Status |
|----|--------|--------|
| S1 | `lims_app` so RLS applies | **Met.** |
| S2 | bcrypt + must-change + complexity | **Met.** |
| S3 | JWT secret; refuse default | **Met.** |
| S4 | No request body logging | **Met.** |
| S5 | Aliquot execute cohort + null + txn + dest INSERT | **Met.** Live TC-S5-004 as `uat-labtech`: 200, 50→35, dest 15, parent set. S5-001 still 400 `source_not_in_cohort`. |
| S6 | Entry upsert/write-back cohort only | **Met.** |

## STRIDE (remediation)

| Threat | Control |
|--------|---------|
| Spoofing | S2 + S3 Met |
| Tampering | S5 + S6 Met |
| Repudiation | Unchanged this cycle |
| Info disclosure | S1 + S4 Met |
| DoS | Out of scope (S8 Med) |
| Elevation | App role not Superuser. Seed flags dogfood-only (Sec2). |

## Conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **Sec1** | High | Refuse default JWT. **Met.** |
| **Sec2** | High | Insecure/dev-seed flags unset outside dogfood. Standing hygiene. |
| **Sec3** | High | No password body logs. **Met.** |
| **Sec4** | High | Cohort checks server-side. **Met.** |
| **Sec5** | High | Execute cohort + `experiment:manage`. **Met.** |
| **Sec9** | High | Labtech execute happy path. **Met** @ `1d3762a` / 0062. Live TC-S5-004 Pass. |
| **Sec8** | High | Must-change + complexity. **Met.** |
| **Sec6** | Med | Align docs that claimed RLS before S1. |
| **Sec7** | Med | Do not call the whole product production-ready (S7–S15 still open). |
| **Sec10** | Med | `0062` uses `created_by = current_user_id()` on **FOR ALL**. Prefer INSERT WITH CHECK only; keep SELECT/UPDATE/DELETE on project/contents. Follow-on, not a hold. |

## Explicit non-fixes this cycle

S7–S15 remain open on codebase.md. This stamp does not merge `security/high-s1-s6` to `main`.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept** |
| **Date** | 2026-08-21 |
| **Hold S1–S6 packet?** | **No** |
| **Reviewer** | CSO; live Sec9 by Tobias @ `1d3762a` |
| **Deep `/cso`** | skipped |

SECURITY REVIEW: Accept  
DEEP CSO: skipped
