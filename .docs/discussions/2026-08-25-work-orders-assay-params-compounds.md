# Discussion: Work orders, assay parameters, compounds — and analysis without instruments

**Date:** 2026-08-25  
**Status:** Discussion — product direction; not implement gate  
**Related:**  
- [Framework discussion](2026-08-25-framework-driven-lims-accessioning.md)  
- Accessioning **A-15** / Processing **X-5** (tests vs process work)  
- [orders-and-projects idea](../ideas/orders-and-projects.md)  
- Sample-type transitions (aliquot/pool source→dest map)  
- LimsRuns / analyses / parsers  

---

## 1. Marc framing (summary)

1. **Experiments / LimsRuns / Processes already are the work framework** for how the lab executes. Keep that. Prefer **analysis tied to LimsRuns**.  
2. **Do not like analysis at accessioning.** An ordered analysis is “what was asked for,” not a complete description of **what the lab must do**. Labs need **backlogs / work orders** — work depends on analysis ordered, **sample type**, **TAT**, parameters, etc.  
3. **Drug discovery:** compounds *are* samples (sample/container driver) → need **compound registration** plus **receive/track lots**; assays always run under **parameters** (cell lines, concentrations, etc.).  
4. We have **source→dest maps** for aliquot/pool (`sample_type_transitions`). We need a parallel idea: a **routing map** that, given analysis + sample type + TAT (+ …), tells the lab **which process(es)** are required.  
5. **Parameters / cell lines / etc.** are captured on the **order** and flow to the **test** (instance of the analysis).

---

## 2. Direct answer: analysis without an instrument?

**Partially handled today — by design split:**

| Path | Instrument? | Today |
|------|-------------|--------|
| **Manual Test + Result entry** | No | Supported. Analysis on Test; results entered without a LimsRun. |
| **LimsRun** | Optional for “no file” | `analysis_id` is **required** on the run (Decision #6 — no non-reportable / null-analysis runs). **Instrument / CRO is required for parsers** (instrument XOR CRO on `data_parsers`), not necessarily for every run that only exists to hold structured work. |
| **Parser import** | Yes (or CRO) | Parser catalog requires instrument XOR CRO source. |

**Gap / clarify in product language:**

- “Analysis tied to LimsRun” is the right SoT for **assay execution units** that publish structured results.  
- **Non-instrument assays** (visual score, plate read typed in, calculation-only, CRO return without our instrument catalog) should still be able to use a LimsRun with `analysis_id` and **manual entry or file without an in-house instrument** — or stay on classic Test/Result until a “manual LimsRun” profile is explicit.  
- Do **not** invent `analysis_id = null` runs (already rejected). Method-dev belongs on lab projects (orders idea), not null analysis.

**Recommendation:** Stamp later: LimsRun always has analysis; instrument_id / cro_source_id **nullable** when lifecycle is manual / results typed; parsers still require instrument|CRO when importing.

---

## 3. Product model sketch (discussion only)

### 3.1 Separate “what was asked” from “what lab must do”

```text
ORDER (asked-for)                    WORK (lab must do)
─────────────────                    ──────────────────
analysis / assay requested           process definition(s) to run
TAT / due                            backlog / work order items
parameters (cell line, conc, …)      experiment + lims_run steps
sample / lot identity                sample type transitions (prep)
```

Accessioning registers **identity + vessel** (and maybe links to an order). It should **not** be the place that pretends “assign analysis = full work plan.”

### 3.2 Routing map (analogue of sample_type_transitions)

Existing:

```text
(source_sample_type, operation) → allowed_dest_sample_type
```

Proposed (sketch):

```text
(analysis_id, sample_type_id, tat_class?, …) → process_definition_id(s)
```

- Many-to-many rows (like transitions): one analysis × sample type may require extract process + assay process.  
- TAT / priority may select alternate process packs (STAT vs standard).  
- Config in DB; mutate = `config:edit`.  
- Output feeds **work orders / backlog**, not silent Test creation alone.

### 3.3 Parameters on order → Test instance

| Layer | Holds |
|-------|--------|
| **Analysis** (catalog) | Declares allowed / required **parameter definitions** (cell_line, dose, readout, …) — FieldDefinitions or analysis-param schema |
| **Order line** (asked-for) | Captures **parameter values** for this request |
| **Test** (instance) | Copies or links those values so LimsRun / Results / QC know the experimental context |

Same pattern as: FieldDefinitions on entries, not free-text buried in notes.

### 3.4 Compounds (drug discovery)

| Need | Fit |
|------|-----|
| Compound = sample identity | Samples + sample_type “Compound” / registration fields (FieldDefinitions / OOB) |
| Lots of compound | Containers + contents + receive of **lots**; possibly lot as sample child or container lot metadata — needs a packet (materials/lots idea adjacent) |
| Assay under parameters | Order params → Test → LimsRun (cell line, conc series, etc.) |

Driver remains **sample/container** model; compound registration is intake+catalog, not a second LIMS.

---

## 4. Implications for current docs

| Doc / issue | Change |
|-------------|--------|
| Accessioning PRD | Reinforce: optional analysis at receive is **not** the work-order system; default AR may omit test assignment as product preference |
| A-15 / X-5 | Elevate: work orders + routing map are the intended resolution direction |
| Processing PRD | Add “work order / backlog” as missing layer between order and process instance |
| Umbrella PRD | Framework includes **work routing**, not only intake profiles |
| Atomic receive P0 | Still fine for identity+vessel; **prefer not** to center “assign analyses at receive” in the happy path |

---

## 5. Persona comments (lightweight)

### CEO
Agree: stop selling “assign test at accession” as the lab work model. Sell **order → work plan → process/lims_run**. Keep AR as receive identity. Sequencing: don’t block AR P0 on the full routing engine — but **stop writing PRD goals that put analysis at the center of accessioning**.

### VP Lab Ops
Agree hard: bench needs a **work list** (“run Extract-then-Qubit on these DNA daughters by Friday”), not a naked Test row with no process. Parameters/cell lines must be on the order or the tech invents them. Non-instrument assays still need a clear “how we capture results” path (manual run or classic results).

### Security CSO
Routing maps and order params are **config + write surfaces**. Mutate maps with `config:edit`. Order/test param writes under same AuthZ as sample/project. No Client-editable routing that expands process membership.

### Scientific CSO
Parameters are scientific context for the Test/Result — must be structured and versioned with the instance. Analysis catalog defines what params mean; order captures values; LimsRun/Results remain SoT for outcomes. Compound lots must not lose lineage (parent compound → lot vessels).

---

## 6. Open questions (for later stamp)

| ID | Question |
|----|----------|
| WO-1 | Entity name: **work_order** vs reuse process instance as the only work unit? |
| WO-2 | Exact keys for routing map (analysis × sample_type × TAT × …)? |
| WO-3 | One process vs ordered list of processes per route hit? |
| WO-4 | Non-instrument analysis: mandatory LimsRun (manual lifecycle) vs classic Test/Result only? |
| WO-5 | Compound registration = sample_type + fields, or separate `compounds` table linked to samples? |
| WO-6 | Lot = new sample, container lot field, or materials module? |
| WO-7 | When is Test row created — at order, at process start, or at lims_run start? |

---

## 7. Suggested next packets (not started)

1. **Work-order / routing map** (analysis × sample_type × TAT → process definitions)  
2. **Analysis parameters** (catalog defs + order values → test instance)  
3. **Compound registration + lot receive** (sample/container driven)  
4. Clarify **manual / non-instrument LimsRun** profile  

Keep **atomic receive P0** for identity + first vessel; strip product emphasis on analysis-at-accession.
