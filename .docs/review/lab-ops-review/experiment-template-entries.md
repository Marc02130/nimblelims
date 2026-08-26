# Lab Ops Review (SVP): Experiment template entries

**Date:** 2026-08-10  
**Status:** **Accept with conditions**  
**Reviewer persona:** SVP Lab Ops (PhD biology; chemistry & sequencing; ~30y biotech/pharma)  
**Packet:** [tech-sketch/experiment-template-entries.md](../tech-sketch/experiment-template-entries.md) §0 (locked foundation through 2026-08-10)  
**Prior hold:** 2026-07-29 (premature catalog) — **superseded** by product Q&A locks  

---

## 1. Executive summary

The packet is no longer “two empty grids.” Product locked a **credible lab spine**:

- Queue → select (scan plate/tube) → fixed cohort  
- Header + Samples entries  
- Aliquot/pool **plan + execute** (containers, new dest samples, amount=mass/count never volume)  
- LIMS Run for instruments (analysis required)  
- Free edit + optional submit + template entry dependencies + default all-submitted to complete experiment  
- Write-back only for experiment-derived sample attributes, submit-only, config-driven targets  

That matches how target labs actually work and correctly keeps accessioning, materials, and NGS index/sample-sheet as **later** ideas.

**Verdict: Accept with conditions** for foundation + v1 predefined spine. **Do not expand scope** into materials/index sets/accessioning rewrite in this phase.

---

## 2. Lab fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| Cohort intake | 9 | Queue + discretionary select + scan plate/tube; no silent process auto-link |
| Fixed set after start | 9 | Matches “process as one”; cancel/restart is honest |
| Identity vs process data | 9 | RO accessioning fields; write-back only for experiment-derived sample attrs |
| Container / aliquot | 8 | Execute model correct; implement carefully (pools, partial transfers) |
| Instrument boundary | 10 | LIMS Run only; analysis required |
| Lifecycle / gates | 8 | Free edit + optional submit + template deps + default all-submitted — good |
| Scope discipline | 9 | Explicit OOS + ideas for accessioning, materials, index sets |
| Template authoring | 8 | In sketch; needs clear admin UX for deps and write-back map |

**Overall lab readiness: 8.5/10** for v1 spine — **implementable** after conditions.

---

## 3. What improved since Hold (2026-07-29)

| Prior concern | Status |
|---------------|--------|
| Only two generic tables, no lab spine | **Addressed** — header, samples, aliquot plan/results + LIMS |
| Aliquot without child samples | **Addressed** — execute creates dest samples + updates source amounts |
| No queue / intake | **Addressed** — start of experiment/run only |
| Process auto-link ambiguity | **Addressed** — explicit select; process filters queue only |
| Write-back vs accessioning | **Addressed** — RO identity; config map; submit only |
| Volume on sample like commercial LIMS tools | **Addressed** — amount never volume; containers own metrics |
| Full commercial-LIMS catalog pressure | **Addressed** — deferred with ideas |

---

## 4. Conditions (must land with implement)

| ID | Condition | Why |
|----|-----------|-----|
| **L1** | Queue + start UX for **experiment and LIMS run** before calling cohort “done” | Without this, sample_data grids are empty and unusable |
| **L2** | Scan plate → all samples on plate; scan tube → tube contents | Bench speed; barcode workflow |
| **L3** | Aliquot/pool **execute** is a real action (not plan documentation only) | Inventory + child samples |
| **L4** | Amount = mass/count only; volume display-only / inbound convert | Data integrity |
| **L5** | Write-back never on client_sample_id / client / subject; never container metrics | Accessioning + container SoT |
| **L6** | Template entry dependencies + default “all submitted to complete experiment” | SOP control without blocking free edit mid-work |
| **L7** | Keep template sign-off path working while entries ship | Don’t break activation |
| **L8** | Do not slip materials, index sets, or accessioning rewrite into this phase | Scope |
| **L9** | **All** aliquot/pool methods in v1 (by mass, by volume, target mass, target volume, target concentration, and other method modes product defines) — not “one method first” | Labs choose method per process |

---

## 5. Risks / watch items (non-blocking)

| Risk | Mitigation |
|------|------------|
| Aliquot method matrix complexity | **Not deferred:** v1 must support **all** methods labs use (by mass, by volume, target mass, target volume, target concentration, etc.). Columns/UI driven by method flag; full matrix in scope — **L9** |
| Pool (multi-content tube) edge cases | Explicit tests: reduce each source content; dest sample identity rules |
| Ad hoc columns without write-back | Clear UI so techs don’t expect Sample update |
| “Cancel and restart” for more samples | Document in UI empty/help; measure demand before mid-flight add |

---

## 6. Ideas acknowledged (correctly OOS)

| Idea | Lab ops view |
|------|----------------|
| local `.docs-internal/ideas/accessioning-and-workflows-revisit.md` (not committed) | **Critical next workflow** after entries spine |
| local `.docs-internal/ideas/materials-and-lot-tracking.md` (not committed) | Needed for many SOPs; not blocking this foundation |
| local `.docs-internal/ideas/index-sets-and-sequencing-setup.md` (not committed) | NGS must-have later; experiment_data OK interim |

---

## 7. Asks for other reviews

| Review | Focus |
|--------|--------|
| **Architecture** | Grid/export/submit APIs; execute aliquot transaction; container amount updates; no volume column |
| **UI** | Queue+scan; template entry builder; RO sample fields; write-back map; save vs submit |
| **Security** | Write-back allowlist/config; submit auth; RLS on grid/export |
| **CEO** | Scope freeze on v1 spine; prioritization of accessioning next |

---

## 8. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (L1–L9) |
| **Date** | 2026-08-10 |
| **Implement foundation + v1 predefined?** | **Yes**, after eng/CEO/UI/security pass conditions (Lab Ops does not block further review) |
| **Prior Hold** | Lifted for this scope |

### Bottom line (persona)

This is a **lab-credible** first cut: intake, fixed cohort, real aliquot execute, instrument on LIMS Run, and controlled write-back. Build the spine; park materials, indexes, and accessioning in ideas. Do not reopen “two grids only” debates — the locks in §0 are enough to proceed through the rest of the review chain.
