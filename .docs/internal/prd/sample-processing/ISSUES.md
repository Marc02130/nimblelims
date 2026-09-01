# Temporary issues — Sample processing (index)

**Status:** Synced 2026-08-26 (PRD/SPEC framework-first + Leadership/BA/Dev)  
**PRD:** [PRD.md](PRD.md) · **Spec:** [../../specs/sample-processing/SPEC.md](../../specs/sample-processing/SPEC.md)  
**Stamps:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)  
**Team notes:** [../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md](../../../discussions/2026-08-26-issues-sync-leadership-ba-dev.md)

Split by layer:

| Doc | Covers |
|-----|--------|
| [ISSUES-processes.md](ISSUES-processes.md) | Process definitions / instances / journey |
| [ISSUES-experiments.md](ISSUES-experiments.md) | Templates, entries, aliquot/pool, extract-hold |
| [ISSUES-lims-runs.md](ISSUES-lims-runs.md) | LimsRuns, parsers, publish, non-instrument |

---

## Framework posture (from PRD §0)

Execute stack **exists**. Missing middle = **order → routing map → work_order → Process/Exp/LimsRun**.

| Stamp | Disposition on ISSUES |
|-------|------------------------|
| WO-1 work_order | **X-5** — packet not open; track only |
| WO-2 analysis × sample_type × TAT(days) | Routing map design |
| WO-3 ordered process chain on WO | Routing map design |
| WO-4 LimsRun + analysis; manual OK | **R-18** |
| WO-7 Test at LimsRun start / ensure-on-publish | **X-5 / R-*** — not at accession |
| WO-5/6 registration/lots | **Deferred** |

---

## Team comments (2026-08-26)

| Team | Comment |
|------|---------|
| **Leadership** | Don’t start WO schema until packet opened; keep execute substrate; AR before WO |
| **BA** | Requirements must describe asked-for vs must-do; AC for WO-7 Test timing |
| **Dev** | Unblock **E-9** restamp independently; E-10/E-14 before inventing work_order tables |

---

## Cross-cutting

| ID | Issue | Why | Next |
|----|-------|-----|------|
| X-1 | Process / Exp / LimsRun blurred in UI/docs | Wrong SoT | PRD diagram; nav audit |
| X-2 | Extract-then-Qubit E2E + testdata incomplete | No dogfood | After E-9 + seeds |
| X-3 | SOP+AI Apply ≠ live process | Product lie | Explicit non-goal |
| X-4 | MVP “processing not release bar” vs real SOPs | Priority fog | Leadership sequencing |
| **X-5** | Asked-for vs work_order / routing / params | Bench “what’s next?” | **Packet opened 2026-08-28** — [post-receive-work-spine](../../../review/requirements/post-receive-work-spine.md) |
| **X-6** | Docs path drift (`.docs/review` → `.docs/review`) | Agents miss files | Sweep links |

## Priority across layers

1. **Experiments E-9** (dual-map kick-back restamp) — blocker for extract-hold closure  
2. **E-10 / E-14 / E-12** — atomic pair UI, transition admin (`config:edit`), template dest type  
3. **E-6** — depends on accessioning AR status (Available for Testing)  
4. **X-5** — **open** as `post-receive-work-spine` (P1 asked-for first)  
5. **LimsRuns R-18 / R-11** — manual LimsRun clarity + Qubit testdata  
6. Processes P-4 / P-1 — truth + naming  

Do **not** prioritize full WO schema ahead of AR P0 or E-9.
