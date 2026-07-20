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
| **1** | How do we ensure AI-generated `parser_config` JSONB is **standardized** and works with the **code framework** that runs parsers? | **Open** (proposed approach below) | P2 AI setup; schema freeze for P1 | See **Decision #1 (proposed)** | 2026-07-12 | Architecture | Single schema + validate before save; AI must emit that schema only |
| **10** | How is **user testing** built into parser creation (example files + test files + edge cases)? | **Decided** (CEO confirmed) | P1 framework dry-run; P2 AI edge suggestions | See **Decision #10** | 2026-07-12 | Product / CEO | Results correctness is core LIMS value; multi-file + edges required |
| **11** | Parser scope: analysis-only vs analysis×instrument/CRO? | **Decided** | Whole feature | **Analysis + instrument** or **analysis + CRO** only—not analysis alone | 2026-07-12 | CEO | Formats/names vary by instrument (model/vendor) and CRO; analysis-only is unmaintainable |
| **12** | AI on every import vs setup-only? | **Decided** | Whole feature / P2 | **Setup only.** Instrument/CRO consistency → one parser, many cheap imports | 2026-07-12 | CEO | Minimize AI cost; deterministic day-to-day import |
| **13** | MVP phase cut and priority? | **Decided** | Roadmap | **P0+P1 MVP (high priority)**; P2 after P0+P1; result import is expected (manual entry not OK as primary path) | 2026-07-12 | CEO | Modern LIMS table stakes |
| **14** | Resolve open questions before implementation? | **Decided** | Process | **Yes** — blocking questions resolved before implementation starts | 2026-07-12 | CEO | Aligns with development-process gate |
| 2 | Instrument catalog grain: instance vs model/vendor? | **Decided** | P0 catalog | **Type** (vendor, model) + **instance** (type FK, serial, name). No location until [lab-locations](../ideas/lab-locations.md). Parsers/runs key **instance**. | 2026-07-19 | Product | Format ~ type; lineage ~ instance |
| 3 | Permission for parser / instrument / CRO CRUD? | **Open** | P0–P1 | _Suggested:_ `config:edit` | | Product | Align with other lab config |
| 4 | Allow override to a parser for a **different** analysis than the run? | **Open** | P1 UI/API | _Suggested:_ block (or warn+block) | | Product | Promote uses run.analysis_id |
| 5 | Snapshot `parser_config` on first import? | **Open** / lean defer | P3 | _Suggested:_ FK only for MVP | | Architecture | Lineage via parser_id enough if edits audited |
| 6 | Non-reportable run (no analysis): how is parser required? | **Open** | P1 import | _No template fallback_ (column removed). Options: require analysis for import; or allow source+parser with analysis optional for non-reportable | 2026-07-12 | Product | Template-scoped parsers removed by decision |
| **15** | Keep `experiment_template_id` on parsers? | **Decided** | Schema | **Remove** the column entirely | 2026-07-12 | Product / Architecture | Parsers are analysis×instrument/CRO only |
| 7 | Instruments/CRO catalogs multi-tenant scope? | **Decided** | P0 | **Lab-global only.** No org segregation. Multi-tenant **out of scope** until real multi-org users — see [ideas/multi-tenant.md](../ideas/multi-tenant.md) | 2026-07-18 | Product | Pre-release; single lab deployment |
| 8 | Multiple parsers per analysis×source: default selection rule? | **Open** | P1 | _Suggested:_ `is_default` + require unique default | | Product | |
| 9 | Table naming: keep `instrument_parsers` vs rename? | **Open** | P1 migration | _Suggested:_ keep table, evolve columns | | Architecture | Less migration noise |

---

## Decision #1 (proposed) — Standardize `parser_config` for framework + AI

**Status:** Open · **Proposed default for review** · **Blocks:** P2 (AI); strongly informs P1 schema freeze  
**Date proposed:** 2026-07-12  
**Owner:** Architecture (+ Security for AI path)

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

### Decision record (fill when locked)

| Field | Value |
|-------|--------|
| **Status** | Open / Decided provisional / Decided |
| **Chosen approach** | |
| **schema_version at ship** | |
| **Dry-run required before AI save?** | |
| **Date** | |
| **Owner** | |

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
| 10b | Open / implement default | Caps e.g. 10 files, 10 MB each |
| 10c | Open / lean | All hard-error-free to activate |
| 10d | **Decided** | Accepted edge fixtures stored with parser |

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided** (CEO confirmed) |
| **Example files** | 1+ |
| **Test files** | 1+; engine-run; activate after ≥1 clean pass |
| **File storage** | **Persisted** (not ephemeral) |
| **AI edge suggestions** | Yes on setup (P2); human accept; engine executes |
| **Date** | 2026-07-12 · storage clarified 2026-07-18 |

---

## Decision #11 — Scope parsers by analysis × instrument or analysis × CRO

**Status:** **Decided** · **Date:** 2026-07-12 · **Owner:** CEO  

| Rule | Detail |
|------|--------|
| Lab | Parser keyed by **analysis + instrument** |
| CRO | Parser keyed by **analysis + CRO source** |
| Forbidden | Parser keyed by **analysis alone** (must handle all instruments/CROs → unmaintainable) |
| Run tracking | Store instrument XOR CRO + `parser_id` so import lineage matches scope key |

**Rationale:** File format and column names vary by instrument model/vendor and by CRO data systems.

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

## Phase gate

| Phase | Scope | Open blockers |
|-------|--------|---------------|
| **P0** | Instrument types + instances + CRO catalogs | Q3 |
| **P1** | Parsers analysis×source; run FKs; **persisted** setup files; test harness; import by `parser_id` | Q1 freeze (core fields), Q4, Q6, Q8, Q9; #10b–c polish |
| **P2** | AI draft + edge suggestions | **Q1 locked** + Security P2; **P0+P1 done** |
| **P3+** | Snapshot / richer formats / multi-tenant cutover patterns | Only when there are real production users (Q5 etc.) |

**Pre-release:** phase the **work** (P0→P1→P2). Do **not** invest in production dual-write / switchover plans until multi-tenant production use exists.

**CEO:** Resolve open questions **before implementation starts**. Architecture, security, and UI reviews still outstanding.

---

## Related product locks (from idea/requirements — not re-opened here)

- Parser SoT = DB JSONB instructions; AI setup-only.  
- Run stores `instrument_id` XOR `cro_source_id` + `parser_id` (default + override).  
- Promote remains separate (analysis_id on publish).  
