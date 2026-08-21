# Security Review: High remediation packet (S1–S6)

**Date:** 2026-08-21  
**Status:** **Accept with conditions**  
**Packet:** Remediation of [codebase.md](codebase.md) High findings  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Tech sketch:** [`.docs/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)  
**UAT:** [`UAT_Scripts/uat-security-high-s1-s6.md`](../../UAT_Scripts/uat-security-high-s1-s6.md) ([PR 41](https://github.com/Marc02130/nimblelims/pull/41), Tobias restamp, Accept with conditions)  
**Scope:** Post-implement stamp of `security/high-s1-s6` @ `d97e756`. Not a product-wide production sign-off. DEEP CSO: skipped.

## Relationship to codebase audit

| Doc | Role |
|-----|------|
| [codebase.md](codebase.md) | Finding list |
| **This packet** | How High closes; implement + UAT stamp |

## UAT status (Tobias live + pytest, 2026-08-21)

| ID | Theme | Status |
|----|--------|--------|
| S1 | `lims_app` so RLS applies | **Met.** Isolation passed. Restart-twice confirmed (TC-S1-001). |
| S2 | bcrypt + must-change + complexity | **Met.** |
| S3 | JWT secret; refuse default | **Met.** TC-S3-001 step 2: backend Exited 1 on default JWT. TC-S3-002: forged default-secret token → 401. TC-PROD-001 passed. Pytest complement 24 passed. |
| S4 | No request body logging | **Met.** |
| S5 | Aliquot execute cohort + null amount + txn | **Refuse Met.** Labtech happy path **500** RLS on `INSERT containers` (Sec9). Admin execute 200. |
| S6 | Entry upsert/write-back cohort only | **Met.** |

`create_admin.py` ImportError if run as a script on this image is a quality nit, fail-closed, not a High.

## STRIDE (remediation)

| Threat | Control after restamp |
|--------|------------------------|
| Spoofing | S2 Met. S3 refuse-default proven live. |
| Tampering | S6 Met. S5 refuse Met; labtech execute 500 (Sec9). |
| Repudiation | Unchanged this cycle |
| Info disclosure | S4 Met. S1 isolation felt under `lims_app`. |
| DoS | Out of scope (S8 Med) |
| Elevation | App role is not Superuser. Seed flags stay dogfood-only (Sec2). |

## Conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **Sec1** | High | Production must not start with the known-default JWT. **Met** (live refuse + forged-token 401 + TC-PROD-001). |
| **Sec2** | High | `ALLOW_INSECURE_DEFAULTS` and `ALLOW_DEV_SEED_USERS` stay unset/false outside explicit dogfood. |
| **Sec3** | High | Login must not log plaintext passwords. **Met.** |
| **Sec4** | High | Cohort checks server-side only. **Met** (S6). |
| **Sec5** | High | Aliquot execute: source ∈ cohort and `experiment:manage` retained. Refuse **Met.** |
| **Sec9** | High | Lab Technician with `experiment:manage` must complete aliquot execute happy path. `INSERT containers` must be allowed or **403**, never **500**. Fail-closed today. Not holding this packet. |
| **Sec6** | Med | Align docs that claimed RLS before S1 (S10 hygiene). |
| **Sec7** | Med | Do not claim the whole product production-ready until Sec9 and remaining codebase Med (S7–S15) are closed. |
| **Sec8** | High | Must-change-password server-side + complexity. **Met.** |

## Explicit non-fixes this cycle

S7–S15 remain open on codebase.md. This stamp does not merge `security/high-s1-s6` to `main`.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Date** | 2026-08-21 |
| **Hold S1–S6 packet?** | **No.** Residual is Sec9 only. |
| **Reviewer** | CSO, UAT by Tobias @ `d97e756` / [PR 41](https://github.com/Marc02130/nimblelims/pull/41) |
| **Deep `/cso`** | skipped |

SECURITY REVIEW: Accept with conditions  
DEEP CSO: skipped
