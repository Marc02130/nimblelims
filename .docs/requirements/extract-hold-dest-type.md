# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN** — land S3 + L2 + seeds (Blood×aliquot→DNA, DNA×pool→pooled DNA)  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md) ([PR 55](https://github.com/Marc02130/nimblelims/pull/55))  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest `sample_type` on aliquot/pool, L1/S1 process membership, start-time entry allow-list, and many-to-many `sample_type_transitions` with `config:edit` mutate AuthZ.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Gate OPEN; build against sketch on main | Marc 2026-08-23 |
| Dest type only on aliquot/pool entry beside Method (no execute re-prompt) | Marc + Deiter L2 |
| `sample_type_transitions` is `config:edit` only (S3) | Günter |
| Seed Blood×aliquot→DNA **and** DNA×pool→pooled DNA | Marc 2026-08-23 |
| L1 execute-minted dest joins this instance; start `accepted_sample_types` | Marc + prior locks |
| Catalog many-to-many; multi-hop = process steps | Marc + Heidi |
| No new experiment-plan object | Marc + Heidi bounce |
| No Sample/`material_class` column; no matrix drop; no receive/mid-entry gate; no if-blood-then; no transitions on `template_definition` | Heidi bounce |
| Compose up only while implementing/testing, then down | Marc |
| Not IC50 | Marc |

## 3. Goals

As sketched: L2 plan-entry dest type; S3 catalog AuthZ; L1 join; start allow-list; both seed rows.

## 4. Non-goals

No new experiment-plan object; no Sample/`material_class`; no matrix drop; no receive/mid-entry type gate; no if-blood-then; no transitions on `template_definition`; no TruSeq/SOP+AI/IC50.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Dest type on existing aliquot/pool plan entry beside Method; blank = Same as parent. |
| AC2 | Execute does not re-prompt dest type (L2). |
| AC3 | Catalog many-to-many; select lists allowed dests. |
| AC4 | Off-table dest → refuse. |
| AC5 | Multi-hop = process steps. |
| AC6 | Pool: one shared source type or refuse. |
| AC7 | L1/S1 join after start; append 403. |
| AC8 | `accepted_sample_types` gates start only. |
| AC9 | Seed includes Blood × aliquot → DNA **and** DNA × pool → pooled DNA. |
| AC10 | Catalog mutate requires `config:edit` only (S3). |
| AC11 | C2: eligibility/Qubit key off `sample_type`. |
| AC12 | No Sample/`material_class` column; no new experiment-plan object. |

## 6. Path exercised

Blood → DNA (aliquot) → pooled DNA (pool) → next step allow-list.

## 7. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** — implement order |
| Architecture | **Accept** — bounce bars stand |
| UI | **Accept (U6)** — entry setup as sketched |
| Lab Ops | **Accept** (L1 Met; L2) |
| Security / CSO | **Accept** (S1 Met; S3) |

**Implement gate:** **OPEN.** Not IC50.
