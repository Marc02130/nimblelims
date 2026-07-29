# Security Review: Experiment template entries

**Date:** 2026-07-29  
**Verdict date:** 2026-07-29  
**Status:** **Accepted with conditions**  
**Mode:** Feature-scoped (plan review, not full /cso infra scan)  
**Tech sketch:** [`.docs/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)  
**Parent context:** [security-review/process-and-experiment.md](./process-and-experiment.md)  
**Architecture:** A1–A7 conditions apply  

## Executive summary

Attack surface expansion is **small and well-bounded**: new read endpoint for roster projection + template JSON validation. Highest risks are **information disclosure** (sample metadata outside experiment set) and **integrity** (writes to display-only roster, or write-back expansion). Existing entries API already uses `require_experiment_manage` and typed upserts.

**Verdict: Accept with conditions.** No CRITICAL blockers for P0 if conditions enforced.

## Attack surface (delta)

```
NEW
  GET /v1/entries/{entry_id}/roster     authenticated, experiment:manage
  Template write path validates entries[]  (same experiment:manage as template CRUD)

UNCHANGED (reuse)
  PUT /v1/entries/{id}/values
  write-back to Sample allowlist
  Entry RLS via experiment membership patterns
```

## STRIDE (this feature)

| Threat | Component | Assessment | Control |
|--------|-----------|------------|---------|
| **S** Spoofing | Roster/values API | Low | JWT + `require_experiment_manage` |
| **T** Tampering | Roster write | **High if unblocked** | **Reject upsert for sample_roster** (A1) |
| **T** Tampering | sample_columns injection | Med | Server allowlist; no dynamic SQL |
| **T** Tampering | write-back expansion | Med | Do **not** expand `SAMPLE_WRITE_BACK_COLUMNS` in P0 |
| **R** Repudiation | Entry save / write-back | Med | Existing audit fields + write_back_previous |
| **I** Info disclosure | Roster projects Sample | **High** | Rows **only** from experiment’s sample_executions; sample RLS |
| **I** Info disclosure | List names | Low | Only FKs on those samples |
| **D** DoS | Huge roster | Low | Soft cap document 500; no unbounded export |
| **E** Elevation | Client authors templates | High if mis-RBAC | Clients lack experiment:manage (Decision #9) |

## Findings

### F1: Roster must not accept value upserts — HIGH (confidence 9/10)

**Today:** `upsert_values` rejects only `display_table` (`entry_service.py` ~246–250).

**Exploit:** If `sample_roster` is added without extending the reject list, a client with manage could write fake values into a display block (integrity / UI confusion).

**Fix (required):** Treat `sample_roster` like `display_table` (architecture **A1**). Test required.

### F2: Roster query must join only experiment samples — HIGH (confidence 9/10)

**Exploit:** If handler accepts arbitrary `sample_id` query params or loads “all samples for client,” data leaks.

**Fix (required):**  
`sample_ids = executions for entry.experiment_id` only.  
No query param override in P0.  
Batch load those IDs under RLS.  
Architecture **A3/A4**.

### F3: Client-side column projection is unsafe — MEDIUM (confidence 8/10)

**Exploit:** Duplicated allowlist in frontend drifts; malicious client asks for columns not intended (if a bulk sample API returns full objects).

**Fix (required):** Server-owned roster DTO with projected cells only (API B). Do not return full Sample ORM dump.

### F4: Template JSON mass assignment — MEDIUM (confidence 7/10)

**Exploit:** Oversized or nested malicious `config` blobs; unexpected keys.

**Fix:** Pydantic model: fixed fields; `sample_columns: list[str]` max length (e.g. 32); strip unknown keys; reject non-allowlisted strings.

### F5: Write-back scope creep — MEDIUM (confidence 8/10)

**Not introducing new columns is correct.** Any expansion of `SAMPLE_WRITE_BACK_COLUMNS` needs separate security review (already flagged in parent process review).

**Condition:** P0 does not expand allowlist.

### F6: Auth gate is manage-only for all entry reads — LOW/INFO (confidence 9/10)

**Observed:** Entire entries router depends on `require_experiment_manage`.

**Implication:** Lab users without manage cannot view entries/roster even if they can view experiments. Aligns with current Phase 2; Decision #9 is about **edit**. Future “entry:read for lab tech” is out of P0—do not silently open without product decision.

**Condition:** Document that P0 roster visibility = manage; do not weaken to public or client.

## OWASP (scoped)

| Item | Result |
|------|--------|
| A01 Access control | Manage gate + RLS; no client template edit |
| A03 Injection | No raw SQL from column keys; allowlist map only |
| A04 Insecure design | Display-only roster; fail closed columns |
| A07 Auth | Existing JWT/RBAC |
| A09 Logging | Prefer log roster access anomalies (optional P1) |

## Data classification

| Data on roster | Class | Notes |
|----------------|-------|-------|
| client_sample_id | Confidential | Lab sample identifiers |
| biotype, matrix, status | Internal/Confidential | Metadata |
| dates | Confidential | Operational |
| No passwords/PHI assumed beyond sample metadata | — | Follow sample RLS |

## Conditions

| ID | Condition |
|----|-----------|
| **S1** | Reject value upserts for `sample_roster` (same as display_table) + test |
| **S2** | Roster rows only from experiment sample_executions; no arbitrary sample_id input |
| **S3** | Server projects cells; response does not dump full Sample with unrelated columns |
| **S4** | Validate template entries with allowlist; max columns; no expand write-back allowlist |
| **S5** | Keep `require_experiment_manage` for roster in P0; document |
| **S6** | Confirm RLS: user who cannot see sample must not see it on roster (test isolation) |

## NOT a finding

- Using JSONB for `config` (validated)  
- Last-write-wins write-back (pre-decided Q4; unchanged)  
- Keeping protocol/transfer in template (no new data path)

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (S1–S6) |
| **Date** | 2026-07-29 |
| **Critical open** | 0 if A1/S1 and S2 implemented |
| **Block implement?** | No — conditions are implement-time gates |

### Disclaimer

This is a plan-scoped security review of the feature packet, not a full infrastructure /cso audit of the NimbleLIMS deployment.
