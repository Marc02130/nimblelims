# P2 closeout — merge `feat/work-order-p2` to `main`

**Date:** 2026-09-01  
**Branch:** `feat/work-order-p2` leftover; product is on `main`  
**Click SHA:** `bf51b19` (`bf51b192b417663f677b80be6d8b9afd790cb78a`) — Alembic **`0078`**  
**Merge SHA:** `5040f2d` (`5040f2d` Merge feat/work-order-p2 into main) — feat tip at merge was `4b8c41f`  
**Docs stamp:** living closeout (this fold)  
**Execute joints:** `1572071`  
**Stem:** `post-receive-work-spine`  
**UAT:** [`UAT_Scripts/uat-post-receive-work-spine.md`](../../../UAT_Scripts/uat-post-receive-work-spine.md) live stamp `bf51b19`

**Now:** P2 is on `main`. Product SHA for **AC-P2-OQ-WO-7** is **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`). Tobias signed **per-AC Pass** on `bf51b19` (do **not** rewrite those Results). **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`): Test **`55f9cad9`** `(DNA, WGS)` has `{library_kit: TruSeq}` from blood WO **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`). **Was not recoded.** **OQ-WO-7 Closed.** **Overall P2 stayed unsigned / not Pass.** Merge `5040f2d` landed with **OQ-WO-7 OPEN** — that history stands; do **not** pretend it was held for OQ-WO-7. **CEO Accept (Rolf)** of Hans’s written what/why stands; “Grok Build codes first” is **done**. Freeze skip NULL is **Tobias Pass** on `bf51b19`. Asked-for-only Marc lock from PR **111** still stands. **Leadership Confirm 2026-09-01** (ELISA not on DNA; second tube; extract LimsRun later). Closeout **1.4 / OQ-WO-8** is **OPEN.** **CEO Confirm 1–6 (Rolf)** plus Qubit-reuse punch: wear existing Qubit; do **not** mint a second catalog analysis named Quantified DNA. Old 1.4 struck; **422 on 0 LimsRuns is right.** Named asked-for LimsRun slot is a **punch pending Leadership Confirm** (not part of 1–6; not Closed). Send: [`.docs/discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md`](../../discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md). Do **not** invent overall P2 Pass. Stack **down**. Not IC50.

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
| Cardinality 1 (map-save/Route 422 on 0 or 2+ asked-for LimsRuns) | Coded + Tobias **Pass** `bf51b19` for **assay** asked-fors. **1.4 Quantified DNA** is an assay ask (Qubit once) — **CEO Confirm 1–6 (Rolf)**; **OQ-WO-8 OPEN**; named-slot pending |
| Supporting QC same-route, own Test | Tobias **Pass** `bf51b19` |
| Freeze skip NULL | Coded `0078` + Tobias **Pass** `bf51b19` (classic NULL; first start `{cell_line: A549}`; later start left it). `{}` on `99b692d3` stays `8cfa2a9` history. **Not** a merge hold |
| Route two-accept 409 | Tobias **Pass** `bf51b19` |
| Seq-1 sequential asked-fors (two WOs; WES on DNA tube) | Tobias **Pass** `bf51b19`. Dest-cohort params (**1.2** / **OQ-WO-7**) **not scored** on that SHA |
| OQ-WO-6 extract punch | **CLOSED** for the common path — extract is an **experiment** (equipment) and does not wear the panel `analysis_id`. **Not** a forever ban on extract-as-LimsRun. After extract on **WGS / WES / ELISA**, Qubit/Nanodrop is **process QC**, not the asked-for. Assay ask: one asked-for LimsRun. **1.4 Quantified DNA:** Qubit **is** the asked-for LimsRun (**CEO Confirm 1–6 Rolf**; wear existing Qubit). **OQ-WO-8 OPEN**. Named-slot pending |
| Dest mint only at execute | **Leadership Confirm** |
| No route branching | **Marc lock, pending Leadership overwrite** |
| Care about the asked-for only | **Marc lock 2026-09-01 (PR 111), pending Leadership overwrite** — still stands |
| ELISA not on DNA; second tube own asked-for; separate containers = separate assignments | **Leadership Confirm 2026-09-01** (Rolf/Deiter/Hans/Heidi/Günter) |
| OQ-WO-7 WGS params on DNA Test from WO after C3 | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup — **was not recoded**. Merged `5040f2d` with OPEN — that history stands |
| Closeout 1.4 Quantified DNA | **CEO Confirm 1–6 (Rolf).** Wear existing Qubit; no second Quantified DNA analysis. Old 1.4 struck; 422 on 0 LimsRuns. **OQ-WO-8 OPEN.** Named-slot pending Leadership Confirm. Send: [2026-09-01-p2-closeout-1-4-quantified-dna](../../discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md) |
| Overall P2 Pass | **Unsigned / not Pass** |
| Merge to `main` | **Landed** `5040f2d` with OQ-WO-7 OPEN (history) |

**Out of the merge on purpose:** route branching / dest auto-joining a second WO; 2+ matching routes **picker** (product is **409**); P3–P5; IC50. **OQ-WO-7** stayed known OPEN.

---

## Left after merge (not a merge hold)

1. **Leadership Confirm** of sequential asked-fors (WGS on blood owns WGS params; C3 DNA; C2 aliquot continues WGS; WES = new asked-for on the DNA tube, then aliquoted or used up; own params). Marc lock is pending overwrite. Tobias Pass of two WOs is **not** that Confirm.
2. **OQ-WO-7 / closeout 1.2 — Closed. AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). After C3 (Blood→DNA) WGS start on the DNA dest froze **WGS params from the work order’s asked-for** onto the **DNA Test**. Test **`55f9cad9`** `(DNA, WGS)` has `{library_kit: TruSeq}` from blood WO **`4ea9de0c`**, **not** `{}`, **not** Qubit params. Seq-1 on `bf51b19` did **not** score this. Merge `5040f2d` did **not** include it — do **not** rewrite that merge as a hold. Leftover **`9f86d14`** on **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`) **is** this Grok Build work (pytest in that same commit). **Was not recoded.** **Do not** treat leftover as a UAT click. Lookup: (1) WO asked-for **only if** `asked.analysis_id == run.analysis_id`; (2) else walk `parent_sample_id` for a routed asked-for of that analysis; (3) else `{}`; (4) freeze skip: write onto NULL; do not overwrite an already-frozen payload including locked empty `{}`. **Pass / Fail / not-a-Fail** stay the AC definition. It is **not** freeze skip and **not** dest-follow.
3. **Closeout 1.4 — Quantified DNA (CEO Confirm 1–6 Rolf; OQ-WO-8 OPEN):** The SKU is **data**, not a tube-only product. **Quantified DNA is an assay ask.** **Qubit is the asked-for LimsRun** (exactly one; wear existing Qubit `analysis_id`; Test `(DNA, Qubit)` is the ask). Do **not** mint a second catalog analysis named Quantified DNA. **Other process QC** (Nanodrop, …) may sit — other analyses, own Tests, **not** a second asked-for. Extract stays experiment / equipment; **no** analysis_id; **no** boolean `extracted = True/False` Result. Old 1.4 (zero LimsRuns) **struck**. 422 on 0 LimsRuns is **right** for this SKU. WGS/WES/ELISA unchanged: Qubit stays process QC on those asks. Tube-only DNA later SKU. Named asked-for LimsRun slot is a **punch pending Leadership Confirm** (not part of 1–6; not Closed). Send: [2026-09-01-p2-closeout-1-4-quantified-dna](../../discussions/2026-09-01-p2-closeout-1-4-quantified-dna.md).
4. **Overall P2 Pass** — unsigned. Leadership did not stamp overall Pass. Closeout **1.4** has **CEO Confirm 1–6 (Rolf)**; **OQ-WO-8 stays OPEN**. Do not write Full Leadership Confirm or overall Pass from this fold.
5. **Merge** — **Landed** `5040f2d` with OQ-WO-7 OPEN. Do not invent overall P2 Pass. Freeze skip NULL **Pass** on `bf51b19` is not a hold.

Do **not** recode dest-follow, cardinality, freeze skip NULL, or Route two-accept 409 unless a new Fail lands.

---

## Coding leftover (OQ-WO-7 after merge)

| # | Gap | Now | Do |
|---|-----|-----|----|
| **1.1 Cardinality 1** | Two ELISA LimsRuns must 422 | **Done.** Tobias Pass `bf51b19` | Do not re-score |
| **1.2 / OQ-WO-7** | WGS params on the DNA Test from the WO after C3 | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Code on `main` via leftover **`9f86d14`**. Seq-1 Pass without scoring dest-cohort params | **Do not recode.** Lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`) **was not recoded** |
| **1.3 Freeze skip NULL** | Classic `{}` vs frozen `{}` | **Done** (`0078`). Tobias Pass `bf51b19` | Do not transfer `99b692d3` |
| **1.4 Quantified DNA** | Tube-only zero-LimsRun vs assay ask | **CEO Confirm 1–6 (Rolf).** Wear existing Qubit. Old 1.4 struck. **OQ-WO-8 OPEN.** Named-slot pending | **Do not code** extract-only / zero LimsRuns / boolean Test / second Quantified DNA analysis / named-slot as closed |

**Do not code:** route branching; dest auto-join second WO; copy WGS params onto WES; second asked-for for Qubit; analysis picker on `/receive`; 2+ routes picker; P3–P5. Do not forever-ban extract-as-LimsRun — later, if equipment is an instrument.

---

## Standing UAT rule (Leadership Confirm 2026-09-01)

After **two** UAT attempts on the same issue, the **next** run needs a written “what we are testing and why” **before** the click — fixtures, Pass/Fail, and what is **not** a Fail. Do **not** rewrite signed stamps (`bf51b19`, `8cfa2a9`, `9342439`, P1, `02fe95f`, Deiter `570bbc0` Lab Ops Met) to satisfy this rule.

**Science (2026-09-01):** same grain. OQ-WO-7 lands as **Brief → code → UAT with Pass/Fail and not-a-Fail → stamp → merge**. Clarifying WGS params on the DNA Test from the WO after C3 made the product better. Not IC50.

**CEO Accept (Rolf, 2026-09-01):** Accept Hans’s written what/why as **AC-P2-OQ-WO-7** before Tobias. Pass/Fail and not-a-Fail as in that brief. “Grok Build codes first” is **done** (`9f86d14` on `80f054b`). Remaining work is **Tobias**. Result stays **unsigned**. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. **In-bar**. Do **not** rewrite `bf51b19`. Not IC50.

**Tobias Result (2026-09-01):** **AC-P2-OQ-WO-7 Pass** on `80f054b`. Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** not recoded. **OQ-WO-7 Closed.** Closeout **1.4** stays OPEN. Overall P2 unsigned. Does **not** rewrite `bf51b19`. Not IC50.

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
| AC-P2-seq-1 two WOs | **Pass** — 1.2 / OQ-WO-7 not scored on `bf51b19` |
| AC-P2-OQ-WO-7 WGS params from WO after C3 | **Pass** (Tobias, 2026-09-01, `80f054b`) — Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**; leftover **`9f86d14`** not recoded |
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
| OQ-WO-7 dest-cohort params (1.2) | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Code on `main` via **`9f86d14`** | **Do not recode.** Lookup was not recoded. Closeout **1.4** still OPEN |
| Quantified DNA (1.4) | **CEO Confirm 1–6 (Rolf).** Wear existing Qubit. **OQ-WO-8 OPEN.** Named-slot pending | Deiter/Hans/Heidi/Günter stamp to close OQ-WO-8. Do **not** code zero-LimsRun extract-only or named-slot as closed |
| Historical Route/WO-7/AC-P2-9..11 | **Signed Pass** | Do not re-score |
| Asked-for-only Marc lock (PR 111) | **Stands** | Do not rewrite |
| ELISA / second-tube | **Leadership Confirm 2026-09-01** | ELISA not on DNA; two blood tubes → two assignments (`container_id`); OQ-WO-6 still assay LimsRun only |
| Standing UAT two-attempt rule | **Folded** | After two UAT attempts on the same issue, next run needs written “what we are testing and why” before the click |
| Science 2026-09-01 | **Folded** | Per-AC Pass. Overall unsigned. Merged with OQ-WO-7 OPEN. Leftover `9f86d14` is this work on `80f054b`. History. Not IC50 |
| CEO Accept (Rolf) of Hans AC-P2-OQ-WO-7 brief | **Folded** 2026-09-01 | Written what/why Accept before Tobias. Grok Build (`9f86d14`) is on `80f054b`. History. Not IC50 |
| Tobias AC-P2-OQ-WO-7 Pass | **Folded** 2026-09-01 | Pass on `80f054b`. Test `55f9cad9` TruSeq from WO `4ea9de0c`. `9f86d14` not recoded. OQ-WO-7 Closed. 1.4 later. Overall unsigned |
| Overall P2 Pass | **Unsigned** | Do not invent from this fold. 1.4 has CEO Confirm 1–6; OQ-WO-8 OPEN. Do not write Full Leadership Confirm |
| Merge to `main` | **Landed** `5040f2d` | With OQ-WO-7 OPEN (history) |
