# Idea: AI-assisted data analysis

**Status:** Placeholder / exploratory  
**Date:** 2026-07-12  
**Related:** [run-results.md](run-results.md), [ai-data-import.md](ai-data-import.md), dose-response / LIMS runs manuals

## One-liner

Use AI to help scientists **interpret and query** run/result data (summaries, anomalies, natural-language questions)—without replacing validated calculations or official results.

## Problem

After data is imported and (optionally) promoted to structured results:

- Spotting outliers or plate patterns is manual  
- Dose-response and other analyses require specialist UI  
- Cross-sample comparisons need ad-hoc exports  
- Managers want plain-language status (“which samples fail acceptance?”)  

NimbleLIMS already has structured results (tests/analytes/raw), dose-response fitting, and flexible JSONB. AI analysis would sit **on top** of trusted data, not invent values into the ledger.

## Sketch (not committed)

| Capability | Intent |
|------------|--------|
| **NL query** | “Show samples where Lead > LOQ” against results + RLS |
| **Anomaly flags** | Suggest replicates or wells for human review (not auto-reject) |
| **Run summary** | Narrative of import completeness, promote preview issues, QC notes |
| **Analysis assist** | Explain curve fit flags, suggest exclusions **with justification** |
| **Report draft** | Outline client-facing text from approved results only |

### Guardrails (must, if built)

- **No silent overwrite** of `raw_result` / reported values / DR fits  
- Suggestions are **advisory**; lab retains release decisions  
- Cite underlying rows/IDs in answers (traceable)  
- Client/project RLS on every retrieval  
- Clear UI labeling: “AI assist — not validated calculation”  

### Non-goals (placeholder)

- Replacing 4PL / R calculator as official curve engine  
- Auto-publish based on AI judgment  
- Unbounded chat over the whole lab DB without scope  

## Fit with shipped work

| Shipped | This idea |
|---------|-----------|
| Promote-on-publish → structured results | Cleaner SoT for NL query / reporting |
| Dose-response on LimsRun | AI explains; R service still computes |
| Publish preview | Analysis AI is post-structure, not mapping |

## Open questions (when reviewed)

1. Scope: single run vs project vs client portfolio?  
2. Retrieval: SQL tools vs RAG over exports vs agent API?  
3. Which roles may use analysis assist (lab only vs client)?  

## Success metric

Faster investigation of failed/out-of-spec sets; fewer spreadsheet round-trips; zero incidents of AI writing official results without explicit human action.
