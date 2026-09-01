# PRD: Sample processing

**Domain:** Processes · Experiments · LIMS runs (+ work orders / routing)  
**Status:** Framework-first (Leadership 2026-08-26)  
**Spec:** [../../specs/sample-processing/SPEC.md](../../specs/sample-processing/SPEC.md)  
**Umbrella:** [../nimblelims-prd.md](../nimblelims-prd.md)  
**Stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Discussions:** [what-is-a-good-framework](../../../discussions/2026-08-25-what-is-a-good-framework.md) · [work-orders](../../../discussions/2026-08-25-work-orders-assay-params-compounds.md)  
**Team:** Leadership  

---

## 0. Framework posture (Leadership)

Process / Experiment / LimsRun are the **execution framework** (already largely shipped). The missing configurable middle is **order → routing → work_order → execute**.

```text
ORDER (asked-for: analysis, TAT, params)
        │
        ▼
ROUTING MAP (DB)   analysis × sample_type × TAT(day range)
        │          → ordered chain of process_definitions
        ▼
WORK_ORDER         backlog / “what lab must do”
        │
        ▼
PROCESS INSTANCE → Experiment steps and/or LimsRun(analysis)
        │
        ▼
RESULTS (Test created at LimsRun start / ensure-on-publish — WO-7)
```

| Stamp | Rule |
|-------|------|
| FW-0 | Fixed execute roles; DB joints for routing/params/METHOD_CATALOG/transitions |
| FW-2 | Profiles/routing ≠ Workflow Templates |
| WO-1 | Entity = **work_order** |
| WO-2 | Route keys: **analysis + sample_type + TAT (days range)** |
| WO-3 | Work order embeds **ordered chain** of process definitions |
| WO-4 | Non-instrument: **LimsRun + analysis**; manual OK; instrument only for parsers |
| WO-7 | **Test** at LimsRun start / ensure-on-publish — not at accession |
| WO-5/6 | Registration / lots deferred (compound = one Sample; prefer lot as child later) |

---

## 1. Problem

After intake, labs need a clear **work list** and an execute stack. Blurring Process / Experiment / LimsRun, or treating “Test at accession” as the work plan, creates the complexity crisis. Drug-discovery assays need **parameters** (cell line, etc.) on the order, flowing to the assay instance.

## 2. Goals

### 2.1 Framework

| ID | Goal |
|----|------|
| F1 | Keep Process / Experiment / LimsRun as **one execute substrate** — route into them |
| F2 | Add **work_order** + **routing map** (config:edit) as the work-entry framework |
| F3 | Order carries analysis + TAT + **parameter values**; analysis catalog defines param defs |
| F4 | Analysis tied to **LimsRun**; manual/non-instrument runs allowed without parser |
| F5 | Aliquot/pool **source→dest** map remains (`sample_type_transitions`); sibling of work routing |
| F6 | Sidebar/active configs for routing packs activated with `config:edit` (FW-1b pattern) |

### 2.2 Execute domain

| ID | Goal |
|----|------|
| G1 | Process definition → instance → experiment and/or lims_run steps |
| G2 | Entries ≠ Results; LimsRun owns import until publish |
| G3 | Process assignment is **Contents** (sample **in** a container), not sample-only. A sample may have many vessels; only one container-with-sample is on the process |
| G4 | Cohort: Available for Testing + that container-with-sample membership; locked after start |
| G5 | Aliquot/pool mint: dest container-with-sample **continues** the process; inbound source assignment is **removed** |
| G6 | Publish → Tests/Results without inventing Tests at plan-save |
| G7 | Clear non-goals (CUT methods, SOP+AI→process lie, etc.) |

## 3. Non-goals

- Second workflow engine beside Process/Exp/LimsRun  
- Analysis-at-accession as work plan  
- Null-analysis LimsRuns  
- CUT aliquot methods; materials module; multi-tenant  
- Shipping registration/lots in the same packet as AR  
- Process membership as sample-only (no container) — **bounce**; see §4.1  

## 4. Mental model (execute)

```text
Process definition  ──instantiate──►  Process instance
                                         ├─ eln_experiment → Experiment + Entries → aliquot/pool
                                         └─ lims_run → LimsRun(analysis) → import? → publish → Results
```

### 4.1 Critical: process assignment is a sample in a container

**A sample is identity. A container is a physical vessel. Contents is “this sample is in this vessel.”** A sample can have **many** physical containers at once (tube still on the bench, aliquot on a plate).

**Only a sample-in-a-container is assigned to a process.** The process does not hold a bare `sample_id`. It holds that **Contents** row (sample + container).

| Legal | Not legal |
|-------|-----------|
| Tube T containing sample S is on the process | Sample S “on the process” with no container |
| After plating, plate well W containing S (or daughter D) is on the process; tube T is **not** | Sample S still “in the process” in both tube and plate |
| After extract, DNA daughter + its tube continues; blood tube is **removed** | Blood sample-only assignment surviving mint |

After aliquot/pool **execute**, **every dest** container-with-sample **continues**; **every inbound source** assignment is **removed**. Later work-order Start uses those continuing assignments. Work order `sample_id` stays the asked-for parent (order / lineage root). Tests belong to the **sample that was assayed**.

**Schema:** `eln_process_samples.container_id` (0077). Unique `(process_id, container_id)` and active unique `(process_id, sample_id)` where not removed.

**Bounce:** assigning a sample with no container; keeping the inbound vessel on the process after mint; treating process membership as sample-only.

## 5. Leadership notes

| Persona | Note |
|---------|------|
| CEO | Work routing completes the framework product; don’t block AR on full WO engine |
| Lab Ops | Bench “what’s next?” = work_order → process chain with params |
| Security CSO | Routing/params mutate = config:edit; process join stays AuthZ-gated |
| Sci CSO | Params structured on order→test; results SoT unchanged; compound roll-up later |

## 6. Acceptance criteria (product)

| ID | Criterion |
|----|-----------|
| AC-F1 | Docs describe work_order + routing map as framework joints |
| AC-F2 | Routing v1 keys = analysis × sample_type × TAT day-range → ordered process chain |
| AC-F3 | Test not created at accession; created at LimsRun start / ensure-on-publish |
| AC-F4 | Non-instrument assay usable via LimsRun + manual entry |
| AC-P-C1 | Process assignment is sample **in** a container (Contents). A sample may have many containers; only one container-with-sample is on the process |
| AC-P-C2 | After aliquot/pool execute, dest(s) continue; inbound source assignment(s) are removed |
| AC1–AC8 | Existing execute ACs (process, cohort, save/submit, aliquot, publish, journey) remain |

## 7. Shipped vs lag

| Area | Status |
|------|--------|
| Process / Experiment / LimsRun / parsers | Shipped |
| sample_type_transitions + dest type | Mostly shipped |
| Process assignment grain = container-with-sample | **0077** `container_id` on `eln_process_samples`; assign/mint/later-Start use Contents |
| Atomic pair UI / dual-map FD | Lag / kick-back |
| S3 transition admin UI | Lag |

## 8. References

- `.docs/internal/prd/sample-processing/ISSUES*.md`  
- `.docs/review/tech-sketch/experiment-template-entries.md`  
- `.docs/review/tech-sketch/extract-hold-dest-type.md`  
