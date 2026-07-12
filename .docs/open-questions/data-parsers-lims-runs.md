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
| **10** | How is **user testing** built into parser creation (example files + test files + edge cases)? | **Decided (provisional)** | P1 framework dry-run; P2 AI edge suggestions | See **Decision #10** | 2026-07-12 | Product | Setup quality gate before parser is trusted for production imports |
| 2 | Instrument = named instance vs type? | **Open** | P0 catalog | _Suggested:_ named source/instance (or named export stream) | | Product | CRO exports are streams more than asset types |
| 3 | Permission for parser / instrument / CRO CRUD? | **Open** | P0–P1 | _Suggested:_ `config:edit` | | Product | Align with other lab config |
| 4 | Allow override to a parser for a **different** analysis than the run? | **Open** | P1 UI/API | _Suggested:_ block (or warn+block) | | Product | Promote uses run.analysis_id |
| 5 | Snapshot `parser_config` on first import? | **Open** / lean defer | P3 | _Suggested:_ FK only for MVP | | Architecture | Lineage via parser_id enough if edits audited |
| 6 | Non-reportable run (no analysis): how is parser required? | **Open** | P1 import | _Suggested:_ template parser fallback only | | Product | Matches today |
| 7 | Instruments/CRO catalogs multi-tenant scope? | **Open** | P0 | _Suggested:_ lab-global, not client-owned | | Product / Security | Config not client portal |
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

**Status:** **Decided (provisional)** · **Date:** 2026-07-12 · **Owner:** Product  
**Blocks:** P1 (engine dry-run harness); P2 (AI edge-test suggestions)

### Intent

Creating/editing a parser is not only “upload one sample and hope.” The framework must support **guided validation** so the lab trusts the config before it is used on real LimsRuns.

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

### Still open under #10

| Sub-Q | Suggested default |
|-------|-------------------|
| 10a | Retain uploaded files in DB vs ephemeral session only? | Ephemeral + optional attach to parser for re-run |
| 10b | Max files / max size? | e.g. 10 files, 10 MB each |
| 10c | Must all tests pass to activate, or majority? | All hard-error-free |
| 10d | Synthetic edge fixtures stored as blobs or generated on the fly? | Store accepted fixtures with parser |

### Decision record

| Field | Value |
|-------|--------|
| **Status** | **Decided (provisional)** |
| **Example files** | 1+ |
| **Test files** | 1+; engine-run; activate after ≥1 clean pass (provisional) |
| **AI edge suggestions** | Yes on setup (P2); human accept; engine executes |
| **Date** | 2026-07-12 |

---

## Phase gate

| Phase | Scope | Open blockers |
|-------|--------|---------------|
| **P0** | Instrument + CRO catalogs | Q2, Q3, Q7 |
| **P1** | Parser scoped analysis×source; run FKs; import by `parser_id`; **example+test file dry-run harness** | Q1 schema freeze (core fields), Q4, Q6, Q8, Q9; **#10a–c** for product polish |
| **P2** | AI draft config + **AI edge-test suggestions** | **Q1 fully locked** + Security P2 + #10d |
| **P3** | Snapshot, formats, SOP bridge | Q5 |

---

## Related product locks (from idea/requirements — not re-opened here)

- Parser SoT = DB JSONB instructions; AI setup-only.  
- Run stores `instrument_id` XOR `cro_source_id` + `parser_id` (default + override).  
- Promote remains separate (analysis_id on publish).  
