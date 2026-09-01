# P2 closeout — merge `feat/work-order-p2` to `main`

**Date:** 2026-08-31  
**Branch:** `feat/work-order-p2` @ `2759649`  
**Stem:** `post-receive-work-spine`  
**Merge bar:** full-pipeline UAT Pass, then merge to `main`. Overall P2 is **unsigned / not Pass** today. Hold merge until the items below that you treat as in-bar are green.

This is a working list, not a Leadership Confirm and not a UAT Result stamp. Do **not** rewrite signed UAT (`9342439`, `8cfa2a9`, `b005cfe`, `9c4f9da`, `3b56cfb`, P1 `c649245`, Deiter `02fe95f`).

---

## 0. What already shipped (do not reopen)

| Slice | Status | SHA / note |
|-------|--------|------------|
| P1 asked-for lake | **Pass**, on `main` | `c649245` / PR 81 |
| Receive freeze (no analysis picker; non-empty `analysis_ids` → 422) | **Pass** | Do not reopen CORE |
| Explicit Route; ordered `process_definition[]`; first Start = `chain[0]` only | **Pass** | `8cfa2a9` |
| Empty Route 422; map overlap 409 (TAT ∩ first-step types ∩ LimsRun analysis **sets**); Blood extract + later DNA qPCR map-save 201 (not AND) | **Pass** | `8cfa2a9` UI click-save |
| WO-7 publish refuse whole run (`test_missing` 422) | **Pass** | `8cfa2a9` / history `b005cfe` |
| AC-P2-9..11 (no map analysis/type picker; derived types; map-save handoff 422) | **Pass** | `9342439` |
| Later-step type-gate (qPCR start on still-Blood 422) | **Pass** | `9342439` (not dest-type E2E) |
| Contents assignment (`0077`): no vessel / two vessel 422; receive-tube 201 | Deiter **Pass** | `02fe95f` — Lab Ops click, not Tobias QA |
| Dest-follow execute (C2 same Sample + extra container; C3 derivative + `parent_sample_id`; dest join in execute txn) | **Coded** | `1572071`. Deiter Lab Ops **Met** on `570bbc0`. Tobias **unsigned** |
| OQ-WO-6 extract punch | **CLOSED** | Extract is a **process**, not a LimsRun. Exactly one asked-for LimsRun = assay step. Supporting QC = same-route LimsRuns, own Tests |
| Dest mint only at execute | **Leadership Confirm** | Route / Start / map-save / asked-for mint **zero** daughters |
| No route branching this phase | **Marc lock, pending Leadership overwrite** | WGS on blood (owns WGS params); C3 DNA; C2 aliquot continues WGS; **WES = new asked-for on the DNA tube, then aliquoted or used up** (own params) |

**Out of this merge on purpose:** route branching / dest auto-joining a second WO; 2+ matching routes **picker** (product is **409**, not pick); P3 results persist; P4 SOP Apply; P5 parser setup; IC50.

---

## 1. Decision before more code

Leadership (Marc) should pick the merge bar. Two honest options:

**A — Merge dest-follow + route grain, leave freeze skip OPEN.** Tobias Passes C2/C3 (and any new ACs you add below). Freeze skip stays a follow-up. Overall P2 stamp can say **Pass except freeze skip** if Leadership accepts that.

**B — Freeze skip is in-bar.** Then coding item 1.3 must land **before** Tobias restamps freeze, and classic `/tests` must leave `asked_for_params` **NULL** (or a freeze marker must exist). Do not score skip-on-`{}` as Pass on current schema — `tests.asked_for_params` is `NOT NULL DEFAULT '{}'`.

Recommended if the goal is “merge this to main now”: **A**, plus coding 1.1 and 1.2 so the live lock does not Fail UAT.

---

## 2. Coding (Grok Build)

### 2.1 Must for the live lock (do these before Tobias restamps new ACs)

| # | Gap | Why it fails UAT if scored as written | Where |
|---|-----|----------------------------------------|--------|
| **1.1 Cardinality 1 among LimsRuns** | Docs: map-save / Route **422** if the asked-for analysis appears **0 or 2+** times among LimsRun steps. Two ELISA LimsRuns refused (they would share one Test `(sample, ELISA)` — not QC). | **Coded.** Map-save 422 if any LimsRun `analysis_id` appears twice. Route requires asked-for count **exactly 1** (supporting QC other analyses still legal). Zero LimsRuns still 422. Overlap 409 still uses the unique analysis **set**. Pytest in `test_work_order_p2.py`. | `backend/app/services/routing_service.py` |
| **1.2 WO-7 asked-for lookup after C3** | Docs: WGS asked-for on **blood** owns WGS params. C3 mints DNA; later LimsRun is the assay step on the dest cohort. | `_mint_tests_at_start` looks up `AskedFor` with `sample_id == cohort sample` **and** `analysis_id == run.analysis_id`. After C3 the cohort is **DNA**; the WGS asked-for is still on **blood** → params come back `{}`. Need lookup via the work order’s `asked_for_id` (or parent lineage), not dest `sample_id`. | `backend/app/services/lims_run_service.py` ~314–324 |

Pytest to add with those patches:

- Map-save **422** when a chain has two LimsRuns with the same asked-for `analysis_id`.
- Map-save **201** when extract (process, no `analysis_id`) + one ELISA LimsRun + one Qubit LimsRun (other analysis).
- Route **422** when asked-for analysis count among LimsRuns is 0 or 2+; **200** when count is 1 (supporting QC allowed).
- After C3 DNA dest, first start of the WGS LimsRun writes `asked_for_params` from the **blood** asked-for, not `{}`.

### 2.2 Freeze skip (only if merge bar B)

| # | Gap | Work |
|---|-----|------|
| **1.3 Classic NULL or freeze marker** | `tests.asked_for_params` is `nullable=False, server_default='{}'`. First start cannot tell classic default `{}` from frozen `{}`. `if test: continue` is **not** a freeze. | **Coded (NULL path).** Alembic `0078`: column nullable, no `{}` server default. Existing `{}` rows left as frozen empty. Classic `POST /tests` writes NULL. First LimsRun start writes onto NULL. Later start does not overwrite NULL-after-write or frozen `{}`. Tobias still unsigned. |

### 2.3 Verify, do not recode unless Tobias Fails

| # | Item | Note |
|---|------|------|
| Route two-accept **409** | **Coded** (`len(acceptable) > 1` → 409). Unsigned UAT only. | No picker this phase. |
| Contents remaining-volume 422 | **Coded** (`contents_has_remaining`; amount 0 not assignable; NULL amount still a vessel). | |
| Dest-follow join without `process_step_id` | **Coded** (`_follow_destination_in_process`). | Deiter Fail on `02fe95f` is history. |
| `0074` catalog visibility | Migration exists; alice Route+Start **Pass** on `8cfa2a9`. Docs still list P2-4 as open. | Only recode if a lab-tech still cannot **read** the mapped def/steps at Route. |
| Map-save 201 same inbound types, different LimsRun analyses | **Coded** as set overlap, not AND. Unsigned as a dedicated AC. | Covered in spirit by `8cfa2a9` extract-first vs Qubit-first. |

### 2.4 Do not code for this merge

- Route branching / one WO splitting to WGS+WES.
- Dest auto-joining a second work order.
- Copying WGS params onto a WES asked-for.
- Extract as a LimsRun / hanging asked-for `analysis_id` on extract.
- Second asked-for for Qubit/Nanodrop (those are supporting LimsRuns, own Tests).
- Analysis picker on `/receive`.
- 2+ routes UI picker (stay 409).
- P3–P5.

---

## 3. UAT script updates (`UAT_Scripts/uat-post-receive-work-spine.md`)

Keep signed stamps as history. Add or punch **unsigned live ACs** so Tobias scores the lock, not leftover wording.

### 3.1 Already numbered — do not rewrite the steps; Tobias restamps Results

| AC | Live click | Tobias |
|----|------------|--------|
| **AC-P2-C1** assignment identity (no vessel / two vessel 422; receive-tube 201) | Deiter Pass `02fe95f`; Lab Ops Met `570bbc0` | **Unsigned** — restamp on live SHA |
| **AC-P2-C2** same dest type (tube → plate): same Sample, extra container, inbound `removed` even with leftover volume, Later Start follows dest | Numbered on `570bbc0`; execute `1572071`; Lab Ops Met | **Unsigned** |
| **AC-P2-C3** Blood → DNA: new Sample + container, `parent_sample_id`, parent stays Blood, Later Start follows DNA | Same | **Unsigned**. Same click as extract-hold **1.7** |

Fixture honesty already in the script (keep):

- Set Contents amount **before** execute (`PATCH` contents, not `eln_process_samples`). **400 `source_amount_null` is setup, not Fail.**
- C2 leftover inbound volume is **not** Fail. Emptying is not required.
- No dest at Route / Start / map-save is **intended**, not Fail.
- DNA execute is **C3**, not a C2 Fail.

### 3.2 Add (or punch) so the script matches expected product

| New / punch | Expected | Notes |
|-------------|----------|--------|
| **AC-P2-card-1** map-save two ELISA LimsRuns | **422** | **In script** (live unsigned stamp). |
| **AC-P2-card-2** map-save extract (process) + Qubit LimsRun + ELISA LimsRun | **201** | **In script.** |
| **AC-P2-card-3** Route when asked-for analysis missing from chain / appears twice | **422**, asked-for stays `requested`, no WO | **In script.** Do not re-score empty Route on `8cfa2a9`. |
| **AC-P2-qc-1** Qubit in the **same** route as the asked-for assay | Qubit gets its **own** Test `(sample, Qubit)` at Qubit LimsRun start. Asked-for analysis still once on the assay LimsRun. Do **not** put Qubit/Nanodrop on extract. | **In script.** |
| **AC-P2-4 freeze skip NULL** | Classic `/tests` NULL; first start writes; later start does not overwrite | **In script.** Requires `0078`. Do not transfer `99b692d3` `{}`. |
| **AC-P2-seq-1** sequential asked-fors (WGS then WES) | Route **blood** for WGS; C3 DNA; C2 aliquot continues WGS; **new asked-for on the DNA tube** for WES; aliquot or use up. Two WOs. Dest does **not** auto-join WES. | **In script.** Dest-cohort params (1.2) is **not** this AC. |
| **AC-P2-5 addendum** Route two-accept **409** | Two saved maps that both accept this type **and** this analysis → **409**, no silent `first()` | **In script.** Do not re-score the rest of AC-P2-5. |
| Extract is a process | Do **not** author extract as a LimsRun wearing ELISA. | Honesty for map-save, not a dest-follow Fail. |

### 3.3 Do not add / do not score

- Dest existing at Route, Start, or map-save.
- Emptying the C2 source as a Pass condition.
- DNA dest scored as C2.
- Rewrite of `9342439` dest-type mint Hold (Start-extract still Blood / 0 DNA is **history**, not a ban on C3).

---

## 4. What Tobias needs to do

Work the **live** SHA on `feat/work-order-p2` (not `570bbc0` as a product execute SHA — that was docs/UAT numbering). Execute joints are **`1572071`**. Fold Results into the live dest-follow stamp; do not transfer Pass/Fail onto older SHAs.

**Required for dest-follow merge bar**

1. **AC-P2-C1** — Pass or Fail on live SHA (Deiter Pass is Lab Ops only).
2. **AC-P2-C2** — numbered execute click. Fail only if new Sample, dest not on process, or Later Start follows the parent tube. Leftover volume ≠ Fail. `source_amount_null` ≠ Fail if amount was never set.
3. **AC-P2-C3** — numbered execute click. Fail if dest lands on Blood Sample, parent `container_id` retargeted, dest not on process, or Later Start follows Blood.

**Required if 2.1 / 3.2 land before the restamp**

4. Cardinality ACs (two ELISA 422; extract+Qubit+ELISA 201; Route 0/2+ 422).
5. Supporting-QC own Test.
6. Sequential asked-fors (WGS params stay on WGS WO; WES new asked-for on DNA tube).
7. Route two-accept **409** (the existing unsigned step).

**Do not**

- Re-score signed Passes on `8cfa2a9` / `9342439` / P1.
- Score freeze skip as Pass on `{}`.
- Score no-dest-at-Route/Start as dest-follow Fail.
- Score DNA as C2.
- Claim overall P2 Pass if C2/C3 Fail, or if freeze skip is in-bar and still OPEN.

After clicks: one docs commit that writes Tobias Results into the **live** stamp only.

---

## 5. Leadership / product (not Tobias)

| Item | Status | Needed to merge? |
|------|--------|------------------|
| Sequential asked-fors (WGS on blood; WES on DNA tube, then aliquot or use up) | **Marc lock, pending overwrite** | Yes — Confirm or rewrite before teaching it as shipped |
| Freeze skip OPEN vs in-bar | OPEN | Decision in §1 |
| OQ-WO-6 extract CLOSED | **Confirm already landed** | No restamp |
| Supporting QC same-route | Rolf/Marc Confirm landed | No restamp |
| Overall P2 Pass | Unsigned | Tobias Results + (optional) freeze decision |

---

## 6. Suggested order

1. **Marc:** pick merge bar A vs B (§1). Confirm sequential asked-fors wording (§5).
2. **Code 1.1 + 1.2** (cardinality count; WO-7 asked-for via work order). Pytest. Commit/push on `feat/work-order-p2`.
3. **Script 3.2** — add the unsigned ACs; leave signed stamps alone.
4. If bar **B**: code 1.3, then add a freeze-skip AC that uses **NULL**, not `{}`.
5. **Tobias** restamps C1/C2/C3 + new ACs + Route two-accept 409.
6. Docs fold of Results. **No overall Pass** until those Results are Pass (and freeze skip is either deferred or Pass).
7. Merge `feat/work-order-p2` → `main`.

---

## 7. One-page scoreboard

| Gate | Owner | Now | Merge needs |
|------|-------|-----|-------------|
| Cardinality 1 (count, not set) | Dev + Tobias | **Pass** on `bf51b19` | Do not re-score |
| WO-7 params after C3 | Dev | **Not coded** (1.2); **not scored** on seq-1 | Code if dest-cohort params are in-bar |
| Dest-follow C2/C3 | Tobias | **Pass** on `bf51b19` (Deiter Met stays Lab Ops) | Do not re-score |
| Assignment C1 | Tobias | **Pass** on `bf51b19` | Do not re-score |
| Route two-accept 409 | Tobias | **Pass** on `bf51b19` | Do not re-score |
| Map overlap 409 / empty Route 422 / first Start chain[0] / publish refuse / AC-P2-9..11 | — | **Signed Pass** | Do not re-score |
| Freeze skip NULL | Tobias | **Pass** on `bf51b19` (classic NULL; wrote `{cell_line: A549}`; later start left it) | Do not transfer `99b692d3` |
| Sequential asked-fors | Tobias | **Pass** two WOs on `bf51b19`; Leadership Confirm still pending overwrite | Dest-cohort 1.2 not scored |
| Route branching / picker / P3–P5 | — | Out of P2 | Do not build |
| Overall P2 Pass | Tobias + Leadership | **Unsigned** | Leadership Confirm + leftover 1.2 decision |
| Merge to `main` | Marc | **Held** | After overall P2 Pass |
