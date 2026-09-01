# PRD: Configuration framework

**Domain:** How a lab configures the spine — accessioning, asked-for, routing, execution  
**Status:** Working draft (2026-08-30). Documents the framework. **Not an implement packet.**  
**Spec:** [../../specs/configuration/SPEC.md](../../specs/configuration/SPEC.md)  
**User stories:** [../../user-stories/configuration/USER-STORIES.md](../../user-stories/configuration/USER-STORIES.md)  
**Umbrella:** [../nimblelims-prd.md](../nimblelims-prd.md)  
**Stamps:** [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Related packets:** accessioning CORE · [post-receive-work-spine](../post-receive-work-spine/PRD.md) · [sample-processing](../sample-processing/PRD.md)  
**Team:** Leadership  

Do **not** treat this file as a rewrite of signed P2 UAT (`8cfa2a9`) or as a merge vote. P2 product merge stays held. Dest-type mint stays Hold.

---

## 0. Why this exists

Every lab runs the same spine. Each lab differs in **how**: which sample types exist, what was asked for, which ordered work applies, which process/experiment/LimsRun actually runs.

A good framework (FW-0):

- **Fixed spine** — identity, AuthZ/RLS, Result integrity, Process / Experiment / LimsRun roles.
- **Configurable joints in the DB** — not a fork, not customer Python.
- **OOB defaults** so a startup can operate before configuring everything.
- **`config:edit`** mutates catalog. Execute permissions stay on execute.

This PRD names the four joints that sit on the lab path. Platform catalogs (lists, Field Management, analyses, parsers) feed those joints; they are not a fifth spine step.

---

## 1. Spine (normative)

```text
ACCESSIONING     identity + 1..N vessels          RECEIVE
ASKED-FOR        requested analysis + TAT + params  ORDER
ROUTING          TAT × first-step type × LimsRun    PLAN
                 in chain → work_order snapshot
EXECUTION        Process → Experiment | LimsRun     DO
RESULTS          Test (WO-7 at LimsRun start)       REPORT
```

| Layer | Job | Not its job |
|-------|-----|-------------|
| **Accessioning** | Register specimen + vessels. Stay on `/receive`. | Record asked-for. Mint Tests. Start work. |
| **Asked-for** | Record what was requested (analysis, TAT, params). Later look-up. | Assign a Test. Mint a work order. Type-gate sample type. |
| **Routing** | Expand a request into an ordered list of process definitions. Queue a work order. | Execute. Mint Tests. Author sample types or analyses onto the map. |
| **Execution** | Run Process → Experiment and/or LimsRun. Type-gate **current** sample at start. | Be the asked-for lake. Be a second workflow engine. |

**Receive ≠ order ≠ work.** Three motions. Route is unnumbered and later. First Start instantiates `chain[0]` only.

---

## 2. Configuration per layer

### 2.1 Accessioning

**OOB (FW-1):** atomic receive only. Intake-profile engine is deferred.

| What a lab configures | Where today | Mutate |
|-----------------------|-------------|--------|
| Sample types, projects, container types | Lists | `config:edit` |
| Sample fields (OOB + custom) | Field Management | `config:edit` |
| Lab sample ID pattern | Name templates | `config:edit` |
| Default tube (RQ-AR-8) | Intended off-form; current UI still exposes a 1×1 picker (CORE drift) | — |

**Locked, not configurable:** no analysis picker on `/receive`; non-empty `analysis_ids` → **422**; happy path stays on the form; zero Tests.

A second intake style is a future **profile row**, not a wizard revival (FW-2: profiles ≠ Workflow Templates).

### 2.2 Asked-for

The lake records a request. It does not decide whether the lab can actually run it.

| What a lab configures | Where today | Mutate |
|-----------------------|-------------|--------|
| Active analyses (assays) | Analyses catalog | `config:edit` |
| Default TAT (days) | `analyses.turnaround_time` (asked-for may copy as default) | `config:edit` |
| Assay param defs (keys, required, unit, list) | `analysis_param_defs` | `config:edit` |
| Param enum lists | Lists | `config:edit` |

**Locked:** asked-for save mints **zero** Tests and **zero** work orders. Status `routed` is P2 Route only. Type × analysis eligibility is **not** this layer. The lake may hold a scientifically wrong pairing (Qubit on blood); refusal belongs to routing / execute start.

Params are **order capture**. Freeze onto `tests.asked_for_params` is WO-7 at **LimsRun start**, not here.

### 2.3 Routing

A route is an ordered job, not an assay picker.

| What a lab configures | Where today | Mutate |
|-----------------------|-------------|--------|
| TAT range + ordered `process_definition[]` | `/admin/routing-map` | `config:edit` |
| Display of types / analyses / emerging | Derived on read from selected processes | (read) |

**No admin analysis picker. No admin sample-type picker.** (Proposed after signed `8cfa2a9` map-row = analysis+TAT; see P2 send.)

**Assignment (Leadership Confirm; Round 2 honesty):**

1. Current sample type ∈ first process’s **first** Experiment/LimsRun allow-list.
2. Asked-for analysis is **contained** in the chain’s LimsRun set (a route **may have multiple analyses**).

Zero acceptable → **422**. Two saved rows that both accept this type **and** this analysis → **409**. Never `first()`.

**Map save:**

- **409** only when overlapping TAT **and** overlapping first-step types **and** overlapping LimsRun analyses.
- **422** when the type emerging from process *x* is not accepted by process *x+1*. Emerging = aliquot/pool dest on *x* last Experiment/LimsRun if set; else last-step accepted types.

Dest-type **mint** remains Hold. Handoff is catalog intent, not “the tube became DNA.”

### 2.4 Execution (Process / Experiment / LimsRun)

One execute substrate. Route feeds it. Do not invent a second engine.

| Unit | How it is defined (Decision #6) | Config the lab authors |
|------|--------------------------------|------------------------|
| **Process** | Always a reusable **definition**; a running process is an instance | Ordered typed steps (`eln_experiment` \| `lims_run`), labels, **accepted sample types per step** |
| **Experiment** | Ad hoc **or** from **ExperimentTemplate** | Template entries, FieldDefinitions, aliquot/pool dest type. **No inbound type list.** |
| **LimsRun** | Always tied to an **analysis** (WO-4). No first-class LimsRun template today | Process step picks `analysis_id`; parsers/instruments bind to analysis. **No inbound type list.** |

**Typed process steps (Decision #1):**

- Experiment step → `experiment_template_id` + accepted sample types.
- LimsRun step → `analysis_id` (lazy LimsRun on Start step) + accepted sample types.

**Accepted inbound sample types are SoT on the process-definition step** (`eln_process_definition_step_accepted_sample_types`). Set in the process-definition editor. They do **not** belong on ExperimentTemplate, Experiment, LimsRun, or Analysis.

That is process-local on purpose: the same template or analysis can sit in two SOPs with different inbound types. Routing, create-route display, map-save handoff, and later-step start all read **this** list. Empty allow-list fails closed (`422 route_sample_type`). Standalone (non-process) Experiment / LimsRun start is not gated by this table.

**Process assignment (critical):** only a **sample in a container** is on a process. A sample may have many physical containers; the process holds one Contents row. See [sample-processing PRD §4.1](../sample-processing/PRD.md).

**Emerging / dest type (catalog)** lives on the ExperimentTemplate aliquot/pool OOB entry (`default_dest_sample_type`). Routing may **read** it for map-save handoff 422. **Mint** is that OOB pair’s **execute** (not generic entry Submit, not Route, not process Start): dest sample and/or container with vol/conc/mass. After mint, every dest container-with-sample continues; every inbound source assignment is removed. Tests belong to the assayed sample; lineage traces to the original. Sequencing LimsRuns store prep + run metadata/metrics only — not sequence files.

**Also execution catalog:** METHOD_CATALOG / `sample_type_transitions` (sibling of work routing); data parsers (analysis × instrument XOR CRO); Workflow Templates (FW-2: optional automation, not the SoT for what procedure applies).

### 2.5 Authoring a LimsRun step (AI SOP vs human) — no live run

AI at SOP time does **not** create a `lims_runs` row. That row is execute: Start step, later, on a work order. AI (north star) drafts the **catalog** the process already uses.

```text
SOP + example instrument files
        │  AI / MCP  (draft-only, implement gate CLOSED)
        ▼
eln_process_definition                    inactive
  step kind = lims_run
    analysis_id                           existing or proposed analysis
    accepted sample types                 on this step (§3)
  optional sibling steps                  eln_experiment + templates
data_parsers                              inactive, unbound  (needs example files)
        │  human reviews in the same UIs as manual authoring
        ▼
config:edit activate
        │  admin points routing_map at the definition(s)
        ▼
Route → work_order → Start → lazy LimsRun instance (WO-4, WO-7)
```

| Object AI may draft | Stored as | How a human edits it | How it gets on a process |
|---------------------|-----------|----------------------|--------------------------|
| LimsRun **step** | `eln_process_definition_steps` (`step_kind=lims_run`, `analysis_id`) + step accepted types | Process-definition editor: kind, analysis, **Accepted sample types**, label — same as CFG-6 | It **is** the process step. AI inserts the row on the draft definition. A human can add the same kind of step by hand. |
| Analysis (if new) | `analyses` (+ param defs, analytes) | Analyses admin | Step points at it via `analysis_id` |
| Parser | `data_parsers` JSON + `parser_analyses` M2M, inactive | Thin review / dry-run / activate. Not “author parser JSON from scratch.” | Bound to the **analysis** (M2M), not to the process step. **Not chosen when authoring the process.** Chosen at **import** on the live LimsRun (instrument XOR CRO → active parser; optional `parser_id` override). Manual/non-instrument runs need no parser (WO-4). |
| Experiment step | `experiment_templates` + `eln_experiment` step | Template entries UI + process editor | Same definition, different step kind |

**One SOP → one process definition** (Leadership round 1). A job with two methods (extract SOP + Qubit SOP) may propose **two draft definitions**. AI does **not** write `routing_map`. A human orders those definitions on the map.

**SOP-only** → process skeleton (steps + types + analysis bind). **Parser draft requires** example files of production-import shape. Files-only (no SOP) is not the product.

**Today’s lie:** `POST /v1/sop-parse` Apply writes an ExperimentTemplate only. It does not write a process definition, a LimsRun step, or a `data_parsers` row. Interim P4 is “Apply writes a process definition.” North star is MCP drafts process **and** parser. Gate **CLOSED**.

**Edit after activate:** change the process-definition step (analysis, accepted types, order) the same way as any other definition. In-flight work orders keep their snapshot. Parser edits are catalog (`config:edit`); next import uses the saved parser, no LLM.

---

## 3. Type gate — process-definition step is the home

**Lock (Marc, 2026-08-30):** accepted sample types stay on **process definition steps**. Do not add an accepted-type picker to Experiment templates, Experiments, LimsRuns, or Analyses. Type gates catch blood-on-Qubit. They do **not** catch an earlier LimsRun reusing the asked-for `analysis_id` (**OQ-WO-6**). Extract is not a special assay.

| Consequence | Detail |
|-------------|--------|
| One SOP, one list | Extract-then-Qubit can accept plasma on extract and DNA on Qubit; a different process can reuse the same Qubit analysis with a different inbound list |
| Route and Start agree | First-process first-step types drive Route; that same step list gates Start |
| Create-route display | Shows the step lists (and emerging dest from the last experiment of process *x*), not a map-authored type |
| No type on the execute object | An ExperimentTemplate does not declare “DNA only.” A LimsRun / analysis does not either |
| Ad hoc start | Experiment or LimsRun started **outside** a process is not gated by this table |

Do **not** read this as “missing UI on experiments and LimsRuns.” The UI is the process-definition step editor.

---

## 4. Open discussion — should LimsRuns have a template? (no implement)

**Question (narrowed):** Experiment steps point at an ExperimentTemplate (entries, dest). LimsRun steps point at an Analysis. Should LimsRun have a reusable template for **run setup** (parser, instrument, worklist, lifecycle) the way Experiment has a template for entries?

**Inbound sample types are not a reason to add one.** Those live on the process step (§3).

**Do not implement. Do not restamp P2 on an answer. Dest-type mint stays Hold.**

### What exists today

| | Experiment | LimsRun |
|-|------------|---------|
| Reusable definition | **ExperimentTemplate** (entries, dest type, optional lifecycle) | **Analysis** (analytes, TAT, param defs, parser bind) |
| Process-step pointer | `experiment_template_id` | `analysis_id` |
| Inbound accepted types | **Process-definition step** (§3) | **Process-definition step** (§3) |
| Optional extra pointer | — | `lims_runs.experiment_template_id` (historical: lifecycle_type / worklist). This is **not** a LimsRun template. |

Decision #6: processes are always defined; experiments may be ad hoc. It does **not** introduce a LimsRun template. WO-4: every LimsRun has an analysis.

### Lean (not a stamp)

Do **not** add a LimsRunTemplate to hold accepted types. That need is closed by §3.

Do **not** add a LimsRunTemplate that duplicates Analysis. Experiment templates exist because experiments have **structured entries**. LimsRuns have **analysis + import/publish**. That catalog already is Analysis + parser bind.

A LimsRunTemplate becomes interesting only if the same assay has several run **shapes** (different parsers, worklists, lifecycle) that are not the analysis itself. Until a lab needs that, it is a second identity beside Analysis. Historical `lims_runs.experiment_template_id` should not be grown into that object.

### What this does *not* decide

- Dest-type mint (Hold).
- Whether extract LimsRun may share asked-for `analysis_id` (still open on P2).
- Hans freeze skip (`{}` ambiguous).
- Overall P2 Pass.

---

## 5. Principles (do not drift)

1. Config in DB. Mutate catalog = `config:edit` (FW-1b). Route = `test:assign`. Start = `experiment:manage`. Publish = `experiment:publish`.
2. Maps, not if-statements. Sibling of `sample_type_transitions`.
3. One execute substrate. Routing snapshots process definitions; it does not run them.
4. Display derived types/analyses/emerging on create-route so admins do not author blind.
5. Empty allow-list fails closed at the gate that needs it.
6. OOB usable without a second intake profile.
7. Configuration never bypasses RLS.

## 6. Non-goals

- LimsRunTemplate (no implement). Do not move accepted types off process-definition steps
- Intake-profile engine
- Dest-type mint / blood→DNA daughter
- Second workflow engine
- Analysis picker on receive
- Admin analysis or sample-type picker on the routing map (proposed lock)
- Rewriting signed UAT stamps
- Customer Python / webhooks as the mint or route path

## 7. Success (when this framework is honest)

- A second lab expresses “ELISA on plasma, 5-day TAT, extract then assay then report” as **rows**.
- Each layer’s config has a named home. Accepted types used by Route are the **process-definition step** lists a tech hits at Start.
- Admins can see, on create-route, which types and analyses a process’s steps carry.
- Experiments and LimsRuns do not grow their own accepted-type pickers.

---

## Related

- Framework definition: [what-is-a-good-framework](../../../discussions/2026-08-25-what-is-a-good-framework.md)
- P2 route lock send: [2026-08-30-p2-route-lock](../../../discussions/2026-08-30-p2-route-lock.md)
- Spine OQs: [open-questions/post-receive-work-spine.md](../../../review/open-questions/post-receive-work-spine.md) (OQ-WO-4 / TAT-1 / WO-5)
- Experiments Decision #6: [open-questions/experiments.md](../../../review/open-questions/experiments.md)
- Operator path: [`/manuals/HOWTO.md`](../../../../manuals/HOWTO.md)
