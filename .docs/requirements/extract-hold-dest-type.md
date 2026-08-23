# Requirements: Extract-hold dest sample type

**Date:** 2026-08-23  
**Status:** CEO Accept — Architecture + UI re-read after fold; Lab Ops + CSO before implement  
**Stem:** `extract-hold-dest-type`  
**Tech sketch:** [`.docs/tech-sketch/extract-hold-dest-type.md`](../tech-sketch/extract-hold-dest-type.md)  
**Hold source:** [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) (PR 51, CEO Accept)

## 1. Purpose

Extract-then-Qubit Hold: dest copies the parent’s type/matrix and never lands on `eln_process_samples`. Blood → DNA daughter → Qubit on the daughter cannot ship.

This packet unlocks **dest sample type** on aliquot execute, process membership for execute-minted dests, and a **start-time** accepted-type gate. It does not fix SOP+AI Apply, parsers, or matrix.

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Frame can hold process + parser; Apply cannot | PR 51 / `sop-ai-to-process.md` |
| Extract-then-Qubit Hold until dest type + process-sample | PR 51; Marc 2026-08-21 |
| Optional dest `sample_type` beside Method; blank = Same as parent | Marc 2026-08-23 CEO Accept |
| Execute: write `samples.sample_type`, keep `parent_sample_id`, add dest to `eln_process_samples` on this instance | Marc 2026-08-23 |
| Existing columns only; no new Sample column | Marc + Heidi bounce |
| Dropping `samples.matrix` is **not** this packet | Marc 2026-08-23 |
| TruSeq library = same dest-type rule **later** | Marc 2026-08-23 |
| **Sample type can change through a process** | Marc 2026-08-23 fold |
| Accepted sample types gate at **experiment start** and **LimsRun start**; refuse if type not allowed | Marc 2026-08-23 fold |
| **Not** a receive gate; **not** mid-entry | Marc 2026-08-23 fold |
| **L1/C1/S1:** execute-minted dest joins this instance after start (product of the step); arbitrary append refuse/403; AuthZ: this instance, same client, `experiment:manage` | Marc 2026-08-23 fold |
| **C2:** while matrix copies parent, eligibility and Qubit key off `sample_type`, not matrix | Marc 2026-08-23 fold |
| **C3:** dest type ≠ parent is **aliquot-only**; pool stays blank = parent | Marc + Heidi 2026-08-23 fold |
| Dest type beside Method; blank “Same as parent.”; no sample-ID box / wizard / sample-detail hop | Mathilda UI |
| Bounce receive gate, sample-ID box, mid-entry type check | Mathilda re-read |
| Bounce new Sample column, matrix drop, receive gate | Heidi re-read |
| Not IC50 | Marc / PR 51 |

## 3. Goals

- On **aliquot** plan lines: optional dest `sample_type` (list), co-located with method. Blank → parent type.
- On **pool** plan lines: no dest-type override (always parent) — **C3**.
- On **execute**: create dest with that type rule; set `parent_sample_id`; keep existing amount/container rules.
- On **execute** under a process: insert **execute-minted** dest into `eln_process_samples` for **this** instance (**L1**). Arbitrary append stays 403.
- At **experiment start** and **LimsRun start**: refuse if sample’s `sample_type` is not in the step’s accepted types. Not receive. Not mid-entry.
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
- No product UI beyond entry-setup sketch (Mathilda reviews only).
- No sample-ID box, wizard, or hop to sample detail for dest type.
- Compose stays down unless checking docs against the app.

## 5. Acceptance criteria

| ID | Criterion |
|----|-----------|
| AC1 | Aliquot plan line accepts optional dest `sample_type` next to method. |
| AC2 | Pool plan line does **not** accept dest type ≠ parent; dest always parent type (**C3**). |
| AC3 | Blank aliquot dest type → execute writes parent’s `sample_type` onto the dest sample. |
| AC4 | Set aliquot dest type → execute writes that list value onto `samples.sample_type`. |
| AC5 | Dest sample has `parent_sample_id` = source sample. |
| AC6 | When experiment is under an ELN process, execute adds **execute-minted** dest to `eln_process_samples` for that process instance (not removed) — **L1**. |
| AC7 | Ad hoc experiment (no process): dest sample still created; no process-sample row required. |
| AC8 | Arbitrary append of a sample onto a running process instance is refuse / 403. AuthZ: this instance, same client, `experiment:manage`. |
| AC9 | Experiment start refuses when sample `sample_type` ∉ step accepted types. |
| AC10 | LimsRun start refuses when sample `sample_type` ∉ step accepted types. |
| AC11 | No type gate at receive. No type gate mid-entry. |
| AC12 | Eligibility and Qubit key off `sample_type`, not matrix (**C2**). |
| AC13 | No migration that adds a Sample column. Heidi bounces a new Sample column, a matrix drop, or a receive gate. |
| AC14 | Matrix on dest is unchanged by this packet (still copies parent or existing execute behavior). |
| AC15 | Entry setup: dest type beside Method on **aliquot** only; blank shows “Same as parent.”; no sample-ID box, wizard, sample-detail hop, receive gate, or mid-entry type check. |

## 6. Path exercised (catalog, not SOP text)

Blood intake → DNA daughter (aliquot dest type ≠ blood) → Qubit analysis on the daughter (start allows DNA, refuses blood). Source links stay Katinka’s NCI Frederick URLs in `sop-ai-to-process.md`. Anton’s catalog for this path may live in repo; SOP PDFs do not.

## 7. Sign-off

| Review | Role | Verdict |
|--------|------|--------|
| CEO | Marc — scope freeze | **Accept** 2026-08-23 (fold L1/C2/C3 + start-time type gate required before implement) |
| Architecture | Heidi — existing columns; bounce new Sample column / matrix drop / receive gate; dest ≠ parent aliquot-only | Prior Accept; **re-read after fold** |
| UI | Mathilda — entry setup; bounce receive gate / sample-ID box / mid-entry type check; dest ≠ parent aliquot-only | Prior Accept (conditions); **re-read after fold** |
| Lab Ops | Deiter — Leadership | Open |
| CSO | Hans — Leadership | Open |

**Implement gate:** CLOSED until Lab Ops + CSO sign (and Architecture / UI re-read this fold).
