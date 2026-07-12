# Requirements: Data parsers, instruments/CRO sources, and LimsRun import

**Date:** 2026-07-12  
**Status:** Draft for review (CEO · Security · Architecture · UI)  
**Idea / direction:** [`.docs/ideas/ai-data-import.md`](../ideas/ai-data-import.md)  
**Depends on (shipped):** [run-results](../ideas/run-results.md) promote-on-publish (`analysis_id`, analyte aliases, `ResultPromotionService`)  
**Related:** [manuals/lims-runs.md](../manuals/lims-runs.md), SOP parse (template-centric AI, separate)

## 1. Introduction

### 1.1 Problem

LimsRun import today depends on an **`InstrumentParser` tied to an experiment template**. Real labs and CROs need:

- A **reusable, deterministic** way to turn instrument/CRO result files into `lims_run_data`  
- Scoping by **analysis + instrument** (in-house) or **analysis + CRO** (external)  
- **Lineage on the run** (which source and which parser were used) for troubleshooting  
- Optional **AI only at setup** to draft parser instructions from a sample text file—not on every import  

Promote-on-publish already maps JSONB columns → analytes/results when `analysis_id` is set. That path is stronger when import produces **stable field names** that match analyte names/aliases.

### 1.2 Goal

| Goal | Description |
|------|-------------|
| **G1** | Parsers are **first-class DB configs** (JSONB instructions), not custom code |
| **G2** | Parsers are keyed by **analysis + instrument** or **analysis + CRO source** |
| **G3** | Each LimsRun stores **instrument or CRO**, and **parser_id** (default + override) |
| **G4** | Day-to-day import is **deterministic** (no LLM) |
| **G5** | Optional AI **drafts** `parser_config` from an example text file; human saves |
| **G6** | Import and promote remain two clear stages (file→JSONB, JSONB→Results) |

### 1.3 Out of scope (this requirements set)

- Full equipment management (calibration, IQ/OQ, location, service history)  
- User-uploaded or generated executable parser code  
- AI inventing numeric results or auto-promoting without publish  
- Binary proprietary formats as MVP (XLSX may be a later phase)  
- Replacing SOP→template AI (that path remains template-centric)  
- Changing promote-on-publish product rules (already shipped)

### 1.4 Personas

| Persona | Needs |
|---------|--------|
| Lab manager / admin | Configure instruments, CRO sources, parsers once |
| Lab tech | On a run: set analysis + source, import file, publish |
| CRO workflow user | Same import path at `results_received`; source = CRO |
| Support / troubleshooting | See which parser/source a historical run used |

---

## 2. Definitions

| Term | Meaning |
|------|---------|
| **Instrument** | Light catalog entry for an in-lab data source (named instance or named export stream) |
| **CRO source** | Light catalog entry for an external lab/org export stream |
| **Parser** | DB row: scope (analysis + instrument\|CRO) + **`parser_config` JSONB** instructions |
| **parser_config** | Declarative instructions: delimiter, skip_rows, header, column map (`source_col` → `field_name`), etc. |
| **Generic parse engine** | Application code (`InstrumentDataService` or successor) that applies any `parser_config` to a file |
| **Default parser** | Preferred parser for a given analysis × source (when multiple exist) |
| **Run parser** | `lims_runs.parser_id` — the instructions used (or to be used) for that run’s import |

---

## 3. Functional requirements

### FR-1: Instrument catalog (light)

| ID | Requirement |
|----|-------------|
| FR-1.1 | System shall support CRUD for **instruments** (name, optional vendor/model/description, active flag). |
| FR-1.2 | Instruments are **lab configuration**, not full asset management. Serial/calibration optional later. |
| FR-1.3 | Soft-deactivate (active=false) preferred over hard delete when parsers reference the instrument. |
| FR-1.4 | Permission: configurable lab admin (`config:edit` or dedicated permission—**open**). |

### FR-2: CRO source catalog (light)

| ID | Requirement |
|----|-------------|
| FR-2.1 | System shall support CRUD for **CRO sources** (name, optional description, optional link to client/org, active). |
| FR-2.2 | CRO source is the external analogue of instrument for parser scoping and run lineage. |
| FR-2.3 | Soft-deactivate when referenced by parsers. |
| FR-2.4 | Same permission class as instruments unless product splits later. |

### FR-3: Parser as DB instructions (not code)

| ID | Requirement |
|----|-------------|
| FR-3.1 | A parser shall be stored as a database entity with **`parser_config` JSONB**—no per-source code modules or user scripts in v1. |
| FR-3.2 | `parser_config` shall be interpretable by a **generic** server-side engine (extend existing `InstrumentDataService` / `ParserConfig` schema). |
| FR-3.3 | Minimum instruction support: delimiter (tab/comma/semicolon/etc.), encoding, skip_rows / header_row, column mappings (`source_col`, `field_name`, `data_type`, optional `unit`), optional well_col / sample_col. |
| FR-3.4 | Parser shall be scoped to **exactly one** of: (analysis + instrument) or (analysis + CRO source). |
| FR-3.5 | Multiple named parsers per analysis×source allowed; at most one **`is_default`** per scope pair. |
| FR-3.6 | Admin UI (or analysis-adjacent UI) for manual create/edit/list of parsers without AI. |
| FR-3.7 | Compatibility: existing template-linked parsers remain usable during transition (see FR-7). |

### FR-4: LimsRun tracks source and parser

| ID | Requirement |
|----|-------------|
| FR-4.1 | `lims_runs` shall store optional **`instrument_id`** XOR optional **`cro_source_id`** (product: one source type per run). |
| FR-4.2 | `lims_runs` shall store **`parser_id`** (FK to parser) once resolved or selected. |
| FR-4.3 | When user sets `analysis_id` + instrument **or** cro_source, system shall **default** `parser_id` to the default (or sole) active parser for that pair. |
| FR-4.4 | User may **override** `parser_id` to another active parser; system shall **persist** the override (not re-resolve on every import). |
| FR-4.5 | Import shall use **`run.parser_id`’s `parser_config`**, not a silent re-lookup that ignores stored id. |
| FR-4.6 | If `parser_id` is null at import, system shall either resolve-and-persist once (if unambiguous) or return **4xx** with a clear “select/configure parser” message. |
| FR-4.7 | UI shall show analysis, instrument/CRO, and parser (default vs override) on run overview. |
| FR-4.8 | Stored `parser_id` supports troubleshooting: “which instructions did this run use?” even if catalog defaults change later. |
| FR-4.9 | Optional later (not MVP): snapshot of `parser_config` at first import for bit-for-bit historical freeze. |

### FR-5: Deterministic import on LimsRun

| ID | Requirement |
|----|-------------|
| FR-5.1 | Import remains allowed only in existing statuses (`running`, `results_received`). |
| FR-5.2 | Upload path: text table file → apply `parser_config` → preview optional → write `lims_run_data`. |
| FR-5.3 | No LLM call on import path. |
| FR-5.4 | Validation failures (missing expected fields, bad delimiter, etc.) shall be user-visible and actionable. |
| FR-5.5 | Integration with promote-on-publish unchanged: when `analysis_id` set, publish maps `field_name`/aliases → results. |

### FR-6: Optional AI parser setup (not required for MVP core)

| ID | Requirement |
|----|-------------|
| FR-6.1 | User may upload an **example** text result file (txt/csv/tsv) and select analysis + instrument\|CRO to **draft** a parser. |
| FR-6.2 | AI may propose `parser_config` only; **human must review and save** before the parser is active for import. |
| FR-6.3 | AI shall not invent result values; only structure/mapping suggestions. |
| FR-6.4 | Optional: AI may suggest new analyte aliases (human confirm before write)—see [ai-analyte-resolution](../ideas/ai-analyte-resolution.md). |
| FR-6.5 | Requires configured LLM credentials (e.g. existing Anthropic pattern from SOP parse); degrade with clear error if missing. |
| FR-6.6 | Async job + poll + apply pattern recommended (consistent with `/v1/sop-parse`). |

### FR-7: Compatibility and migration

| ID | Requirement |
|----|-------------|
| FR-7.1 | During transition, if run has no analysis×source parser, import may fall back to template-scoped parser and should **set `parser_id`** when that parser is used. |
| FR-7.2 | SOP parse may continue to create template-linked parsers; product may later offer “save as analysis×source parser.” |
| FR-7.3 | Migration path documented for moving template parsers to analysis×source scope where possible. |

### FR-8: Permissions and audit

| ID | Requirement |
|----|-------------|
| FR-8.1 | Catalog and parser CRUD restricted to lab configuration roles (not lab client users). |
| FR-8.2 | Run field changes (analysis, source, parser) require run edit permissions consistent with existing LimsRun RBAC. |
| FR-8.3 | Import and parser CRUD actions are auditable (who, when, entity ids). |
| FR-8.4 | Client RLS: instruments/CRO sources/parsers are lab-global config unless multi-tenant product later scopes them (default: lab-only, not client-configurable). |

### FR-9: Non-reportable runs

| ID | Requirement |
|----|-------------|
| FR-9.1 | Runs without `analysis_id` may still import if a `parser_id` is available (template fallback or source-only parser if product allows). |
| FR-9.2 | Existing start-run warning for no analysis remains; promote still skipped without analysis. |

---

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Import performance suitable for multi-MB text files; no LLM latency on import. |
| NFR-2 | Parser JSON schema validated on save (reject invalid configs). |
| NFR-3 | Backward compatible import for existing template-parser runs during migration window. |
| NFR-4 | Secrets: LLM keys only on backend env; never sent to client beyond job status. |
| NFR-5 | Clear separation in UX and API: setup vs import vs promote. |

---

## 5. Data model sketch (requirements-level)

```
instruments (id, name, vendor?, model?, description?, active, …)
cro_sources (id, name, description?, client_id?, active, …)

parsers / instrument_parsers (evolved)
  id, name, description, active, is_default
  analysis_id NOT NULL
  instrument_id NULL
  cro_source_id NULL
  -- exactly one of instrument_id / cro_source_id set
  parser_config JSONB NOT NULL
  experiment_template_id NULL  -- legacy optional

lims_runs (additions)
  instrument_id NULL
  cro_source_id NULL
  parser_id NULL
  -- analysis_id already exists
```

---

## 6. Two mapping layers (must remain clear in UX/docs)

```
File column  --parser-->  row_data[field_name]  --promote-->  Result(analyte)
```

| Layer | Config | When |
|-------|--------|------|
| Parser | source_col → field_name | Import |
| Promote | field_name / alias → analyte | Publish if analysis_id set |

---

## 7. Phased delivery (recommended)

| Phase | Scope | AI | LimsRun |
|-------|--------|-----|---------|
| **P0** | Instrument + CRO source catalogs + UI | No | Optional FKs only if cheap |
| **P1** | Parser scoped analysis×source; manual editor; **run instrument/CRO/parser_id**; import uses run parser | No | **Yes** |
| **P2** | AI draft parser from example text file | Yes | Setup only |
| **P3** | Snapshots, richer formats, SOP bridge, alias co-suggest | Optional | Polish |

**Recommended first implementation branch:** P0+P1.  
**Second branch:** P2.

---

## 8. Acceptance criteria (MVP = P0+P1)

1. Lab can create an instrument and a CRO source.  
2. Lab can create a parser for (analysis + instrument) and (analysis + CRO) with JSONB config via UI (no AI required).  
3. On a LimsRun, user can set analysis + instrument or CRO; **default parser_id is applied and stored**.  
4. User can override parser_id; override is stored and used on import.  
5. Import applies stored parser_config deterministically; fails clearly if parser missing/invalid.  
6. Publish + promote still works when analysis_id set (existing behavior).  
7. Historical run shows which instrument/CRO and parser_id were used.

**P2 acceptance (when scheduled):**  
8. From sample text file + analysis + source, AI produces draft parser_config; user must save; import still never calls AI.

---

## 9. Open questions (for reviewers)

**Living log:** [`.docs/open-questions/data-parsers-lims-runs.md`](../open-questions/data-parsers-lims-runs.md)

| # | Question | Suggested default |
|---|----------|-------------------|
| **1** | How is AI/manual `parser_config` kept compatible with the import engine? | **Schema-first:** one Pydantic/JSON Schema; validate all writers; AI emits that schema only; dry-run on sample file |
| 2 | Instrument = named instance vs type? | Named source/instance (or named export stream) |
| 3 | Permission for parser CRUD? | `config:edit` |
| 4 | Allow override to a parser from a different analysis? | No without strong warning / block |
| 5 | Snapshot parser_config on first import? | Defer to P3; FK sufficient for MVP |
| 6 | Non-reportable run without analysis: require template parser only? | Yes for MVP |
| 7 | Multi-tenant: are instruments global to lab only? | Lab-only, not client-owned |

---

## 10. Review packet

| Review | Location | Status |
|--------|----------|--------|
| Requirements (this doc) | [requirements/data-parsers-lims-runs.md](data-parsers-lims-runs.md) | **Ready for review** |
| CEO / product | [ceo-review/data-parsers-lims-runs.md](../ceo-review/data-parsers-lims-runs.md) | Awaiting review |
| Security | [security-review/data-parsers-lims-runs.md](../security-review/data-parsers-lims-runs.md) | Awaiting review |
| Architecture | [architecture-review/data-parsers-lims-runs.md](../architecture-review/data-parsers-lims-runs.md) | Awaiting review |
| UI / UX | [ui-review/data-parsers-lims-runs.md](../ui-review/data-parsers-lims-runs.md) | Awaiting review |
| Idea (exploration) | [ideas/ai-data-import.md](../ideas/ai-data-import.md) | Direction sketch |

**Gate:** Do not start P1 implementation until CEO + Architecture blockers in open questions are **Decided** (or provisional defaults accepted). Security must accept trust boundaries before AI setup (P2) ships.
