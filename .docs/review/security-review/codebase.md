# Security Review: Current codebase (NimbleLIMS)

**Date:** 2026-08-21  
**Status:** Revise  
**Tech sketch:** n/a — shipped tree, not a feature packet  
**Remediation packet (High S1–S6):** [requirements/security-high-s1-s6.md](../requirements/security-high-s1-s6.md) · [security-review/security-high-s1-s6.md](security-high-s1-s6.md) · branch `security/high-s1-s6` @ `1d3762a` — **Accept**  
**Remediation packet (Med/Low S7–S15):** [requirements/security-med-low-s7-s15.md](../requirements/security-med-low-s7-s15.md) · [security-review/security-med-low-s7-s15.md](security-med-low-s7-s15.md) · branch `security/med-low-s7-s15` — **In review**  
**Related reviews:** [data-parsers-lims-runs](data-parsers-lims-runs.md) · [experiment-template-entries](experiment-template-entries.md) · [process-and-experiment](process-and-experiment.md) · [run-results](run-results.md) · [schema-evolution](schema-evolution.md)  
**Scope:** STRIDE over HEAD `6a21c947`, plus Tobias live UAT of `security/high-s1-s6` through Sec9 @ `1d3762a`. DEEP CSO: skipped.

## Executive summary

The original audit (HEAD `6a21c947`) found the app connected as the Postgres superuser, seeded SHA256 defaults, a JWT env mismatch, body logging, unbound aliquot execute, and write-back by raw `sample_id`.

Tobias live UAT on `security/high-s1-s6` @ `1d3762a`: **S1–S6 Met**, including Sec9 (labtech TC-S5-004 200 after 0062). The High packet is **Accept**. Med/Low **S7–S15** implemented on `security/med-low-s7-s15` (P1–P4 including cookie AuthN); live UAT / merge to `main` still pending. This stamp does **not** make the whole product production-ready until High+Med land and UAT signs off.

## Surface delta

| Surface | Risk after restamp |
|---------|---------------------|
| AuthN | S2 + S3 Met; S10 cookie AuthN Met (P4); S15 lockout Met |
| RLS / `lims_app` | S1 Met; S11 FORCE + contents Met (P3) |
| Save / submit / write-back | S6 Met; S14 allowlist Met |
| Aliquot execute | S5 Met including dest INSERT |
| Experiment/run start | S7 Met (P2 access gate) |
| Parsers / SOP / import | S8 Met (10 MB caps) |
| Frontend token + `hasPermission` | S10 Met (P4 cookie AuthN; `hasPermission` UX only) |
| Compose / logs | S4 Met; S12 prod overlay Met |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | bcrypt + must-change Met. Default JWT refused on production-like start. |
| Tampering | Cohort write-back Met. Aliquot execute Met for labtech. |
| Repudiation | Unchanged |
| Info disclosure | No body logs. Client isolation felt under `lims_app`. |
| DoS | S8 still open |
| Elevation | App role is not Superuser. Seed flags stay dogfood-only. |

## Findings / conditions

| ID | Severity | Status | Condition |
|----|----------|--------|-----------|
| S1 | High | **Met** | `lims_app` not Superuser; Client B 404 on Client A sample. |
| S2 | High | **Met** | bcrypt + must-change + complexity. |
| S3 | High | **Met** | Live refuse default JWT. Forged default-secret token → 401. |
| S4 | High | **Met** | No login body / password in logs. |
| S5 | High | **Met** | Cohort / null / insufficient fail closed. Labtech dest INSERT via 0062. Live TC-S5-004 200. |
| S6 | High | **Met** | Off-cohort upsert 400; write-back cohort only. |
| S7 | Med | **Met (P2+0065)** | Start/link + RLS: lab staff need `project_users` (UAT hold fix; no same-client short-circuit). |
| S8 | Med | **Met (P1)** | Cap `import-file` and SOP uploads (10 MB) + nginx. |
| S9 | Med | **Met (P1)** | Authenticate `POST /results/validate` (`result:enter`\|`review`). |
| S10 | Med | **Met (P4+0066)** | httpOnly cookies + CSRF; JWT `jti` denylist on logout; `hasPermission` UX only. |
| S11 | Med | **Met (P3)** | FORCE RLS on samples/tests/results/projects/batches/containers/client_projects; contents RLS; containers INSERT vs SELECT/UPDATE/DELETE split (`0064`). |
| S12 | Med | **Met (P3+!reset)** | `docker-compose.prod.yml` uses `ports: !reset []` so host `5432` is actually dropped. |
| S13 | Low | **Met (P1)** | verify-email no existence leak; GET `/roles` `/permissions` need manage/config. |
| S14 | Low | **Met (P1)** | biotype/temperature removed from write-back allowlist; remain system display. |
| S15 | Low | **Met (P2)** | Postgres `login_throttle`; lock after N failures (429). |

## Not in scope this review

- Full gstack `/cso` infra / CI / supply chain
- Live pentest or exploit PoCs
- True multi-org
- Accessioning-only packet

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Revise** (whole product until High+Med merge + live UAT; findings Met on remediation branches) |
| **High S1–S6 packet** | **Accept** |
| **Date** | 2026-08-21 |
| **Hold S1–S6 packet?** | **No** |
| **Reviewer** | CSO; Sec9 live by Tobias @ `1d3762a` |
