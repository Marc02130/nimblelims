# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** **Implement gate OPEN** — land S3 + L2 + Blood×aliquot→DNA seed  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Security:** [`.docs/security-review/extract-hold-dest-type.md`](../security-review/extract-hold-dest-type.md) ([PR 55](https://github.com/Marc02130/nimblelims/pull/55))  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest `sample_type` on aliquot/pool, L1/S1 process membership for execute-minted dests, start-time entry allow-list, and a many-to-many system-wide transition catalog with **`config:edit`** mutate AuthZ.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Gate **OPEN** for implement with S3 + Deiter L2 + Blood×aliquot→DNA seed | Günter / Leadership [PR 55](https://github.com/Marc02130/nimblelims/pull/55) |
| **S3:** `sample_type_transitions` mutate is `config:edit` only (not Client, not `experiment:manage` alone) | Günter Security/CSO |
| **S1 Met:** execute-minted dest join after start | Günter + Lab Ops L1 |
| Lab Ops Accept; L1 Met; L2 = plan entry only, no execute re-prompt | Deiter |
| Many-to-many catalog; multi-hop = process steps | Marc + Heidi |
| Not IC50 | Marc |

## 3. Goals

Same as prior packet, plus explicit S3 AuthZ on catalog mutate.

## 4. Non-goals

Matrix drop; TruSeq; SOP+AI Apply; IC50; execute re-prompt; Sample/`material_class` column.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Dest type on plan entry beside Method; blank = Same as parent. |
| AC2 | Execute does not re-prompt dest type (**L2**). |
| AC3 | Catalog many-to-many; select lists all allowed dests. |
| AC4 | Off-table dest → refuse. |
| AC5 | Multi-hop = process steps. |
| AC6 | Pool: one shared source type or refuse. |
| AC7 | L1/S1: execute-minted dest joins this instance after start; append 403. |
| AC8 | `accepted_sample_types` gates start only. |
| AC9 | Seed includes Blood × aliquot → DNA. |
| AC10 | Catalog mutate requires **`config:edit` only** (**S3**). |
| AC11 | C2: eligibility/Qubit key off `sample_type`. |
| AC12 | No Sample/`material_class` column. |

## 6. Path exercised

Blood → DNA (aliquot seed) → Qubit.

## 7. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** |
| Architecture | **Accept** |
| UI | **Accept (U6)** |
| Lab Ops | **Accept with conditions** (L1 Met; L2) |
| Security / CSO | **Accept with conditions** (S1 Met; S3) — PR 55 |

**Implement gate:** **OPEN.** Implement lands S3 + L2 + seed. Not IC50.
