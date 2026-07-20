# Open Questions — Data parsers + LimsRun source/parser lineage

**Status:** Living decision log  
**Requirements:** [`.docs/requirements/data-parsers-lims-runs.md`](../requirements/data-parsers-lims-runs.md)  
**Idea:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)  
**Reviews:** [CEO](../ceo-review/data-parsers-lims-runs.md) · [Security](../security-review/data-parsers-lims-runs.md) · [Architecture](../architecture-review/data-parsers-lims-runs.md) · [UI](../ui-review/data-parsers-lims-runs.md)

## Gate rule

Do not implement a phase until questions that **block** that phase are **Decided** (or **Decided provisional** with a written default).

| Status | Meaning |
|--------|---------|
| **Open** | Blocks related work |
| **Decided (provisional)** | Ship temporary rule; revisit before expanding scope |
| **Decided** | Locked |
| **Deferred** | Out of scope for named phase |

---

## Questions

| # | Question | Status | Blocks | Decision | Date | Owner | Rationale |
|---|----------|--------|--------|----------|------|-------|-----------|
| **1** | How do we ensure AI-generated `parser_config` JSONB is **standardized** and works with the **code framework** that runs parsers? | **Decided** | P1 schema freeze; P2 AI | See **Decision #1** — schema-first proposal **accepted** | 2026-07-19 | Product + Architecture | Single schema + validate before save; AI emits that schema only |
| **10** | How is **user testing** built into parser creation (example files + test files + edge cases)? | **Decided** (CEO confirmed) | P1 framework dry-run; P2 AI edge suggestions | See **Decision #10** | 2026-07-12 | Product / CEO | Results correctness is core LIMS value; multi-file + edges required |
| **11** | Parser scope: analysis-only vs analysis×instrument/CRO? | **Decided** (refined #17) | Whole feature | Parser keyed by **instrument XOR CRO**; **M2M to analyses** (not analysis-only, not single analysis FK on parser) | 2026-07-12 / 19 | CEO + Product | Format ~ instrument; one ICP file can serve RCRA-8 and RCRA-13 |
| **17** | Parser↔analysis cardinality? | **Decided** | Schema P1 | **Many-to-many `parser_analyses`** | 2026-07-19 | Product | Metals ICP imports all metals; run analysis selects which analytes to promote/store as results |
| **12** | AI on every import vs setup-only? | **Decided** | Whole feature / P2 | **Setup only.** Instrument/CRO consistency → one parser, many cheap imports | 2026-07-12 | CEO | Minimize AI cost; deterministic day-to-day import |
| **13** | MVP phase cut and priority? | **Decided** | Roadmap | **P0+P1 MVP (high priority)**; P2 after P0+P1; result import is expected (manual entry not OK as primary path) | 2026-07-12 | CEO | Modern LIMS table stakes |
| **14** | Resolve open questions before implementation? | **Decided** | Process | **Yes** — blocking questions resolved before implementation starts | 2026-07-12 | CEO | Aligns with development-process gate |
| 2 | Instrument catalog grain: instance vs model/vendor? | **Decided** | P0 catalog | **Type** (vendor, model) + **instance** (type FK, serial, name). No location until [lab-locations](../ideas/lab-locations.md). Parsers/runs key **instance**. | 2026-07-19 | Product | Format ~ type; lineage ~ instance |
| 3 | Permission for parser / instrument / CRO CRUD? | **Decided** | P0–P1 | **`config:edit`** | 2026-07-19 | Product | Acceptable; aligns with other lab config |
| 4 | Allow override to a parser for a **different** analysis than the run? | **Decided** | P1 UI/API | **Block** — parser must be linked to `run.analysis_id` via `parser_analyses` | 2026-07-19 | Product | Import validity |
| 5 | Snapshot `parser_config` on import vs versioning? | **Decided** | P1 schema + admin UX | **No JSON snapshot.** Versioned parser rows + `active`; import stores version `parser_id` | 2026-07-19 | Product | See **Decision #5** |
| 6 | Non-reportable run (no analysis) / method-dev path? | **Decided** | All run paths | **No non-reportable runs.** `analysis_id` **required** on every run (create/start/import/publish). Method-dev deferred to [orders-and-projects](../ideas/orders-and-projects.md) | 2026-07-19 | Product | See **Decision #6**; aligns [run-results #6](run-results.md) |
| **15** | Keep `experiment_template_id` on parsers? | **Decided** | Schema | **Remove** the column entirely | 2026-07-12 | Product / Architecture | Parsers are analysis×instrument/CRO only |
| **16** | Run analysis + multi instrument/parser rules? | **Decided** | P1 import/schema | See **Decision #16** | 2026-07-19 | Product | Run tied to analysis; multiple instruments/parsers allowed; each must match analysis + that instrument/CRO |
| 7 | Instruments/CRO catalogs multi-tenant scope? | **Decided** | P0 | **Lab-global only.** No org segregation. Multi-tenant **out of scope** until real multi-org users — see [ideas/multi-tenant.md](../ideas/multi-tenant.md) | 2026-07-18 | Product | Pre-release; single lab deployment |
| 8 | Multiple parsers per analysis×source: default selection rule? | **Decided (provisional)** | P1 | `parser_analyses.is_default` for that analysis; at most one default per (analysis, instrument\|cro) among linked parsers | 2026-07-19 | Product | |
| 9 | Table naming: keep `instrument_parsers` vs rename? | **Decided** | P1 migration | **Rename → `data_parsers`** (generic; instrument + CRO). API/UI: “Data parsers” | 2026-07-19 | Product | See **Decision #9** |

---

## Decision #1 — Standardize `parser_config` for framework + AI

**Status:** **Decided** · **Date:** 2026-07-19 · **Owner:** Product (+ Architecture implementation)  
**Blocks:** None remaining for product — implement per approach below

### Problem

- Runtime import is **code**: a generic engine (today `InstrumentDataService` + Pydantic `ParserConfig`) reads `parser_config` JSONB and applies it to a file.
- AI (and humans) also **write** that JSONB.
- If AI emits free-form or drifting shapes, import fails, security surface grows, and promote field names become unpredictable.

**Requirement:** one **canonical schema** is the contract for (1) DB storage, (2) engine, (3) admin UI, (4) AI draft.

### Proposed approach: schema-first, validate always, AI constrained

```
                    ┌─────────────────────────────┐
                    │  Canonical ParserConfig     │
                    │  (versioned JSON Schema +   │
                    │   Pydantic model in code)   │
                    └─────────────┬───────────────┘
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                      ▼
    Admin UI form          AI draft job            Import engine
    (structured edit)      (prompt + schema)       (InstrumentDataService)
           │                      │                      │
           └──────────► validate ─┴──► reject if invalid ──► only then save / run
```

#### 1. Single source of truth for the instruction language

| Artifact | Role |
|----------|------|
| **Pydantic `ParserConfig`** (extend existing in `flexible_experiment.py`) | Runtime validation in Python; import + API |
| **JSON Schema** generated from (or kept in sync with) that model | Publish to docs; embed in AI system prompt; optional frontend form validation |
| **`schema_version` field** inside `parser_config` (e.g. `"1"`) | Migrations when engine gains features |

**Do not** invent a second “AI-only” shape. AI must emit the **same** object the engine already accepts.

Today’s core (as-is engine):

```json
{
  "schema_version": "1",
  "delimiter": ",",
  "encoding": "utf-8",
  "skip_rows": 0,
  "columns": [
    {
      "source_col": "Well",
      "field_name": "well_position",
      "data_type": "string",
      "unit": null
    }
  ],
  "well_col": "Well",
  "sample_col": null
}
```

Note: engine currently hardcodes some behavior (e.g. UTF-8, csv.reader defaults). **P1 should extend `ParserConfig` + engine together** for any new keys (`delimiter`, etc.)—no orphan JSON keys the code ignores.

#### 2. Validation gate (mandatory, all writers)

| Writer | Gate |
|--------|------|
| Manual API/UI save | `ParserConfig.model_validate(body)` → **422** on failure |
| AI draft | Validate model; if invalid, **retry once** with validation errors in prompt, then fail job |
| AI “apply” / user save of draft | Same validate as manual |
| Import | Re-validate stored config on load (catch DB drift / old bad rows) |

Optional: **dry-run** against the sample file after validate—engine runs `parse(sample_bytes, max_rows=N)`; surface row errors before save. Strongly recommended for AI apply.

#### 3. Constrain the AI (P2)

| Technique | Detail |
|-----------|--------|
| **System prompt** | “Return ONLY JSON matching this JSON Schema: …” (full schema text or `$defs`) |
| **Few-shot** | 1–2 valid example configs for tab- and comma-delimited files |
| **Structured output** | Prefer provider JSON mode / tool schema if available (Anthropic structured outputs) |
| **Post-process** | Strip markdown fences; parse JSON; validate; never `eval` |
| **Allow-list** | `data_type` ∈ {string, float, integer, boolean}; reject unknown keys (Pydantic `extra='forbid'`) |
| **Context** | Pass analysis analyte names/aliases so `field_name` suggestions align with promote |

#### 4. Versioning and evolution

| Rule | Detail |
|------|--------|
| Bump `schema_version` when engine semantics change | e.g. v1 → v2 adds `null_tokens` |
| Engine supports N and N-1 versions or migrates on read | Avoid breaking historical `parser_id` rows |
| AI always asked for **latest** schema_version | |
| Feature flags | New keys ignored only during dual-read migration—not as permanent silent ignore |

#### 5. What we explicitly will **not** do

- Free-form natural language stored as “parser”  
- Executable snippets (JS/Python) in JSONB  
- AI-invented instruction keys the engine does not implement  
- Trust AI output without server-side validation  

### Success criteria for Decision #1

1. Any saved parser passes `ParserConfig` validation.  
2. Import never runs unvalidated config.  
3. AI draft failure rate due to schema mismatch is low; dry-run failures are user-visible.  
4. Adding a new instruction requires: model + engine + schema_version + AI prompt update (checklist).

### Alternatives considered

| Alt | Why weaker |
|-----|------------|
| Free JSON, “best effort” engine | Silent wrong imports; hard to debug |
| Separate AI schema + mapper | Two contracts drift |
| Code-gen parsers per file | Ops nightmare; security |

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided** |
| **Chosen approach** | Schema-first proposal as written above (Pydantic + JSON Schema; validate all writers; AI constrained to same schema; no free-form / no code) |
| **schema_version at ship** | `"1"` (extend with engine in P1 as needed) |
| **Dry-run before AI save** | Recommended; engine dry-run on sample after validate (P2) |
| **Date** | Proposed 2026-07-12 · **Accepted 2026-07-19** |
| **Owner** | Product (accept) · Architecture (implement) |

---

## Decision #10 — Parser creation includes multi-file **user testing** in the framework

**Status:** **Decided** (CEO confirmed 2026-07-12) · **Owner:** Product / CEO  
**Blocks:** P1 (engine dry-run harness); P2 (AI edge-test suggestions)

### Intent

Creating/editing a parser is not only “upload one sample and hope.” The framework must support **guided validation** so the lab trusts the config before it is used on real LimsRuns.

**CEO:** Results are why NimbleLIMS exists; multiple tests and edge cases are required for **correct** import—not optional polish.

### Decided rules

| Rule | Detail |
|------|--------|
| **Example files** | User may attach **1 or more** example files used to **derive / refine** `parser_config` (headers, delimiter, skip_rows, column map). |
| **Test files** | User may attach **1 or more** test files used to **validate** a candidate config (must not be required to be the same set as examples). |
| **Engine runs tests** | Framework runs the **same import engine** against each test file with the candidate `parser_config` (schema-validated first—Decision #1). |
| **Pass / fail visible** | Per-file and aggregate results: success, row counts, warnings, hard errors (missing columns, coerce failures, empty parse). |
| **Activate gate (provisional)** | Parser may be marked **ready for production import** only after at least **one** test file passes with zero hard errors (warnings allowed but listed). Soften later if product wants draft parsers for experimental use. |
| **AI edge tests (P2)** | From uploaded data (examples and/or tests), AI may **suggest additional synthetic or derived edge test cases**—e.g. negative values, empty cells, extra columns, missing expected columns, scientific notation, BOM/encoding quirks—expressed as **test file payloads or fixtures**, not as free-form code. |
| **Human owns edges** | User accepts/rejects AI edge suggestions; only accepted fixtures run through the engine. |
| **No AI on production import** | Unchanged: LimsRun import never calls the LLM. |

### Roles of file sets

```
Example file(s)  ──►  propose / refine parser_config  (human and/or AI draft)
                            │
                            ▼
                     validate schema (ParserConfig)
                            │
Test file(s)     ──►  engine.parse(file, config)  ──►  pass/fail report
  + optional AI-suggested edge fixtures
                            │
                     user reviews ──► save / activate parser
```

| Set | Purpose | Min count |
|-----|---------|-----------|
| **Examples** | Teach the shape of the real export | ≥ 1 |
| **Tests** | Prove the config works on held-out or edge data | ≥ 1 for activate (provisional) |

Users may reuse an example as a test, but the product should **encourage** at least one independent test file when available.

### AI-suggested edge tests (detail)

Given column stats from examples/tests (types, min/max, null rate, sample of values), AI may propose fixtures such as:

| Edge class | Example suggestion |
|------------|-------------------|
| Sign / range | Negative numeric where all training positives |
| Empty / null | Blank cell in required-looking column |
| Extra noise | Extra trailing column; junk preamble row |
| Type stress | `"N/A"`, `"<LOD"`, scientific notation |
| Structure | Missing header; wrong delimiter variant |

**Output shape (proposed):** list of `{ name, description, file_content or mutations, expect: pass|warn|fail }` — still run only through the **code engine**, never “AI judges pass/fail” as sole gate.

### Sub-decisions under #10

| Sub-Q | Status | Decision |
|-------|--------|----------|
| 10a | **Decided** | **Persist** examples/tests/edges (`parser_setup_files` in P1)—not ephemeral-only |
| 10b | **Decided** | Caps: **10 files**, **10 MB each** (per role pool or total setup set—implement as max 10 files and max 10 MB per file) |
| 10c | **Decided** | **All** test (and edge) files must be **hard-error-free** to activate a version |
| 10d | **Decided** | Accepted edge fixtures stored with parser |

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided** (CEO confirmed + product polish 2026-07-19) |
| **Example files** | 1+ |
| **Test files** | 1+; engine-run |
| **Activate gate** | **All** tests/edges hard-error-free (**10c**) |
| **File caps** | **10 files**, **10 MB each** (**10b**) |
| **File storage** | **Persisted** (not ephemeral) |
| **AI edge suggestions** | Yes on setup (P2); human accept; engine executes |
| **Date** | 2026-07-12 · storage 2026-07-18 · 10b/10c 2026-07-19 |

---

## Decision #11 / #17 — Parser = instrument|CRO file shape; many analyses via M2M

**Status:** **Decided** · **Updated:** 2026-07-19 · **Owner:** CEO + Product  

| Rule | Detail |
|------|--------|
| **Parser source** | Keyed by **instrument instance** XOR **CRO source** (file format/shape) |
| **Parser ↔ analyses** | **Many-to-many** table `parser_analyses` |
| **Forbidden** | Analysis-only parser (no instrument/CRO); single forced analysis FK that prevents sharing |
| **Example** | Metals ICP parser linked to **RCRA-8** and **RCRA-13**. Instrument may report all metals; **run.analysis_id** chooses which panel is stored/promoted |
| **Run** | One analysis (what we care about for Results); many imports/instruments possible |

**Rationale:** Format varies by instrument/CRO. One instrument output can feed multiple analysis definitions without duplicating parsers.

---

## Decision #12 — AI setup-only (economics)

**Status:** **Decided** · **Date:** 2026-07-12 · **Owner:** CEO  

Instruments and CROs emit **consistent** files. Create parser once (optionally with AI assist in P2); **never** use AI to parse every result file. Minimizes cost and keeps import deterministic.

---

## Decision #13 — MVP and priority

**Status:** **Decided** · **Date:** 2026-07-12 · **Owner:** CEO  

| Item | Decision |
|------|----------|
| MVP | **P0 + P1** |
| P2 | After P0+P1 complete |
| Priority | **High** — result import is expected; primary reliance on manual entry is not acceptable for modern LIMS |

---

## Decision #16 — Run ↔ analysis; multi instrument/parser; no random parsers

**Status:** **Decided** · **Date:** 2026-07-19 · **Owner:** Product  

### Rules

| Rule | Detail |
|------|--------|
| **Run tied to analysis** | Reportable / structured import path: run has **`analysis_id`** (the assay whose results are expected). Promote already uses this. |
| **Multiple instruments** | A single run **may use more than one instrument** (and/or CRO sources) over its life—e.g. different files from different boxes. |
| **Multiple parsers** | Therefore a run may use **more than one parser**—one per import context, not one forever on the run. |
| **Not a random parser** | Every parser used must be valid for **that run’s analysis** and for **the instrument (or CRO) that produced the file**. |

### Validity (enforced in app; preferably DB-checkable where easy)

```
run.analysis_id  = A
import uses instrument I (or CRO C) and parser P

Required:
  EXISTS parser_analyses(parser_id=P, analysis_id=A)
  if lab:  P.instrument_id = I
  if CRO:  P.cro_source_id = C
```

- There is **no** free choice of “any parser in the system.”  
- Capability = active parser for that instrument/CRO **linked** to analysis A via `parser_analyses`.

### Schema implication (see schema-changes)

Single `lims_runs.parser_id` + single `instrument_id` is **not enough** for multi-file multi-instrument lineage.

**Preferred model:**

| Store | Role |
|-------|------|
| `lims_runs.analysis_id` | Assay for the run (required for import of structured results path) |
| **`lims_run_imports`** (or equivalent) | Each import event: instrument XOR cro, `parser_id`, timestamps, user |
| `lims_run_data.import_id` | Optional FK so rows know which import/parser produced them |

Optional UI convenience: “last instrument / last parser” denormalized on the run—not the sole source of truth.

### Import UX sketch

1. Run has analysis set (Metals).  
2. User starts import → picks **instrument** (or CRO) → system offers only parsers for **(Metals, that instrument)** (default + override within that pair only).  
3. Second import may pick a **different** instrument/parser; still must match Metals.  
4. Promote on publish still uses run `analysis_id` + all `lims_run_data` field_names.

---

## Phase gate

| Phase | Scope | Open blockers |
|-------|--------|---------------|
| **P0** | Instrument types + instances + CRO catalogs | **None** (product) — review packets resubmitted |
| **P1** | `data_parsers` + versioning; setup files (10/10MB); all-clean activate; import by version `parser_id` | **None** (product) — Architecture/Security/UI re-accept |
| **P2** | AI draft + edge suggestions | Security P2 accept; **P0+P1 done** |
| **P3+** | Richer formats / multi-tenant cutover patterns | Only when there are real production users |

**Pre-release:** phase the **work** (P0→P1→P2). Do **not** invest in production dual-write / switchover plans until multi-tenant production use exists.

**2026-07-19:** Product open questions closed. Reviews: CEO **Accept**; Architecture / Security / UI **Accept with conditions** — **ready for P0/P1 implementation**.

---

## Decision #5 — Parser versioning + active (no JSON snapshot on import)

**Status:** **Decided** · **Date:** 2026-07-19 · **Owner:** Product  
**Blocks:** P1 schema + parser admin UX + import lineage

### Rejected approach

Do **not** store a copy of `parser_config` JSON on `lims_run_imports` (or the run). No per-import config blob.

### Decided approach

Treat each **saved definition** of a parser as an **immutable version row**. Imports point at a **specific version** via `parser_id`. Lineage = that FK, not a duplicated JSON snapshot.

| Column / concept | Role |
|------------------|------|
| **`id`** | This version’s PK — what `lims_run_imports.parser_id` stores |
| **`version_group_id`** | Stable identity of the logical parser across versions |
| **`version`** | Monotonic int per group (1, 2, 3…) |
| **`active`** | Whether this version is the **current production** definition for the group |
| **`parser_config`** | Instructions for **this version only** (not mutated after save) |

### Rules

1. **Create** first version: `version = 1`, `version_group_id` set (typically = first row’s `id` or a dedicated UUID), user may activate (usually yes for v1).
2. **Any update** to a parser’s definition (config, analysis links, name/source scope as product defines) **does not PATCH in place** — it **inserts a new version row** (`version = max+1` for that group) with the new definition.
3. After save of a new version, UI **prompts: make this version active?**
   - **Yes** → set new row `active = true`; set **all other** rows in the same `version_group_id` to `active = false`.
   - **No** → new version stays inactive (draft/candidate); previous active version remains the one used for default import resolution.
4. **Default selection / capability / pickers** use only **`active = true`** versions (plus other validity: analysis M2M, instrument/CRO match).
5. **Historical imports** keep their stored `parser_id` (specific version). Re-opening that import’s lineage loads **that version’s** `parser_config` — even if a newer version is now active.
6. Inactive versions remain **readable** (audit, re-inspect, optional “activate this older version” which deactivates the current active).
7. Soft-retire a whole logical parser: deactivate the active version without activating another (group has no active version → not offered for new imports).

### Why this instead of snapshot JSON

| Concern | Versioned rows | Import JSON snapshot |
|---------|----------------|----------------------|
| “What instructions ran?” | FK → immutable version row | Blob on every import |
| Edit safety | Old versions untouched | Mutating live row breaks history unless snapshotted |
| Storage | One config per version, shared by many imports | Config duplicated per import |
| Admin UX | Version history + activate prompt | Opaque edit history |

**Not the same as** promote lineage (`results.lims_run_id`) — that is which run produced results.

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided** |
| **Date** | 2026-07-19 |
| **Owner** | Product |
| **Summary** | No import-time `parser_config` snapshot; version + active on parser table; updates create new versions; activate prompt deactivates prior active in the group |

---

## Decision #9 — Rename `instrument_parsers` → `data_parsers`

**Status:** **Decided** · **Date:** 2026-07-19 · **Owner:** Product  
**Blocks:** P1 migration naming

### Decided

| Layer | Name |
|-------|------|
| **Table** | **`data_parsers`** (rename from `instrument_parsers`) |
| **Model / code** | `DataParser` (replace `InstrumentParser`) |
| **API** | `/v1/data-parsers` |
| **UI** | “Data parsers” |

### Why

- Parsers cover **instrument XOR CRO**, not instruments only.  
- Aligns with feature name “data parsers.”  
- Rename cost is low in the same P1 migration that drops `experiment_template_id` and adds versioning.

### Migration note

`RENAME TABLE instrument_parsers TO data_parsers` (or Alembic equivalent); update FKs, RLS policies, indexes, and app code. Pre-release: no dual-name period required.

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided** |
| **Date** | 2026-07-19 |
| **Owner** | Product |
| **Summary** | Generic **`data_parsers`** table/API/UI; retire `instrument_parsers` name |

---

## Decision #6 — No non-reportable runs; method-dev deferred to lab projects

**Status:** **Decided** · **Date:** 2026-07-19 · **Owner:** Product  
**Blocks:** Nothing for P1 special-case import (path removed). Method-dev UX blocked on [orders-and-projects](../ideas/orders-and-projects.md)

### Decided

1. **No non-reportable runs** anywhere in the LimsRun product path.  
2. **`run.analysis_id` is required** from create — not optional for start, import, or publish.  
3. **Do not** keep “continue without analysis”, `acknowledge_no_analysis`, or publish-without-promote.  
4. **Method development / scratch / work-over-time** is **deferred** until **lab projects** ([ideas/orders-and-projects.md](../ideas/orders-and-projects.md)). Still uses a real analysis later—not null.  
5. **Promote on publish** always uses the run’s analysis.

### Rejected

| Approach | Why rejected |
|----------|----------------|
| Run or import with no analysis | Fights parser M2M; ambiguous assay identity |
| “Non-reportable” as first-class run mode | Method-dev needs analysis + lab project later, not a hole |
| Start-run ack to skip analysis | Superseded 2026-07-19 |

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided** |
| **Date** | 2026-07-19 |
| **Owner** | Product |
| **Summary** | Every run has analysis_id; no non-reportable path; method-dev deferred to lab projects |

---

## Related product locks (from idea/requirements — not re-opened here)

- Parser SoT = DB JSONB instructions; AI setup-only.  
- Run tied to analysis; multi-instrument imports; M2M parser↔analyses.  
- Promote remains separate (analysis_id on publish).  
- Permissions: **`config:edit`** for instrument/CRO/parser CRUD.  
- **Parser versions + active** (Decision #5); import stores version `parser_id` only.  
- **No non-reportable runs** (Decision #6); method-dev → [orders-and-projects](../ideas/orders-and-projects.md).  
- Table/API name **`data_parsers`** (Decision #9).  

