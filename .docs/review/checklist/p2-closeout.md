# P2 closeout — merge `feat/work-order-p2` to `main`

**Date:** 2026-09-01  
**Branch:** `feat/work-order-p2`  
**Click SHA:** `bf51b19` (`bf51b192b417663f677b80be6d8b9afd790cb78a`) — Alembic **`0078`**  
**Docs stamp:** living closeout (this fold)  
**Execute joints:** `1572071`  
**Stem:** `post-receive-work-spine`  
**UAT:** [`UAT_Scripts/uat-post-receive-work-spine.md`](../../../UAT_Scripts/uat-post-receive-work-spine.md) live stamp `bf51b19`

**Now:** **Merge bar Met** (Marc/CEO). Product may merge `feat/work-order-p2` to `main`. Tobias signed **per-AC Pass**. **Overall P2 is unsigned / not Pass.** Closeout **1.2 dest-cohort asked-for lookup** is **Coded** (WO `asked_for_id` same analysis, else parent lineage). Freeze skip NULL is **Tobias Pass** on `bf51b19` (not a merge hold). Asked-for-only Marc lock from PR **111** still stands. Stack **down**. Not IC50.

This is a working list, not a Leadership Confirm and not a UAT Result stamp. Do **not** rewrite signed UAT (`9342439`, `8cfa2a9`, `b005cfe`, `9c4f9da`, `3b56cfb`, P1 `c649245`, Deiter `02fe95f` C2 **Fail**). Do **not** rewrite Deiter Lab Ops Met on `570bbc0`. Do **not** restamp unsigned Tobias C2/C3 on `570bbc0`.

---

## Now

| Slice | Status |
|-------|--------|
| P1 asked-for lake | **Pass**, on `main` (`c649245` / PR 81) |
| Receive freeze | **Pass** — do not reopen CORE |
| Route / first Start `chain[0]` / empty Route 422 / map overlap 409 / Blood extract + later DNA qPCR 201 | **Pass** `8cfa2a9` |
| WO-7 publish refuse | **Pass** `8cfa2a9` |
| AC-P2-9..11 + later-step type-gate | **Pass** `9342439` |
| C1 assignment (no vessel / two vessel 422; receive-tube 201) | Deiter Pass `02fe95f` (history). Tobias **Pass** `bf51b19` |
| C2 same-type dest-follow | Deiter Fail `02fe95f` (history). Lab Ops Met `570bbc0`. Tobias **Pass** `bf51b19`. Tobias C2 on `570bbc0` stays **unsigned** |
| C3 Blood → DNA dest-follow | Lab Ops Met `570bbc0`. Tobias **Pass** `bf51b19`. Tobias C3 on `570bbc0` stays **unsigned** |
| Cardinality 1 (map-save/Route 422 on 0 or 2+ asked-for LimsRuns) | Coded + Tobias **Pass** `bf51b19` for **assay** asked-fors. Extracted DNA (**1.4**) may have **zero** LimsRuns |
| Supporting QC same-route, own Test | Tobias **Pass** `bf51b19` |
| Freeze skip NULL | Coded `0078` + Tobias **Pass** `bf51b19` (classic NULL; first start `{cell_line: A549}`; later start left it). `{}` on `99b692d3` stays `8cfa2a9` history. **Not** a merge hold |
| Route two-accept 409 | Tobias **Pass** `bf51b19` |
| Seq-1 sequential asked-fors (two WOs; WES on DNA tube) | Tobias **Pass** `bf51b19`. Dest-cohort params (**1.2**) **not scored** on that stamp — now **Coded** |
| OQ-WO-6 extract punch | **CLOSED** for the common path — extract is an **experiment** (equipment) and does not wear the panel `analysis_id`. **Not** a forever ban on extract-as-LimsRun. After extract on an **assay** ask, Qubit/Nanodrop QC LimsRun may quantify DNA. **Process QC is not an asked-for.** Assay ask: one asked-for LimsRun. Extracted DNA ask: zero assay LimsRuns legal (**1.4**) |
| Dest mint only at execute | **Leadership Confirm** |
| No route branching | **Marc lock, pending Leadership overwrite** |
| Care about the asked-for only | **Marc lock 2026-09-01 (PR 111), pending Leadership overwrite** — still stands |
| Overall P2 Pass | **Unsigned / not Pass** |
| Merge to `main` | **Met** (Marc/CEO). Product may merge |

**Out of this merge on purpose:** route branching / dest auto-joining a second WO; 2+ matching routes **picker** (product is **409**); P3–P5; IC50.

---

## Left after merge (not a merge hold)

1. **Leadership Confirm** of sequential asked-fors (WGS on blood owns WGS params; C3 DNA; C2 aliquot continues WGS; WES = new asked-for on the DNA tube, then aliquoted or used up; own params). Marc lock is pending overwrite. Tobias Pass of two WOs is **not** that Confirm.
2. **Closeout 1.2 — Coded (not a merge hold):** WO-7 `_mint_tests_at_start` freezes from `work_order.asked_for_id` when the run is on a WO process and `asked.analysis_id == run.analysis_id`, else walks `parent_sample_id`. Blood WGS `{library_kit: TruSeq}` freezes onto the DNA dest Test. QC LimsRuns do not steal assay params. Seq-1 on `bf51b19` did **not** score dest-cohort params. Tobias restamp if in-bar.
3. **Closeout 1.4 — Extracted DNA asked-for (zero assay LimsRuns):** If asked-for is Extracted DNA, they get a DNA tube. No sequencing. No other LimsRuns. Today map-save/Route **422** when a chain has **zero** LimsRuns (`Route has no LIMS Run analysis`). That 422 is **wrong** for this asked-for. Two ELISA LimsRuns still 422. Extract may be a LimsRun later if equipment is an instrument.
4. **Overall P2 Pass** — Tobias has not signed overall Pass. Do not write it from this fold.
5. **Merge** — **Met.** Marc/CEO: merge `feat/work-order-p2` to `main` now. Do not invent overall P2 Pass. Freeze skip NULL **Pass** on `bf51b19` is not a hold. 1.2 is coded, not a hold.

Do **not** recode dest-follow, cardinality, freeze skip NULL, or Route two-accept 409 unless a new Fail lands.

---

## Coding leftover

| # | Gap | Now | Do |
|---|-----|-----|----|
| **1.1 Cardinality 1** | Two ELISA LimsRuns must 422 | **Done.** Tobias Pass `bf51b19` | Do not re-score |
| **1.2 WO-7 asked-for after C3** | Lookup is `sample_id == cohort` + `analysis_id` | **Coded.** Freeze from `work_order.asked_for_id` (same analysis), else parent lineage. QC LimsRuns do not steal assay params. | Tobias restamp dest-cohort params if in-bar |
| **1.3 Freeze skip NULL** | Classic `{}` vs frozen `{}` | **Done** (`0078`). Tobias Pass `bf51b19` | Do not transfer `99b692d3` |
| **1.4 Extracted DNA asked-for** | Zero assay LimsRuns; DNA tube only | Map-save/Route still **422** on 0 LimsRuns | Code iff in-bar: allow extract-only route when asked-for is Extracted DNA |

**Do not code:** route branching; dest auto-join second WO; copy WGS params onto WES; second asked-for for Qubit; analysis picker on `/receive`; 2+ routes picker; P3–P5. Do not forever-ban extract-as-LimsRun — later, if equipment is an instrument.

---

## UAT (done for the live stamp)

Live stamp is `bf51b19`. Tobias · local compose · 2026-08-31 · **down** after.

| AC | Tobias |
|----|--------|
| AC-P2-C1 | **Pass** |
| AC-P2-C2 | **Pass** on `bf51b19`. Unsigned on `570bbc0` |
| AC-P2-C3 | **Pass** on `bf51b19`. Unsigned on `570bbc0` |
| AC-P2-card-1 two ELISA map-save 422 | **Pass** |
| AC-P2-card-2 extract + Qubit + ELISA 201 | **Pass** |
| AC-P2-card-3 Route 0 or 2+ 422 | **Pass** |
| AC-P2-qc-1 Qubit own Test | **Pass** |
| AC-P2-4 freeze skip NULL | **Pass** |
| AC-P2-5 addendum Route two-accept 409 | **Pass** |
| AC-P2-seq-1 two WOs | **Pass** — 1.2 not scored |
| Overall P2 | **unsigned / not Pass** |

Do **not** re-score `8cfa2a9` / `9342439` / P1 / Deiter `02fe95f` C2 Fail. Do **not** score dest at Route/Start as Fail. Do **not** score leftover C2 volume as Fail. Do **not** score DNA as C2. Do **not** restamp unsigned Tobias C2/C3 on `570bbc0`.

---

## One-page scoreboard

| Gate | Now | Merge needs |
|------|-----|-------------|
| Cardinality 1 | **Pass** `bf51b19` | — |
| Freeze skip NULL | **Pass** `bf51b19` | — |
| C1 / C2 / C3 | **Pass** `bf51b19`. Deiter Lab Ops Met `570bbc0`. Tobias C2/C3 **unsigned** on `570bbc0`. Deiter C2 Fail `02fe95f` history | — |
| Route two-accept 409 | **Pass** `bf51b19` | — |
| Seq-1 two WOs | **Pass** `bf51b19` | Leadership Confirm of the lock (not a merge hold) |
| Dest-cohort params (1.2) | **Coded** — freeze from WO asked-for / parent lineage | Tobias restamp if in-bar (not a merge hold) |
| Extracted DNA asked-for (1.4) | Zero LimsRuns still map-save/Route **422** | Post-merge / iff in-bar |
| Historical Route/WO-7/AC-P2-9..11 | **Signed Pass** | Do not re-score |
| Asked-for-only Marc lock (PR 111) | **Stands** | Do not rewrite |
| Overall P2 Pass | **Unsigned** | Do not invent from this fold |
| Merge to `main` | **Met** (Marc/CEO) | Not freeze skip (Pass on `bf51b19`). Not 1.2 (coded) |
