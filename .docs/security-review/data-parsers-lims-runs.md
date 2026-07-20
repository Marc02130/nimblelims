# Security Review (CSO): Data parsers + LimsRun source/parser lineage

**Date:** 2026-07-12  
**Resubmitted:** 2026-07-19  
**Verdict date:** 2026-07-19  
**Status:** **Accepted with conditions** (P1 clear; P2 conditional)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [`.docs/tech-sketch/data-parsers-lims-runs.md`](../tech-sketch/data-parsers-lims-runs.md)  
**Schema changes:** [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

## Trust boundaries (accepted)

```
[Lab admin]  CRUD catalogs + data_parsers (config:edit)
[Lab user]   run analysis required; import file + instrument|CRO + parser version
[Backend]    ParserEngine only — no eval/exec of user content
[Setup]      same engine; server-enforced 10 files / 10 MB
[P2]         AI drafts JSON only; human save; never on import
[Publish]    existing promote (analysis always set)
```

## STRIDE results

| Threat | Mitigation | Status |
|--------|------------|--------|
| Spoofing | JWT + existing auth | **OK** for P1 |
| Tampering (maps) | `config:edit` only; schema validate; audit | **OK** |
| RCE | Forbid executable parsers; JSON + engine only | **OK — must-test** |
| AI key injection | `extra=forbid`; validate AI output | **OK for P2 design** |
| Repudiation | version `parser_id` on import; activate audit | **OK** |
| Info disclosure (LLM) | P2 only; lab roles; minimize PII | **P2 condition** |
| Cross-client config | Lab-global catalogs; not client-owned | **OK** (multi-tenant later) |
| DoS | **10 files / 10 MB** server-side; no AI on import | **OK — must-enforce** |
| Elevation | Clients blocked from config CRUD | **OK** |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** |
| **Blockers for P1** | **None** if S1–S5 implemented |
| **Blockers for P2 (AI)** | S6–S8 before P2 ships |
| **Reviewer** | Security (CSO posture) |
| **Date completed** | 2026-07-19 |

### P1 conditions (implement with feature)

| # | Condition |
|---|-----------|
| S1 | **No** user code/snippets in `parser_config` — Pydantic allow-list only; reject unknown keys. |
| S2 | Import and setup parse paths **never** call LLM (assert in tests / code review). |
| S3 | Upload limits **enforced server-side**: max 10 files, max 10 MB each; reject oversized before storage. |
| S4 | **`config:edit`** required for catalog/parser mutate; client roles cannot CRUD. |
| S5 | Audit: create/activate parser version; import with `parser_id` + actor + timestamp. |

### P2 conditions (before AI setup ships)

| # | Condition |
|---|-----------|
| S6 | LLM credentials only on server; never exposed to client. |
| S7 | Treat model output as untrusted: validate ParserConfig; engine judges tests — never AI pass/fail alone. |
| S8 | Document/minimize PII in example files sent to LLM; lab-only access to setup + draft jobs. |

## Notes

Design posture is sound for a deterministic import LIMS feature. P1 is security-clear with standard authZ/validation/limits. P2 is a separate gate.
