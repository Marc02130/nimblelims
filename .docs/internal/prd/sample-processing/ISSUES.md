# Temporary issues — Sample processing (index)

**Status:** Synced 2026-09-20 (product north star + E-10 Met; Leadership Core)  
**PRD:** [PRD.md](PRD.md) · **Spec:** [../../specs/sample-processing/SPEC.md](../../specs/sample-processing/SPEC.md)  
**Stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md) · [../../../decision-logs/product-north-star-2026-09-20.md](../../../decision-logs/product-north-star-2026-09-20.md)  
**Team notes:** [../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md](../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md)

Split by layer:

| Doc | Covers |
|-----|--------|
| [ISSUES-processes.md](ISSUES-processes.md) | Process definitions / instances / journey |
| [ISSUES-experiments.md](ISSUES-experiments.md) | Templates, entries, aliquot/pool, extract-hold |
| [ISSUES-lims-runs.md](ISSUES-lims-runs.md) | LimsRuns, parsers, publish, non-instrument |

---

## Product north star (Leadership 2026-09-20)

Two goals define the product. They are not a new packet — they constrain sequencing and docs.

| # | Goal | Meaning |
|---|------|---------|
| **1** | **Framework first** | Flexible LIMS via **configuration in the DB** (rules, design, page layouts) — not re-coding when a laboratory adopts it |
| **2** | **AI configuration from SOPs** | AI proposes that config from SOPs; humans edit/refine. Starts with sample-processing catalog; broadens later |

**Sequencing lock:** Finish **sample processing** before opening AI-assisted config for login, reporting, storage, or other surfaces. Framework (goal 1) is what makes goal 2 possible across the product. Living guidance: [ai-sop-north-star](../../../review/requirements/ai-sop-north-star.md). Parked breadth: [open-questions/ai-config-breadth.md](../../../review/open-questions/ai-config-breadth.md).

---

## Framework posture (from PRD §0)

Execute stack **exists**. Missing middle = **order → routing map → work_order → Process/Exp/LimsRun**.

| Stamp | Disposition on ISSUES |
|-------|------------------------|
| WO-1 work_order | **X-5** — packet open (`post-receive-work-spine`) |
| WO-2 analysis × sample_type × TAT(days) | Routing map design |
| WO-3 ordered process chain on WO | Routing map design |
| WO-4 LimsRun + analysis; manual OK | **R-18** |
| WO-7 Test at LimsRun start / ensure-on-publish | **X-5 / R-*** — not at accession |
| WO-5/6 registration/lots | **Deferred** |

---

## Team comments (2026-09-20)

| Team | Comment |
|------|---------|
| **Leadership** | North star locked (framework → AI config). Sample processing first. Tobias honesty-check uniqueness **7.9 / 7.9b** (not a merge). |
| **BA** | Fold goals into living PRD / OQ; keep ISSUES priority current (E-10 Met → E-14/E-12 → E-6/E-7) |
| **QA** | Living UAT §7 Pass on `dc7ee92` with E-10 Met; Tobias re-check 7.9 / 7.9b honesty only |

---

## Cross-cutting

| ID | Issue | Why | Next |
|----|-------|-----|------|
| X-1 | Process / Exp / LimsRun blurred in UI/docs | Wrong SoT | **Docs punch 2026-09-11:** HOWTO § Later execution table; processes / experiments / lims-runs / nav / api-endpoints. Sidebar tooltips. `/v1/processes` rename **not** in this fold (P-1 leftover). |
| X-2 | Extract-then-Qubit E2E + testdata incomplete | No dogfood | After seeds / dest path |
| X-3 | SOP+AI Apply ≠ live process | Product lie | Explicit non-goal until north-star packet; see [ai-sop-north-star](../../../review/requirements/ai-sop-north-star.md) |
| X-4 | MVP “processing not release bar” vs real SOPs | Priority fog | Leadership sequencing (sample processing close → then AI breadth) |
| **X-5** | Asked-for vs work_order / routing / params | Bench “what’s next?” | **Packet opened 2026-08-28** — [post-receive-work-spine](../../../review/requirements/post-receive-work-spine.md) |
| **X-6** | Docs path drift | Agents miss files | Sweep links |
| **X-7** | AI config beyond sample processing (login, reporting, storage, …) | Scope creep | **Parked** until sample processing closed — [ai-config-breadth](../../../review/open-questions/ai-config-breadth.md) |

## Priority across layers

1. **E-9** dual-map — **Decided** (dest container type shipped)  
2. **E-10** atomic pair — **Met** on `main` (PR **129**, `e56a89f`); UAT §7 **Pass** on `dc7ee92` (incl. 7.9 / 7.9b uniqueness); **Hold merge lifted**. Tobias honesty-check 7.9 / 7.9b (not a merge).  
3. **E-14 + E-12** — transition catalog admin (`config:edit`) + template dest type (**next** after Tobias check)  
4. **E-7 + E-6** — type gate layer + intake Available for Testing  
5. **X-5** — `post-receive-work-spine` (asked-for / work_order)  
6. **LimsRuns R-18 / R-11** — manual LimsRun clarity + Qubit testdata  
7. Processes P-4 / P-1 — truth + naming  

Do **not** open AI config packets for login / reporting / storage until sample processing is closed. Do **not** prioritize full WO schema ahead of E-14/E-12.
