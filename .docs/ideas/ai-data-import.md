# Idea: Parser setup (analysis + instrument/CRO) with optional AI assist

**Status:** **In review** — **CEO Accept** (high priority, P0+P1 MVP); Security · Architecture · UI outstanding  
**Date:** 2026-07-12  
**Requirements:** [../requirements/data-parsers-lims-runs.md](../requirements/data-parsers-lims-runs.md)  
**Tech sketch:** [../tech-sketch/data-parsers-lims-runs.md](../tech-sketch/data-parsers-lims-runs.md)  
**Open questions:** [../open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md)  
**Related:** [run-results.md](run-results.md), [ai-analyte-resolution.md](ai-analyte-resolution.md), [ai-data-analysis.md](ai-data-analysis.md), [manuals/lims-runs.md](../manuals/lims-runs.md)

## One-liner

**Parsers are first-class, reusable, deterministic configs.** AI is only used (optionally) to **draft** a parser from an example instrument/CRO result file. Day-to-day import never requires AI.

## Product intent (decided sketch)

| Principle | Decision |
|-----------|----------|
| **SoT for import** | Saved **parser config in DB (JSONB instructions)** — not the LLM, not custom code |
| **AI role** | **Setup assistant** only: propose delimiter, header row, skip rows, column map from a sample file |
| **Human role** | Review/edit/save parser; re-run import without AI |
| **Repetition** | Same analysis + same instrument (or same CRO) → **reuse** the parser |
| **Parser source** | **Instrument instance** XOR **CRO** (file shape) |
| **Parser ↔ analyses** | **Many-to-many** — e.g. ICP metals parser → RCRA-8 and RCRA-13 |
| **Run analysis** | What we **promote/store** (subset of what instrument may report) |
| **On each LimsRun** | Track **`instrument_id` or `cro_source_id`**, and **`parser_id`** (default from analysis+source, user may override; store for troubleshooting) |
| **Setup files** | **1+ example** files (derive config) and **1+ test** files (engine dry-run); text tables (tab/comma/etc.) |
| **User testing** | Framework runs same import engine on test files before activate; AI may suggest **edge tests** (e.g. negatives) — human accepts; engine judges |
| **Open questions** | [open-questions/data-parsers-lims-runs.md](../open-questions/data-parsers-lims-runs.md) |
| **Multi-tenant** | **Out of scope** — lab-global catalogs; future: [multi-tenant.md](multi-tenant.md) |
| **Lab locations** | Buildings/rooms + rename client `locations`→`addresses` — [lab-locations.md](lab-locations.md); not in P0/P1 |

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
Instrument / CRO ──► Parser (file shape, all columns)
                         │
                         ├── analysis RCRA-8   (M2M)
                         └── analysis RCRA-13  (M2M)

Run.analysis_id picks which panel to promote; import still uses instrument+parser

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

## How parsers and LimsRuns work together

Two different concerns, one pipeline:

| Concern | Owns | When |
|---------|------|------|
| **Parser** | *How* the file becomes JSONB rows (`lims_run_data`) | Import (running / results_received) |
| **Analysis + promote** | *How* JSONB becomes Tests/Results | Publish (only if `analysis_id` set) |

Today the run has **`analysis_id`** (promote opt-in) and import still resolves a parser via **template** in code. Target: **`experiment_template_id` is removed from parsers**; selection is **analysis + instrument|CRO** only; template remains on the run for protocol/lifecycle/worklist.

### End-to-end flow (lab, standard lifecycle)

```
1. Setup (once, not per run)
   Admin creates Parser(analysis=Metals, instrument=LCMS-1)
   optional AI draft from sample .txt → save parser_config

2. Create LimsRun
   template = metals plate protocol (lifecycle, worklist, …)
   analysis_id = Metals          ← reportable path
   instrument_id = LCMS-1        ← optional on run; helps auto-pick parser
   parser_id = <resolved or explicit>

3. Start run
   require analysis_id (no non-reportable path)
   if analysis set but no parser for analysis×source → warn or block import later

4. Import (running)
   file → InstrumentDataService(parser_config) → lims_run_data rows
   NO AI
   validation: columns match parser field_names (as today, but parser from run not only template)

5. Review / complete

6. Publish
   if analysis_id set → ResultPromotionService
     field_name / aliases → analytes on that analysis
     ensure Test(sample, analysis), write Result(raw, replicate, lims_run_id)
   analysis always set → promote on publish (instrument SoT stays JSONB)
```

### CRO lifecycle (same idea)

```
draft → ordered → running → results_received → complete → published
                              ↑
                         import here (and/or running)

Run: analysis_id + cro_source_id (e.g. Eurofins)
Parser: (analysis, cro_source) — same deterministic import
Promote: unchanged (analysis-gated)
```

CRO lifecycle type still comes from the **template**; CRO **source** is who returned the file and which parser applies.

### What lives on the LimsRun (**decided** — refined 2026-07-19)

| Field / entity | Role |
|----------------|------|
| `experiment_template_id` | Protocol, lifecycle, worklist |
| **`analysis_id`** | **Run is tied to this analysis** (expected results / promote catalog) |
| **`lims_run_imports`** | **Each import** records instrument XOR CRO + **`parser_id`** (run may have many) |
| `lims_run_data.import_id` | Optional link from rows to that import |

**Not:** a single random `parser_id` on the run for all time. Multiple instruments ⇒ multiple parsers over the run’s life.

**Constraints (product — Decision #16):**

- Parser used on an import **must** have `parser.analysis_id = run.analysis_id`.  
- Parser **must** match the instrument or CRO chosen for that import (`parser.instrument_id` / `cro_source_id`).  
- UI lists only parsers for **(run.analysis, selected instrument|CRO)**—default + override **within that pair only**.  
- Instrument/CRO is eligible for the run’s analysis iff a parser exists for that pair (capability via catalog).  
- Store parser on the **import event** for troubleshooting (do not silent re-resolve later for that batch).

**Import UX:**

```
Run analysis = Metals
Import 1: instrument LCMS-1 → default parser (Metals, LCMS-1) → lims_run_imports + data
Import 2: instrument GC-2  → default parser (Metals, GC-2)   → another import event
Publish: promote all data under analysis Metals
```

### How the parser is stored (**not code**)

A parser is a **DB row of instructions**, not deployed code or a plugin.

```
instrument_parsers (evolve name if needed: data_parsers)
├── id, name, description, active
├── analysis_id          FK  — scope
├── instrument_id        FK nullable  — lab path
├── cro_source_id        FK nullable  — CRO path
├── is_default           bool  — default among siblings for same analysis×source
├── parser_config        JSONB  ← THE INSTRUCTIONS
├── created_by / modified_at / …
```

**`parser_config` is declarative config** read by the shared `InstrumentDataService` (generic engine already in the app):

| Instruction area | Examples in JSONB |
|------------------|-------------------|
| File shape | `delimiter`, `encoding`, `skip_rows`, `header_row` |
| Identity columns | `well_col`, `sample_col` |
| Column map | `columns[]`: `source_col` → `field_name`, `data_type`, `unit` |
| Future | date formats, null tokens, multi-line headers — still data, not code |

```
┌─────────────────────┐     read config      ┌──────────────────────────┐
│  parsers table      │ ──────────────────►  │ InstrumentDataService    │
│  parser_config JSONB│                      │ (generic Python engine)  │
└─────────────────────┘                      └────────────┬─────────────┘
                                                          │ apply to file
                                                          ▼
                                                 lims_run_data rows
```

- **No** per-instrument Python modules in v1.  
- **No** user-uploaded scripts.  
- AI (optional setup) only **fills JSONB**; after save, import never calls the LLM.  
- Same pattern as today: `InstrumentParser.parser_config` already is JSONB — we re-key/scope the row and point the run at it.

**Why store `parser_id` on the run if config is in the parser table?**

| Store | Purpose |
|-------|---------|
| Catalog parser row | Reusable definition for many runs |
| `lims_runs.parser_id` | **Lineage**: this run used *this* definition (override or default) |
| Optional import-time snapshot | Freeze config if catalog parser is later edited (P3+) |

Editing a catalog parser affects **future** imports / runs that re-select default; past runs keep pointing at the same row (and optionally a snapshot if we add it).

### Two mapping layers (do not conflate)

```
File column "Pb (ug/L)"
    │  parser maps source_col → field_name
    ▼
row_data["Pb_ug_L"] = "12.3"          ← lims_run_data (import)
    │  promote matches field_name / alias → analyte
    ▼
Result(analyte=Lead, raw_result="12.3")  ← published structure
```

| Layer | Config | Best practice |
|-------|--------|----------------|
| **Parser** | `source_col` → `field_name` | Prefer `field_name` = analyte name or **stable alias** you will maintain |
| **Promote** | `field_name` → analyte (name/alias) | Uses analysis’s analytes + `analyte_aliases` |

Ideal setup: parser emits field names that already resolve on promote (zero unresolved columns). AI setup can suggest both parser map **and** alias adds (alias apply remains human-confirmed).

### UI sketch (run detail)

1. **Overview:** Analysis (shipped) + Instrument **or** CRO source + resolved Parser (read-only chip / change link).  
2. **Data tab / Import:** Upload file → apply **run’s** parser → preview rows → commit.  
3. **Publish:** existing promotion preview (creates/updates/conflicts).  

Parser **create/edit** lives under Admin (or Analysis detail), not reinvented on every run — run only **selects**.

### Compatibility with template parsers

| Decision | Behavior |
|----------|----------|
| **DB** | **DROP** `instrument_parsers.experiment_template_id` |
| **Import** | No fallback to template |
| **SOP parse** | Must stop creating template-scoped parsers; use analysis×source setup (or protocol-only) |
| **Template on run** | Still required for lifecycle/protocol |

### Branch fit (with LimsRun)

| Phase | Includes LimsRun touch? |
|-------|-------------------------|
| P0 catalog (instrument/CRO) | Minimal (entities only) |
| P1 parser + import use | **Yes** — resolve parser on import; optional FKs on run |
| P2 AI draft | Setup UI only; runs unchanged |
| P3 auto-select polish | `instrument_id`/`cro_source_id` on run, UI |

---

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
  parser_config JSONB,  -- no experiment_template_id
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
5. ~~Relationship to experiment template parsers~~ — **Decided: drop template FK; migrate or delete old rows.**
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
