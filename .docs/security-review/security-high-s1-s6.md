# Security Review: High remediation packet (S1–S6)

**Date:** 2026-08-20  
**Status:** **Accept with conditions**  
**Packet:** Remediation of [codebase.md](codebase.md) High findings  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Tech sketch:** [`.docs/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)  
**UAT:** [`UAT_Scripts/uat-security-high-s1-s6.md`](../../UAT_Scripts/uat-security-high-s1-s6.md) (Tobias, 2026-08-20, Accept with conditions)  
**Scope:** Post-implement stamp of `security/high-s1-s6`. Not a production sign-off. DEEP CSO: skipped.

## Relationship to codebase audit

| Doc | Role |
|-----|------|
| [codebase.md](codebase.md) | Finding list / production block |
| **This packet** | How High closes; implement + UAT stamp |

Do **not** flip all of S1–S6 to Met on codebase.md from this stamp. See status table below.

## UAT status (dogfood)

Observed: `ENVIRONMENT=development`, `ALLOW_INSECURE_DEFAULTS=true`, branch `security/high-s1-s6` @ `7f84b31` (UAT) / `e45d5c5` (this review parent).

| ID | Theme | Status after UAT |
|----|--------|------------------|
| S1 | `lims_app` so RLS applies | **Met with residual.** Isolation smoke passed (Client B 404 on Client A sample). Role exists, not Superuser. Restart-twice / ensure-log line not run. |
| S2 | bcrypt + must-change + complexity | **Met.** `$2b$` hash; complexity 400; old temp 401. |
| S3 | JWT secret; refuse default | **Open for production.** App starts with `SECRET_KEY` set. Live refuse-default (TC-S3-001 step 2, TC-PROD-001) not run. TC-S3-002 N/A on default secret + `ALLOW_INSECURE_DEFAULTS`. Pytest covers refuse. |
| S4 | No request body logging | **Met.** Login logs method/path/status only. |
| S5 | Aliquot execute cohort + null amount + txn | **Refuse Met. Happy path residual.** `source_not_in_cohort`, `source_amount_null`, insufficient amount fail closed. Labtech happy path **500** RLS on `INSERT containers`. Admin retry 200. |
| S6 | Entry upsert/write-back cohort only | **Met.** Off-cohort PUT 400 `sample_not_in_cohort`. Submit write-back S1 only. |

## STRIDE (remediation)

| Threat | Control after UAT |
|--------|-------------------|
| Spoofing | S2 Met. S3 refuse-default not live-proven on this stack. |
| Tampering | S6 Met. S5 refuse Met; labtech execute broken (500). |
| Repudiation | Unchanged this cycle |
| Info disclosure | S4 Met. S1 isolation felt under `lims_app`. |
| DoS | Out of scope (S8 Med) |
| Elevation | S1 removes owner bypass for the app role. Seed gating is flag-dependent. |

## Conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **Sec1** | High | Production must not start with the known-default JWT. Live TC-S3-001 step 2 / TC-PROD-001 still required before any production claim. |
| **Sec2** | High | `ALLOW_INSECURE_DEFAULTS` and `ALLOW_DEV_SEED_USERS` stay unset/false outside explicit dogfood. |
| **Sec3** | High | Login must not log plaintext passwords. **Met** on this UAT. |
| **Sec4** | High | Cohort checks server-side only. **Met** (S6). |
| **Sec5** | High | Aliquot execute: source ∈ cohort **and** `experiment:manage` retained. Refuse **Met**. |
| **Sec9** | High | Lab Technician with `experiment:manage` must complete aliquot execute happy path. `INSERT containers` must be allowed or **403**, never **500**. |
| **Sec6** | Med | Align docs that claimed RLS before S1 (S10 hygiene). |
| **Sec7** | Med | Do not claim production ready until Sec1 + Sec9 close. |
| **Sec8** | High | Must-change-password server-side + complexity. **Met** (Q7 / TC-S2-001). |

## Explicit non-fixes this cycle

S7–S15 remain open on codebase.md. This stamp does not merge `security/high-s1-s6` to `main`.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Date** | 2026-08-20 |
| **Block production?** | **Yes** until Sec1 (live refuse-default) and Sec9 (labtech execute) |
| **Reviewer** | CSO, UAT by Tobias |
| **Deep `/cso`** | skipped |

SECURITY REVIEW: Accept with conditions  
DEEP CSO: skipped
