# Discussion: Framework-first — accessioning, asked-for, routing, processing

**Date:** 2026-09-02  
**Branch:** `Framework-Review`  
**Team:** Leadership (Lab Ops, CEO, Security CSO, Scientific CSO)  
**Status:** Discussion rundown — **not** an implement gate, **not** a UAT Result, **not** overall P2 Pass. Not IC50.  
**Stamps:** [framework-stamps-2026-08-26](../decision-logs/framework-stamps-2026-08-26.md) (**FW-0…FW-2**, **WO-1…WO-7**)  
**Prior:** [what is a good framework](2026-08-25-what-is-a-good-framework.md) · [framework-driven accessioning](2026-08-25-framework-driven-lims-accessioning.md) · [work orders / params](2026-08-25-work-orders-assay-params-compounds.md) · [P2 route lock](2026-08-30-p2-route-lock.md) · [closeout 1.4 Quantified DNA](2026-09-01-p2-closeout-1-4-quantified-dna.md)

Does **not** rewrite signed UAT (`bf51b19`, `8cfa2a9`, `9342439`, P1, Deiter `02fe95f`) or OQ-WO-7 / OQ-WO-8 Closed.

---

## 1. Framework first (what we actually built)

A good NimbleLIMS framework is **FW-0**: a **fixed spine** with **DB joints**. The four layers that developed are not four products. They are four jobs on one operating system.

```text
RECEIVE (identity + vessel)          ← intake. OOB = atomic receive. Zero Tests.
        │
        ▼
ASKED-FOR (order)                    ← analysis + TAT + params. Zero Tests. Zero work.
        │
        ▼
ROUTING MAP (config)                 ← TAT + ordered process_definition[]. No pickers.
        │
        ▼
WORK ORDER (snapshot of the chain)   ← what the lab must do. Still zero Tests.
        │
        ▼
EXECUTE (already existed)            ← Process → Experiment | LimsRun(analysis)
        │                                 Test at LimsRun start (WO-7). Params freeze.
        ▼
RESULTS / REPORTS                    ← later packet (P3). Not this rundown.
```

| Layer | Job | Not its job |
|-------|-----|-------------|
| **Accessioning** | Register specimen + first vessel(s) | Invent the work plan, mint Tests, pick analysis |
| **Asked-for** | What was requested + params + TAT | Bench step list, Test row, process instance |
| **Routing / work order** | Expand the request into an ordered process chain | Store instrument files, mint daughters, freeze params |
| **Processing** | Do the work on the tube in hand | Be a second workflow engine; wear the asked-for on extract |

**Maps, not if-statements.** Admin authors rows (`config:edit`). Runtime matches them. Never `first()`. Empty map mints nothing.

**One execute substrate.** Do not build a second engine beside Process / Experiment / LimsRun. Route **into** those. Workflow Templates may automate; they are not SoT for “what procedure am I in?” (**FW-2**).

**Params travel.** Catalog defines keys. Asked-for holds values. First LimsRun start of the **asked-for analysis** snapshots onto `tests.asked_for_params` and freezes (**WO-7**, OQ-WO-7 Closed).

**Care about the asked-for only.** Extract is route machinery when the ask is WGS / Quantified DNA / ELISA. Qubit is the ask **only** when Quantified DNA is the asked-for (OQ-WO-8 Closed). On WGS, Qubit is process QC, not the ask.

---

## 2. Accessioning — how a **new** intake would land

### Existing substrate (do not replace)

- `POST /samples/receive` — one transaction: Sample identity + 1..N containers.
- **Zero Tests.** Empty / omitted `analysis_ids` → 201. Non-empty → **422**. No analysis picker on `/receive`.
- Contents = sample-in-a-container. Process assignment later requires `container_id`.
- Fields: Field Definitions + Lists (OOB + custom). Name templates. `config:edit` for catalog mutate.
- AuthZ: sample-create + project RLS. Client does not open the lab.

**FW-1:** OOB intake = atomic receive only. A second intake **profile** is allowed later; it is not a second receive service.

### How you would implement a new accessioning

1. **Keep the receive transaction.** Identity + vessels, zero Tests, same 422 on analysis_ids.
2. **Configure the joints, don’t fork the path.** New required fields, sticky set, name pattern, sample type, container type → Field Management / Lists / name templates. Activate to sidebar with **`config:edit`** (**FW-1b**).
3. **If a second real lab mode is needed** (manifest+verify, dual entry): that is an **intake profile** row pointing at the **same** receive service — not a wizard revival, not a second “Samples” product (**FW-1**, **FW-2**).
4. **Do not** order work at receive. Asked-for is a later look-up. Tech stays on `/receive` and scans the next tube.

**Would not invent:** analysis-at-accession, Test mint, dest DNA at receive, a parallel accessioning engine.

### Worked example: one form, one sample event, three distinct samples

**Bench:** A collection event produced **three distinct specimens** (not equivalent — not three tubes of the same identity). They want **one form**. Vessel counts:

| Identity | Containers |
|----------|------------|
| Sample A | 2 |
| Sample B | 2 |
| Sample C | 1 |

That is **3 Sample rows** and **5 containers**. The two tubes on A are equivalent **vessels of A** (already shipped: 1 sample + 1..N barcodes). A vs B vs C are **different identities**. Do **not** receive this as one Sample with five barcodes — that would lie and say they are the same specimen.

**OOB today (no new profile):** three `POST /samples/receive` calls.

1. Receive A: primary barcode + one additional barcode → Sample A + 2 containers. Zero Tests.  
2. Receive B: same shape → Sample B + 2 containers.  
3. Receive C: one barcode → Sample C + 1 container.

Each call is the existing CORE transaction ([AR multi-container](../decision-logs/2026-08-26-ar-multi-container.md)). Collision on any barcode → **409**, that call rolls back. Non-empty `analysis_ids` → **422**.

**One form in the existing framework (intake profile, not a new engine):**

1. **UI / profile** = “sample event receive.” Form lists N identities; each identity has 1..N barcodes. Activate with `config:edit`.  
2. **Each identity still hits the receive core** (same service, same rules). Preferred: **one outer transaction** wrapping three cores so the event is all-or-nothing; a barcode clash rolls the whole form back.  
3. **Event is grouping, not a fourth Sample** unless the lab needs the event as its own identity (then it is a parent Sample + three children — that is lineage, not receive-of-five-tubes). Default: event id / visit / collection datetime as **fields** on each of A, B, C (Field Management / list), shared value, three rows.  
4. **Still zero Tests.** Still no analysis picker. Asked-for is later, per Sample (or per tube’s Sample).

**After receive (same spine):**

| Layer | What happens |
|-------|----------------|
| **Asked-for** | Per Sample. A, B, and C may each get ELISA, Quantified DNA, both (second tube own asked-for), or none. Create still mints zero work. |
| **Route** | Per asked-for row. Two tubes of A that are both in play are **two process assignments** (`container_id`) if both enter process — same Sample, two vessels. Do not collapse A’s two tubes into one assignment. |
| **Process** | Tube in hand. Dest mint only at execute. A’s extra receive container is **not** C2 dest-follow; it was minted at receive. C2 is execute of same-type aliquot **after** receive. |

**Would not invent:** one Sample for the event; Tests at the form; dest DNA on the form; treating A’s second tube as a derivative; a second receive API that bypasses CORE 422/409.

---

## 3. Asked-for (ordering) — how a **new** order would land

### Existing substrate

- `POST /v1/asked-for` — analysis + TAT + `params` on an already-received sample.
- Status `requested` until explicit **Route**. Cancel while requested.
- Unique `(sample_id, analysis_id)` (open asked-for). Permission: reuse **`test:assign`** (OQ-AF-2).
- Param defs live on the **analysis** (`config:edit`). Unknown / missing required keys → 422. No built-in “required if” (OQ-AF-6). Prefer list-backed enums.
- Create mints **zero** Tests, **zero** work orders, **zero** processes.

### How you would implement a new asked-for

Example: **Quantified DNA** (OQ-WO-8 Closed) or **WGS** or **ELISA**.

1. **Catalog the analysis** (wear **existing** Qubit for Quantified DNA — do not mint a second analysis named Quantified DNA). Attach param defs if the assay has them (`library_kit` on WGS; Qubit may have none).
2. **Receive the tube first.** Then record asked-for on that Sample. Second tube on the same Sample = **own** asked-for + own route (ELISA vs WGS stay apart).
3. **Do not Route from save.** Tech hits Route later (OQ-WO-1).
4. **Params stay on the asked-for row** until the asked-for LimsRun starts. Then they freeze onto the Test from **`work_order.asked_for_id`** (same `analysis_id`), else parent lineage (OQ-WO-7). QC LimsRuns do not steal.

**Would not invent:** Test at order, auto-route, numbers on asked-for, a second “Orders” engine, copying WGS params onto WES.

---

## 4. Routing — how a **new** route would land

### Existing substrate

- Routing map row = **TAT range (days) + ordered `process_definition[]`**. No admin analysis picker. No admin sample-type picker.
- Types and analyses are **derived** from the chain: first process’s first Experiment/LimsRun allow-list; LimsRun steps carry `analysis_id`.
- Map save **409** when TAT ∩ first-step types ∩ LimsRun analysis **sets** all overlap. Extract-first vs Qubit-first for the same TAT is legal.
- Map save **422** when process *x* emerging type is not accepted by process *x+1* (catalog handoff, not dest mint).
- Assay ask: asked-for analysis appears **exactly once** among LimsRuns (the **named asked-for LimsRun slot**). Eligibility is `asked.analysis_id` vs **that slot**, not “any chain that contains Qubit.” 0 or 2+ → **422**. Two ELISA LimsRuns refused.
- **Route:** current type on first-step allow-list **and** named-slot match. Zero acceptable → **422**. Two saved rows that both accept → **409**. Exactly one → queued `work_order` (snapshot of the chain). Never `first()`.
- Route does **not** start processes and mints **zero** daughters.

`work_order` (**WO-1**, **WO-3**) embeds the ordered chain. `eln_processes.work_order_id` + `route_position` is SoT (OQ-WO-3). Start instantiates **first pending** definition only.

### How you would implement a new route

Example: Quantified DNA on blood.

1. **Author process definitions first** (extract experiment dest DNA; Qubit LimsRun wearing existing Qubit `analysis_id`; optional Nanodrop LimsRun with a **different** analysis).
2. **Save a map row:** TAT + `[extract, qubit, …]`. First-step types come from extract’s first Experiment. Named asked-for slot = the Qubit LimsRun.
3. **Do not put Qubit on a WGS map as the named slot.** A WGS map may contain Qubit as **process QC** (other analysis). Quantified DNA asked-for must not join that map (wrong slot / 409).
4. **ELISA** is a different map (blood / plasma first step, ELISA LimsRun). Do not hang ELISA on DNA after C3.

**Would not invent:** analysis picker on the map, type picker, auto-route, dest sample at Route, a picker when two maps accept (product is **409**).

---

## 5. Processing — how a **new** process / experiment / LimsRun would land

### Existing substrate

| Entity | Role |
|--------|------|
| **Process definition** | Always defined. Ordered typed steps. Reusable. `config:edit`. |
| **Process instance** | Started from a work order (or legacy assign). Tube in hand = `(sample, container_id)`. |
| **Experiment** | Equipment / SOP / aliquot-pool execute. **Not** an analysis. Dest type is catalog intent until execute. |
| **LimsRun** | Instrument (or manual, **WO-4**) execution unit. **`analysis_id` required.** Parser at **import**, not on the step. |
| **Test** | Assay **instance** `(sample, analysis)` minted/attached at **LimsRun start** (**WO-7**). Not at receive, asked-for, Route, or publish. Publish **422** if missing. |

**Extract (common path):** experiment on a process. Equipment, not instruments. **No** asked-for `analysis_id`. Blood→DNA is C3 dest mint at execute (`parent_sample_id`). Same-type extra tube is C2 (same Sample, additional container). Dest exists **only** after execute.

**Later Start** follows the dest container. First Start instantiates `chain[0]` only. `experiment:manage` to Start; `experiment:publish` to publish.

### How you would implement a new process pack

1. **Definition, not a one-off instance.** New extract / library-prep / ELISA process = new (or reused) **process definition** with typed steps.
2. **Put the asked-for analysis on exactly one LimsRun step.** Supporting QC = other LimsRun steps, other analyses, own Tests.
3. **Do not hang the panel analysis on extract.** If equipment later is an instrument, extract **may** become a LimsRun — then it emits instrument values, not a boolean `extracted = true`.
4. **Dest mint is execute.** Route / Start / map-save / asked-for mint zero daughters. Same type → extra container on the same Sample. Different type → new derivative Sample + container.
5. **Feed from the work order.** Instantiating uses existing process AuthZ — no client expand, no second membership path (**WO-7** conditions).
6. **Optional ExperimentTemplate** automates entries. It is not the routing SoT (**FW-2**). SOP Apply (P4) creates a **process definition**, not a parallel engine.

**Would not invent:** a workflow engine beside Process/Exp/LimsRun, Test at process Start (Test is LimsRun start of the **asked-for** analysis), dest at Route, ELISA-on-DNA, Qubit-as-asked-for on a WGS WO.

---

## 6. One walk-through (same framework, two asked-fors)

**Blood, two tubes, two asks** (Leadership Confirm: separate containers = separate assignments).

| Tube | Asked-for | Route | Execute | Test |
|------|-----------|-------|---------|------|
| Blood A | **ELISA** | ELISA map (no extract-to-DNA) | ELISA LimsRun on blood / plasma | `(blood, ELISA)` at ELISA start |
| Blood B | **Quantified DNA** | extract → **Qubit** (named slot) → optional Nanodrop | C3 DNA dest; Qubit LimsRun on DNA | `(DNA, Qubit)` at Qubit start. Nanodrop own Test if present |
| Blood B (later) | **WGS** (new asked-for on DNA or sequential on blood) | extract → QC (process QC) → **WGS** LimsRun | WGS start on DNA | `(DNA, WGS)` freezes **WGS** params from that WO, not Qubit, not `{}` |

Same spine. Different map rows. Different named slots. No new engines.

---

## 7. Asked-for UI: list selection vs Record vs Route

**Layer lock:** each screen selects the object of **that** layer. Mixing them is why Record feels broken.

| Layer | What you select | Payload you then fill |
|-------|-----------------|------------------------|
| Receive | barcodes / identities | sample type, project, fields |
| **Record asked-for** | **samples** (identities) | analysis + TAT + params |
| **Route** | **asked-for rows** (orders) | nothing — map match |
| Process assign | containers (tube in hand) | which process |
| LimsRun start | cohort `sample_ids` | — |

### What the UI does today (`/asked-for`)

The grid is the **asked-for lake** (one row per `(sample, analysis)`), not a sample list.

- Checkboxes select **asked-for ids** with `status=requested`. That selection feeds **Route selected** (`POST /v1/asked-for/route` `{ asked_for_ids }`). Per-row Route is `POST /v1/asked-for/{id}/route`.
- **Record requested analysis** ignores the grid. It opens `AskedForForm` with a Samples Autocomplete (`multiple` in code). The user picks samples **again**, one option per dropdown click, then analysis + TAT + params.
- API already accepts `sample_ids[]` and writes **one asked-for row per sample** (same analysis / TAT / params). Unique `(sample, analysis)` → 409 on dup.

So: list selection is wired for **Route**. Record re-picks **samples**. That is two different objects. The dropdown is not “one sample max” on the API — it is a chip picker that adds one sample at a time.

Sample-detail Record (`lockSamples`) already hides the sample field. The asked-for page never passes `lockSamples` because the grid is not samples.

### How Route works with “selecting samples”

It doesn’t. Route does **not** take sample ids.

Each asked-for row is routed **independently**: TAT + current sample type + named asked-for LimsRun slot → 0 maps **422**, 2 maps **409**, 1 map → one `work_order` for **that** asked-for. Batch Route is N of those in one HTTP. It does **not** merge samples into one work order. Cohort (several samples on one LimsRun) is **LimsRun start**, not Route.

If two selected asked-fors are ELISA on A and Quantified DNA on B, they hit **different maps**. If both are ELISA on A and B (same analysis + TAT, types accepted), they still mint **two work orders** unless a later joint says otherwise.

Selecting **samples** and clicking Route would be the wrong layer: a sample may have zero, one, or several asked-fors.

### Framework-first Record (what you described)

1. Select **samples** in a sample list (or a sample mode on this page).  
2. Dialog shows **analysis + TAT + params only** (`lockSamples`).  
3. `POST /v1/asked-for` `{ sample_ids, analysis_id, tat_days, params }` → N lake rows. Still zero Tests, zero work orders.

No new entity. Same create service. UI stops asking for identity twice.

### Options (Record)

| | Pattern | Use | Cost |
|--|---------|-----|------|
| **A** | Today: pick samples in the dialog | Fine for one-off from the lake page | Double identity; chip-at-a-time |
| **B** | List-select samples → dialog is analysis + TAT (+ params) | Bench bulk order; matches the API | Need a **sample** selection surface (Samples grid, or asked-for page in “samples” mode) |
| **C** | Record only from `/samples` (already `lockSamples` for **one** open sample) | Identity is already in context | Extend to **N selected** samples on that page |
| **D** | One asked-for row covering N samples | Looks simpler | **Breaks the spine** — asked-for is `(sample, analysis)`. Don’t. |

**Marc lock (2026-09-03): Record = B.** List-select **samples** → dialog is analysis + TAT (+ params). Same `POST /v1/asked-for` `{ sample_ids[] }`. Pending Leadership overwrite. Not coded in this fold.

### Options (Route)

| | Pattern | Use | Cost |
|--|---------|-----|------|
| **1** | Today: per-row + Route selected **asked-for** ids | Correct layer | User must understand the grid is orders, not samples |
| **2** | Select samples → Route all `requested` asked-fors on those samples | If the page is sample-centric | Ambiguous when a sample has two asked-fors (ELISA + WGS) — must Route **both** or pick |
| **3** | One work order for N samples that share analysis + TAT | One backlog card | **New joint.** Today WO is per asked-for; multi-sample work is LimsRun **cohort** at start |
| **4** | Batch Route all-or-nothing vs partial | Event-like “route this tray” | Today each id is independent; one 409 does not define the rest |

**Marc lock (2026-09-03): Route = 1.** Per-row + Route selected **asked-for** ids. Do not teach Route as sample selection. Pending Leadership overwrite.

### Should Route be on a container?

**No — not at Route.** The tube enters the **process**, not the map match.

Process assignment is already the **sample in a container** (`eln_process_samples.container_id` required). Two tubes on the same Sample that are both in play are **two assignments**. No vessel → **422**. Two vessels and no pick → **422**. That pick is **First Start / process assign**, not Route.

| Layer | Object | Why |
|-------|--------|-----|
| Asked-for | **Sample** | What was requested of the specimen. Unique `(sample, analysis)`. |
| Route | **Asked-for row** | Which map → one `work_order`. Zero Tests, zero daughters, **zero process instances**. |
| First Start | **Container** | Instantiates `chain[0]` and assigns the **tube in hand**. |
| Later Start / dest | **Dest container** | Execute minted the vessel; follow that, not the parent tube. |

Route’s job is “which ordered process chain.” Start’s job is “which vessel is on the bench.” Collapsing those at Route would make Route mint a process assignment — it does not, and should not (OQ-WO-1: Route is not Start).

**Same Sample, two receive tubes:**

| Intent | Asked-for | Route | Start |
|--------|-----------|-------|-------|
| Both tubes, same assay | **One** asked-for on the Sample | **One** WO | Two assignments if both go on process (pick each `container_id`) |
| Tube 1 ELISA, tube 2 Quantified DNA | **Two** asked-fors on the Sample (Leadership Confirm: second tube own asked-for) | **Two** Routes, two WOs | Each WO’s first Start picks **that** tube |
| Only one of two equivalent tubes is worked | One asked-for on the Sample | One WO | Start picks **that** container; the other stays off-process |

**Options if the room wants vessel bound earlier:**

| | When `container_id` is chosen | Effect |
|--|-------------------------------|--------|
| **R0 (current / lock)** | First Start / assign | Route stays map match. Tube pick is bench. |
| **R1** | Route body includes `container_id`, still no process instance | WO remembers intended vessel; Start still instantiates; 422 if that vessel is gone |
| **R2** | Route mints `chain[0]` assignment on that container | Route **is** Start. Breaks “Route does not start the chain.” Don’t without a new stamp. |
| **R3** | Asked-for is `(container, analysis)` | Order is per tube. Breaks `(sample, analysis)` uniqueness and “asked-for is identity.” Don’t unless Leadership overwrites P1. |

**Recommendation: R0.** Keep Route on the asked-for row. Bind the container when the tube is taken into a process (First Start). Record B still selects **samples** (identity), not containers — extra receive tubes of the same Sample share that asked-for until Start picks the vessel (or a second asked-for is recorded for a different assay).

### What not to invent

- Picking analysis again at Route (map already has the named slot).  
- Auto-route on Record (OQ-WO-1: tech hits Route).  
- One asked-for for three distinct samples.  
- Using asked-for-row checkboxes as the sample list for Record without changing what the grid **is**.  
- Route-as-Start (R2) or asked-for-per-container (R3) without a Leadership overwrite of P1 / OQ-WO-1.

---

## 8. What this rundown is not

- Not a second accessioning product.  
- Not permission to code extract-only zero-LimsRun routes (old 1.4 struck).  
- Not P3 persist lock, P4 SOP Apply, P5 parser admin — those stay later packets on the **same** spine.  
- Not intake-profile **engine** (still deferred until a second real profile is needed).  
- Not compound/lot registration (**WO-5 / WO-6** deferred).  
- Not overall P2 Pass.

---

## 9. For the room

This is the framework we already have. A **new** accessioning, asked-for, route, or process pack is **catalog + map + definition** on that spine — not a new module.

Please overwrite if a layer’s job is wrong. Not IC50.
