# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** Lab Ops Accept (L1 Met; L2) — gate CLOSED until Günter `config:edit`  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Lab Ops:** [`.docs/lab-ops-review/extract-hold-dest-type.md`](../lab-ops-review/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest `sample_type` on aliquot/pool, L1 process membership for execute-minted dests, start-time entry allow-list, and a **many-to-many** system-wide transition catalog. Not SOP+AI Apply, parsers, or matrix.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Lab Ops Accept with conditions; **L1 Met**; **L2** = dest type only on plan entry, no execute re-prompt | Deiter / Marc 2026-08-23 |
| Seed Blood × aliquot → DNA with implement | Marc / Lab Ops |
| Catalog is **many-to-many**: one source → many dests via separate rows | Marc + Heidi |
| Multi-hop = process steps, not one chained catalog row | Marc + Heidi |
| Gate opens when Günter stamps `config:edit` on the catalog | Marc |
| No product code until gate opens | Marc + Mathilda |
| System-wide config table; blank always allowed; pool same-type rule; L1/C2; C3 retracted | Prior PR 54 locks |
| Not IC50 | Marc |

## 3. Goals

- Optional dest type beside Method on aliquot and pool; blank → parent.
- Many-to-many catalog rows; entry select shows all allowed dests for source × op.
- Dest type set only on plan entry (**L2**); execute never re-prompts.
- Multi-hop via process steps (Blood→plasma then plasma→cfDNA).
- L1 join-after-start; start entry allow-list; C2 key off `sample_type`.
- Seed Blood×aliquot→DNA with implement; further rows via `config:edit`.

## 4. Non-goals

- No product code before Günter stamp.
- No Sample/`material_class` column; no template JSON transitions; no if-blood-then.
- No execute re-prompt for dest type; no matrix drop; no TruSeq; no IC50.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Dest type on plan entry beside Method (aliquot and pool); blank = Same as parent. |
| AC2 | Execute does **not** re-prompt dest type (**L2**). |
| AC3 | Catalog many-to-many: separate rows per allowed dest; select lists all for source × op. |
| AC4 | Off-table dest → refuse. |
| AC5 | Multi-hop is process steps, not a single chained catalog row. |
| AC6 | Pool: one shared source type or refuse; then catalog lookup. |
| AC7 | L1: execute-minted dest joins this instance after start; append 403. |
| AC8 | `accepted_sample_types` gates start only. |
| AC9 | Seed with implement includes Blood × aliquot → DNA. |
| AC10 | Catalog CRUD requires `config:edit` (Günter). |
| AC11 | C2: eligibility/Qubit key off `sample_type`. |
| AC12 | No Sample/`material_class` column. |

## 6. Path exercised

Blood → DNA (aliquot seed row) → Qubit. Optional later: Blood → plasma → cfDNA as two steps. Mixed-type pool refuse.

## 7. Sign-off

| Review | Verdict |
|--------|--------|
| CEO | **Accept** |
| Architecture | **Accept** (many-to-many; multi-hop = steps) |
| UI | **Accept (U6)** — plan entry only; many select options; no product UI until gate |
| Lab Ops | **Accept with conditions** (L1 Met; L2) |
| Security | **Open** — Günter `config:edit` opens implement gate |
| CSO | Open |

**Implement gate:** CLOSED until Günter stamps `config:edit` on the catalog. Then implement L2 + seed. Not IC50.
