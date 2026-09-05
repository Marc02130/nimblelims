# Team brief: named-slot UAT restamp, then merge to main

**Date:** 2026-09-04  
**To:** Tobias (click) · Marc (merge if Pass) · Leadership (witness, do not rewrite prior stamps)  
**Status:** Tobias clicked **Pass** on `effd242` (product `6a67667`). Merge-gate restamp recorded as a **new** AC-P2-OQ-WO-8 Result. This is not a rewrite of overall Leadership P2 Pass.  
**Product code:** `6a67667` (`6a67667b4d6378877a38e5542077df316a35077f`) · Alembic **`0079`**  
**Click SHA:** `effd24215b23e1bf9e73a00467a11bdc02bd6eb2` (`effd242`) on `feat/p2-named-slot`. Product `6a67667` is an ancestor of the click SHA. Do **not** click `main`.  
**AC:** [AC-P2-OQ-WO-8](../../UAT_Scripts/uat-post-receive-work-spine.md)  
**Gate:** Tobias Pass on **that recorded SHA** → stamp a **new** Result block → merge `feat/p2-named-slot` to `main`. Fail → **do not merge**.

Do **not** rewrite signed Results on `6244bf6`, `8887e36`, `bf51b19`, `80f054b`, `9342439`, `8cfa2a9`, P1, or Deiter `02fe95f`. The 2026-09-03 Pass on `6244bf6` stays history of that SHA. Named-slot **code is not on `main`**. `8887e36` on `main` is docs stamps only.

Not IC50. Do **not** recode OQ-WO-7.

---

## Why this run

`6244bf6` was rebased onto `8887e36` → current tip **`6a67667`**. Same named-slot product, new SHA. Merge to production still requires a click on the SHA that will land.

This restamp is the merge gate. It is **not** a rewrite of the `6244bf6` Result.

---

## What we are testing and why

Route must compare `asked.analysis_id` to the map author’s named asked-for LimsRun slot (`routing_map.asked_for_step_id`). Chain **containment** is not enough: a WGS map that includes Qubit as process QC must **not** accept a Quantified DNA ask.

After that filter:

| Eligible maps | Required |
|---------------|----------|
| **0** | **422**, no work order, asked-for stays `requested` |
| **1** | mint exactly one work order from that map |
| **2+** | **409** `route_pick_required`; UI **Select a route**; mint **only after** the pick |

No silent `first()`. Wear the **existing Qubit** catalog analysis. Do **not** create an analysis named Quantified DNA.

---

## Setup (do this first)

Stay on **`feat/p2-named-slot`**. Do **not** `git pull origin main` onto this branch. Do **not** rebuild `main` against a DB that already has `0079` (that is the crash you already hit).

```bash
git fetch origin
git checkout feat/p2-named-slot
git pull --ff-only origin feat/p2-named-slot
git rev-parse HEAD
git merge-base --is-ancestor 6a67667 HEAD && echo "named-slot code present"

# If the stack is already this SHA and /health is 200, skip rebuild.
docker compose down
docker compose up -d --build
curl -sS http://localhost:8000/health
docker compose logs backend --tail 30
# expect: MIGRATIONS COMPLETED SUCCESSFULLY
# not: Can't locate revision identified by '0079'
```

`docker system prune -af` does **not** delete the Postgres volume. If you truly need an empty DB: `docker compose down -v` (this wipes data). Prefer keeping the volume if `0079` already applied.

**App:** http://localhost:3000 · **API:** http://localhost:8000  

| Role | Login | Use for |
|------|-------|---------|
| Admin | `admin` / `admin123` | `/admin/routing-map` maps |
| Tech | `alice-tech` / `alice123` | `/receive` then `/asked-for` Route (needs `test:assign`) |

Compose **down** after the run.

---

## Dogfood (Marc / builder) — before Tobias

Walk the three Route outcomes once so Tobias is not debugging setup. Record: who, datetime, SHA `6a67667`. Dogfood is **not** the UAT Result. If dogfood fails, stop and fix; do not send Tobias a broken stack.

---

## Fixture (must be true or the AC is invalid)

The named-slot proof **collapses** if map A and map B differ by sample type or TAT. Then WGS is excluded by type/TAT, not by slot.

1. Wear **existing Qubit**. Do not mint a second catalog analysis named Quantified DNA.
2. **Map A (Quantified DNA):** chain includes Qubit. **Asked-for LIMS Run** = the Qubit step. TAT window that will match the ask.
3. **Map B (WGS + Qubit as QC):** chain includes WGS **and** Qubit. **Asked-for LIMS Run** = the **WGS** step, not Qubit. **Same first-step sample type** and **overlapping TAT** as map A.
4. Three **DNA** (or whatever type both maps accept at first step) samples, Available-for-Testing. Receive with **no** analyses on `/receive`. Stay on receive.
5. Three Quantified DNA asked-for rows (analysis = **Qubit**, TAT inside that window, status `requested`). Record as Ask-1 / Ask-2 / Ask-3.

**Admin UI:** Admin → **Routing map** (`/admin/routing-map`). Add processes. Set **Asked-for LIMS Run** (dropdown: `Process N · <process> · <step> · <analysis>`). Save.

If a chain has only one LimsRun, the slot auto-fills. For map B you **must** pick WGS, not Qubit.

**Deactivate / delete maps** only when the numbered steps say so. Do not leave leftover Qubit-slot maps from other tests in the TAT window.

---

## Numbered click (Tobias, `alice-tech`)

Use the **row Route icon** on `/asked-for`, not **Route selected**. Batch Route does not open the picker.

**Ask-1 — one eligible named slot**

1. Only map A is an acceptable Qubit-slot map (map B stays active; it must **not** match).
2. Route Ask-1.
3. **Pass so far:** one work order minted; asked-for → `routed`; map B did not win.

**Ask-2 — zero eligible maps**

4. Deactivate or delete **all** maps whose named slot is Qubit (keep map B if you want; it still must not match).
5. Route Ask-2.
6. **Pass so far:** **422** “No routing-map row accepts this analysis, TAT, and sample type”; **no** work order; Ask-2 stays `requested`.

**Ask-3 — two or more, then pick**

7. Restore **two** (or more) active maps whose named slot is Qubit, overlapping TAT, same first-step type.
8. Route Ask-3.
9. **Pass so far:** dialog **Select a route** (“More than one authored route accepts this asked-for. Choose one. This does not start work.”). **No** work order yet. Ask-3 still `requested`. Network: **409** `route_pick_required` with `candidates`.
10. Click one candidate.
11. **Pass so far:** exactly one work order from the **chosen** `routing_map_id`; Ask-3 → `routed`. The other candidate did not mint.

Record in the Result (like OQ-WO-7): SHA, time, sample names/types, Qubit `analysis_id`, map A/B ids, Ask-1/2/3 ids, work-order ids, HTTP codes. Without those IDs the stamp is incomplete.

---

## Pass

- Quantified DNA routes to the named Qubit slot.
- WGS+Qubit-as-QC does **not** steal Ask-1.
- Zero maps → 422, nothing minted.
- Two or more → picker; mint only after pick; no silent `first()`.
- Existing Qubit only.

## Fail

- Eligibility is “Qubit appears anywhere in the chain.”
- Map B wins Ask-1.
- 2+ maps mint without the dialog, or mint both, or pick `first()`.
- A second catalog analysis named Quantified DNA was created or required.
- Click was on `main` / wrong SHA / missing `0079`.
- Ask-1 “passed” because map B’s first-step type or TAT did not overlap — that is **not** this AC.

## Not a Fail

- OQ-WO-7 after C3.
- Destination follow / C2 / C3.
- Historical zero-LimsRun 1.4 copy.
- ELISA on a second tube.
- Route does not start a Test or LimsRun.
- `6244bf6` history.

---

## After the click

**If Fail:** stop. Write Fail + SHA + what broke in the UAT **new** block. Do **not** merge. Do **not** rewrite `6244bf6`.

**If Pass:**

1. Add a **new** live Result under AC-P2-OQ-WO-8 (or a restamp heading). Keep the `6244bf6` Result verbatim.
2. Note product-merge SHA **`6a67667`**. Do not move overall Leadership Pass off `6244bf6`; this restamp is the **merge click**, not a rewrite of overall P2.
3. Commit that stamp on `feat/p2-named-slot`.
4. Merge to `main`:

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff feat/p2-named-slot -m "Merge feat/p2-named-slot: named asked-for LimsRun slot (0079)"
git push origin main
```

Or open a PR from `feat/p2-named-slot` → `main` and merge after the stamp commit. Do not squash away `0079`.

5. `docker compose down` after the run.

**Do not merge** on dogfood-only, pytest-only, or the old `6244bf6` paper stamp. The merge SHA must contain `backend/db/migrations/versions/0079_asked_for_lims_run_slot.py`.
