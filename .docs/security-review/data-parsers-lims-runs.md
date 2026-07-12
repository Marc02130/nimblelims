# Security Review (CSO): Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Status:** **Awaiting review**  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)

## Trust boundaries (proposed)

```
[Lab admin]  CRUD instruments / CRO sources / parsers (config permission)
[Lab user]   set run analysis + source + parser; upload import file
[Backend]    apply parser_config only (no eval/exec of user code)
[Optional]   AI setup job: file sample + catalog context → draft JSON only
[Publish]    existing promote path (unchanged)
```

## STRIDE checklist (reviewer)

| Threat | Concern | Proposed mitigation | Status |
|--------|---------|---------------------|--------|
| Spoofing | Stolen token edits parsers | Existing auth/JWT | _Review_ |
| Tampering | Malicious parser maps wrong columns | Lab-only config; validate JSON schema; audit | _Review_ |
| Tampering | User scripts / RCE | **Forbid** executable parsers; JSON instructions only | _Review_ |
| Repudiation | Who imported with which parser | Store parser_id; audit import + config changes | _Review_ |
| Info disclosure | Sample file to LLM (P2) | Backend-only key; minimize PII in prompt; no client key | _Review_ |
| Info disclosure | Cross-client parsers | Lab-global config; not client-owned (confirm) | _Review_ |
| DoS | Huge file / AI job | Size limits; async job; no AI on import | _Review_ |
| Elevation | Client user configures parsers | Block client roles from config CRUD | _Review_ |

## Must-accept conditions (draft)

1. **No user-supplied code execution** for parsers.  
2. Import path never calls LLM.  
3. AI setup (if any) is lab-only, confirm-before-save, secrets server-side.  
4. RLS: created `lims_run_data` / results remain under existing project isolation.  
5. Parser/instrument/CRO catalogs not writable by lab client users.

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
