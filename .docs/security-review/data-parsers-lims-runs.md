# Security Review (CSO): Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Resubmitted:** 2026-07-19  
**Status:** **Resubmitted for security review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes:** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Ask of security (this pass)

Accept or condition **P1** and note **P2** AI requirements. Product locks below are fixed for this cycle.

## Trust boundaries

```
[Lab admin]  CRUD instrument types/instances, CRO sources, data_parsers (config:edit)
[Lab user]   set run analysis (required); import with instrument|CRO + parser version
[Backend]    ParserEngine applies parser_config only (no eval/exec)
[Setup]      dry-run engine on test files (same code path); caps 10 files / 10 MB
[Optional P2] AI setup: examples → draft JSON; stats → edge fixtures only
[Publish]    existing promote path (analysis always present)
```

## Product locks with security impact

| Lock | Security note |
|------|----------------|
| **No executable parsers** | JSONB instructions + engine only |
| **Schema-first ParserConfig (Q1)** | `extra=forbid`; validate all writers including AI |
| **AI setup-only (P2)** | Import path never calls LLM |
| **config:edit** | Clients cannot mutate catalogs/parsers |
| **Versioned parsers** | Import stores version `parser_id` (lineage/audit); no config snapshot blob |
| **Setup caps 10 / 10 MB** | DoS bound on uploads |
| **All-clean activate** | Reduces bad production parsers (integrity) |
| **Lab-global catalogs** | No multi-tenant segregation this cycle |
| **analysis_id required** | Clearer promote/authz story |

## STRIDE checklist (reviewer)

| Threat | Concern | Proposed mitigation | Status |
|--------|---------|---------------------|--------|
| Spoofing | Stolen token edits parsers | Existing auth/JWT; `config:edit` | _Review_ |
| Tampering | Malicious column maps | Lab-only config; schema validate; audit | _Review_ |
| Tampering | User scripts / RCE | **Forbid** executable parsers | _Review_ |
| Tampering | AI injects unknown keys | `extra=forbid`; allow-listed types | _Review_ |
| Repudiation | Who imported with which parser | Store version `parser_id` on import; audit | _Review_ |
| Info disclosure | Sample files to LLM (P2) | Backend key; minimize PII; lab-only | _Review_ |
| Info disclosure | Cross-client config | Lab-global; not client-owned | _Review_ |
| DoS | Huge uploads / AI jobs | **10 files / 10 MB**; async AI; no AI on import | _Review_ |
| Elevation | Client configures parsers | Block client roles from config CRUD | _Review_ |

## Must-accept conditions (draft)

1. **No user-supplied code execution** for parsers.  
2. Import path **never** calls LLM.  
3. AI setup (P2) is lab-only, confirm-before-save, secrets server-side.  
4. Edge tests from AI are fixtures run by **engine**, not AI-judged.  
5. RLS: run data / results under existing isolation; catalogs lab-config only.  
6. File size/count limits enforced server-side (**10 / 10 MB**).  
7. Activate only after engine tests pass (**all** hard-error-free).  

## P1 vs P2

| Phase | Security focus |
|-------|----------------|
| **P1** | Config authZ; no RCE; upload limits; audit; schema validation |
| **P2** | LLM data handling; prompt injection; no trust of model for pass/fail |

## Verdict (fill in)

| Field | Value |
|-------|--------|
| **Verdict** | _Pending_ (Accept / Accept with conditions / Reject) |
| **Blockers for P1** | |
| **Blockers for P2 (AI)** | |
| **Reviewer** | |
| **Date completed** | |

## Notes

_Resubmitted 2026-07-19: Q1 accepted, 10b/10c locked, data_parsers rename, versioning, analysis required, M2M._
