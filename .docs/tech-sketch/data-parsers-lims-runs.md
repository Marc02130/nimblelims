# Tech sketch: Data parsers, instruments/CRO, LimsRun import

**Date:** 2026-07-12  
**Status:** Ready for architecture / UI / security / CEO review  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem (technical)

| Today | Gap |
|-------|-----|
| `instrument_parsers.experiment_template_id` required | Parsers not keyed by analysis × instrument/CRO |
| Import resolves parser only via template | Run does not store source or parser used |
| `ParserConfig` is minimal; engine hardcodes UTF-8 / csv defaults | Need explicit delimiter/encoding in schema for real files |
| SOP AI creates template-centric parser | Need setup path: examples + tests + optional AI draft of same schema |
| No harness | Need multi-file dry-run before activate |

## 2. Goals / non-goals (technical)

**Goals**

- Single **ParserConfig** contract for DB, engine, UI, AI  
- Generic **parse engine** only (no user code)  
- Catalogs: instruments, cro_sources  
- Parsers scoped analysis + (instrument XOR cro_source)  
- LimsRun: `instrument_id` | `cro_source_id`, `parser_id` (default + override, stored)  
- Setup: 1+ examples, 1+ tests; engine judges; optional AI edges (P2)  
- Production import: deterministic, no LLM  

**Non-goals**

- Equipment CMMS, executable parsers, XLSX v1, changing promote rules  

## 3. Component diagram

```
┌─────────────┐  ┌──────────────┐
│ instruments │  │ cro_sources  │
└──────┬──────┘  └──────┬───────┘
       │                │
       └────────┬───────┘
                ▼
┌───────────────────────────────────┐
│ data_parsers (evolve instrument_  │
│   parsers)                        │
│  analysis_id + instrument|cro     │
│  parser_config JSONB              │
│  is_default, active               │
└───────────────┬───────────────────┘
                │ parser_id (stored)
                ▼
┌───────────────────────────────────┐     ┌─────────────────────────┐
│ lims_runs                         │────►│ ParserEngine            │
│  analysis_id (exists)             │     │ (extend InstrumentData  │
│  instrument_id | cro_source_id    │     │  Service)               │
│  parser_id                        │     │  parse(bytes, config)   │
└───────────────────────────────────┘     └───────────┬─────────────┘
                                                      │
                                                      ▼
                                              lims_run_data
                                                      │
                                              publish promote
                                              (existing)
```

**Setup path (not production import):**

```
ParserSetupService
  ├── validate(ParserConfig)
  ├── run_tests(config, test_files[]) → Report
  ├── (P2) draft_config(example_files[], analysis) → AI → validate
  └── (P2) suggest_edge_fixtures(stats) → AI → human accept → run_tests
```

## 4. Data model

> **Authoritative schema delta for architecture / migrations:**  
> [`.docs/schema-changes/data-parsers-lims-runs.md`](../schema-changes/data-parsers-lims-runs.md)  
> Sections below are a summary; if they disagree with that file, **schema-changes wins**—update both.

### 4.1 New tables

```sql
-- Light instrument catalog (lab)
instruments (
  id UUID PK,
  name TEXT NOT NULL UNIQUE,  -- or unique(active) policy TBD
  vendor TEXT NULL,
  model TEXT NULL,
  description TEXT NULL,
  active BOOLEAN NOT NULL DEFAULT true,
  created_at, created_by, modified_at, modified_by
);

-- Light CRO / external export source
cro_sources (
  id UUID PK,
  name TEXT NOT NULL UNIQUE,
  description TEXT NULL,
  client_id UUID NULL REFERENCES clients(id),  -- optional org link
  active BOOLEAN NOT NULL DEFAULT true,
  created_at, created_by, modified_at, modified_by
);
```

### 4.2 Evolve `instrument_parsers` (keep table name for migration ease)

```sql
ALTER instrument_parsers:
  experiment_template_id  NULLABLE  -- was NOT NULL; legacy rows keep value
  analysis_id             UUID NULL REFERENCES analyses(id)
  instrument_id           UUID NULL REFERENCES instruments(id)
  cro_source_id           UUID NULL REFERENCES cro_sources(id)
  is_default              BOOLEAN NOT NULL DEFAULT false
  active                  BOOLEAN NOT NULL DEFAULT true
  -- parser_config JSONB already exists
  -- name, description already exist

CHECK: (instrument_id IS NOT NULL) <> (cro_source_id IS NOT NULL)
       OR (both null AND experiment_template_id IS NOT NULL)  -- legacy only

-- Partial unique: at most one default per analysis×source
UNIQUE INDEX uq_parser_default_instrument
  ON instrument_parsers (analysis_id, instrument_id)
  WHERE is_default AND active AND instrument_id IS NOT NULL;

UNIQUE INDEX uq_parser_default_cro
  ON instrument_parsers (analysis_id, cro_source_id)
  WHERE is_default AND active AND cro_source_id IS NOT NULL;
```

**New (analysis-scoped) rows:** `analysis_id` set + exactly one of instrument/cro.  
**Legacy rows:** `experiment_template_id` set; analysis/instrument/cro null until migrated.

### 4.3 LimsRun columns

```sql
lims_runs:
  instrument_id  UUID NULL REFERENCES instruments(id) ON DELETE SET NULL
  cro_source_id  UUID NULL REFERENCES cro_sources(id) ON DELETE SET NULL
  parser_id      UUID NULL REFERENCES instrument_parsers(id) ON DELETE SET NULL

CHECK: NOT (instrument_id IS NOT NULL AND cro_source_id IS NOT NULL)
```

`analysis_id` already present.

### 4.4 Setup artifacts (P1 ephemeral or light persistence)

**Provisional:** session/API-held uploads during wizard; optional later table:

```sql
parser_setup_files (
  id, parser_id NULL,  -- null until parser saved
  role  TEXT CHECK (role IN ('example', 'test', 'edge_fixture')),
  filename, content_type, size_bytes,
  storage_ref or bytea,  -- prefer object storage / limited bytea
  created_by, created_at
);
```

P1 can use **in-request multipart** for dry-run without permanent storage (open Q10a).

## 5. ParserConfig contract (schema-first)

### 5.1 Pydantic model (target v1)

Extend existing `ParserConfig` / `ParserColumn` with `extra='forbid'`:

```python
class ParserColumn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_col: str
    field_name: str
    data_type: Literal['string', 'float', 'integer', 'boolean'] = 'string'
    unit: Optional[str] = None

class ParserConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1'] = '1'
    delimiter: Literal[',', '\t', ';', '|'] = ','
    encoding: str = 'utf-8'  # allow utf-8-sig
    skip_rows: int = Field(0, ge=0)
    header_row: int = Field(0, ge=0)  # relative semantics: document clearly
    columns: List[ParserColumn] = Field(min_length=1)
    well_col: Optional[str] = None
    sample_col: Optional[str] = None
```

**Engine must implement every field** in this model (extend `InstrumentDataService` for delimiter/encoding; today skip_rows + columns + well_col only).

JSON Schema derived for AI prompts and optional FE validation.

### 5.2 Validation gates

| Path | Validate |
|------|----------|
| POST/PATCH parser | `ParserConfig.model_validate` → 422 |
| Import | re-validate stored config on load |
| Setup dry-run | validate then `engine.parse` each test file |
| AI draft | validate (+ one repair retry) then optional dry-run |

### 5.3 Parse engine API

```python
class ParseReport:
    ok: bool
    hard_errors: list[str]
    warnings: list[str]
    row_count: int
    preview_rows: list[dict]  # capped

class ParserEngine:
    def parse(self, file_bytes: bytes, config: ParserConfig, *, max_rows: int | None) -> ParseReport
    def run_test_suite(self, config: ParserConfig, files: list[tuple[str, bytes]]) -> list[FileReport]
```

Import path: `parse` → bulk insert `lims_run_data` (existing).  
Setup path: `run_test_suite` only—no DB import.

## 6. Runtime flows

### 6.1 Default / override parser on run

```
set analysis_id + instrument_id (or cro_source_id)
  → resolve default parser (is_default or sole active for pair)
  → SET lims_runs.parser_id
user override: user PATCH parser_id → store; do not re-resolve on import

import:
  require parser_id (or resolve-once-and-persist if null and unambiguous)
  config = load(parser_id).parser_config
  engine.parse(file) → lims_run_data
```

### 6.2 Import resolution order

1. `run.parser_id` if set  
2. Else default for `(analysis_id, instrument|cro)` → persist  
3. Else legacy template parser for `experiment_template_id` → persist id if found  
4. Else 400  

### 6.3 Parser setup wizard (P1 without AI)

1. Choose analysis + instrument|CRO + name  
2. Edit config form (or paste JSON validated)  
3. Upload example file(s) ≥1 (optional for pure manual map; recommended)  
4. Upload test file(s) ≥1  
5. Run tests → report  
6. Activate if ≥1 test with zero hard errors (Decision #10 provisional)  
7. Save parser row  

### 6.4 AI setup (P2)

1. Examples → AI returns **only** ParserConfig JSON (schema in prompt)  
2. Validate → repair once → fail job if still invalid  
3. Dry-run examples as smoke (optional)  
4. AI suggests edge fixtures from column stats → user accept subset  
5. Run full test suite including accepted edges  
6. User saves  

**Production import never calls AI.**

### 6.5 Promote (unchanged)

`field_name` in row_data → analyte name/alias on `run.analysis_id` at publish.

**Design note:** setup UI should encourage `field_name` aligned with analyte names/aliases.

## 7. API sketch (v1)

| Method | Path | Notes |
|--------|------|-------|
| CRUD | `/v1/instruments` | config permission |
| CRUD | `/v1/cro-sources` | config permission |
| CRUD | `/v1/data-parsers` or `/v1/instrument-parsers` | filter by analysis, instrument, cro |
| POST | `/v1/data-parsers/validate-config` | body: parser_config |
| POST | `/v1/data-parsers/test` | multipart: config + test files → reports |
| POST | `/v1/data-parsers/draft` | P2 AI; examples multipart |
| POST | `/v1/data-parsers/suggest-edges` | P2 AI; returns fixtures not pass/fail |
| PATCH | `/v1/lims-runs/{id}` | analysis_id, instrument_id, cro_source_id, parser_id |
| POST | `/v1/lims-runs/{id}/import` | use run.parser_id config (file upload path may already exist partially) |

Exact path naming: prefer evolving existing parser routes if any; otherwise `/v1/data-parsers`.

Permissions (provisional): catalog/parser CRUD = `config:edit`; run fields = existing run edit; import = existing run import; AI = same as parser CRUD + server key.

## 8. UI surfaces (for UI review)

| Surface | Behavior |
|---------|----------|
| Admin Instruments | Fill-height DataGrid CRUD |
| Admin CRO sources | Same |
| Admin / Analysis Parsers | List by analysis; editor; example/test upload; test results panel; Activate |
| LimsRun Overview | Analysis + Instrument XOR CRO + Parser chip (default/override) |
| LimsRun Import | File → engine with stored parser_id; errors plain language |

## 9. Migration plan

1. Add `instruments`, `cro_sources`.  
2. Add nullable columns on `instrument_parsers` + CHECKs/indexes; make `experiment_template_id` nullable.  
3. Backfill: leave legacy template parsers as-is.  
4. Add lims_runs FKs.  
5. Change import resolution (new path first, legacy fallback).  
6. Optional data migration: copy template parser → analysis×source when mapping known.  

## 10. Phase mapping

| Phase | Deliver |
|-------|---------|
| **P0** | `instruments`, `cro_sources` models/API/UI |
| **P1** | Parser scope columns; ParserConfig v1 + engine delimiter/encoding; setup test harness (multi-file); lims_runs FKs; import by parser_id; default/override |
| **P2** | AI draft + edge suggestions (async jobs); still validate+engine |
| **P3** | Config snapshot on import; XLSX; permanent setup file storage; SOP bridge |

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Schema/engine drift | Single Pydantic model; extra=forbid; tests for engine fields |
| AI invalid JSON | Schema in prompt; validate; one repair; dry-run |
| Wrong promote mapping | Encourage field_name = analyte; setup report unresolved vs analysis analytes |
| Large files | Size limits; max_rows on preview; async AI only |
| Legacy template parsers | Explicit fallback + persist parser_id |

## 12. Open technical items → open-questions doc

- Q1 lock (schema + AI contract)  
- Q10a–d (file retention, limits, activate rule)  
- Permission string (Q3)  
- Path naming for APIs  

## 13. Success metrics (technical)

- Import path has zero LLM dependencies in call graph  
- 100% of saved configs pass `ParserConfig` validation in CI fixtures  
- Setup test suite catches missing-column configs before activate  
