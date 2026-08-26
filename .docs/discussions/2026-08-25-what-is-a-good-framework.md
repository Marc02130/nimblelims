# Discussion: What is a good framework? (impact of work-orders on the framework thesis)

**Date:** 2026-08-25 · **Stamps:** 2026-08-26 ([decision-logs/framework-stamps-2026-08-26.md](../decision-logs/framework-stamps-2026-08-26.md))  
**Status:** Discussion synthesis — **FW/WO questions stamped**  
**Inputs:**  
- [Framework + accessioning](2026-08-25-framework-driven-lims-accessioning.md)  
- [Work orders / assay params / compounds](2026-08-25-work-orders-assay-params-compounds.md)  
**Personas:** CEO · Security CSO · SVP Lab Ops  

---

## 1. How the work-order thread impacts the framework discussion

The first framework discussion was **intake-heavy**: “don’t hard-code one accessioning path; use DB profiles; AR = OOB default.”

The work-order thread **widens and corrects** that:

| Before (narrow) | After (clearer) |
|-----------------|-----------------|
| Framework ≈ flexible **intake** | Framework ≈ configurable **lab operating system** on a fixed spine |
| Spine drawn as Sample → Tests → Results → Reports | Same spine, but **Tests ≠ work plan**. “Asked for” (order/analysis/params) ≠ “must do” (processes / lims_runs) |
| A-15 parked as accessioning smell | A-15 is a **first-class framework gap**: missing **routing / work-order** layer |
| Process/Experiment/LimsRun listed as “shipped enhancement” | Those **are already the execution framework** — don’t reinvent them; **feed them** from orders + routing maps |
| Analysis at receive as optional AR feature | Product preference: **de-center analysis at accessioning**; receive = identity + vessel |

**Net impact:** The framework thesis stands, but the **missing middle** is clearer:

```text
RECEIVE (identity + vessel)     ← intake profiles (AR = OOB)
        │
        ▼
ORDER / ASKED-FOR               ← analysis, TAT, parameters (cell line, …)
        │
        ▼
ROUTING MAP (config)            ← analysis × sample_type × TAT → process definition(s)
        │                         (sibling of sample_type_transitions)
        ▼
WORK ORDERS / BACKLOG           ← what the lab must do
        │
        ▼
EXECUTE FRAMEWORK (exists)      ← Process → Experiment | LimsRun(analysis)
        │
        ▼
RESULTS / REPORTS
```

Intake flexibility without this middle still leaves the lab asking “what’s next?” — the original complexity crisis.

---

## 2. What is a **good** framework? (working definition)

A good NimbleLIMS framework has these properties:

### 2.1 Fixed spine, configurable joints

- **Fixed:** Sample/container identity, lineage, AuthZ/RLS, Result integrity, Process/Experiment/LimsRun roles.  
- **Configurable (DB):** fields, lists, intake profiles, analysis catalogs + **parameter defs**, **routing maps**, process definitions, METHOD_CATALOG / transitions, parsers, review gates.  
- **Not configurable:** bypassing RLS, null-analysis “fake runs,” silent overwrite of reported results.

### 2.2 Layers with clear jobs (no double SoT)

| Layer | Job | Not its job |
|-------|-----|-------------|
| **Intake** | Register specimen + first vessel | Invent full work plan |
| **Order / asked-for** | What client/scientist requested + params | Bench step list |
| **Routing / work order** | Expand request → lab procedures | Store instrument raw files |
| **Process / Experiment** | Prep SOP, mint daughters, capture entry data | Be the only place analyses live |
| **LimsRun** | Assay execution unit tied to **analysis** | Replace sample identity |
| **Results** | Structured outcomes | Intake config |

### 2.3 Maps, not if-statements

Good frameworks look like **`sample_type_transitions`**: many-to-many config rows, admin-edited, enforced at execute.

Needed siblings:

- Intake profiles  
- **Work routing:** `(analysis, sample_type, tat, …) → process_definition(s)`  
- Analysis parameter definitions → values on order → copied to test instance  

### 2.4 OOB defaults that run a real lab day-one

Empty framework = consulting. Good framework ships **seeded BioTech/Pharma defaults** (AR receive, Blood→DNA transition, example process packs) so a drug-discovery startup can receive compound lots and run an assay without designing the product first.

### 2.5 One execution substrate

Do not build a second “workflow engine” beside Process/Experiment/LimsRun. **Route into** those. Workflow Templates may automate, but they are not a parallel SoT for “what procedure am I in?”

### 2.6 Config is an AuthZ surface

Mutate framework tables with **`config:edit`** (or stricter). Runtime paths still use sample-create / project RLS / experiment:manage as today. Profiles never mean “Client can open the lab.”

### 2.7 Parameters travel with the instance

Catalog defines *what* can be asked (cell line, dose, …). Order captures *values*. Test/LimsRun *consume* them. Notes fields are not the framework.

---

## 3. Persona comments

### CEO (Founder / product)

**Impact:** Work-orders **upgrade** the framework story from “flexible forms” to “configurable operating system.” That’s the wedge vs a hard-coded LIMS and vs a pile of disconnected modules.

**Good framework:** Same spine; joints in DB; OOB that runs a compound-to-assay day; no analysis-at-accession as the hero story.

**Conditions**

| ID | Comment |
|----|---------|
| **C1** | Keep AR P0 for receive identity — don’t block it on the full routing engine. |
| **C2** | Stop PRD language that centers “assign analysis at accession.” |
| **C3** | Next framework packet after AR coherence: **routing map + order params** (not wizard revival). |
| **C4** | Compounds = samples + lots on existing spine — don’t fork a second LIMS. |

```
CEO: Framework thesis strengthened; missing middle = work routing; hold AR code scope
```

### Security CSO

**Impact:** More config tables (routing, params, profiles) = more elevation risk if Client-writable or if “route to process” auto-inserts process membership without AuthZ.

**Good framework:** Config mutate least-privilege; runtime still RLS; audit which profile/route produced a work order; one receive service; LimsRun still requires analysis (no null-analysis hole).

**Conditions**

| ID | Comment |
|----|---------|
| **S1** | Routing map + param defs: **`config:edit` only**. |
| **S2** | Instantiating a process from a work order uses existing process AuthZ — no silent expand across clients. |
| **S3** | Order/param writes follow sample/project access. |
| **S4** | Manual/non-instrument LimsRun OK; parsers still instrument\|CRO — don’t weaken import AuthZ. |

```
SECURITY CSO: Agree; config:edit; no RLS bypass; process join stays gated
```

### SVP Lab Ops

**Impact:** This is the bench truth. Techs don’t wake up for “Tests.” They wake up for **work**: extract these, assay those under this cell line, by this TAT. Analysis-at-accession created fake clarity.

**Good framework:**

1. Receive is fast (OOB AR).  
2. Something (order + routing) tells them **which process** and **with which params**.  
3. Process/Experiment/LimsRun are where they actually work — already familiar.  
4. Non-instrument assays still have an obvious “enter results here” path.  
5. Admin configures maps offline; tech never designs the product at the rack.

**Conditions**

| ID | Comment |
|----|---------|
| **L1** | Work list must answer “what’s next?” without opening three screens. |
| **L2** | Params/cell lines on the order — not tribal knowledge. |
| **L3** | Routing map must respect sample type (don’t send blood to a DNA-only Qubit process). |
| **L4** | Don’t ship half a work-order UI that orphans Tests again. |
| **L5** | AR first for identity; work-order packet next for ops clarity. |

```
LAB OPS: Strong agree; work routing is the framework hole; execute stack stays Process/Exp/LimsRun
```

---

## 4. Revised “framework layers” table (canonical for discussions)

| Layer | Exists today? | Config shape |
|-------|---------------|--------------|
| Fields / lists / name templates | Yes | FieldDefinitions, lists |
| Intake profiles | Partial (hard AR docs + unfinished wizard) | **Needed** — AR = OOB seed |
| Order / asked-for + params | Weak (analysis on sample; little structured params) | **Needed** |
| Work routing map | No (only type transitions for aliquot) | **Needed** — sibling of `sample_type_transitions` |
| Process / Experiment / Entries | Yes | Definitions, templates, METHOD_CATALOG, transitions |
| LimsRun + analysis (+ optional parser) | Yes | Analyses, parsers (instrument\|CRO when importing) |
| Results / review gates | Yes (partially configurable) | Review config, write-back allowlists |

---

## 5. What this does *not* change

- Atomic receive P0 sequencing for **identity + first vessel**  
- AuthZ spine for receive (PR 68)  
- Process / Experiment / LimsRun as execution SoT  
- Decision: no null-analysis LimsRuns  
- Sample/container as compound/lot carrier  

---

## 6. One-paragraph answer

The work-order discussion **doesn’t replace** the framework thesis — it **completes** it. A good framework is not “many UIs.” It is a **fixed scientific/ops spine** with **DB-configured joints**: intake profiles, order+parameters, routing maps into **existing** Process/Experiment/LimsRun execution, and OOB defaults that run. CEO wants that product identity without blowing AR scope; CSO wants config least-privilege; Lab Ops wants a real “what’s next?” work list fed by analysis × sample type × TAT × params — not analysis glued onto accessioning.
