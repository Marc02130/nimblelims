# Idea: Remediate High security findings (S1–S6)

**Status:** Active — remediation packet  
**Date:** 2026-08-20  
**Source audit:** [`.docs/security-review/codebase.md`](../security-review/codebase.md) (Verdict: **Revise**; block production until S1–S6)  
**Branch:** `security/high-s1-s6`

## One-liner

Close the six **High** findings that defeat AuthN/AuthZ and data integrity so NimbleLIMS can be treated as production-capable for client isolation and lab write paths.

## Why now

The codebase security review (2026-08-20) concluded: RLS does not apply to the app DB role; JWT secret env mismatch leaves the default HMAC key; passwords are unsalted SHA256 with well-known seeded users; request bodies (including logins) are logged; aliquot execute and entry write-back are not cohort-safe.

Until S1–S6 land, **do not treat this stack as production**.

## In scope (High only)

| ID | Theme |
|----|--------|
| S1 | Non-superuser app DB role so RLS/FORCE RLS apply |
| S2 | bcrypt/argon2; no well-known UAT passwords except explicit dev |
| S3 | Single JWT secret env; refuse default |
| S4 | Stop logging request bodies |
| S5 | Aliquot execute: one transaction; source ∈ experiment; refuse null source amount |
| S6 | Write-back/upsert only for experiment cohort samples |

## Out of scope (this cycle)

- Medium/Low from the same audit (S7–S15) — follow-up packet  
- Full gstack `/cso` infra/CI/supply-chain deep dive  
- True multi-org tenancy redesign  
- Frontend-only AuthZ theater (document; S10 stays Med)

## Success

Automated tests prove: forged default JWT fails; SHA256 passwords rejected/migrated; body logs gone; cross-cohort upsert/write-back and unbound aliquot sources fail closed; app queries under RLS-bound role see only allowed rows.
