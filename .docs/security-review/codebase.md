# Security Review: Current codebase (NimbleLIMS)

**Date:** 2026-08-20  
**Status:** Revise  
**Tech sketch:** n/a — shipped tree, not a feature packet  
**Related reviews:** [data-parsers-lims-runs](data-parsers-lims-runs.md) · [experiment-template-entries](experiment-template-entries.md) · [process-and-experiment](process-and-experiment.md) · [run-results](run-results.md) · [schema-evolution](schema-evolution.md)  
**Scope:** Feature packet (STRIDE) over HEAD `6a21c947` (2026-08-20 17:27 ET). DEEP CSO: skipped (gstack skill present, `/cso` not run).

## Executive summary

NimbleLIMS has real RBAC on most mutating FastAPI routes, a CSV parser engine (no user code exec), and several entry-path controls that match the 2026-08-10 packet (submit-only write-back, sample-scoped grid from experiment membership, Client denied `experiment:manage`). Those are not enough for the product’s isolation claim.

The application database user is the PostgreSQL Docker superuser (`lims_user`). RLS — including `FORCE ROW LEVEL SECURITY` on later ELN tables — does not apply to FastAPI. Migrations always seed well-known passwords hashed with unsalted SHA256. Docker Compose sets `JWT_SECRET_KEY` while the app reads `SECRET_KEY`, so the signing key stays the hardcoded default. Request middleware logs login bodies.

Until S1–S6 are fixed, do not treat this stack as production or as enforcing client isolation.

## Surface delta

| Surface | Risk |
|---------|------|
| AuthN (JWT, SHA256, seeded users) | Forged/guessed admin |
| RLS / `is_admin()` / FORCE RLS | Not felt by app role |
| Entry grid/export | Cohort OK for sample-scoped; upsert IDs not constrained |
| Save / submit / write-back | Save OK; submit can miss cohort |
| Aliquot execute | Partial commit; unbound sources |
| Experiment/run start | No client check |
| Parsers / SOP / import | Engine OK; run/SOP size uncapped |
| Frontend token + `hasPermission` | UI-only |
| Compose / logs | Defaults and password logs |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | JWT + DB lookup; defeated by default HMAC secret and SHA256+seeded accounts |
| Tampering | RBAC; write-back allowlist; execute/write-back not cohort-transactional |
| Repudiation | `modified_by` / `write_back_previous` / config timestamps; no submit/execute audit table |
| Info disclosure | RLS bypassed for app; body logs; unauthenticated `/results/validate` |
| DoS | Parser setup capped; run import and SOP not |
| Elevation | Client lacks `experiment:manage`; System client = full `has_project_access`; `config:edit` can mint admins |

## Findings / conditions

| ID | Severity | Condition |
|----|----------|-----------|
| S1 | High | App must use a non-superuser, non-owner DB role so RLS/FORCE RLS apply. |
| S2 | High | bcrypt/argon2; do not seed well-known UAT passwords except explicit dev. |
| S3 | High | Read one JWT secret env; refuse default. Compose sets `JWT_SECRET_KEY`; app reads `SECRET_KEY`. |
| S4 | High | Stop logging request bodies. |
| S5 | High | Aliquot execute: one transaction; source ∈ experiment; refuse null source amount. |
| S6 | High | Write-back/upsert only for experiment cohort samples. |
| S7 | Med | Start experiment/run: enforce client/project, not merely sample exists. |
| S8 | Med | Cap `import-file` and SOP uploads (10 MB). |
| S9 | Med | Authenticate `POST /results/validate`. |
| S10 | Med | `localStorage` JWT + client `hasPermission` are not AuthZ; comments must not claim RLS works until S1. |
| S11 | Med | FORCE RLS on samples/tests/results/…; RLS on `contents`; replace `is_admin() OR true`; `SET LOCAL` + bind GUC. |
| S12 | Med | Do not publish `:5432` with default password; `start.sh` must use `DATABASE_URL`. |
| S13 | Low | Tighten verify-email and GET `/roles` `/permissions`. |
| S14 | Low | `specimen_biotype_id` / `temperature` cannot be both system-RO and write-back. |
| S15 | Low | Login rate limit / lockout. |

## Not in scope this review

- Full gstack `/cso` infra / CI / supply chain
- Live pentest or exploit PoCs
- True multi-org
- Accessioning-only packet
- Whether `experiment:publish` is granted in a given live DB (route is fail-closed)

## Prior packet conditions still open in shipped code

| Packet | ID | Status in HEAD |
|--------|-----|----------------|
| experiment-template-entries | S1 grid/export cohort | **Mostly met** for sample-scoped (`_experiment_sample_ids`). **Open** for upsert of arbitrary `sample_id`. |
| experiment-template-entries | S2 write-back allowlist / no identity | **Mostly met** (`client_sample_id` excluded). **Open:** `specimen_biotype_id` in both system and allowlist. |
| experiment-template-entries | S3 write-back only on submit | **Met** on HTTP save (`apply_write_back=False`). |
| experiment-template-entries | S4 aliquot txn / authz / amount | **Open** (partial commit, unbound source, null amount). |
| experiment-template-entries | S5 export ACL | **Met** (`experiment:manage`; Client cannot call). |
| experiment-template-entries | S6 write-back map = experiment:manage | **Met**. |
| experiment-template-entries | S7 audit submit/execute | **Partial** (config + `write_back_previous`; no event table). |
| data-parsers-lims-runs | S1 no user code in parser_config | **Met** (`ParserConfig` `extra=forbid`, CSV engine). |
| data-parsers-lims-runs | S2 no LLM on import | **Met** for run import; SOP parse is a separate LLM path. |
| data-parsers-lims-runs | S3 10 files / 10 MB | **Met** on setup/test; **open** on run `import-file`. |
| data-parsers-lims-runs | S4 `config:edit` for catalog mutate | **Met**; list is any authenticated user. |
| data-parsers-lims-runs | S5 parser audit | **Partial**. |
| data-parsers-lims-runs | S6–S8 P2 AI | SOP uses server `ANTHROPIC_API_KEY` (S6 direction OK); not a full P2 close. |
| process-and-experiment | RLS on new ELN tables | Policies + FORCE exist; **ineffective** for app superuser (this S1). |
| run-results | RLS + lab-only publish | Publish permission checked; **RLS bypassed** (S1). `experiment:publish` not found in role-seed migrations (fail-closed). |
| schema-evolution | RLS on new fields / schema admin blast | FieldDefinitions mutate is `config:edit`; isolation still S1. |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Revise** |
| **Date** | 2026-08-20 |
| **Block production?** | **Yes** until S1–S6 |
| **Reviewer** | Security (CSO posture), HEAD `6a21c947` |
