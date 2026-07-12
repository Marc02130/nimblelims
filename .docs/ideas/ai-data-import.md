# Idea: Parser setup (analysis + instrument/CRO) with optional AI assist

**Status:** Product direction locked for scope sketch · not implemented  
**Date:** 2026-07-12 · updated same day  
**Related:** [run-results.md](run-results.md), [ai-analyte-resolution.md](ai-analyte-resolution.md), [ai-data-analysis.md](ai-data-analysis.md), [manuals/lims-runs.md](../manuals/lims-runs.md)

## One-liner

**Parsers are first-class, reusable, deterministic configs.** AI is only used (optionally) to **draft** a parser from an example instrument/CRO result file. Day-to-day import never requires AI.

## Product intent (decided sketch)

| Principle | Decision |
|-----------|----------|
| **SoT for import** | Saved **parser config** — not the LLM |
| **AI role** | **Setup assistant** only: propose delimiter, header row, skip rows, column map from a sample file |
| **Human role** | Review/edit/save parser; re-run import without AI |
| **Repetition** | Same analysis + same instrument (or same CRO) → **reuse** the parser |
| **Scope key (lab)** | **Analysis + instrument** |
| **Scope key (CRO)** | **Analysis + CRO** (CRO is the “source system” when work is external) |
| **Example file for setup** | **Text table required**: `.txt` / CSV-like with **tab, comma, semicolon**, etc. (not binary-only instruments in v1) |

This is **not** “AI imports results every time.” It is “AI helps you configure the thing that will import results forever.”

## Why not always AI?

- Same instrument / same CRO exports the same shape for months.  
- Deterministic parse is faster, auditable, offline-capable, and cheaper.  
- Promote-on-publish already expects stable column names/aliases — a parser that normalizes headers into catalog fields strengthens that path.

## Current system (as-is)

| Piece | Today |
|-------|--------|
| **`InstrumentParser`** | Exists; **`parser_config` JSONB**; currently tied to **`experiment_template_id`** |
| **Import** | `InstrumentDataService` applies parser to CSV/bytes; runs import into `lims_run_data` |
| **SOP AI** | Claude extracts **template + parser + worklist** from SOP + sample instrument file — template-centric, not analysis/instrument-centric |
| **Promote** | Column → analyte via name/alias on publish (separate from parser setup) |

**Gap:** Parsers are not yet a catalog keyed by **analysis + instrument** or **analysis + CRO**. No first-class Instrument or CRO-source entity for parser ownership. AI path is SOP→template, not “upload result file → save reusable parser for this analysis.”

## Target model (proposed)

```
Analysis ──┬── Instrument (lab)  ──► Parser (deterministic config)
           └── CRO (external)    ──► Parser (deterministic config)

Setup (once):
  1. Choose Analysis + Instrument | CRO
  2. Upload example result file (txt/tsv/csv, declare or detect delimiter)
  3. Optional: AI proposes parser_config (columns, skip_rows, well/sample col, …)
  4. User edits + Save → Parser version/revision
  5. Optional: propose analyte aliases for unmatched headers (see ai-analyte-resolution)

Use (every run):
  LimsRun (has analysis_id) + selected parser (or auto-pick by instrument/CRO)
  → deterministic parse → lims_run_data
  → publish promote uses name/alias as today
```

### Parser config (reuse existing shape)

Keep evolving `parser_config` (already in codebase):

```json
{
  "delimiter": "\t",
  "encoding": "utf-8",
  "skip_rows": 2,
  "header_row": 0,
  "well_col": "Well",
  "sample_col": null,
  "columns": [
    {"source_col": "Pb_ug_L", "field_name": "Pb_ug_L", "data_type": "float", "unit": "ug/L"},
    {"source_col": "Sample", "field_name": "sample_name", "data_type": "string"}
  ]
}
```

Day-to-day import: **no Claude call**.

### AI setup job (optional path)

Inputs:

- Analysis id (analyte list as context for mapping suggestions)  
- Instrument id **or** CRO id  
- Example file (text + delimiter hint)  

Outputs (draft only until confirm):

- Full `parser_config`  
- Optional: suggested new **analyte aliases** (not auto-applied)  
- Warnings: ambiguous columns, empty headers, multi-line preambles  

Reuse patterns from SOP parse: async job, poll, apply — but **apply creates/updates a Parser row**, not necessarily a whole experiment template.

### Non-goals (this idea)

- AI inventing numeric result values  
- AI required on every import  
- Full LIMS **equipment management** (calibration, service, IQ/OQ) in v1  
- Binary instrument formats (XLSX, proprietary) as first milestone (can follow)  
- Replacing promote-on-publish mapping rules  

## Do we need instrument tracking?

**Yes — light catalog, not full equipment ops.**

| Need | Recommendation |
|------|----------------|
| **Stable identity for “who produced this file?”** | Yes — otherwise “parser per analysis + instrument” has nothing to hang on |
| **Full asset tracking** (serial, location, calibration, status) | **No for v1** — defer |
| **CRO** | Reuse or introduce a light **external lab / CRO party** (could start as `Client` subtype, org list, or `cro_labs` table) — key is **stable id + name** for parser scoping |

### Minimal entities (suggested)

```
instruments (
  id, name, vendor?, model?, description?, active, …
)  -- lab instruments; optional free-text serial later

-- OR for CRO:
cro_sources (
  id, name, client_id?, description?, active, …
)

instrument_parsers  (evolve from today)
  id, name,
  analysis_id FK,           -- NEW: primary scope
  instrument_id FK null,    -- lab path
  cro_source_id FK null,    -- CRO path (one of instrument/cro set)
  experiment_template_id null?,  -- optional link for backward compat
  parser_config JSONB,
  …
  UNIQUE-ish: (analysis_id, instrument_id) or (analysis_id, cro_source_id)
```

**v1 UX:** Admin (or Lab Manager) maintains Instruments list + CRO sources list + Parsers for each analysis combo.  
**v0 without new tables (provisional):** store `instrument_name` / `cro_name` strings on parser — weaker uniqueness, harder reporting; only if shipping faster, then migrate.

**Run association (later):** optional `lims_runs.instrument_id` or `cro_source_id` so import auto-selects parser when analysis is set. Not required for first “save parser” milestone.

## Is this too big for one branch?

**Yes for a single “ship everything” branch.** Split by product value.

| Phase | Branch-sized deliverable | AI? | Depends on |
|-------|--------------------------|-----|------------|
| **P0** | Light **Instrument** (+ optional **CRO source**) catalog CRUD + UI | No | — |
| **P1** | **Parser** entity scoped to analysis + instrument\|CRO; manual editor for `parser_config`; attach/select on run import | No | P0 |
| **P2** | **AI draft** from example text file (delimiter detection + column map); review UI; save to parser | Yes (Claude, same as SOP) | P1 |
| **P3** | Optional alias proposals; wire run auto-select parser; template FK deprecation path | Optional AI | P1–P2 |
| **P4** | XLSX / multi-sheet / more formats | Later | P1 |

**Recommended first branch:** **P0 + P1** (catalog + manual parser + use on import) — delivers “set up once, reuse forever” without AI risk.  
**Second branch:** **P2** AI setup assist (reuses SOP-parse job patterns).  

One mega-branch (catalog + re-key parsers + AI + run wiring + promote polish) will be hard to review and UAT.

### Overlap with existing SOP parse

| SOP parse (shipped) | This idea |
|---------------------|-----------|
| SOP document + instrument file | **Result file only** (+ analysis context) |
| Creates **template** (+ parser + worklist) | Creates/updates **parser** for analysis×instrument/CRO |
| Template-centric | **Analysis/source-centric** |

Keep both: SOP path for **protocol setup**; this path for **data-format setup** when the assay is already known.

## Open questions (remaining)

1. **Instrument vs equipment type:** Is “instrument” an instance (LCMS-1) or a type (Agilent 6495)? Prefer **instance or named source** for CRO (“Eurofins metals export”); types can be a later field.  
2. **One parser per analysis×source or many?** Allow multiple named parsers (versions / plate vs list formats); default flag optional.  
3. **Who may edit parsers?** `config:edit` vs `experiment:manage` vs lab tech.  
4. **Delimiter:** user-selected vs AI-detected vs both (recommend both).  
5. **Relationship to experiment template parsers:** migrate, dual-write, or leave template parsers as legacy.  
6. **Sample identity column:** map to sample_id at import vs leave for later linking.  

## Success metrics

- Time to first successful re-import of the **second** file from same instrument/CRO ≪ first (no AI, no re-mapping).  
- % of promote previews with zero unresolved columns when parser is used.  
- AI used only on **create/edit parser**, not on routine import.

## Success criteria for “done” (MVP)

1. Lab can register Instrument and/or CRO source.  
2. Lab can create a parser for Analysis + that source **manually**.  
3. Run import uses that parser deterministically.  
4. (Optional same epic / next branch) AI drafts parser from example `.txt`/CSV; user saves.  
```
