# Open questions: security-high-s1-s6

**Status:** Living decision log  
**Date:** 2026-08-20  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)  
**Blocks:** P0d (S1) until Q1–Q2 decided; P0a–P0c may start after review Accept

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| Q1 | How to bootstrap `lims_app` password in Docker — Alembic with env, `init.sql`, or compose `POST_INIT`? | **Open** | P0d | Prefer: create role in Alembic reading `LIMS_APP_PASSWORD` from env at migrate time; document required env. Alternative: db Dockerfile init. | | Eng + Arch |
| Q2 | Production: delete well-known seed users, disable them, or force password reset on first deploy? | **Open** | P0d / prod cutover | Provisional lean: **no seed users in production images**; local/UAT only when `ALLOW_DEV_SEED_USERS=true`. | | Product + Security |
| Q3 | May `ENVIRONMENT=development` alone allow default JWT, or require explicit `ALLOW_INSECURE_DEFAULTS=true`? | **Decided (provisional)** | P0a | **Require both** `ENVIRONMENT=development` (or `test`) **and** `ALLOW_INSECURE_DEFAULTS=true` for default secret. Compose local sets both. Production never sets the flag. | 2026-08-20 | Security |
| Q4 | bcrypt vs argon2? | **Decided (provisional)** | P0b | **bcrypt** — README/UAT/tests already assume bcrypt (`$2b$`). | 2026-08-20 | Eng |
| Q5 | S5 refuse-null amount: confirm product OK to fail execute when contents.amount is null? | **Decided (provisional)** | P0c | **Yes** — fail closed; lab must set tracked amount before execute. Aligns audit S5. | 2026-08-20 | Product / Security |
| Q6 | Include any Med (S7–S12) quick wins in this branch? | **Decided** | — | **No** — High only; Med follow-up packet. Exception: docs comments that falsely claim RLS works (S10 doc hygiene) may update with S1. | 2026-08-20 | CEO |

## Gate rule

- **P0a–P0c:** unblocked once CEO · Arch · Security · QA Accept (with conditions OK).  
- **P0d:** blocked on **Q1**, **Q2**.  
- New blockers discovered in implement → add rows here; pause that phase.
