# UI / UX Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** **Accept with conditions**  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/post-receive-work-spine.md) (Accept with conditions L1–L5)  
**Personas:** lab tech · lab manager · admin (`config:edit`) · client (read-only)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)

gstack `/plan-design-review` applied as **lab-workflow criteria** on the tech sketch (APP UI, not marketing). Interactive mockup / AskUserQuestion loop skipped: named packet target, no `DESIGN.md`, formal Nimble stamp only. Live-site `/design-review` is post-implement.

---

## Executive summary

Atomic receive CORE is shipped. Tubes land **Available for Testing** with **zero Tests**. The next screen the bench needs is **what was asked**, not a second Tests page.

**P1 is a request lake. P2 is the work list.** If `/asked-for` looks or reads like today’s Tests page, techs will treat it as Tests and WO-7 is dead on arrival. Lab Ops **L1** is the product bar; this stamp makes it pixels, copy, empty states, and errors.

Sketch UI completeness is **4/10**: it names `pages/AskedFor.tsx`, a sample-detail panel, sidebar after Receive, multi-select, and “reuse analysis dropdown not TestForm.” It does not specify hierarchy, empty states, 409/422 copy, scan-into-set, TAT due date, status chips, partial multi-sample failure, or the P2 split from the lake. Conditions below close that for implementers. **Do not revise the packet to invent a third engine or put analysis on `/receive`.**

**P1 may implement** if **U1–U8** land in the same PR. **P2 UX stays closed** until **U9–U11** plus Lab Ops **L2–L4** and **OQ-WO-1**. P3/P4/P5 bind later PRs (**U12–U14**).

**Verdict: Accept with conditions.**

---

## Flows reviewed

### P1 lake (this PR)

```
Receive (shipped, dumb)  →  stay on /receive
         │
         ▼  sidebar next item
 /asked-for
   pick 1..N Available-for-Testing samples (checkbox + scan-to-add)
   pick analysis + TAT days (+ params if defs exist)
   Save request
         │
         ▼
  asked-for rows status=requested
  zero Tests, zero Processes, zero LimsRuns, zero work_orders
  stay on /asked-for
```

Sample detail: same add + table. **Not** on `/receive`. **Not** TestForm.

### P2 work list (later PR — do not grow Start onto the P1 page)

```
asked-for requested
   map match?  yes → work_order queued (auto-route; OQ-WO-1)
               no  → stay requested; “No work plan” + configure-routing (admin)
   Work orders surface
     Start → existing process start (select / scan; cohort locks)
     complete step N → next ordered step in the same process
   LimsRun start → Test (WO-7); asked-for params frozen on Test
```

### P3 / P4 / P5 (later)

- P3: type numbers on an existing Test / results UI, **never** on asked-for.
- P4: SOP Apply → **draft process definition**; human save; not dest-type E2E.
- P5: admin parser example → test → dry-run → activate. AI = setup-only.

---

## Screen (P1) — what the user sees

Reuse existing app UI: `FillHeightPage` + `FillHeightTable` + MUI X DataGrid + `ListFilterChips`. Dense workspace, not cards.

```
Sample Mgmt
  Receive
  Asked-for          ← NEW, immediately after Receive
  Samples
  Tests              ← stays (WO-4 classic). Not the order path.
  …

/asked-for
┌──────────────────────────────────────────────────────────────────┐
│ Asked-for                                                        │
│ Record requested analyses. This does not start work.             │
│                                                                  │
│ [Record request]     filters: Project · Analysis · Status        │
│                                                                  │
│ sample | type | analysis | TAT | due | status | Cancel           │
│                                                                  │
│ Empty: Receive samples, then record what was asked.              │
│        [Go to Receive]  [Record request]                         │
└──────────────────────────────────────────────────────────────────┘

Record-request dialog
┌──────────────────────────────────────────────────────────────────┐
│ Request analysis                                                 │
│ Add samples: [scan / type barcode]  [Add]                        │
│ Selected (N): name · type · status   (remove)                    │
│ or checkbox grid of Available for Testing                        │
│ Analysis *                                                       │
│ TAT (days) *     Due 2 Sep 2026                                  │
│ Params: only if analysis_param_defs exist; else hidden           │
│ [Cancel]                    [Save request]                       │
└──────────────────────────────────────────────────────────────────┘
```

**Primary action:** Record / Save **request**. Never Start, Execute, Assign test, Create test, Order process.

---

## Copy dictionary (normative for P1)

| Surface | Use | Never |
|---------|-----|-------|
| Nav / title | **Asked-for** | Orders, Tests, Work, Assignments |
| Subtitle | Record requested analyses. This does not start work. | Assign tests after receive |
| Primary CTA | **Record request** / **Save request** | Assign test, Create test, Start work, Order process |
| Success toast | Requested {analysis} for {n} sample(s). | Test created, Work started, Work queued |
| Cancel | **Cancel request** | Delete test, Void work |
| Empty lake | Receive samples, then record what was asked. | No tests found. Create a test. |
| Client | Read-only. You can view requested analyses. | Any mutate CTA |

Do not rename `projects` → orders. Do not label this page Work orders (that is P2).

---

## Nimble UI checklist

| Dimension | P1 finding | Condition |
|-----------|------------|-----------|
| Queue / start | P1 is **not** a start queue. Multi-sample one action is the rack path. Scan-to-add must exist or techs click one-by-one. No Start on `requested`. | U2, U6 |
| Capture grid | Wide DataGrid. Sample identity RO. Editable fields live in the record dialog (analysis, TAT, params). Save request ≠ Submit-to-execute. | U3, U6, U8 |
| Empty states | Sketch silent. “No items found.” would send people to Tests. | U4 |
| Errors | API codes only. 409/422 must name sample + analysis in lab language. | U5 |
| Admin authoring | Param defs may be empty OOB — hide params, no JSON editor. Routing map is P2. | U8, U10 |
| LIMS vs ELN | Asked-for ≠ Test ≠ work_order ≠ Process. Analysis required on the **request**, not on receive, not as “start a run.” | U1, U6 |
| Accessibility | Keyboard on Record/Save, barcode Add, Cancel. Status chips contrast. | U7, U8 |
| Mobile | Laptop / scanner bench. No mobile redesign. DataGrid + dialog is enough. | U8 |

---

## gstack design passes (lab criteria)

Classifier: **APP UI**. Calm hierarchy, utility copy, DataGrid is the workspace (cards would be a hard rejection).

| Pass | Score | Gap a 10 would close |
|------|-------|----------------------|
| 1 Information architecture | 5/10 | Lake vs work list vs Tests must be three named places. Sketch names one page. |
| 2 Interaction states | 3/10 | Loading / empty / 409 partial / success / client RO unspecified. |
| 3 Journey | 6/10 | Receive → asked-for is the right emotional beat (request without lying work started). Stay-on-page after save matches receive. Fork to Tests is the failure. |
| 4 AI slop | 8/10 | No hero, no card grid. Risk is Tests-clone chrome + “Assign test” muscle memory, not marketing slop. |
| 5 Design system | 7/10 | Reuse FillHeightPage, DataGrid, ListFilterChips, CustomAttributeField, receive barcode field. No DESIGN.md — do not invent a new visual language. |
| 6 Responsive / a11y | 3/10 | Keyboard + chip contrast unspecified; laptop-only is acceptable if stated. |
| 7 Unresolved | — | OQ-WO-1 blocks **P2 UX**, not P1. TAT due-date display (Lab Ops watch) is U7. |

Sketch overall **4/10**. P1 is implementable only with **U1–U8** as the missing UI spec.

---

## What already exists (reuse)

| Pattern | Where | Use for |
|---------|-------|---------|
| Stay on page + toast + sticky | [`AtomicReceive.tsx`](../../../frontend/src/pages/AtomicReceive.tsx) | Save request then stay on `/asked-for` |
| Barcode field | same | Scan-to-add samples to the request set |
| Multi-select DataGrid | [`SamplesManagement.tsx`](../../../frontend/src/pages/SamplesManagement.tsx) | 1..N sample picker |
| ListFilterChips | [`ListFilterChips.tsx`](../../../frontend/src/components/common/ListFilterChips.tsx) | Project / analysis / status |
| FillHeightPage + DataGrid | Tests / Samples / Processes | Asked-for list |
| Analysis dropdown | Analyses list (`getAnalyses`), **not** TestForm, **not** AnalysisSelector (battery) | Request analysis |
| List-backed field | `CustomAttributeField` + Lists | P1 params when defs exist |
| Status Chip | Runs / Processes | requested / cancelled |
| Parser admin | [`DataParsersManagement.tsx`](../../../frontend/src/pages/admin/DataParsersManagement.tsx) | P5; prior UI stamp still binds |

**Do not reuse:** `TestForm` (creates/edits Tests). Accessioning wizard (removed). Receive analysis picker (forbidden). Samples “Assign to process” copy on this page (that is execute, P2).

---

## Conditions

Must land in the **named phase**. P1 PR is blocked without U1–U8.

| ID | Phase | Severity / note | Condition |
|----|-------|-----------------|-----------|
| **U1** | **P1** | Binds **L1** copy | **Asked-for is a request lake.** Page title and sidebar **Asked-for**. Subtitle: “Record requested analyses. This does not start work.” CTA **Record request** / **Save request**. Toast: “Requested {analysis} for {n} sample(s).” **Forbidden** on this surface: assign test, create test, start work, order process, tests created, work queued. No analysis picker and no asked-for chrome on **`/receive`**. |
| **U2** | **P1** | Binds **L1** multi-sample | **One operator action** for a set of samples with the same analysis + TAT + params. Picker: DataGrid checkbox of **Available for Testing** **and** a barcode field that adds the scanned sample to the set (rack path). API may POST one row per sample; the tech clicks Save **once**. Partial: list per-sample 409/422 (name the sample); keep successes; do not silently drop failures. Do not require one click per tube. |
| **U3** | **P1** | Binds **L1** surfaces | Surfaces: **`/asked-for`** + **sample detail Asked-for table + add**. Sidebar Sample Mgmt item **immediately after Receive**. Permission: `test:assign` to create; `sample:read` to view. **Do not** mount this on `/receive`. **Do not** import or open `TestForm`. **Do not** add a Create Test control on asked-for. Analysis control = active-analyses dropdown only. |
| **U4** | **P1** | Empty states | Empty lake: “Receive samples, then record what was asked.” Actions: **Go to Receive** and **Record request**. Not “No tests found.” Empty eligible samples: “No samples Available for Testing.” Sample detail with zero rows: Record request, not “No tests.” Empty params catalog: hide the params block (empty object); never a JSON editor. |
| **U5** | **P1** | Errors | Lab-readable, not raw FastAPI objects (reuse receive `formatApiDetail`). **409:** “{analysis} is already requested for {sample}.” **422** discarded / not Available for Testing: “Cannot request analysis on this sample ({status}).” **422** params: name the unknown/missing key. **403:** existing RLS copy (no project access). Never “Test already exists” or “Failed to create test.” |
| **U6** | **P1** | Lake behavior | **No Start / Execute / Route** on a `requested` row in P1. Success **stays on `/asked-for`** (clear dialog, refresh grid, do not navigate to Tests or sample detail). **No results column**, no numeric entry, no work_order column. Saving must not imply work started. Classic `/tests` stays for WO-4; this page does not link “create test.” |
| **U7** | **P1** | TAT + chips | TAT field label **TAT (days)** integer ≥ 1. Show a **computed due date** next to it (techs do not think in integer ranges). Status chips: `requested` = info, `cancelled` = default; contrast ≥ 4.5:1; no `routed` chip until P2. Cancel while `requested` with confirm: “Cancel this request? You can record it again later.” |
| **U8** | **P1** | Filters, a11y, client, params | List filters: project, analysis, status (default **requested**) — RQ-AF-9. Keyboard: Tab through dialog; Enter on barcode Add and Save request; Cancel is a real button. Laptop-first; no mobile redesign. **Client:** read-only list if they can read the sample; no Record / Cancel. Params when defs exist: `CustomAttributeField` / list-backed selects, not free JSON. Picker shows sample **name, type, status** so discarded/wrong type is obvious. Do not block a second analysis on a sample already in a process. |
| **U9** | **P2** | Work list ≠ lake | **Work orders** is a **different** surface (sidebar after Asked-for, or equivalent). **Start** lives there and reuses existing process start (select + scan; cohort locks after start). Do **not** add Start/Execute to `/asked-for` requested rows when P2 ships. Entity label **work order** (WO-1). Tech sees **one** link to the process, not two FKs (OQ-WO-3). |
| **U10** | **P2** | OQ-WO-1 | **Auto-route when a map row matches** — no Route click on every ELISA. No match / empty map: asked-for stays `requested`; tech copy **“No work plan for this request.”** `config:edit` sees **Configure routing**. Empty map **must not** toast success or “work queued” (AC-P2-2). Resolve OQ-WO-1 before P2 UX coding (Lab Ops stance). |
| **U11** | **P2** | Binds L2–L4 UX | Routing-map authoring shows one process definition with its steps in order, not an unordered bag. Display the first ordered Experiment or LimsRun step’s allowed types as informational copy only; map save does not AND the intake type across later steps. At step start, type refuse (`route_sample_type`): “This step does not accept the sample’s current type. The sample is not broken.” Completing step **N** surfaces the next ordered step. At LimsRun start, asked-for params show the target frozen value on the Test; first-start freeze remains OPEN on `b005cfe`, so do not present later-start overwrite prevention as shipped. |
| **U12** | **P3** | Persist lock only | No results-entry UI on asked-for. P3 types numbers on an **existing Test**. Missing `units_default` → 422 with “This analyte has no default unit.” No unit picker. |
| **U13** | **P4** | Binds **L5** | SOP Apply success: “Draft process definition created. Review and save. Not activated.” Human save; never silent auto-activate. **Do not** say the NCI extract → Qubit path is runnable or that daughters exist. Navigate to the draft process definition, not only an ExperimentTemplate. |
| **U14** | **P5** | Parser setup | Admin: example file → expected-output test → **dry-run** → activate only if tests pass. Empty: “No active parser for this analysis + instrument — create one.” AI draft labeled **setup only**; Import on a run never says AI. Prior parser UI stamp (data-parsers U1–U4) still binds. Client: no parser mutate. |

---

## Bounce (fails this Accept)

- Analysis picker or asked-for form on `/receive`
- TestForm / Create test / “Assign test” copy on asked-for
- Start / Execute / Route on P1 `requested` rows
- One-by-one save as the only multi-sample path
- Empty state “No tests found”
- Toast “Test created” or “Work queued” on P1 save
- Results column / number pad on asked-for
- JSON params editor for techs
- Sidebar label Orders / Tests / Work for this lake
- P2 Start grafted onto the lake instead of a work-order surface
- SOP Apply success claiming blood → DNA → Qubit
- Client Record request / routing / parser mutate

---

## NOT in scope (explicit)

| Deferred | Why |
|----------|-----|
| Hide or remove classic Test-create (WO-4) | Lab Ops watch; later ops tweak if dogfood shows the fork |
| Mobile-first asked-for | Bench is laptop + scanner |
| Visual mockups / new design system | No DESIGN.md; reuse MUI DataGrid workspace |
| Intake-profile / bulk intake / wizard | Receive CORE closed |
| Dest-type E2E UI | extract-hold packet |
| Projects → orders rename | Parked |
| Param uniqueness including cell line | Fine for P1 empty-params; later when defs are real |

---

## Open questions (UI stance)

| ID | Stance |
|----|--------|
| **OQ-WO-1** | **Agree with Lab Ops.** Auto-route on match; else stay `requested` with configure-routing for admin. Does not block P1. Blocks P2 UX (U10). |
| **OQ-WO-3** | One process link in the UI. Arch picks FK. |
| **OQ-AF-1/2/3** | Already decided: both surfaces, `test:assign`, empty-object params. U3/U8 implement that. |

---

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (U1–U14) |
| **Date** | 2026-08-28 |
| **Implement gate** | **OPEN for P1 only** (same as Lab Ops) |
| **P1** | **OPEN** — U1–U8 land in the P1 PR (copy lake, multi-sample + scan-to-add, not `/receive`, empty/error/TAT/chips, no Start) |
| **P2** | **CLOSED** until U9–U11 + L2–L4 in sketch + OQ-WO-1. Do not put Start on the lake. |
| **P3** | U12 — not “type results on asked-for” |
| **P4** | U13 with L5 |
| **P5** | U14 (admin; may parallel P1) |
| **Product UI code** | None this stamp. Grok Build after reviews. |
| **Named scope** | Post-receive work spine — P1 lake UI first; P2 work list later |

```
UI REVIEW: Accept with conditions (U1–U14)
IMPLEMENT GATE: OPEN (P1 only; U1–U8 same-phase)
```
