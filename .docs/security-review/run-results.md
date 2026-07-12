# Security Review (CSO): LimsRun → Results (structured promotion)

**Date:** 2026-07-11  
**Branch:** `run-results`  
**Reviewer:** CSO / Security  
**Idea:** [`.docs/ideas/run-results.md`](../ideas/run-results.md)  
**Tech:** [`.docs/design/run-results.md`](../design/run-results.md)

## Executive Summary

Promotion on **publish** is the right control point: high privilege (`experiment:publish`), intentional, auditable. **Opt-in** is explicit: only when **`lims_runs.analysis_id`** is set—reduces accidental result creation.

Risks: **authorization**, **integrity** (wrong analyte/sample), **client isolation**, **overwrite**.

**Acceptable if:** lab-only; RLS preserved on created results; transactional publish+promote; no client-user path; lineage audited.

## Trust boundary

```
[Lab user] publish run
      │
      ▼
[Backend] validate map + tests + samples (RLS)
      │
      ▼
[Write] results rows + run.status=published
      │
      ▼
[Readers] lab + client users (results only if sample/project access)
```

Instrument JSONB may contain sponsor-sensitive values—same classification as results once promoted.

## STRIDE

### Spoofing
Stolen token with publish rights.  
**Mitigation:** Existing auth; short-lived JWT; no change unique to this feature.

### Tampering
- Malicious/wrong alias maps Client A data to wrong analyte.  
- Promote overwrites reviewed results.  
**Mitigation:** Alias uniqueness; `on_conflict` policy; audit before/after; prefer skip-if-human-edited later.

### Repudiation
Who published and created which results?  
**Mitigation:** `entered_by` = publisher; audit event with run_id, counts, map version; lineage FKs.

### Information disclosure
| Vector | Mitigation |
|--------|------------|
| Result visible across lab clients | Results access must follow **test → sample → project.client_id** RLS (same as manual entry) |
| Preview leaks other clients’ samples | Preview query under same RLS as run data |
| Logs of raw values | Avoid logging full matrices |

### Denial of service
Huge promote on publish blocks API.  
**Mitigation:** Limits, batching, timeout; optional async with care (don’t leave published without results—prefer sync transaction or status “publishing”).

### Elevation of privilege
Publish creates results without separate `result:enter`.  
**Mitigation:** **Decided:** publish alone is enough for this path—document as intentional; do not grant publish lightly.

## Authorization matrix

| Action | Lab admin | Lab tech (publish) | Lab tech (result enter only) | Lab client |
|--------|-----------|--------------------|------------------------------|------------|
| Configure promotion map / aliases | Yes (config) | No / limited | No | **No** |
| Import run data | Yes | Yes | Yes | **No** |
| Start run without analysis (ack non-reportable) | Yes | Yes | Yes | **No** |
| Publish + promote (analysis set) | Yes | Yes if **publish** perm (implies result write) | **No** | **No** |
| View structured results | Yes | Yes | Yes | **Own client only** |

Aligns Decision **#9** (lab edits data) and **#7** (client sees own samples/results).

## Data integrity requirements

1. **Transactional** publish + promote (all or nothing).  
2. **Idempotent** promote key: `(test_id, analyte_id)` and/or source data row.  
3. **No silent drop** of required analytes if template marks them required—fail publish.  
4. **Alias table** uniqueness prevents cross-analyte collision.  
5. Do not write untrusted free-form keys into `custom_attributes` without field validation.

## Checklist before GA

- [ ] RLS tests: client A cannot read results from promote of client B samples  
- [ ] Permission tests: publish without result rights  
- [ ] Failure mid-promote rolls back status  
- [ ] Audit log completeness  
- [ ] Alias conflict admin validation  

## Residual risk

Scientifically wrong values in instrument file still become “official” results on publish—**lab responsibility**. Mitigate with preview and QC culture, not security controls alone.

## Recommendations

1. Gate promote on **publish** only (decided).  
2. Require explicit permissions model.  
3. First-class lineage columns—not JSONB bag.  
4. Strict test prerequisite reduces orphan/wrong-client writes.  

**CSO verdict: Acceptable** with transactional integrity + RLS + lab-only publish path.

---

Related: [ceo](../ceo-review/run-results.md) · [ui-review](../ui-review/run-results.md) · [tech](../design/run-results.md)
