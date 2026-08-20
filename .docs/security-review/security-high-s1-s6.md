# Security Review: High remediation packet (S1–S6)

**Date:** 2026-08-20  
**Status:** **Accept with conditions**  
**Packet:** Remediation of [codebase.md](codebase.md) High findings  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Tech sketch:** [`.docs/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)

## Relationship to codebase audit

| Doc | Role |
|-----|------|
| [codebase.md](codebase.md) | Finding list / production block (Revise until S1–S6) |
| **This packet** | How we close High; implement gate |

After ship, update **codebase.md** finding table: S1–S6 → Met (or Met with residual).

## STRIDE (remediation)

| Threat | Remediation |
|--------|-------------|
| Spoofing | S2 bcrypt; S3 refuse default JWT |
| Tampering | S5 txn + cohort; S6 cohort write-back |
| Repudiation | Unchanged this cycle (no new audit table) |
| Info disclosure | S4 no body logs; S1 RLS effective |
| DoS | Out of scope (S8 Med) |
| Elevation | S1 removes owner bypass; seed gating reduces default admin abuse |

## Conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **Sec1** | High | Production/`ENVIRONMENT=production` must not start with known-default JWT even if compose mis-set. |
| **Sec2** | High | `ALLOW_INSECURE_DEFAULTS` and `ALLOW_DEV_SEED_USERS` must default **unset/false** in production docs and any prod compose profile. |
| **Sec3** | High | Login upgrade path must not log plaintext passwords. |
| **Sec4** | High | Cohort checks server-side only — never trust client “sample on experiment” UI state. |
| **Sec5** | High | Aliquot execute authZ: source ∈ cohort **and** existing RBAC (`experiment:manage` or current execute permission) retained. |
| **Sec6** | Med | After S1, grep docs/comments for “RLS enforces” and align language (S10 hygiene). |
| **Sec7** | Med | Do not claim “production ready” in README until UAT for this stem passes. |

## Explicit non-fixes this cycle

S7–S15 remain open on codebase.md. Do not mark codebase audit **Accept** until High Met; Med may remain Revise/open.

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** Sec1–Sec7 |
| **Block production until** | S1–S6 implemented + tests + UAT |
| **Deep `/cso`** | Still optional follow-up (infra/CI); not a substitute for S1–S6 |

## Implement gate

**Cleared for P0a–P0c** after CEO/Arch/QA also Accept.  
**P0d** additionally needs open-questions Q1–Q2.
