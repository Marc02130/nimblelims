# Security Review (CSO): Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Resubmitted for review** (tech sketch ready)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Trust boundaries (from sketch)

```
[Lab admin]  CRUD instruments / CRO sources / parsers (config permission)
[Lab user]   set run analysis + source + parser; upload import file
[Backend]    ParserEngine applies parser_config only (no eval/exec)
[Setup]      dry-run engine on test files (same code path)
[Optional P2] AI setup: examples → draft JSON; stats → edge fixtures only
[Publish]    existing promote path (unchanged)
```

## STRIDE checklist (reviewer)

| Threat | Concern | Proposed mitigation | Status |
|--------|---------|---------------------|--------|
| Spoofing | Stolen token edits parsers | Existing auth/JWT | _Review_ |
| Tampering | Malicious column maps | Lab-only config; schema validate; audit | _Review_ |
| Tampering | User scripts / RCE | **Forbid** executable parsers; JSON + engine only | _Review_ |
| Tampering | AI injects unknown keys | `extra=forbid`; allow-listed types | _Review_ |
| Repudiation | Who imported with which parser | Store `parser_id`; audit | _Review_ |
| Info disclosure | Sample files to LLM (P2) | Backend key; minimize PII; lab-only | _Review_ |
| Info disclosure | Cross-client config | Lab-global catalogs; not client-owned | _Review_ |
| DoS | Huge uploads / AI jobs | Size limits; async AI; no AI on import | _Review_ |
| Elevation | Client configures parsers | Block client roles from config CRUD | _Review_ |

## Must-accept conditions (draft)

1. **No user-supplied code execution** for parsers.  
2. Import path **never** calls LLM.  
3. AI setup (P2) is lab-only, confirm-before-save, secrets server-side.  
4. Edge “tests” from AI are fixtures run by **engine**, not AI-judged.  
5. RLS: `lims_run_data` / results stay under existing isolation.  
6. File size/count limits on setup uploads.

## P1 vs P2

| Phase | Security focus |
|-------|----------------|
| **P1** | Config authZ; no RCE; upload limits; audit |
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

_Add findings during review._
