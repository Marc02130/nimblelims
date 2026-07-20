# Tech sketch: Data parsers, instruments/CRO, LimsRun import

**Date:** 2026-07-12  
**Status:** **Accepted for implementation** (reviews 2026-07-19)  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Open questions:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)  
**Process:** [`.docs/development-process/README.md`](../development-process/README.md)

## 1. Problem (technical)

| Today | Gap |
|-------|-----|
| `instrument_parsers` (+ template FK) | **Rename → `data_parsers`**; drop template link; instrument XOR CRO + M2M analyses |
| Import resolves parser only via template | Run stores source + `parser_id`; no template fallback |
| `ParserConfig` is minimal; engine hardcodes UTF-8 / csv defaults | Need explicit delimiter/encoding in schema for real files |
| SOP AI creates template-centric parser | Need setup path: examples + tests + optional AI draft of same schema |
| No harness | Need multi-file dry-run before activate |

## 2. Goals / non-goals (technical)

**Goals**

- Single **ParserConfig** contract for DB, engine, UI, AI  
- Generic **parse engine** only (no user code)  
- Catalogs: **instrument_types** + **instruments** (instances), cro_sources  
- Parsers: **instrument XOR cro** + **M2M `parser_analyses`** (one ICP parser → many analyses)  
- Run: **`analysis_id`** (what we promote); imports: source + parser per batch  

- Setup: 1+ examples, 1+ tests; engine judges; optional AI edges (P2)  
- Production import: deterministic, no LLM  

**Non-goals**

- Equipment CMMS, executable parsers, XLSX v1, changing promote rules  
- **Multi-tenant / org segregation** (lab-global config only; see readiness below)

### 2b. Multi-tenant readiness (not implementation)

**Context:** Real multi-org users are not the current target. Full multi-tenant design lives in [ideas/multi-tenant.md](../ideas/multi-tenant.md). Instruments/CRO/parsers are **prepared** so tenancy can be added later without redesigning the import pipeline.

| Principle | Application here |
|-----------|------------------|
| **Ship lab-global** | One deployment = one lab’s catalogs; no org switcher |
| **Additive later** | Future `tenant_id` (or equivalent) + per-tenant unique + RLS—not a second parser engine |
| **Clean ownership chain** | `instrument`/`cro_source` → `parser` → `lims_run.parser_id` stays the resolution story |
| **No fake tenancy** | Do not add null tenant columns or dual code paths in P0–P2 |
| **client_id on CRO** | Optional labeling only; not the multi-tenant security boundary |
| **Security now** | Lab roles manage config; lab **client** users do not edit instruments/parsers |

**Engine/import:** remains deterministic and keyed by run’s stored source + `parser_id`. Tenant filtering, when it exists, should sit **above** resolution (which catalogs are visible), not inside `ParserConfig` JSON.

## 3. Component diagram

```
┌──────────────────┐
│ instrument_types │  vendor, model
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────┐
│ instruments      │     │ cro_sources  │
│ (instance)       │     │              │
│ type_id, serial  │     │              │
└────────┬─────────┘     └──────┬───────┘
         │                      │
         └──────────┬───────────┘
                    ▼
┌───────────────────────────────────┐     ┌──────────────────┐
│ data_parsers (version row)        │────►│ parser_analyses  │
│  version_group + version + active │ M2M │ analysis_id      │
│  instrument|cro; parser_config    │     │ is_default       │
└───────────────┬───────────────────┘     └────────┬─────────┘
                │                                  │
                │  lims_run_imports.parser_id      │
                │  (version PK, no config blob)    │
                ▼                                  ▼
┌───────────────────────────────────┐     run.analysis_id
│ lims_runs.analysis_id             │     (RCRA-8 vs RCRA-13)
│  → promote only that analysis’s   │
│    analytes                       │
└───────────────────────────────────┘
```

Example: ICP parser maps all metals; run analysis RCRA-8 promotes only the eight; same parser usable on a RCRA-13 run.

**No location on instruments** this cycle. Client table `locations` is address CRM—not lab rooms. Future: [ideas/lab-locations.md](../ideas/lab-locations.md).

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
instrument_types (
  id UUID PK,
  name TEXT NOT NULL,           -- display label
  vendor TEXT NULL,
  model TEXT NULL,
  description TEXT NULL,
  active BOOLEAN NOT NULL DEFAULT true,
  created_at, created_by, modified_at, modified_by
);

instruments (  -- instances
  id UUID PK,
  instrument_type_id UUID NOT NULL REFERENCES instrument_types(id),
  name TEXT NOT NULL,           -- lab nickname e.g. LCMS-1
  serial_number TEXT NULL,
  description TEXT NULL,
  active BOOLEAN NOT NULL DEFAULT true,
  -- no location_id (see ideas/lab-locations.md)
  created_at, created_by, modified_at, modified_by
);

cro_sources (
  id UUID PK,
  name TEXT NOT NULL UNIQUE,
  description TEXT NULL,
  client_id UUID NULL REFERENCES clients(id),  -- optional label only
  active BOOLEAN NOT NULL DEFAULT true,
  created_at, created_by, modified_at, modified_by
);
```

### 4.2 Rename + evolve → `data_parsers` (Decision #9)

Each **row** is an **immutable version**. Logical parser = `version_group_id`. No import-time JSON snapshot (Decision #5).

```sql
RENAME instrument_parsers TO data_parsers;

ALTER data_parsers:
  DROP experiment_template_id
  instrument_id      UUID NULL REFERENCES instruments(id)
  cro_source_id      UUID NULL REFERENCES cro_sources(id)
  version_group_id   UUID NOT NULL   -- shared by all versions of this parser
  version            INT  NOT NULL   -- 1, 2, 3… per group
  active             BOOLEAN NOT NULL DEFAULT false
  -- NO analysis_id on parser row
  -- parser_config JSONB immutable after insert (updates → new version row)

CHECK: exactly one of (instrument_id, cro_source_id) is non-null
UNIQUE (version_group_id, version)
UNIQUE (version_group_id) WHERE active   -- partial: at most one active version

parser_analyses (
  parser_id UUID NOT NULL REFERENCES data_parsers,  -- version row
  analysis_id UUID NOT NULL REFERENCES analyses,
  is_default BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (parser_id, analysis_id)
);
-- default uniqueness for (analysis, instrument) among active versions enforced in app
```

**Version lifecycle**

```
Create v1 ──► (optional activate) ──► active for imports
     │
  "Edit" ──► insert v2 (inactive) ──► prompt "Make active?"
                                      ├─ Yes → v2 active, v1 inactive
                                      └─ No  → v1 still active; v2 draft
Import stores parser_id = specific version id forever
```

See [schema-changes](../schema-changes/data-parsers-lims-runs.md).

### 4.3 LimsRun columns

```sql
lims_runs:
  instrument_id  UUID NULL REFERENCES instruments(id) ON DELETE SET NULL
  cro_source_id  UUID NULL REFERENCES cro_sources(id) ON DELETE SET NULL
  parser_id      UUID NULL REFERENCES data_parsers(id) ON DELETE SET NULL

CHECK: NOT (instrument_id IS NOT NULL AND cro_source_id IS NOT NULL)
```

`analysis_id` already present.

### 4.4 Setup artifacts (P1 — **persisted**, not ephemeral)

Examples, tests, and accepted edge fixtures are stored for re-run and audit (pre-release: simple storage is fine).

```sql
parser_setup_files (
  id, parser_id NULL,  -- set when parser saved / linked
  role  TEXT CHECK (role IN ('example', 'test', 'edge_fixture')),
  filename, content_type, size_bytes,
  storage_ref or bytea,
  created_by, created_at
);
```

No dual ephemeral/P1 vs permanent path. See schema-changes for the authoritative table.

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

### 6.1 Run analysis + multi-instrument import (Decision #16)

```
run.analysis_id REQUIRED always (Decision #6 — no non-reportable path; create/start/import/publish)

each import:
  1. require run.analysis_id
  2. user selects instrument XOR cro_source
  3. resolve parser: default for (run.analysis_id, source) or user override
     ONLY among parsers where:
       P.active = true
       EXISTS parser_analyses(P, run.analysis_id)
       P.instrument_id = I  (or cro_source_id = C)
  4. create lims_run_imports(run, source, parser_id=P.id, …)  -- version PK
  5. engine.parse(P.parser_config) → lims_run_data(import_id=…)
  6. never re-resolve; no parser_config snapshot on import
```

**Reject:** parser for another analysis; parser for another instrument; inactive version for default pick.  
**Capability:** instrument shown/usable iff an **active** version exists for `(run.analysis_id, instrument)`.

### 6.2 Import resolution order (per import event)

1. Require `run.analysis_id`  
2. Require instrument XOR cro on this import  
3. `parser_id` override only if it is an **active** version matching analysis + source; else default active for pair  
4. Else 400 — no valid active parser for this analysis × source  
5. Persist **version** `parser_id` on **`lims_run_imports`** only (no config blob)

### 6.3 Parser setup wizard (P1 without AI)

1. Choose instrument|CRO + name (+ multi-select analyses)  
2. Edit config form (or paste JSON validated)  
3. Upload example file(s) ≥1 (optional for pure manual map; recommended)  
4. Upload test file(s) ≥1  
5. Run tests → report  
6. **Save** → inserts version row (`version=1` or `max+1`; config immutable thereafter)  
7. **Prompt: make this version active?** (only if **all** tests/edges hard-error-free — #10c)  
   - Yes → `active=true` on new; deactivate other versions in `version_group_id`  
   - No → leave inactive; prior active (if any) stays  
8. File caps: max **10 files**, **10 MB each** (#10b)

**Edit path:** never PATCH `parser_config` on existing version → always new version.

### 6.4 AI setup (P2)

1. Examples → AI returns **only** ParserConfig JSON (schema in prompt)  
2. Validate → repair once → fail job if still invalid  
3. Dry-run examples as smoke (optional)  
4. AI suggests edge fixtures from column stats → user accept subset  
5. Run full test suite including accepted edges  
6. User saves  

**Production import never calls AI.**

### 6.5 Promote (unchanged rules; filters by run analysis)

`field_name` in row_data → analyte name/alias **on `run.analysis_id` only**.

If ICP import wrote 20 metals into JSONB but run analysis is RCRA-8, promote creates Results only for the eight (and listed) analytes; other columns remain instrument data / unresolved for that analysis.

**Design note:** parser field_names should match catalog analyte names/aliases so promote works across linked analyses.

## 7. API sketch (v1)

| Method | Path | Notes |
|--------|------|-------|
| CRUD | `/v1/instruments` | config permission |
| CRUD | `/v1/cro-sources` | config permission |
| CRUD | `/v1/data-parsers` | list active by default; include version history |
| POST | `/v1/data-parsers` | create v1 |
| POST | `/v1/data-parsers/{version_group_id}/versions` | save new version (body: config + analyses + `activate?: bool`) |
| POST | `/v1/data-parsers/{id}/activate` | activate this version; deactivate others in group |
| POST | `/v1/data-parsers/validate-config` | body: parser_config |
| POST | `/v1/data-parsers/test` | multipart: config + test files → reports |
| POST | `/v1/data-parsers/draft` | P2 AI; examples multipart |
| POST | `/v1/data-parsers/suggest-edges` | P2 AI; returns fixtures not pass/fail |
| PATCH | `/v1/lims-runs/{id}` | analysis_id required before import (Decision #6) |
| POST | `/v1/lims-runs/{id}/import` | multipart: file + instrument_id\|cro_source_id + optional parser_id override → creates import event |
| GET | `/v1/lims-runs/{id}/imports` | import history (source + parser per batch) |

Permissions: catalog/parser CRUD = `config:edit`; run fields = existing run edit; import = existing run import; AI = same as parser CRUD + server key.

## 8. UI surfaces (for UI review)

| Surface | Behavior |
|---------|----------|
| Admin Instruments | Fill-height DataGrid CRUD |
| Admin CRO sources | Same |
| Admin **Data parsers** | List **active** by default; version history; editor; example/test; save → **activate prompt** |
| LimsRun Overview | Analysis + Instrument XOR CRO + Parser chip (name + version) |
| LimsRun Import | File → engine with stored version `parser_id`; history shows version used |

## 9. Migration plan (pre-release — keep simple)

**Do not** plan gradual production cutover, dual-write, or long dual-path import until there are real multi-tenant production users. Chunk by **phase**, not by blue/green switchover.

1. **P0:** `instrument_types`, `instruments` (instances), `cro_sources`.  
2. **P1:** `parser_setup_files`; re-scope parsers + **version_group/version/active**; delete old template-scoped rows OK; **DROP `experiment_template_id`**; import events store version `parser_id`.  
3. SOP parse: stop writing template-scoped parsers.  
4. **P2:** AI only (no schema required beyond existing setup files).

## 10. Phase mapping

| Phase | Deliver |
|-------|---------|
| **P0** | `instruments`, `cro_sources` models/API/UI |
| **P1** | **`data_parsers` rename**; version_group/version/active; ParserConfig v1 + engine; setup tests; import by version `parser_id`; activate prompt |
| **P2** | AI draft + edge suggestions (async jobs); still validate+engine |
| **P3** | XLSX; richer formats; SOP bridge polish |

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Schema/engine drift | Single Pydantic model; extra=forbid; tests for engine fields |
| AI invalid JSON | Schema in prompt; validate; one repair; dry-run |
| Wrong promote mapping | Encourage field_name = analyte; setup report unresolved vs analysis analytes |
| Large files | Size limits; max_rows on preview; async AI only |
| Existing template-scoped parser rows | Migrate or delete before DROP column |

## 12. Open technical items

Product questions **closed** (2026-07-19). Remaining: review re-accept + implement.

| Item | Status |
|------|--------|
| Q1 ParserConfig schema-first | **Decided** |
| #10a–d persist / 10 files · 10 MB / all clean activate / edges stored | **Decided** |
| Q3 `config:edit` · Q9 `data_parsers` · Q5 versioning · Q6 analysis required | **Decided** |
| CEO / UI / Architecture / Security re-review | **Accepted 2026-07-19** (conditions in review docs) |

## 13. Success metrics (technical)

- Import path has zero LLM dependencies in call graph  
- 100% of saved configs pass `ParserConfig` validation in CI fixtures  
- Setup test suite: **all** files hard-error-free before activate  

