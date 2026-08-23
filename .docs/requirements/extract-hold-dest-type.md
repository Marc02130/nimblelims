# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** Architecture Accept (re-stamp) — UI re-stamp pending; Lab Ops + CSO before implement  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)

## 1. Purpose

Dest `sample_type` on aliquot/pool, process membership for execute-minted dests, start-time step entry allow-list, and a **system-wide transition catalog**. Pool sources must share one type. Not SOP+AI Apply, parsers, or matrix.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Transitions: lab-wide / system-wide config table (source × aliquot\|pool × allowed dest) | Marc + Heidi |
| Not per entry; not on `template_definition` for transitions | Marc + Heidi |
| Blank = Same as parent always allowed; no config row | Heidi |
| **Pool: all sources share one `sample_type`; mixed → refuse; then one catalog row for that type × pool → dest** | Marc 2026-08-23 (supersedes every-source-has-a-row for mixed types) |
| Mixed container contents (cells, compound, buffer) = experiment contents, not pool; **out** | Marc |
| `accepted_sample_types` still on `template_definition` (entry allow-list) | Marc + Heidi |
| L1/S1, C2; C3 retracted | Marc fold |
| Bounce Sample/`material_class` column; template JSON transitions; if-blood-then; free-text; receive/mid-entry gates | Heidi + Mathilda |
| Not IC50 | Marc |

## 3. Goals

- Optional dest type beside Method on aliquot and pool; blank → parent (always OK).
- System-wide catalog drives allowed dests; entry select filtered; execute refuses off-table.
- Pool requires one shared source type; then one catalog lookup.
- L1 join-after-start; start entry gate; C2 key off `sample_type`.

## 4. Non-goals

- No Sample/`material_class` column; no template JSON transitions; no if-blood-then.
- No mixed-container-contents-as-pool; no matrix drop; no TruSeq; no SOP+AI Apply; no IC50.
- No receive/mid-entry type gate; no free-text dest type; no product UI code here.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Aliquot and pool accept optional dest `sample_type` beside Method. |
| AC2 | Blank → parent; always allowed without a same-type catalog row. |
| AC3 | Set dest → write only if catalog row `(source type, op, dest)` exists. |
| AC4 | Off-table dest → refuse. |
| AC5 | Entry select lists only catalog dests for source × op, plus Same as parent. No free-text. |
| AC6 | Catalog is system-wide client table — not per entry, not on `template_definition`. |
| AC7 | Pool: if sources do not share one `sample_type` → refuse. |
| AC8 | Pool: after same-type check, one catalog row for that type × pool → dest. |
| AC9 | No hardcoded if-blood-then. Seed examples as rows: Blood×aliquot→DNA; DNA×pool→pooled DNA. |
| AC10 | Dest has `parent_sample_id` = source. |
| AC11 | Under process: execute-minted dest joins this instance after start (L1). Append → 403. |
| AC12 | `accepted_sample_types` gates experiment + LimsRun start only. |
| AC13 | No receive gate; no mid-entry type check. |
| AC14 | Eligibility / Qubit key off `sample_type` (C2). |
| AC15 | No Sample/`material_class` column. Catalog table allowed. |
| AC16 | Mixed container contents out of packet. Matrix on dest unchanged. |

## 6. Path exercised

Blood → DNA (aliquot row) → DNA → pooled DNA (pool row, same-type sources) → next step entry allow-list. Mixed-type pool refuse. Katinka links in `sop-ai-to-process.md`; SOP PDFs out of git.

## 7. Sign-off

| Review | Role | Verdict |
|--------|------|--------|
| CEO | Marc | **Accept** + same-type pool fold |
| Architecture | Heidi | **Accept (re-stamp)** 2026-08-23 |
| UI | Mathilda | **Re-stamp pending** (U6 same-type pool) |
| Lab Ops | Deiter | Open |
| CSO | Hans | Open |

**Implement gate:** CLOSED until Lab Ops + CSO + UI re-Accept.
