# P2 closeout — merge `feat/work-order-p2` to `main`

**Date:** 2026-09-01  
**Branch:** `feat/work-order-p2` leftover; product is on `main`  
**Click SHA:** `bf51b19` (`bf51b192b417663f677b80be6d8b9afd790cb78a`) — Alembic **`0078`**  
**Merge SHA:** `5040f2d` (`5040f2d` Merge feat/work-order-p2 into main) — feat tip at merge was `4b8c41f`  
**Docs stamp:** living closeout (this fold)  
**Execute joints:** `1572071`  
**Stem:** `post-receive-work-spine`  
**UAT:** [`UAT_Scripts/uat-post-receive-work-spine.md`](../../../UAT_Scripts/uat-post-receive-work-spine.md) live stamp `bf51b19`

**Now:** P2 is on `main`. Product SHA for **AC-P2-OQ-WO-7** is **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`). Tobias signed **per-AC Pass** on `bf51b19` (do **not** rewrite those Results). **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`) remains unchanged. Named-slot product landed on `feat/p2-named-slot` at **`6244bf6`** (`6244bf6e742c4ed0f046ff8770e2b8c112446fb3`), Alembic **`0079`**. **AC-P2-OQ-WO-8 Pass** (Tobias, 2026-09-03, `6244bf6`): `routing_map.asked_for_step_id` is the named slot; eligibility compares `asked.analysis_id` with that slot, not containment; one named Qubit match mints, zero returns 422, and 2+ returns 409 `route_pick_required` then mints only after the pick; WGS+Qubit-as-QC does not steal Quantified DNA. **Tobias overall P2 Pass (QA)** on `6244bf6` (2026-09-03 21:26 ET) folds per-AC Pass on `bf51b19` + OQ-WO-7 Pass on `80f054b` + OQ-WO-8 Pass on `6244bf6`. **Full Leadership Confirm overall P2 Pass** (Rolf / Deiter / Hans / Heidi / Günter, 2026-09-03) on the same SHA, folding that Tobias overall. Overall P2 Pass is **Met** / Leadership stamped. Distinct from Tobias QA. OQ-WO-8 Closed history from PR 119 and Confirm #2 / Brief from PR 120 remain unchanged. Same OQ-WO-7 lookup after C3; **do not recode.** Not IC50.

This is a working list. **Full Leadership Confirm overall P2 Pass** is stamped on `6244bf6` (2026-09-03). Do **not** rewrite signed UAT (`9342439`, `8cfa2a9`, `b005cfe`, `9c4f9da`, `3b56cfb`, P1 `c649245`, Deiter `02fe95f` C2 **Fail**, Tobias `bf51b19` per-AC, OQ-WO-7 on `80f054b`). Do **not** rewrite Deiter Lab Ops Met on `570bbc0`. Do **not** restamp unsigned Tobias C2/C3 on `570bbc0`.

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
| Cardinality 1 (map-save/Route 422 on 0 or 2+ asked-for LimsRuns) | Coded + Tobias **Pass** `bf51b19` for **assay** asked-fors. **1.4 Quantified DNA** is an assay ask (Qubit once) — **CEO Confirm 1–6 stands**; **OQ-WO-8 Closed** (named asked-for LimsRun slot; not contains-Qubit) |
| Supporting QC same-route, own Test | Tobias **Pass** `bf51b19` |
| Freeze skip NULL | Coded `0078` + Tobias **Pass** `bf51b19` (classic NULL; first start `{cell_line: A549}`; later start left it). `{}` on `99b692d3` stays `8cfa2a9` history. **Not** a merge hold |
| Route two-accept 409 | Tobias **Pass** `bf51b19` |
| Seq-1 sequential asked-fors (two WOs; WES on DNA tube) | Tobias **Pass** `bf51b19`. Dest-cohort params (**1.2** / **OQ-WO-7**) **not scored** on that SHA |
| OQ-WO-6 extract punch | **CLOSED** for the common path — extract is an **experiment** (equipment) and does not wear the panel `analysis_id`. **Not** a forever ban on extract-as-LimsRun. After extract on **WGS / WES / ELISA**, Qubit/Nanodrop is **process QC**, not the asked-for. Assay ask: one asked-for LimsRun. **1.4 Quantified DNA:** Qubit **is** the asked-for LimsRun (**CEO Confirm 1–6 stands**; wear existing Qubit). **OQ-WO-8 Closed**. Named-slot Closed (eligibility vs named slot, not contains-Qubit) |
| Dest mint only at execute | **Leadership Confirm** |
| No route branching | **Full Leadership Confirm #2** (2026-09-03): keep the Marc lock; Seq-1 Pass is not this Confirm |
| Care about the asked-for only | **Full Leadership Confirm #2** (2026-09-03): keep PR 111 |
| ELISA not on DNA; second tube own asked-for; separate containers = separate assignments | **Leadership Confirm 2026-09-01** (Rolf/Deiter/Hans/Heidi/Günter) |
| OQ-WO-7 WGS params on DNA Test from WO after C3 | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** is the lookup — **was not recoded**. Merged `5040f2d` with OPEN — that history stands |
| Closeout 1.4 Quantified DNA | **OQ-WO-8 Closed history preserved** (PR 119). Wear existing Qubit; no second Quantified DNA analysis. Zero-LimsRun Extracted DNA clause struck. Product `6244bf6` / `0079` persists `routing_map.asked_for_step_id`; **AC-P2-OQ-WO-8 Pass** verifies named-slot eligibility and 0/1/2+ behavior. |
| AC-P2-OQ-WO-8 named slot + picker | **Pass** Tobias, `6244bf6` (`feat/p2-named-slot`, `0079`). Named slot is `routing_map.asked_for_step_id`; 0→422, 1→mint, 2+→409 `route_pick_required` then pick mints; no containment steal |
| Tobias overall P2 Pass (QA) | **Pass** 2026-09-03 21:26 ET, `6244bf6` / `0079`. Folds `bf51b19` (`0078`; card-1/2/3, qc-1, freeze skip NULL, Route two-accept 409, seq-1 with 1.2 not scored, C1/C2/C3) + `80f054b` (OQ-WO-7) + `6244bf6` (OQ-WO-8) |
| Leadership overall P2 Pass | **Met** / **Pass**. Full Leadership Confirm (Rolf / Deiter / Hans / Heidi / Günter, 2026-09-03) on `6244bf6`, folding Tobias overall |
| Merge to `main` | **Landed** `5040f2d` with OQ-WO-7 OPEN (history) |

**Out of the merge on purpose:** route branching / dest auto-joining a second WO; named-slot product and the **2+ matching-route picker**; P3–P5. The older “product is 409 only / no picker” teaching is superseded. **OQ-WO-7** stayed known OPEN.

---

## Left after merge (not a merge hold)

1. **Full Leadership Confirm #2 folded** (Rolf / Deiter / Hans / Heidi / Günter, 2026-09-03): WGS on blood owns WGS params; C3 DNA; C2 aliquot continues WGS; WES = new asked-for on the DNA tube, then aliquoted or used up; own params. Tobias Seq-1 Pass of two WOs is **not** that Confirm.
2. **OQ-WO-7 / closeout 1.2 — Closed. AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). After C3 (Blood→DNA) WGS start on the DNA dest froze **WGS params from the work order’s asked-for** onto the **DNA Test**. Test **`55f9cad9`** `(DNA, WGS)` has `{library_kit: TruSeq}` from blood WO **`4ea9de0c`**, **not** `{}`, **not** Qubit params. Seq-1 on `bf51b19` did **not** score this. Merge `5040f2d` did **not** include it — do **not** rewrite that merge as a hold. Leftover **`9f86d14`** on **`80f054b`** (`80f054b274b02bb48f9dcbba5a05378419ea6b90`) **is** this Grok Build work (pytest in that same commit). **Was not recoded.** **Do not** treat leftover as a UAT click. Lookup: (1) WO asked-for **only if** `asked.analysis_id == run.analysis_id`; (2) else walk `parent_sample_id` for a routed asked-for of that analysis; (3) else `{}`; (4) freeze skip: write onto NULL; do not overwrite an already-frozen payload including locked empty `{}`. **Pass / Fail / not-a-Fail** stay the AC definition. It is **not** freeze skip and **not** dest-follow.
3. **Named-slot product and Tobias click — done:** product `6244bf6` / `0079`; AC-P2-OQ-WO-8 **Pass**. Heidi Architecture Accept and Günter CSO Accept support the click; Deiter Lab Ops boundary is reflected in UAT. OQ-WO-8 Closed history remains unchanged.
4. **Tobias overall P2 Pass (QA) — done:** **Pass** 2026-09-03 21:26 ET on `6244bf6` (`0079`). Folds `bf51b19` (`0078`) per-AC Pass — card-1/2/3, qc-1, freeze skip NULL, Route two-accept 409, seq-1 with dest-cohort 1.2 not scored, C1/C2/C3 — plus OQ-WO-7 Pass on `80f054b` and OQ-WO-8 Pass on `6244bf6`. No folded per-AC Result line is rewritten.
5. **Leadership overall Pass — Met.** **Full Leadership Confirm overall P2 Pass** (Rolf / Deiter / Hans / Heidi / Günter, 2026-09-03) on `feat/p2-named-slot` tip `6244bf6`, folding Tobias overall. Distinct from the QA stamp. Kept: no route branching; asked-for only; named-slot (`asked.analysis_id` vs the LimsRun on a process in the route, not containment); 0→422 / 1→mint / 2+→picker / no silent `first()`; OQ-WO-7 Closed; Quantified DNA wears existing Qubit; ELISA not on DNA; dest-follow stands; Route stays `test:assign`; instantiate uses existing process AuthZ.
6. **Merge** — **Landed** `5040f2d` with OQ-WO-7 OPEN (history). Named-slot **code is not on `main`**. Current tip after rebase onto `8887e36` is **`6a67667`**. `6244bf6` AC-P2-OQ-WO-8 Pass stays signed history of that SHA. Product merge waits on Tobias restamp of AC-P2-OQ-WO-8 on `6a67667` ([brief](../../discussions/2026-09-04-p2-named-slot-uat-restamp.md)). Freeze skip NULL **Pass** on `bf51b19` is not a hold.

Do **not** recode dest-follow, cardinality, freeze skip NULL, or Route two-accept 409 unless a new Fail lands.

---

## Coding leftover (OQ-WO-7 after merge)

| # | Gap | Now | Do |
|---|-----|-----|----|
| **1.1 Cardinality 1** | Two ELISA LimsRuns must 422 | **Done.** Tobias Pass `bf51b19` | Do not re-score |
| **1.2 / OQ-WO-7** | WGS params on the DNA Test from the WO after C3 | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Code on `main` via leftover **`9f86d14`**. Seq-1 Pass without scoring dest-cohort params | **Do not recode.** Lookup (WO asked-for same `analysis_id`, else parent lineage, else `{}`) **was not recoded** |
| **1.3 Freeze skip NULL** | Classic `{}` vs frozen `{}` | **Done** (`0078`). Tobias Pass `bf51b19` | Do not transfer `99b692d3` |
| **1.4 Quantified DNA** | Named asked-for LimsRun slot vs containment; ambiguous matching maps | **Done.** Product `6244bf6` / `0079`; AC-P2-OQ-WO-8 **Pass**. `routing_map.asked_for_step_id`; 0→422, 1→mint, 2+→409 `route_pick_required` then pick mints. | Do **not** recode OQ-WO-7 lookup or mint a second Quantified DNA analysis. |

**Do not code in this docs fold:** any product `.py` / `.ts` / Alembic; route branching; dest auto-join second WO; copy WGS params onto WES; second asked-for for Qubit; analysis picker on `/receive`; P3–P5. The named-slot and 2+ picker product is on `feat/p2-named-slot` @ `6244bf6`; this PR only records its stamps. Older “409 only / no picker” copy is superseded.

---

## Full Leadership Confirm #2 / current overall P2 punch list — 2026-09-03

**Full Leadership Confirm** (Rolf / Deiter / Hans / Heidi / Günter). Punch list:

1. **Named-slot + 2+ picker product:** **Done** on `6244bf6` / `0079`; Tobias **AC-P2-OQ-WO-8 Pass**.
2. **Confirm #2 folded:** no route branching and asked-for only remain; zero-LimsRun Extracted DNA clause is struck.
3. **Tobias overall Pass (QA):** **Pass** 2026-09-03 21:26 ET on `6244bf6`, folding `bf51b19` + `80f054b` + `6244bf6`.
4. **Leadership overall Pass:** **Met** / stamped. Full Leadership Confirm overall P2 **Pass** on `6244bf6`, folding Tobias overall.

**Not blocking this closeout:** ELISA/second-tube, destination follow, freeze skip, cardinality, OQ-WO-7, historical 1.4 docs, unsigned `570bbc0` C2/C3, P3–P5.

---

## Standing UAT rule (Leadership Confirm 2026-09-01)

After **two** UAT attempts on the same issue, the **next** run needs a written “what we are testing and why” **before** the click — fixtures, Pass/Fail, and what is **not** a Fail. Do **not** rewrite signed stamps (`bf51b19`, `8cfa2a9`, `9342439`, P1, `02fe95f`, Deiter `570bbc0` Lab Ops Met) to satisfy this rule.

**Science (2026-09-01):** same grain. OQ-WO-7 lands as **Brief → code → UAT with Pass/Fail and not-a-Fail → stamp → merge**. Clarifying WGS params on the DNA Test from the WO after C3 made the product better. Not IC50.

**CEO Accept (Rolf, 2026-09-01):** Accept Hans’s written what/why as **AC-P2-OQ-WO-7** before Tobias. Pass/Fail and not-a-Fail as in that brief. “Grok Build codes first” is **done** (`9f86d14` on `80f054b`). Remaining work is **Tobias**. Result stays **unsigned**. **OQ-WO-7 stays OPEN / AC unsigned** until Tobias stamps. **In-bar**. Do **not** rewrite `bf51b19`. Not IC50.

**Tobias Result (2026-09-01):** **AC-P2-OQ-WO-7 Pass** on `80f054b`. Test **`55f9cad9`** `(DNA, WGS)` `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Leftover **`9f86d14`** not recoded. **OQ-WO-7 Closed.** Closeout **1.4 / OQ-WO-8** is **Closed** by later Full Leadership Confirm (2026-09-02). Overall P2 unsigned. Does **not** rewrite `bf51b19`. Not IC50.

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
| AC-P2-OQ-WO-8 named slot + picker | **Pass** (Tobias, 2026-09-03, `6244bf6`) |
| Tobias overall P2 (QA) | **Pass** 2026-09-03 21:26 ET, `6244bf6`, folding `bf51b19` + `80f054b` + `6244bf6` |
| Leadership overall P2 | **Met / Pass** (Rolf / Deiter / Hans / Heidi / Günter, 2026-09-03) on `6244bf6` |

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
| OQ-WO-7 dest-cohort params (1.2) | **Closed.** **AC-P2-OQ-WO-7 Pass** (Tobias, 2026-09-01, `80f054b`). Test **`55f9cad9`** `{library_kit: TruSeq}` from WO **`4ea9de0c`**. Code on `main` via **`9f86d14`** | **Do not recode.** Lookup was not recoded. Closeout **1.4 / OQ-WO-8 Closed** (named slot) |
| Quantified DNA (1.4) | **OQ-WO-8 Closed.** Product `6244bf6` / `0079`; **AC-P2-OQ-WO-8 Pass**. Wear existing Qubit. Named slot is `routing_map.asked_for_step_id`; eligibility is `asked.analysis_id` vs that slot, not containment; 2+ uses `route_pick_required` then explicit pick | Do **not** recode OQ-WO-7 lookup. Do **not** code zero-LimsRun extract-only |
| Historical Route/WO-7/AC-P2-9..11 | **Signed Pass** | Do not re-score |
| Asked-for-only Marc lock (PR 111) | **Stands** | Do not rewrite |
| ELISA / second-tube | **Leadership Confirm 2026-09-01** | ELISA not on DNA; two blood tubes → two assignments (`container_id`); OQ-WO-6 still assay LimsRun only |
| Standing UAT two-attempt rule | **Folded** | After two UAT attempts on the same issue, next run needs written “what we are testing and why” before the click |
| Science 2026-09-01 | **Folded** | Per-AC Pass. Overall unsigned. Merged with OQ-WO-7 OPEN. Leftover `9f86d14` is this work on `80f054b`. History. Not IC50 |
| CEO Accept (Rolf) of Hans AC-P2-OQ-WO-7 brief | **Folded** 2026-09-01 | Written what/why Accept before Tobias. Grok Build (`9f86d14`) is on `80f054b`. History. Not IC50 |
| Tobias AC-P2-OQ-WO-7 Pass | **Folded** 2026-09-01 | Pass on `80f054b`. Test `55f9cad9` TruSeq from WO `4ea9de0c`. `9f86d14` not recoded. OQ-WO-7 Closed. 1.4 later. Overall unsigned |
| Tobias overall P2 Pass (QA) | **Pass** `6244bf6` | Folds `bf51b19` + `80f054b` + `6244bf6` (21:26 ET) |
| Leadership overall P2 Pass | **Met / Pass** | Full Leadership Confirm on `6244bf6`, folding Tobias overall |
| Merge to `main` | **Landed** `5040f2d` | With OQ-WO-7 OPEN (history) |
