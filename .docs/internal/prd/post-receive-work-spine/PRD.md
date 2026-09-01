# PRD: Post-receive work spine

**Domain:** Asked-for · work orders · results persist · SOP+AI apply · parser setup  
**Status:** Draft for review (Leadership opened 2026-08-28)  
**Stem:** `post-receive-work-spine`  
**Formal requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../../../review/requirements/post-receive-work-spine.md)  
**Spec:** [../../specs/post-receive-work-spine/SPEC.md](../../specs/post-receive-work-spine/SPEC.md)  
**Umbrella:** [../nimblelims-prd.md](../nimblelims-prd.md)  
**Team:** Leadership  

---

## 0. Why this packet now

Atomic receive CORE is closed. The wizard is removed. Samples land as **Available for Testing** with **zero Tests**.

The next product is the missing middle of the framework:

**asked-for → routing → work_order → Process/Exp/LimsRun → Results**

Plus two configuration surfaces that make the execute stack honest: SOP+AI must produce a **process definition**, and labs must be able to **configure instrument/CRO parsers** without writing code.

## 1. Users and jobs

| Role | Job |
|------|-----|
| Lab tech | After scan, record what the client/lab asked (analysis, TAT, params). Later pick work_orders and run steps. |
| Lab manager | See backlog. Configure routing packs. Review results. |
| Admin (`config:edit`) | Routing map, analysis param defs, instruments, parsers. Activate sidebar configs. |
| Client | **Read** asked-for / results on their projects. No receive, no routing mutate, no parser setup. |

## 2. Product principles

1. **Asked-for ≠ work plan.** An ordered ELISA is a request. Extract-then-assay is the work.
2. **One execute substrate.** Route into Process / Experiment / LimsRun. No third engine. Workflow Templates stay optional automation (FW-2).
3. **WO-7.** Test row at LimsRun start. Not receive. Not asked-for. Not work_order save. Publish refuses if Test is missing.
4. **Config in DB.** Routing, param defs, parsers. Mutate = `config:edit`.
5. **Receive stays dumb.** No analysis picker. Ever.
6. **Params are method setup, not results.** Catalog on the analysis; values on asked-for; freeze on the Test at LimsRun start. See [analysis-param-defs working note](../../../decision-logs/2026-08-28-analysis-param-defs.md) (example data, not seed). Fitted IC50 / CLint are results.

## 3. Phase intent (what a lab sees)

### P1 Asked-for (lake)

Tech opens **Asked-for**, picks received samples, picks **analysis (assay)**, enters TAT days, fills **that assay’s param defs** (cell line, temperature, …). Save. Those values sit on `asked_for.params`. Sample still Available for Testing. Tests grid still empty.

### Params (catalog → order → Test)

| Layer | Who | Store |
|-------|-----|--------|
| Catalog | Admin | `analysis_param_defs` keyed by analysis |
| Request | Tech | `asked_for.params` JSON |
| Execution | System at LimsRun start | `tests.asked_for_params` frozen copy |

### P2 Work order

Tech hits **Route** on requested asked-for (not on save). If a map row matches analysis × sample type × TAT, a **work_order** appears with the process chain (e.g. Extract → Qubit). Tech **Start**s that WO with existing Process UI. If no route, stay `requested`; nothing is invented.

### P3 Results

When a Test exists (LimsRun start, or remaining classic Test), typing a number writes `reported_result` + `qualifiers`. Missing analyte default unit → hard fail.

### P4 SOP+AI (interim only)

Upload/parse SOP. Apply creates a **draft process definition** with experiment and/or LimsRun steps. Human saves. This **stops the template-only lie**. It is **not** the differentiator. North star: [ai-sop-north-star](../ai-sop-north-star/PRD.md) (SOP + example execution files → vectors → MCP drafts process **and** parser). Does not fix blood→DNA dest type.

### P5 Parser

**Not** “admin authors parsers in a UI.” Parser setup is an **AI job at SOP time** into the existing parser **framework**. Admin **reviews / dry-runs / activates**. Day-to-day import has no LLM. Thin activate UI may exist; it is not the product story.

## 4. Success

- A startup can receive tubes and record what was asked without lying that work has started.
- A second lab’s “ELISA on plasma, 5-day TAT → process pack A” is **rows**, not a fork.
- SOP + example execution data → AI drafts the process pack (experiments + LimsRuns) and the parser. Human activates. That is the differentiator. See [ai-sop-north-star](../ai-sop-north-star/PRD.md).
- Parser setup is an **AI job at SOP**, not an engineering ticket and not the admin’s day job.
