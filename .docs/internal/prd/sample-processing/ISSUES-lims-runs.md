# Temporary issues — LIMS runs & parsers

**Parent:** [ISSUES.md](ISSUES.md)  
**Status:** Synced 2026-08-26 (WO-4 / R-18; Leadership/BA/Dev)

---

## A. Product boundaries

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| R-1 | LimsRun vs Batch vs Process checklist naming | Wrong tool for the job | Nav + glossary |
| R-2 | Entries must not auto-promote to Results — still a teaching problem | Shadow results | Docs + UI copy |
| R-3 | Instrument SoT = JSONB until publish; Results = projection | Edit fights | Clarify curator vs raw |
| **R-18** | **Analysis without instrument** | Ambiguous path for visual/manual/calc assays | **WO-4 stamped:** LimsRun + analysis required; manual entry OK; instrument only for parsers. Implement: document + UI empty states; no null-analysis |

## B. Lifecycle / process integration

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| R-4 | Lazy create on process step start vs standalone run create | Two entry points | Document both; unify empty states |
| R-5 | Soft warnings when advancing process with incomplete run | Easy to skip assay | Stronger gate or Lab Ops decide |
| R-6 | Run cohort ⊆ process cohort validation incomplete | Wrong samples imported | Enforce |
| R-7 | CRO vs standard lifecycle complexity | Ops errors | Lifecycle picker UX |

## C. Parsers / promote

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| R-8 | Parser catalog (instrument XOR CRO) + versioning — ops skill floor high | Mis-mapped columns | Better setup UX; P2 AI draft only |
| R-9 | Promote-on-publish conflicts (409) need clear owner resolution | Stuck publishes | Conflict UI |
| R-10 | Preview exists but may be underused before publish | Surprise writes | Promote “preview required” optional policy |
| R-11 | Qubit / Extract-then-Qubit **no parser + analysis seed** in catalog | Hold path unblockable | Testdata + analysis seed |
| R-12 | PR 48 instrument CSVs are HCP/LAL/NCI-60 — not Qubit | Wrong fixtures for Hold path | Keep separate; don’t pretend |

## D. Results / tests coupling

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| R-13 | Publish ensures Tests — Tests must not be invented at plan-save for Qubit path | Path lock violation | UAT assert |
| R-14 | Results on parent vs daughter after extract | Classic Hold failure mode | Always assay daughters |
| R-15 | Unit / qualifier rules (AR locks typed number + qualifiers) vs run promote | Two result-entry stories | Align manuals |

## E. Security / config

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| R-16 | Upload size caps exist (S8); parser edge cases remain | DoS / bad files | Keep caps; fixture library |
| R-17 | P2 AI parser setup Security S6–S8 still open | Don’t ship LLM import | Keep AI setup-only |

## Priority sketch

1. **R-11 + R-14** (Hold path assay on daughters + seeds)  
2. **R-6 + R-9** (cohort + conflict UX)  
3. **R-1 + R-2** (naming / SoT teaching)  
