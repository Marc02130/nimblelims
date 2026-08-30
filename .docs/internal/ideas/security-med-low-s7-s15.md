# Idea: Remediate Med/Low security findings (S7–S15)

**Status:** Active — planning packet  
**Date:** 2026-08-21  
**Source audit:** [`.docs/security-review/codebase.md`](../security-review/codebase.md)  
**Depends on:** High S1–S6 **Met** ([security-high-s1-s6](../requirements/security-high-s1-s6.md))  
**Branch:** `security/med-low-s7-s15`

## One-liner

Close remaining **Medium and Low** codebase findings so the product can move from “High Accept” toward a credible production security bar—without reopening S1–S6.

## Why now

High remediations shipped and UAT-stamped. Whole-product verdict remains **Revise** while S7–S15 are Open. Buyers and production checklists will ask about unauthenticated endpoints, upload DoS, published Postgres, and RLS completeness.

## In scope

| ID | Sev | Theme |
|----|-----|--------|
| S7 | Med | Start experiment/run: enforce client/project, not merely sample exists |
| S8 | Med | Cap run `import-file` and SOP uploads (10 MB) |
| S9 | Med | Authenticate `POST /results/validate` |
| S10 | Med | Document that `localStorage` JWT + client `hasPermission` are not AuthZ |
| S11 | Med | FORCE RLS on remaining tenant tables; tighten GUC bind; review `created_by` FOR ALL on containers |
| S12 | Med | Do not publish `:5432` with default password in prod profiles |
| S13 | Low | Tighten verify-email and GET `/roles` `/permissions` |
| S14 | Low | `specimen_biotype_id` / `temperature` cannot be both system-RO display and write-back |
| S15 | Low | Login rate limit / lockout |

## Out of scope

- Reopening S1–S6  
- Full gstack `/cso` deep infra/CI  
- True multi-org redesign  
- Moving JWT to httpOnly cookies (decide separately; S10 is honesty + server AuthZ)

## Success

Each S7–S15 marked **Met** (or **Met with residual** / **Deferred** with written rationale) on codebase.md after phased implement + UAT.
