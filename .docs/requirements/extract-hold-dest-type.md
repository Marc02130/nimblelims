# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** In review — Leadership signs before implement  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51, CEO Accept)

## 1. Purpose

Extract-then-Qubit Hold: dest copies the parent’s type/matrix and never lands on `eln_process_samples`. Blood → DNA daughter → Qubit on the daughter cannot ship.

This packet unlocks **dest sample type** on aliquot/pool execute only. It does not fix SOP+AI Apply, parsers, or matrix.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Frame can hold process + parser; Apply cannot | PR 51 / `sop-ai-to-process.md` |
| Extract-then-Qubit Hold still stands until dest type + process-sample | PR 51; Marc 2026-08-21 |
| Optional dest `sample_type` on aliquot/pool entry, same place as method | Marc 2026-08-23 |
| Blank = parent type | Marc 2026-08-23 |
| Execute: write `samples.sample_type`, keep `parent_sample_id`, add dest to `eln_process_samples` on this instance | Marc 2026-08-23 |
| Existing columns only; no new Sample column | Marc + Heidi bounce |
| Dropping `samples.matrix` is **not** this packet | Marc 2026-08-23 |
| TruSeq library = same dest-type rule **later**, not this packet | Marc 2026-08-23 |
| Not IC50 | Marc / PR 51 |

## 3. Goals

- On aliquot and pool **plan** lines: optional dest `sample_type` (list), co-located with method.
- Blank / omitted → dest inherits parent `sample_type`.
- On **execute**: create dest sample with that type (or parent if blank); set `parent_sample_id`; keep existing amount/container rules from the entries spine.
- On **execute**: insert dest into `eln_process_samples` for the **current process instance** (when the experiment is under a process). Dest is eligible for later steps (e.g. Qubit) without hunting off-process.
- Existing `samples.sample_type` column only.

## 4. Non-goals

- No new Sample columns or tables.
- Do **not** drop or rewrite `samples.matrix` in this packet.
- No TruSeq / library-prep dest-type UI beyond the shared rule reserved for later.
- No SOP bodies in git. No SOP+AI Apply → process work.
- No IC50 / dose-response.
- No product UI beyond what the tech sketch needs for entry setup (Mathilda reviews sketch only).
- Compose stays down unless checking docs against the app.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Aliquot plan line accepts optional dest `sample_type` next to method. |
| AC2 | Pool plan line accepts the same optional dest `sample_type`. |
| AC3 | Blank dest type → execute writes parent’s `sample_type` onto the dest sample. |
| AC4 | Set dest type → execute writes that list value onto `samples.sample_type`. |
| AC5 | Dest sample has `parent_sample_id` = source sample. |
| AC6 | When experiment is under an ELN process, execute adds dest to `eln_process_samples` for that process instance (not removed). |
| AC7 | Ad hoc experiment (no process): dest sample still created; no process-sample row required. |
| AC8 | No migration that adds a Sample column. Heidi bounces a new Sample column or a matrix drop. |
| AC9 | Matrix on dest is unchanged by this packet (still copies parent or existing execute behavior). |

## 6. Path exercised (catalog, not SOP text)

Blood intake → DNA daughter (dest type ≠ blood) → Qubit analysis on the daughter. Source links stay Katinka’s NCI Frederick URLs in `sop-ai-to-process.md`. Anton’s catalog for this path may live in repo; SOP PDFs do not.

## 7. Sign-off

| Review | Role |
|--------|------|
| Architecture | Heidi — existing columns only; bounce new Sample column or matrix drop |
| UI | Mathilda — entry setup UX only if sketch needs it; no product UI code |
| Lab Ops | Deiter — lab fit for dest type on aliquot/pool |
| CEO | Marc — scope freeze before implement |

**Implement gate:** CLOSED until Leadership Accept on the sketch.
