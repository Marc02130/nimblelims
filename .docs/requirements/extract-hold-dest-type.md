# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** Config-table fold — Architecture pick locked; UI re-read; Lab Ops + CSO before implement  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51)  
**Note:** PR 52 merged without Marc fold. PR 54 is the corrected packet. Material-class rules = **config table** (2026-08-23).

## 1. Purpose

Unlock dest `sample_type` on aliquot/pool execute, process membership for execute-minted dests, start-time step entry allow-list, and a **lab-wide transition catalog** so allowed dest types are configuration (not hardcoded if-blood-then). Does not fix SOP+AI Apply, parsers, or matrix.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Material-class rules are **configuration**, not code | Marc 2026-08-23 |
| Table: `source_sample_type` × `operation` (aliquot\|pool) × `allowed_dest_sample_type` | Marc 2026-08-23 |
| **Config table**, not JSON on the template | Heidi Architecture pick 2026-08-23 |
| Entry setup only offers allowed dests for that source × operation | Marc + Mathilda |
| Execute refuses anything not in the table | Marc + Heidi |
| Blank = Same as parent **always allowed** (no-change); no same-type row required | Heidi 2026-08-23 |
| Blood→DNA = aliquot config row; DNA→pooled DNA = pool config row; two process steps; no hardcoded if-blood-then | Marc + Heidi |
| `template_definition.accepted_sample_types` = step **entry** allow-list only | Heidi |
| L1/S1 execute-minted dest joins this instance; C2 key off `sample_type`; C3 retracted | Marc fold |
| Not a Sample column; not `material_class` on Sample; not IC50 | Heidi / Marc |
| Bounce free-text type or mid-entry gate | Mathilda |

## 3. Goals

- Optional dest `sample_type` beside Method on **aliquot and pool**. Blank → parent (always OK).
- Lab-wide **config table** drives which dest types may be chosen/executed per source × operation.
- Entry select lists only those allowed dests (+ Same as parent).
- Execute refuses off-table dest types.
- Execute-minted dest joins `eln_process_samples` for this instance after start (**L1**). Append 403.
- Start gate via `accepted_sample_types` on the step template (entry only).
- Eligibility / Qubit key off `sample_type` (**C2**).

## 4. Non-goals

- No new **Sample** columns / no `material_class` on Sample.
- No transition rules as JSON on `template_definition`.
- No hardcoded type-pair logic in execute.
- No matrix drop; no TruSeq in this packet; no SOP+AI Apply; no IC50.
- No receive or mid-entry type gate; no free-text dest type; no product UI code here.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Aliquot and pool plan lines accept optional dest `sample_type` beside Method. |
| AC2 | Blank dest type → parent type; always allowed without a same-type catalog row. |
| AC3 | Set dest type → execute writes it only if a catalog row exists for `(source type, aliquot\|pool, dest type)`. |
| AC4 | Off-table dest type → execute refuses. |
| AC5 | Entry setup dest select lists only catalog-allowed dests for that source × operation, plus Same as parent. |
| AC6 | No free-text dest type. |
| AC7 | Catalog is a **config table** (not template JSON). Seed examples: Blood×aliquot→DNA; DNA×pool→pooled DNA. |
| AC8 | No hardcoded if-blood-then (or equivalent) in code. |
| AC9 | Dest has `parent_sample_id` = source. |
| AC10 | Under process: execute-minted dest joins this instance after start (**L1**). |
| AC11 | Arbitrary append → 403. |
| AC12 | `template_definition.accepted_sample_types` gates experiment + LimsRun **start** only (entry allow-list). |
| AC13 | No receive gate; no mid-entry type check. |
| AC14 | Eligibility / Qubit key off `sample_type`, not matrix (**C2**). |
| AC15 | No new Sample column / no `material_class` on Sample. Catalog table is allowed. |
| AC16 | Matrix on dest unchanged by this packet. |

## 6. Path exercised (catalog, not SOP text)

Blood → DNA via **aliquot** step (catalog row) → DNA → pooled DNA via **pool** step (catalog row) → next step start gated by `accepted_sample_types`. Blood → DNA via **pool** has no row → refuse. Katinka NCI links stay in `sop-ai-to-process.md`. SOP PDFs stay out of git.

## 7. Sign-off

| Review | Role | Verdict |
|--------|------|--------|
| CEO | Marc | **Accept** + config-table fold 2026-08-23 |
| Architecture | Heidi — config table pick; entry allow-list separate | Prior Accept; pick locked; re-stamp OK after fold |
| UI | Mathilda — filtered dest select; bounce free-text / mid-entry | **Re-read** after this fold |
| Lab Ops | Deiter | Open |
| CSO | Hans — catalog row ownership | Open |

**Implement gate:** CLOSED until Lab Ops + CSO (and UI re-Accept).
