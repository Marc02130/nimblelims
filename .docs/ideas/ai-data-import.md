# Idea: AI-assisted data import

**Status:** Placeholder / exploratory  
**Date:** 2026-07-12  
**Related:** [run-results.md](run-results.md), [ai-analyte-resolution.md](ai-analyte-resolution.md), [ai-data-analysis.md](ai-data-analysis.md)

## One-liner

Use AI to help map messy instrument/CRO files into NimbleLIMS structures (templates, columns, samples, analytes) **with human confirmation** before write.

## Problem

Real import files vary by vendor and CRO:

- Column headers do not match catalog names  
- Samples identified by free text, barcodes, or plate maps  
- Units, qualifiers, and metadata mixed into value columns  
- Parser config is tedious to build from scratch  

v1 already supports structured import via `InstrumentParser` + JSONB `lims_run_data`. Mapping quality still depends on lab setup and manual alias maintenance.

## Sketch (not committed)

| Capability | Intent |
|------------|--------|
| **File → parse draft** | Propose skip rows, delimiter, header row, column types |
| **Column → field map** | Suggest analyte / unit / meta mapping (see [ai-analyte-resolution](ai-analyte-resolution.md)) |
| **Sample identity** | Suggest sample/container match from barcode or name |
| **Template fit** | Propose experiment template or analysis for the file shape |
| **Review UX** | Dry-run table; user accepts/edits before import commit |

### Guardrails (must, if built)

- **Human confirm** before any DB write (import, alias create, template change)  
- Never invent numeric **results** — only structure / identity suggestions  
- Lab catalog + RLS as context; no cross-tenant leakage  
- Audit: who accepted which AI suggestion  

### Non-goals (placeholder)

- Fully autonomous unattended import to production results  
- Replacing InstrumentParser as the SoT for column config  

## Fit with shipped work

| Shipped | This idea |
|---------|-----------|
| Run import + promote on publish | AI helps **before** data is clean enough to promote |
| Analyte aliases (manual list) | AI may **propose** aliases; list remains SoT |
| Promote preview | Import AI is earlier in the pipeline |

## Open questions (when reviewed)

1. Upload wizard vs post-import “fix mapping” on run data?  
2. Cloud vs local LLM / provider?  
3. Persist accepted maps onto InstrumentParser / analyte aliases automatically?  

## Success metric

Time from first file to successful import + promote without hand-editing CSV headers; reduction in unresolved columns at publish preview.
