# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** C3 retracted (Marc) — Architecture Accept pending re-read; UI re-read; Lab Ops + CSO before implement  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51, CEO Accept)  
**Note:** PR 52 merged to main **without** the Marc fold. This follow-up is the corrected packet. **C3 (aliquot-only) retracted** 2026-08-23.

## 1. Purpose

Extract-then-Qubit Hold: dest copies the parent’s type/matrix and never lands on `eln_process_samples`. Blood → DNA daughter → Qubit on the daughter cannot ship.

This packet unlocks **dest sample type** on aliquot **and** pool execute, process membership for execute-minted dests, a **start-time** accepted-type gate, and the allow-list on **`template_definition.accepted_sample_types`**. Type change through the process is a **gate** (so the allow-list can refuse wrong material), not an extract-by-rename. It does not fix SOP+AI Apply, parsers, or matrix.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Frame can hold process + parser; Apply cannot | PR 51 / `sop-ai-to-process.md` |
| Extract-then-Qubit Hold until dest type + process-sample | PR 51; Marc 2026-08-21 |
| Optional dest `sample_type` beside Method on **aliquot and pool**; blank = Same as parent | Marc 2026-08-23 CEO Accept; **C3 retracted** |
| Pool may set dest type ≠ parent (e.g. pooled DNA) so start gate can refuse wrong type | Marc 2026-08-23 retract |
| Execute: write `samples.sample_type`, keep `parent_sample_id` | Marc 2026-08-23 |
| Existing Sample columns only; no new Sample column | Marc + Heidi bounce |
| Dropping `samples.matrix` is **not** this packet | Marc 2026-08-23 |
| TruSeq library = same dest-type rule **later** | Marc 2026-08-23 |
| **Sample type can change through a process** (gate, not rename) | Marc 2026-08-23 fold |
| Accepted sample types gate at **experiment start** and **LimsRun start**; refuse if type not allowed | Marc 2026-08-23 fold |
| Allow-list on step template: **`template_definition.accepted_sample_types`** (not analysis) | Heidi |
| **Not** a receive gate; **not** mid-entry | Marc 2026-08-23 fold |
| **L1/C1/S1:** execute-minted dest joins this instance **after start**; arbitrary append refuse/403; AuthZ: this instance, same client, `experiment:manage` | Marc 2026-08-23 fold |
| **C2:** while matrix copies parent, eligibility and Qubit key off `sample_type`, not matrix | Marc 2026-08-23 fold |
| **C3 retracted:** aliquot-only dest type ≠ parent is **void**; pool same as aliquot | Marc 2026-08-23 |
| Dest type beside Method; blank “Same as parent.”; no sample-ID box / wizard / sample-detail hop | Mathilda UI |
| Bounce receive gate, sample-ID box, mid-entry type check | Mathilda |
| Bounce new Sample column, matrix drop, receive/mid-entry gates | Heidi |
| Not IC50 | Marc / PR 51 |

## 3. Goals

- On **aliquot and pool** plan lines: optional dest `sample_type` (list), co-located with method. Blank → parent type.
- On **execute**: create dest with that type (or parent if blank); set `parent_sample_id`; keep existing amount/container rules.
- On **execute** under a process: insert **execute-minted** dest into `eln_process_samples` for **this** instance **after start** (**L1**). Arbitrary append stays 403.
- Step templates carry **`template_definition.accepted_sample_types`** (UUID list). At **experiment start** and **LimsRun start**: refuse if sample’s `sample_type` ∉ allow-list when the list is non-empty. Not receive. Not mid-entry. Not analysis.
- Eligibility and Qubit key off `sample_type`, not matrix (**C2**).
- Existing `samples.sample_type` column only.

## 4. Non-goals

- No new Sample columns or tables.
- Do **not** drop or rewrite `samples.matrix` in this packet.
- No TruSeq / library-prep dest-type UI beyond the shared rule reserved for later.
- No SOP bodies in git. No SOP+AI Apply → process work.
- No IC50 / dose-response.
- No receive-time type gate. No mid-entry type check.
- No arbitrary append of samples onto a running process instance.
- No product UI beyond entry-setup / template allow-list sketch (Mathilda reviews only).
- No sample-ID box, wizard, or hop to sample detail for dest type.
- Compose stays down unless checking docs against the app.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Aliquot plan line accepts optional dest `sample_type` next to method. |
| AC2 | Pool plan line accepts the **same** optional dest `sample_type` next to method (**C3 retracted**). |
| AC3 | Blank dest type (aliquot or pool) → execute writes parent’s `sample_type` onto the dest sample. |
| AC4 | Set dest type (aliquot or pool) → execute writes that list value onto `samples.sample_type`. |
| AC5 | Dest sample has `parent_sample_id` = source sample. |
| AC6 | When experiment is under an ELN process, execute adds **execute-minted** dest to `eln_process_samples` for that process instance **after start** (not removed) — **L1**. |
| AC7 | Ad hoc experiment (no process): dest sample still created; no process-sample row required. |
| AC8 | Arbitrary append of a sample onto a running process instance is refuse / 403. AuthZ: this instance, same client, `experiment:manage`. |
| AC9 | Step template stores allow-list as `template_definition.accepted_sample_types` (JSONB; no new Sample column; not on analysis). |
| AC10 | Experiment start refuses when allow-list is non-empty and sample `sample_type` ∉ list. |
| AC11 | LimsRun start refuses when allow-list is non-empty and sample `sample_type` ∉ list. |
| AC12 | Empty / absent allow-list → no type refuse at start. |
| AC13 | No type gate at receive. No type gate mid-entry. |
| AC14 | Eligibility and Qubit key off `sample_type`, not matrix (**C2**). |
| AC15 | No migration that adds a Sample column. Heidi bounces a new Sample column, a matrix drop, or a receive/mid-entry gate. |
| AC16 | Matrix on dest is unchanged by this packet (still copies parent or existing execute behavior). |
| AC17 | Entry setup: dest type beside Method on **aliquot and pool**; blank shows “Same as parent.”; no sample-ID box, wizard, sample-detail hop, receive gate, or mid-entry type check. |

## 6. Path exercised (catalog, not SOP text)

Blood intake → DNA daughter (aliquot dest type ≠ blood) → optional pool to pooled DNA → Qubit / next step with `accepted_sample_types` set so wrong material refuses at start. Source links stay Katinka’s NCI Frederick URLs in `sop-ai-to-process.md`. Anton’s catalog for this path may live in repo; SOP PDFs do not.

## 7. Sign-off

| Review | Role | Verdict |
|--------|------|--------|
| CEO | Marc — scope freeze; C3 retracted | **Accept** 2026-08-23 (fold + pool dest type) |
| Architecture | Heidi — L1/C2 + `template_definition.accepted_sample_types`; Accept after pool = aliquot | **Almost** → Accept pending this C3 flip |
| UI | Mathilda — dest type on aliquot and pool; bounce receive gate / sample-ID box / mid-entry type check | **Hold** until re-read of this flip |
| Lab Ops | Deiter — Leadership | Open |
| CSO | Hans — Leadership | Open |

**Implement gate:** CLOSED until Architecture/UI Accept and Lab Ops + CSO sign.
