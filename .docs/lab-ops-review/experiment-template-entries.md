# Lab Ops Review (SVP): Experiment template entries

**Date:** 2026-07-29  
**Status:** **Revise — Hold implementation**  
**Reviewer persona:** SVP Lab Operations (PhD biology; chemistry & sequencing; ~30y biotech/pharma ops)  
**Packet:** [tech-sketch/experiment-template-entries.md](../tech-sketch/experiment-template-entries.md)  
**Requirements:** [experiment-processes-entries.md](../requirements/experiment-processes-entries.md)  
**External reference:** [`manuals/Sapio Experiments Guide.pdf`](../../manuals/Sapio%20Experiments%20Guide.pdf)  
**Open questions:** [experiments.md](../open-questions/experiments.md) (new Q17–Q22)

---

## 1. Executive summary

**We are moving too fast from abstraction to API types.**

The engineering direction (ordered entry blocks on a template, custom columns, population from experiment samples) is *directionally* right for an ELN. The current sketch **is not yet a lab design**. It names two generic tables (`sample_table` / `experiment_table`) and treats aliquoting as “columns on a grid.” That under-serves how real biotech/pharma and sequencing labs actually run work.

Sapio (and every mature ELN/LIMS the persona has used) models an experiment as a **sequence of specialized entries**—Samples, Plates, Aliquot/Pool, Material Tracking, Instrument Tracking, Notes, Forms, domain tools—with **submit/lock**, **template composition**, and **process stringing**. Our plan collapses that catalog into two grids plus optional population. That is not enough for target customers evaluating “can we run NGS library prep / sample prep / QC here?”

**Verdict: Revise. Hold Phase 4 implementation** until lab workflows and an entry **catalog** are written into requirements and the sketch is re-reviewed by this role.

Prior CEO/UI/Architecture/Security “Accept” on this packet is **insufficient alone** to open the implement gate for ELN entry work.

---

## 2. What I reviewed

- Tech sketch (building blocks, row_source, columns, grid API)  
- Decisions #15–#16 (plan/results tables, naming)  
- Sapio Experiments Guide: entry menu, OOTB/Silver/Gold entries, Samples, Plates, Aliquot/Pool, Material Tracking, submit/unlock, templates, process manager mention  
- Existing NimbleLIMS: processes (ELN + lims_run), LimsRun + analysis, Field Management, EntryCapturePanel  

---

## 3. Lab workflow reality (persona lens)

### 3.1 What a customer lab expects from an “experiment”

| Expectation | Sapio-like systems | Our sketch today |
|-------------|--------------------|------------------|
| Ordered procedure inside one experiment | Many entry types in series | Two generic table types |
| Bring samples/plates into the experiment | First-class Samples / Plates entries | sample_executions + generic sample_table |
| Aliquot / pool creates **new sample identities** | Aliquot/Pool / HT plate pooling | Custom columns only—no derivative model |
| Reagent/lot consumption | Material Tracking | **Missing** |
| Instrument used | Instrument Tracking / result viewer | LimsRun path separate; ELN weak |
| Protocol/notes fixed on template | Experiment Notes pre-filled | Protocol tab orphaned |
| Step complete before next | Submit/lock; unlock with reason | Not specified |
| Multi-step SOP across experiments | Process Manager | ELN process exists; entry auto-populate (Q8) open |
| Sequencing setup | Index, Illumina run, sample sheet | LimsRun/analysis only; no ELN entry kinds |

### 3.2 Sequencing / chemistry pressure

For NGS-heavy customers (persona sequencing background):

- **Index assignment**, **pooling**, **plate maps**, **sample sheet generation** are not “another column set on sample_table.” They are **workflow actions with rules** (unique indexes, plate density, pooling mass balance).  
- Dose-response / instrument import correctly lives in **LimsRun**; ELN still must hand off **which samples/plates** cleanly. Sketch does not define plate entry or process→experiment population as non-optional.

### 3.3 GxP / regulated habits (even if full Part 11 is later)

Labs will ask early:

- Can we **lock** a completed table?  
- Who unlocks and **why** (audit)?  
- Are critical fields **required** before complete?  
- Is **lot number** of enzyme/kit captured?

Sketch is silent. That fails a lab ops interview.

---

## 4. Findings (severity = lab adoption risk)

### L1 — CRITICAL: Two generic tables ≠ experiment entry catalog

**Problem:** `sample_table` / `experiment_table` are storage/UI shapes, not lab entry kinds. Customers buy **behaviors** (aliquot creates children, material deducts lot, samples entry owns intake).

**Required before code:** Requirements list **v1 entry catalog** with at least:

| Priority | Entry kind (lab language) | Notes |
|----------|---------------------------|--------|
| P0 | **Samples** (bring samples into experiment) | Distinct from “results grid” |
| P0 | **Custom sample table** (measurements / plan columns) | Your column picker |
| P0 | **Custom experiment form/table** | Conditions, notes fields |
| P0 | **Experiment notes / protocol text** | Template-prefilled |
| P1 | **Plates** (or plate map) | Sequencing/prep reality |
| P1 | **Aliquot / pool** (creates derivatives) | Not only plan columns |
| P1 | **Material / reagent tracking** | Lot, qty used |
| P2 | Instrument tracking; domain tools | Align with LimsRun |

Map each kind to storage (generic table + `predefined_entry_key` / behavior plugin is fine eng-wise—but **product catalog first**).

### L2 — CRITICAL: Aliquot plan without derivative samples is incomplete

**Problem:** Plan rows with dest/volume do not answer: “Where is the daughter tube? What is its ID? What parent volume remains?”

**Required:** Either  

- **A)** Aliquot entry that **creates/links child samples** (preferred for biotech), or  
- **B)** Explicit non-goal: “plan-only documentation; no inventory effect” with customer messaging  

Persona rejects silent B for target pharma/biotech without stating it.

### L3 — HIGH: Population model is right but too thin

**Good:** `row_source = experiment_samples` matches “populate from samples brought into the experiment” (Sapio Samples + process queue).

**Gaps:**

- How samples **get** onto the experiment (UI: pick existing / from process / plate)?  
- Q8 still open (process samples → executions)—**blocking for process-driven labs**  
- No `row_source` for **plates**, **materials**, or **child samples from aliquot**

### L4 — HIGH: No complete/submit semantics on entries

Sapio: green checkmark submit; unlock needs credentials + reason; some entries require prior entry complete.

**Required in design (even if soft gates in v1):**  

- Entry status: draft | complete  
- Optional “required before experiment complete”  
- Audit on unlock  

### L5 — HIGH: Materials/lots absent

Chemistry background: **no lot = no trustworthy experiment** for many customers.

**Minimum P1:** material tracking entry or required custom columns linked to inventory (if inventory exists) / free-text lot with validation later.

### L6 — MEDIUM: Template story vs Protocol/Transfer tabs

Demoting Transfer Steps is correct if **behaviors** replace it. Until aliquot + plates exist, do not claim transfer is “just experiment detail columns.”

Protocol free-text must have a home in the entry catalog (notes), not a orphaned tab forever.

### L7 — MEDIUM: Competitive floor (Sapio guide)

From the guide, customers will compare:

- Breadth of **Add entry** menu  
- **Template** with pre-selected entries and pre-populated fields  
- **Process** chaining templates  
- Specialized NGS tools over time  

Our sketch optimizes the **custom table engine**—necessary infrastructure—but markets as the whole ELN. Separate:

1. **Platform capability:** configurable sample/experiment tables + population  
2. **Lab product:** catalog of OOTB entries and SOPs  

Ship messaging and roadmap must show (2), not only (1).

### L8 — LOW (process): Reviews accepted too early

CEO/UI/arch/security accepted while lab model still moving (detail → roster → sample_table renames). **Slow down:** lab ops sign-off before implement gate on this stem.

---

## 5. What is worth keeping (do not throw away)

| Idea | Lab ops view |
|------|----------------|
| Ordered entries on template → instance | **Yes** — matches Sapio composition |
| Custom columns via FieldDefinitions | **Yes** — forms/tables with predefined fields |
| Population from experiment samples | **Yes** — core |
| Separate LimsRun for instrument curves/import | **Yes** — keep boundary; improve handoff |
| ELN process definitions | **Yes** — string experiments; finish sample auto-link |

Infrastructure sketch is a **substrate**. Catalog + behaviors sit on top.

---

## 6. Required work before re-open implement gate

| # | Deliverable | Owner |
|---|-------------|--------|
| 1 | **Lab workflow brief** (2–3 target SOPs): e.g. NGS library prep step, sample aliquot/prep, simple QC notebook—step by step what entries appear | Product + Lab ops |
| 2 | **Entry catalog v1** table in requirements (kinds, behaviors, P0/P1/P2) | Product + Lab ops |
| 3 | Resolve **Q8** (process samples → experiment) for process-driven path | Product + Eng |
| 4 | Decision: aliquot **creates samples** vs plan-only | Lab ops + Product |
| 5 | Entry **complete/unlock** rules (even soft) in sketch | Eng + Lab ops |
| 6 | Re-run **Lab ops** review → then arch/security delta if catalog changes storage | All |
| 7 | Only then Phase 4 P0 code | Eng |

---

## 7. Open questions raised (log as Q17–Q22)

| # | Question |
|---|----------|
| Q17 | v1 entry catalog: which OOTB kinds beyond two generic tables? |
| Q18 | Does aliquot/pool create child samples and volume adjustments? |
| Q19 | How do plates enter an experiment (first-class entry vs container only)? |
| Q20 | Entry complete/submit and unlock-with-reason in v1? |
| Q21 | Material/lot tracking minimum for v1 vs explicit defer? |
| Q22 | Must process→experiment sample population (Q8) ship with Entries P0? |

---

## 8. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Revise — Hold implementation** |
| **Date** | 2026-07-29 |
| **Implement Phase 4 code?** | **No** until §6 items 1–5 done and this review re-run to Accept / Accept with conditions |
| **Prior Accepts (CEO/UI/Arch/Sec)** | Stand as **technical feedback only**; not sufficient gate for ELN entry build |

### Bottom line (persona)

I will not sign off a system that tells a sequencing lab “configure two grids” and calls that an experiment. Give me a **catalog of lab entries**, **real SOPs**, and **sample/plate/derivative integrity**—then the table engine is the right foundation to implement.
