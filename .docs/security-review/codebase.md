# Security Review: Current codebase (NimbleLIMS)

**Date:** 2026-08-21  
**Status:** Revise  
**Tech sketch:** n/a — shipped tree, not a feature packet  
**Remediation packet (High S1–S6):** [requirements/security-high-s1-s6.md](../requirements/security-high-s1-s6.md) · [security-review/security-high-s1-s6.md](security-high-s1-s6.md) · branch `security/high-s1-s6` @ `d97e756`  
**Related reviews:** [data-parsers-lims-runs](data-parsers-lims-runs.md) · [experiment-template-entries](experiment-template-entries.md) · [process-and-experiment](process-and-experiment.md) · [run-results](run-results.md) · [schema-evolution](schema-evolution.md)  
**Scope:** Feature packet (STRIDE) over HEAD `6a21c947`, plus Tobias live UAT of `security/high-s1-s6` @ `d97e756` ([PR 41](https://github.com/Marc02130/nimblelims/pull/41)). DEEP CSO: skipped.

## Executive summary

The original audit (HEAD `6a21c947`) found the app connected as the Postgres superuser, seeded SHA256 defaults, a JWT env mismatch, body logging, unbound aliquot execute, and write-back by raw `sample_id`.

Tobias live UAT + pytest (2026-08-21) on `security/high-s1-s6` @ `d97e756`: **S1, S2, S3, S4, S6 Met.** **S5 refuse Met.** Residual **Sec9:** labtech execute 500 on `INSERT containers` (fail-closed, not 403). Admin execute works.

The High S1–S6 packet is **Accept with conditions** (Sec9 only). This stamp does **not** merge the remediation to `main` and does not make the whole product production-ready. S7–S15 stay open.

## Surface delta

| Surface | Risk after restamp |
|---------|---------------------|
| AuthN (JWT, bcrypt, must-change) | S2 Met. S3 refuse-default proven live. |
| RLS / `lims_app` | Isolation held. Restart-twice confirmed. |
| Entry grid/export | Unchanged this cycle |
| Save / submit / write-back | S6 Met (cohort) |
| Aliquot execute | Refuse Met. Labtech execute 500 on dest container (Sec9). |
| Experiment/run start | S7 still open |
| Parsers / SOP / import | S8 still open |
| Frontend token + `hasPermission` | S10 still open |
| Compose / logs | S4 Met. S12 still open. |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | bcrypt + must-change Met. Default JWT refused on production-like start. |
| Tampering | Cohort write-back Met. Aliquot refuse Met; labtech execute broken (Sec9). |
| Repudiation | Unchanged |
| Info disclosure | No body logs. Client isolation felt under `lims_app`. |
| DoS | S8 still open |
| Elevation | App role is not Superuser. Seed flags stay dogfood-only. |

## Findings / conditions

| ID | Severity | Status | Condition |
|----|----------|--------|-----------|
| S1 | High | **Met** | `lims_app` not Superuser; Client B 404 on Client A sample. Restart-twice confirmed. |
| S2 | High | **Met** | bcrypt + must-change + complexity. |
| S3 | High | **Met** | Live refuse default JWT (Exited 1). Forged default-secret token → 401. TC-PROD-001 passed. |
| S4 | High | **Met** | No login body / password in logs. |
| S5 | High | **Met** | Cohort / null amount / insufficient fail closed. Sec9: containers RLS allows `created_by = current_user_id()` (migration `0062`); RLS denials map to 403. |
| S6 | High | **Met** | Off-cohort upsert 400; write-back cohort only. |
| S7 | Med | Open | Start experiment/run: enforce client/project. |
| S8 | Med | Open | Cap `import-file` and SOP uploads (10 MB). |
| S9 | Med | Open | Authenticate `POST /results/validate`. |
| S10 | Med | Open | `localStorage` JWT + client `hasPermission` are not AuthZ. |
| S11 | Med | Open | FORCE RLS on remaining tenant tables; `SET LOCAL` + bind GUC. |
| S12 | Med | Open | Do not publish `:5432` with default password. |
| S13 | Low | Open | Tighten verify-email and GET `/roles` `/permissions`. |
| S14 | Low | Open | `specimen_biotype_id` / `temperature` cannot be both system-RO and write-back. |
| S15 | Low | Open | Login rate limit / lockout. |

## Not in scope this review

- Full gstack `/cso` infra / CI / supply chain
- Live pentest or exploit PoCs
- True multi-org
- Accessioning-only packet
- Whether `experiment:publish` is granted in a given live DB (route is fail-closed)

## Prior packet conditions still open in shipped code

| Packet | ID | Status |
|--------|-----|--------|
| experiment-template-entries | S1 grid/export cohort | **Mostly met** sample-scoped. Upsert of arbitrary `sample_id` **Met** on remediation branch (this S6). |
| experiment-template-entries | S2 write-back allowlist | **Mostly met.** `specimen_biotype_id` dual-list still this S14. |
| experiment-template-entries | S3 write-back only on submit | **Met.** |
| experiment-template-entries | S4 aliquot txn / authz / amount | **Refuse Met** on remediation branch. Happy path residual Sec9. |
| experiment-template-entries | S5 export ACL | **Met.** |
| experiment-template-entries | S6 write-back map = experiment:manage | **Met.** |
| experiment-template-entries | S7 audit submit/execute | **Partial.** |
| data-parsers-lims-runs | S1–S2, S4 | **Met** (unchanged). |
| data-parsers-lims-runs | S3 10 MB | **Open** on run `import-file`. |
| process-and-experiment / run-results / schema-evolution | RLS | **Improved** under `lims_app` (this S1). S11 residuals remain. |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Revise** (whole product; Med/Low + Sec9 remain) |
| **High S1–S6 packet** | **Accept with conditions** (Sec9 only) |
| **Date** | 2026-08-21 |
| **Hold S1–S6 packet?** | **No** |
| **Reviewer** | CSO, UAT by Tobias @ `d97e756` / [PR 41](https://github.com/Marc02130/nimblelims/pull/41) |
