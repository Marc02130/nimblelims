# CEO / Product Review: Experiment template entries

**Date:** 2026-07-29  
**Verdict date:** 2026-07-29  
**Status:** **Accepted with conditions**  
**Mode:** SELECTIVE EXPANSION (hold P0; cherry-pick small completeness)  
**Tech sketch:** [`.docs/tech-sketch/experiment-template-entries.md`](../tech-sketch/experiment-template-entries.md)  
**Open questions:** [`.docs/open-questions/experiments.md`](../open-questions/experiments.md) Q11–Q14  
**Reviewer:** Product / CEO review (session)

## Executive summary

This is the right problem. Lab managers author “pre-configured experiments” today and get **protocol prose that never appears on the instance**. Entries already exist in the backend; the product hole is **authoring + sample roster display**. Closing that loop is high leverage for ELN process steps and for single-experiment work.

**Verdict: Accept P0 as sketched**, with conditions below and Q11–Q14 **Decided** as recommended in the sketch.

## Premise challenge

| Premise | Assessment |
|---------|------------|
| Templates should declare places for data display/capture | **Valid** — core ELN value |
| Protocol/transfer tabs are not that surface | **Valid** — they never materialize on instance |
| Reuse existing Entry + FieldDefinition stack | **Valid** — DRY; avoid parallel models |
| Process handoff (plate → run) is out of this slice | **Valid** — different surface; don’t couple |

**If we did nothing:** Templates stay a config island; lab techs open empty experiments; Field Management investment underused in the ELN.

## Alternatives considered

| Approach | Effort | Decision |
|----------|--------|----------|
| **A. Entries tab + sample_roster + capture (sketch P0)** | M | **Chosen** |
| B. Only fix labels / show protocol text on instance | S | Rejected — no structured capture |
| C. Full procedure merge (protocol+transfer+entries one list) in P0 | L | Deferred P2 — ocean for this cycle |
| D. Normalize template entries to SQL tables now | L | Rejected — premature; JSONB already works |

## Scope decisions (cherry-pick)

| # | Proposal | Effort | Decision | Rationale |
|---|----------|--------|----------|-----------|
| 1 | Entries tab + 3 types (roster, sample_data, experiment_detail) | M | **ACCEPTED** | Core job-to-be-done |
| 2 | Server roster API (not client projection) | S | **ACCEPTED** | Security + single allowlist |
| 3 | Sample labels on sample_data grid | S | **ACCEPTED** | Completeness lake; cheap |
| 4 | Transfer plan modeled as experiment_detail (+ sample_data results) | S | **ACCEPTED** | Product refine 2026-07-29; not parallel Transfer Steps |
| 5 | Delete legacy Transfer Steps tab day-one | — | **SKIPPED** for hard delete; **demote/hide OK** once Entries work; sign-off path kept until P1 migrate |
| 6 | Force sample picker at experiment create | S | **SKIPPED** | Empty roster OK; Q14 |
| 7 | Seed example template with 3 entry blocks | S | **DEFERRED P1** | Nice dogfood; not gate |
| 8 | Auto-link process samples → executions (Q8) | M | **DEFERRED** | Separate open question |
| 9 | Procedure merge single list | L | **DEFERRED P2** | After Entries prove out |
| 10 | Predefined action engines | L | **DEFERRED** | Non-goal |

## Product decisions (Q11–Q14)

| # | Decision | Status |
|---|----------|--------|
| **Q11** | Entries = runtime. **Transfer plan = experiment_detail** (source/dest/vol…); **results = sample_data** next. Legacy Transfer tab transitional only. | **Decided** (refined) |
| **Q15** | Same as above — formalized as Decision #15 | **Decided** |
| **Q12** | New entry type **`sample_roster`**. Do not overload `display_table`. | **Decided** |
| **Q13** | **Server allowlist** of Sample OOB + Path-1 columns; fail closed. Not “any FieldDefinition” alone. | **Decided** |
| **Q14** | **No** mandatory sample picker at create in P0. Empty roster with clear empty state. | **Decided** |

## 10x / dream state (not this PR)

```
CURRENT:  Template prose tabs → empty instance
THIS PLAN: Template Entries → tables on instance
12-MO:     Procedure as one ordered list; process auto-fills roster;
           write-back governance; predefined actions live
```

## Error / product failure modes (product view)

| Failure | User sees | Required |
|---------|-----------|----------|
| Template with no entries | Empty Entries on experiment + CTA to template | Yes |
| Roster, no samples | “Link samples to populate” | Yes |
| Invalid column key saved | Block save with field error | Yes |
| Client user tries edit | Denied (Decision #9) | Existing |

## NOT in scope

- LimsRun / analysis interior tables  
- Process override of entry config (Q3)  
- Stricter write-back (Q4)  
- Multi-tenant  

## Conditions (must land with P0)

| ID | Condition |
|----|-----------|
| **C1** | Tab order: Basic Info → **Entries** → Protocol → Transfer → Result Columns |
| **C2** | UI language: prefer **“Tables & forms”** as Entries tab label (or subtitle); avoid calling entries “steps” |
| **C3** | Exit demo: author 3 blocks → create experiment → link samples → roster + edit sample_data → save |
| **C4** | Manuals updated same PR as UI |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (C1–C4) |
| **Date** | 2026-07-29 |
| **Implement?** | **Yes** after architecture + security conditions also met |
| **Lake score** | 4/4 completeness choices preferred over shortcuts for in-scope items |

## Completion summary

```
Mode: SELECTIVE EXPANSION
Premises: accepted
Q11–Q14: Decided
Scope accepted: P0 sketch + server roster + labels
Deferred: seed template, Q8, procedure merge, actions
Critical product gaps: 0
```
