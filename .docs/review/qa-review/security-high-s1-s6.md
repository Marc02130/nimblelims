# QA Review: High security remediation (S1–S6)

**Date:** 2026-08-20  
**Status:** **Accept with conditions**  
**Reviewer:** Testing / QA Lead (packet)  
**Requirements:** [`.docs/review/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Tech sketch:** [`.docs/review/tech-sketch/security-high-s1-s6.md`](../tech-sketch/security-high-s1-s6.md)

## Testability assessment

| Area | Testable? | Notes |
|------|-----------|-------|
| S3 default JWT refuse | Yes | Startup/config unit tests with env matrix |
| S4 no body log | Yes | Assert logger not called with body / middleware unit test |
| S2 bcrypt + upgrade | Yes | Extend `test_auth.py`; SHA256 hash login then assert `$2b$` stored |
| S6 cohort upsert | Yes | Create experiment cohort A; PUT values for sample B → 400 |
| S5 aliquot | Yes | Null amount; non-cohort source; forced failure mid-batch → row counts unchanged |
| S1 RLS app role | Yes | Extend `test_rls_*` connecting as `lims_app` + GUC |

## Conditions (must land with implement)

| ID | Condition |
|----|-----------|
| **Q1** | Create **`UAT_Scripts/uat-security-high-s1-s6.md`** with steps for: login after bcrypt; reject forged token signed with old default (if applicable); confirm logs lack password on login; entry write with foreign sample_id fails; aliquot null amount fails; (P0d) second client cannot read first client’s samples via API as lab user. |
| **Q2** | Implement prompt / PR must update manuals: `backend-auth.md`, README security bullets, `.env.example`. |
| **Q3** | Negative-path UAT required (not only happy path). |
| **Q4** | CI/pytest: at least one test per High ID (S1–S6) before merge. |
| **Q5** | Document local flags `ALLOW_INSECURE_DEFAULTS` + `ALLOW_DEV_SEED_USERS` in UAT preconditions so dogfood still works. |
| **Q6** | Regression: existing entry save/submit happy path for **cohort** samples still passes. |

## UAT personas

| Persona | Focus |
|---------|--------|
| Lab tech | Login; cannot abuse write-back; aliquot fail messages understandable |
| Admin / lab manager | Compose env; no default secret in prod-like run |
| Second client user (P0d) | Isolation visible in UI/API |

## Verdict

**Accept with conditions Q1–Q6.** Packet is testable; security work must not merge without UAT script + automated negatives.

## Implement gate note

QA Accept here is **testability**. Post-implement **UAT pass** remains required before merge to `main` (process).
