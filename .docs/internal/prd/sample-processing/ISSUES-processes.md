# Temporary issues — Processes (ELN)

**Parent:** [ISSUES.md](ISSUES.md)  
**Status:** Synced 2026-08-26 (framework: process = execute target of work_order chain)

---

## A. Model / naming

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| P-1 | ELN `/v1/eln-processes` vs LIMS run **checklists** `/v1/processes` naming collision | Devs/users pick wrong API | Rename or document hard in nav + manuals |
| P-2 | `experiment_link` detail type coexist vs deprecate (**OQ #10 Open**) | Two ways to “attach” experiments | Decide deprecate vs keep |
| P-3 | Process-sample status vs `Sample.status` easy to conflate | Wrong eligibility reasoning | UI labels + docs (Decision #24) |

## B. Runtime consistency

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| P-4 | Minted daughters must land on `eln_process_samples`; historical Hold said they didn’t — code improved, docs/Hold wording stale | Agents re-open fixed holes | Sync `sop-ai-to-process.md` / Hold notes |
| P-5 | Soft advance when lims_run incomplete — UX may be weak or ignored | Steps advance without assay done | Verify warnings; Lab Ops bar |
| P-6 | Run samples ⊆ process cohort validation “where practical” | Leakage / wrong samples on run | Tighten validation |
| P-7 | Lazy LimsRun create on step start vs operator expectation of “run already exists” | Confusion at step 2 | UX copy + empty state |

## C. Definition authoring

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| P-8 | SOP+AI Apply does **not** create process definitions | Cannot author SOP→process from AI path | Separate Apply redesign packet |
| P-9 | Typed-step locks (template id + execution_mode) easy to misconfigure | Broken start | Validation + admin UX |
| P-10 | Snapshot-on-instantiate vs later definition edits | Instances drift from “current SOP” | Document; optional refresh policy later |

## D. Testdata / journey

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| P-11 | No seed process for Extract-then-Qubit / blood→DNA→Qubit | Can’t dogfood journey | Testdata gap OQs |
| P-12 | Journey API sample-scoped; process UI vs sample UI may disagree | Support burden | Align displays |

## Framework note

Work_order embeds an **ordered chain of process definitions** (WO-3). Process instance remains execute SoT — WO does not replace Process.

## Priority sketch

1. **P-4 + P-1** (truth + naming)  
2. **P-5 + P-6** (runtime gates)  
3. **P-8 / P-11** as follow-on packets  
4. Work_order → process instantiate AuthZ when WO packet opens (CSO S2)  
